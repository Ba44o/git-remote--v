"""
Rhode Jeans — ETL v2
====================
Processa um ou mais exports do TikTok Seller Center e mantém um banco
histórico acumulado com 4 tabelas derivadas:

  raw_imports      → cada linha = 1 creator × 1 período (append-only)
  creators_master  → 1 linha por creator (dados do período mais recente)
  period_summary   → KPIs agregados por período
  sync_ready       → visão atual para o portal (compatibilidade)

Uso:
  python agente_rhode/etl_v2.py <arquivo.xlsx> [arquivo2.xlsx ...]
  python agente_rhode/etl_v2.py --dir dados/creators/exports

Outputs (na raiz do projeto):
  warehouse/raw_imports.csv
  warehouse/creators_master.csv
  warehouse/period_summary.csv
  warehouse/sync_ready.csv
"""

import sys
import re
import unicodedata
import warnings
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, datetime

warnings.filterwarnings("ignore", category=UserWarning)

# ── Constantes ────────────────────────────────────────────────────────────────

WAREHOUSE_DIR = Path("warehouse")

MONETARY_COLS = ["gmv_bruto", "gmv_liquido", "reembolso", "aov", "comissao"]
INT_COLS      = ["pedidos", "videos", "lives"]
STR_COLS      = ["tier", "status_reembolso"]

REQUIRED_COLS = {
    "creator_id":       "",
    "periodo":          "",   # YYYY-MM  detectado do filename
    "periodo_inicio":   "",   # YYYY-MM-DD
    "periodo_fim":      "",   # YYYY-MM-DD
    "gmv_bruto":        0.0,
    "gmv_liquido":      0.0,
    "reembolso":        0.0,
    "refund_pct":       0.0,
    "pedidos":          0,
    "aov":              0.0,
    "videos":           0,
    "lives":            0,
    "comissao":         0.0,
    "tier":             "unknown",
    "status_reembolso": "sem_dado",
}

COLUMN_ALIASES = {
    # TikTok Seller Center PT
    "creator_name":                              "creator_id",
    "gmv_atribuido_a_afiliados":                 "gmv_bruto",
    "reembolsos":                                "reembolso",
    "pedidos_atribuidos":                        "pedidos",
    "aov":                                       "aov",
    "videos":                                    "videos",
    "transmissoes_ao_vivo":                      "lives",
    "comissao_estimada":                         "comissao",
    "amostras_enviadas":                         "amostras",
    "itens_vendidos_atribuidos_ao_afiliado":     "items_vendidos",
    "itens_reembolsados":                        "items_reembolsados",
    "media_diaria_de_produtos_vendidos":         "media_diaria",
    # Google Sheets / CSV legado
    "creator":      "creator_id",
    "gmv_bruto":    "gmv_bruto",
    "gmv_lquido":   "gmv_liquido",
    "gmv_liquido":  "gmv_liquido",
    "reembolso":    "reembolso",
    "refund":       "refund_pct",
    "refund_pct":   "refund_pct",
    "comisso":      "comissao",
    "comissao":     "comissao",
    "tier":         "tier",
    "status_reembolso": "status_reembolso",
}

TIER_RULES = [
    (60_000, "Diamante", 0.13),
    (25_000, "Ouro",     0.11),
    (8_000,  "Prata",    0.09),
    (2_000,  "Bronze",   0.07),
    (0,      "Ferro",    0.05),
]


# ── Helpers de transformação ──────────────────────────────────────────────────

def normalise_header(col: str) -> str:
    col = col.strip().lower()
    col = unicodedata.normalize("NFD", col)
    col = "".join(c for c in col if unicodedata.category(c) != "Mn")
    col = re.sub(r"[^\w\s]", "", col)
    col = re.sub(r"\s+", "_", col)
    return re.sub(r"_+", "_", col).strip("_")


def parse_brl(series: pd.Series) -> pd.Series:
    """'R$ 1.234,56' → 1234.56 — suporta também '1234.56' (US)."""
    def _convert(v):
        if pd.isna(v): return np.nan
        s = re.sub(r"R\$\s*", "", str(v)).strip()
        if not s or s in ("-", "—", "nan", "None"): return np.nan
        if "," in s:  # PT-BR: 1.234,56
            return float(s.replace(".", "").replace(",", "."))
        return float(s)  # US ou inteiro
    return series.map(_convert).fillna(0.0)


def parse_pct(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "None": np.nan, "nan": np.nan})
        .astype(float).fillna(0.0)
    )


def clean_creator_id(series: pd.Series) -> pd.Series:
    return (
        series.astype(str).str.strip().str.upper()
        .str.replace(r"^@", "", regex=True)
        .replace({"NAN": "", "NONE": "", "": ""})
    )


def calc_tier(gmv_liq: float) -> tuple[str, float]:
    for threshold, label, rate in TIER_RULES:
        if gmv_liq >= threshold:
            return label, rate
    return "Ferro", 0.05


# ── Detecção de período ───────────────────────────────────────────────────────

def detect_period(path: Path) -> tuple[str, str, str]:
    """
    Extrai período do nome do arquivo.
    Formatos suportados:
      ..._20260301-20260331.xlsx
      ..._2026-03-01_2026-03-31.xlsx
      ..._202603.xlsx
      ..._2026-03.xlsx
    Retorna (periodo_ym, periodo_inicio, periodo_fim) como strings YYYY-MM / YYYY-MM-DD.
    """
    name = path.stem

    # Padrão: dois blocos de data YYYYMMDD ou YYYY-MM-DD
    m = re.search(
        r"(\d{4}[-_]?\d{2}[-_]?\d{2})[-_ ](\d{4}[-_]?\d{2}[-_]?\d{2})",
        name
    )
    if m:
        def parse_dt(s):
            s = re.sub(r"[-_]", "", s)
            return datetime.strptime(s, "%Y%m%d").date()
        d1, d2 = parse_dt(m.group(1)), parse_dt(m.group(2))
        inicio, fim = min(d1, d2), max(d1, d2)
        return inicio.strftime("%Y-%m"), str(inicio), str(fim)

    # Padrão: YYYYMM ou YYYY-MM
    m = re.search(r"(\d{4})[-_]?(\d{2})(?!\d)", name)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            inicio = date(y, mo, 1)
            ultimo = (date(y, mo % 12 + 1, 1) if mo < 12 else date(y + 1, 1, 1))
            fim = date(ultimo.year, ultimo.month, 1) - __import__("datetime").timedelta(days=1)
            return inicio.strftime("%Y-%m"), str(inicio), str(fim)

    # Fallback: mês atual
    hoje = date.today()
    inicio = date(hoje.year, hoje.month, 1)
    return inicio.strftime("%Y-%m"), str(inicio), str(hoje)


# ── Load raw ─────────────────────────────────────────────────────────────────

def load_raw(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        df = None
        for hrow in (0, 1, 2):
            try:
                candidate = pd.read_excel(path, header=hrow, dtype=str)
                candidate.columns = [normalise_header(c) for c in candidate.columns]
                if any(c in COLUMN_ALIASES for c in candidate.columns):
                    df = candidate
                    break
            except Exception:
                continue
        if df is None:
            raise ValueError(f"Não foi possível detectar cabeçalho em: {path.name}")
    elif suffix == ".csv":
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                df = pd.read_csv(path, dtype=str, encoding=enc)
                df.columns = [normalise_header(c) for c in df.columns]
                break
            except UnicodeDecodeError:
                continue
    else:
        raise ValueError(f"Formato não suportado: {suffix}")
    return df


# ── Transform ─────────────────────────────────────────────────────────────────

def transform(df: pd.DataFrame, periodo_ym: str, inicio: str, fim: str) -> pd.DataFrame:
    df = df.copy()

    # 1. Aliases
    df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns}, inplace=True)

    # 2. Descarta linhas completamente vazias
    df.dropna(how="all", inplace=True)

    # 3. Remove linhas de títulos/meta do TikTok
    if "creator_id" in df.columns:
        df = df[~df["creator_id"].astype(str).str.contains(
            r"RANKING|PERFORMANCE|RHODE|^#$|CREATOR_ID|AFFILIATE",
            flags=re.IGNORECASE, na=False
        )]
        df = df[~df["creator_id"].astype(str).str.fullmatch(r"\d+", na=False)]

    # 4. Garante colunas obrigatórias
    for col, default in REQUIRED_COLS.items():
        if col not in df.columns:
            df[col] = default

    # 5. Período
    df["periodo"]       = periodo_ym
    df["periodo_inicio"] = inicio
    df["periodo_fim"]   = fim

    # 6. creator_id
    df["creator_id"] = clean_creator_id(df["creator_id"])
    df = df[df["creator_id"].ne("") & df["creator_id"].ne("SEM_CREATOR")]

    # 7. Monetário
    for col in MONETARY_COLS:
        df[col] = parse_brl(df[col])

    # 8. Percentual
    df["refund_pct"] = parse_pct(df["refund_pct"])

    # 9. Inteiros
    for col in INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # 10. Strings
    for col in STR_COLS:
        df[col] = df[col].astype(str).str.strip().replace(
            {"nan": REQUIRED_COLS[col], "": REQUIRED_COLS[col]}
        )

    # 11. gmv_liquido fallback
    mask = df["gmv_liquido"] == 0
    df.loc[mask, "gmv_liquido"] = df.loc[mask, "gmv_bruto"] - df.loc[mask, "reembolso"]

    # 12. reembolso ↔ refund_pct fallback
    mask_rem = (df["reembolso"] == 0) & (df["refund_pct"] > 0)
    df.loc[mask_rem, "reembolso"] = (
        df.loc[mask_rem, "gmv_bruto"] * df.loc[mask_rem, "refund_pct"] / 100
    ).round(2)
    mask_pct = (df["refund_pct"] == 0) & (df["reembolso"] > 0) & (df["gmv_bruto"] > 0)
    df.loc[mask_pct, "refund_pct"] = (
        df.loc[mask_pct, "reembolso"] / df.loc[mask_pct, "gmv_bruto"] * 100
    ).round(2)

    # 13. Tier calculado
    def _tier(row):
        label, rate = calc_tier(row["gmv_liquido"])
        return pd.Series({"tier": label, "comissao_calculada": round(row["gmv_liquido"] * rate, 2)})

    tier_df = df.apply(_tier, axis=1)
    df["tier"] = tier_df["tier"]
    df["comissao_calculada"] = tier_df["comissao_calculada"]

    # 14. Coluna de origem
    df["_fonte"] = "tiktok_seller_center"

    # 15. Ordem das colunas
    priority = list(REQUIRED_COLS.keys()) + ["comissao_calculada", "_fonte"]
    extra = [c for c in df.columns if c not in priority]
    df = df[[c for c in priority + extra if c in df.columns]]

    return df.reset_index(drop=True)


# ── Derivar tabelas do warehouse ──────────────────────────────────────────────

def build_creators_master(raw: pd.DataFrame) -> pd.DataFrame:
    """1 linha por creator — dados do período mais recente."""
    if raw.empty:
        return raw.copy()
    latest = raw.sort_values("periodo").groupby("creator_id").last().reset_index()
    # Agrega métricas acumuladas
    agg = raw.groupby("creator_id").agg(
        total_gmv_bruto=("gmv_bruto", "sum"),
        total_gmv_liquido=("gmv_liquido", "sum"),
        total_pedidos=("pedidos", "sum"),
        total_reembolso=("reembolso", "sum"),
        total_videos=("videos", "sum"),
        total_lives=("lives", "sum"),
        total_comissao=("comissao_calculada", "sum"),
        periodos_ativo=("periodo", "nunique"),
        primeiro_periodo=("periodo", "min"),
        ultimo_periodo=("periodo", "max"),
    ).reset_index()
    master = latest.merge(agg, on="creator_id", how="left")
    # Recalcula tier pelo GMV acumulado
    master[["tier", "comissao_calculada"]] = master["total_gmv_liquido"].apply(
        lambda g: pd.Series(calc_tier(g))
    )
    return master


def build_period_summary(raw: pd.DataFrame) -> pd.DataFrame:
    """KPIs agregados por período."""
    if raw.empty:
        return pd.DataFrame()

    # Detecta períodos parciais: dias cobertos vs dias do mês
    from calendar import monthrange
    def period_days_info(inicio_str, fim_str):
        try:
            ini = pd.to_datetime(inicio_str)
            fim = pd.to_datetime(fim_str)
            periodo_str = ini.strftime("%Y-%m")
            yr, mo = ini.year, ini.month
            dias_mes = monthrange(yr, mo)[1]
            dias_cobertos = (fim - ini).days + 1
            return dias_cobertos, dias_mes
        except Exception:
            return None, None

    grp = raw.groupby(["periodo", "periodo_inicio", "periodo_fim"])
    summary = grp.agg(
        gmv_bruto_total=("gmv_bruto", "sum"),
        gmv_liquido_total=("gmv_liquido", "sum"),
        reembolso_total=("reembolso", "sum"),
        pedidos_total=("pedidos", "sum"),
        creators_ativas=("creator_id", lambda x: (raw.loc[x.index, "gmv_bruto"] > 0).sum()),
        creators_total=("creator_id", "count"),
        videos_total=("videos", "sum"),
        lives_total=("lives", "sum"),
        comissao_total=("comissao_calculada", "sum"),
    ).reset_index()

    # AOV correto: GMV líquido total / pedidos totais (não média dos AOVs individuais)
    summary["aov_medio"] = (
        summary["gmv_liquido_total"] / summary["pedidos_total"].replace(0, np.nan)
    ).round(2).fillna(0)

    summary["refund_rate_pct"] = (
        summary["reembolso_total"] / summary["gmv_bruto_total"].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    # Detecta período parcial e dias cobertos
    summary[["dias_cobertos", "dias_mes"]] = summary.apply(
        lambda r: pd.Series(period_days_info(r["periodo_inicio"], r["periodo_fim"])),
        axis=1
    )
    summary["periodo_parcial"] = summary["dias_cobertos"] < summary["dias_mes"]

    # Projeção mensal para períodos parciais (extrapolação linear)
    summary["gmv_liquido_projetado"] = summary.apply(
        lambda r: round(r["gmv_liquido_total"] / r["dias_cobertos"] * r["dias_mes"], 2)
        if r["periodo_parcial"] and r["dias_cobertos"] and r["dias_cobertos"] > 0
        else r["gmv_liquido_total"],
        axis=1
    )

    # Variação vs período anterior — usa gmv_liquido_projetado para evitar distorção de mês parcial
    summary = summary.sort_values("periodo").reset_index(drop=True)
    for col in ["gmv_bruto_total", "gmv_liquido_total", "pedidos_total", "creators_ativas"]:
        summary[f"{col}_delta_pct"] = (
            summary[col].pct_change() * 100
        ).round(1).fillna(0)

    return summary


def build_sync_ready(raw: pd.DataFrame) -> pd.DataFrame:
    """Visão do período mais recente (compatibilidade com portal)."""
    if raw.empty:
        return raw.copy()
    ultimo = raw["periodo"].max()
    return raw[raw["periodo"] == ultimo].reset_index(drop=True)


# ── Append ao histórico ───────────────────────────────────────────────────────

def append_to_raw_imports(new_df: pd.DataFrame, warehouse_dir: Path) -> pd.DataFrame:
    raw_path = warehouse_dir / "raw_imports.csv"
    if raw_path.exists():
        existing = pd.read_csv(raw_path, dtype=str, encoding="utf-8-sig").fillna("")
        # Converte colunas numéricas
        for col in MONETARY_COLS + ["refund_pct", "comissao_calculada"]:
            if col in existing.columns:
                existing[col] = pd.to_numeric(existing[col], errors="coerce").fillna(0)
        for col in INT_COLS:
            if col in existing.columns:
                existing[col] = pd.to_numeric(existing[col], errors="coerce").fillna(0).astype(int)

        # Remove período(s) que estão sendo reimportados (evita duplicatas)
        periodos_novos = new_df["periodo"].unique()
        existing = existing[~existing["periodo"].isin(periodos_novos)]
        print(f"  Removidos {len(periodos_novos)} período(s) do histórico para reimport: {list(periodos_novos)}")

        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df.copy()

    return combined.sort_values(["periodo", "creator_id"]).reset_index(drop=True)


# ── Save ──────────────────────────────────────────────────────────────────────

def save_warehouse(raw: pd.DataFrame, warehouse_dir: Path) -> dict:
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    # raw_imports
    p = warehouse_dir / "raw_imports.csv"
    raw.to_csv(p, index=False, encoding="utf-8-sig")
    paths["raw_imports"] = p
    print(f"  [✓] raw_imports.csv    → {len(raw)} linhas ({raw['periodo'].nunique()} períodos)")

    # creators_master
    master = build_creators_master(raw)
    p = warehouse_dir / "creators_master.csv"
    master.to_csv(p, index=False, encoding="utf-8-sig")
    paths["creators_master"] = p
    print(f"  [✓] creators_master.csv → {len(master)} creators únicas")

    # period_summary
    summary = build_period_summary(raw)
    p = warehouse_dir / "period_summary.csv"
    summary.to_csv(p, index=False, encoding="utf-8-sig")
    paths["period_summary"] = p
    print(f"  [✓] period_summary.csv  → {len(summary)} períodos")

    # sync_ready
    sync = build_sync_ready(raw)
    p = warehouse_dir / "sync_ready.csv"
    sync.to_csv(p, index=False, encoding="utf-8-sig")
    paths["sync_ready"] = p
    ultimo = raw["periodo"].max() if not raw.empty else "—"
    print(f"  [✓] sync_ready.csv      → {len(sync)} linhas (período: {ultimo})")

    return paths


# ── Main ──────────────────────────────────────────────────────────────────────

def run(input_files: list[Path], warehouse_dir: Path = WAREHOUSE_DIR) -> None:
    print("\n" + "═" * 56)
    print("  Rhode Jeans — ETL v2 · Data Warehouse")
    print("═" * 56)

    all_new = []
    for path in input_files:
        print(f"\n▶ Processando: {path.name}")
        periodo_ym, inicio, fim = detect_period(path)
        print(f"  Período detectado: {periodo_ym}  ({inicio} → {fim})")

        raw_df = load_raw(path)
        print(f"  Linhas brutas: {len(raw_df)}")

        # Pula arquivos de resumo agregado (sem coluna de creator)
        has_creator_col = any(c in COLUMN_ALIASES for c in raw_df.columns if
                              COLUMN_ALIASES.get(c) == "creator_id" or c in ("creator_name", "creator_id", "creator"))
        if not has_creator_col or len(raw_df) < 2:
            print(f"  [SKIP] Arquivo não contém lista de creators — ignorado.")
            continue

        df = transform(raw_df, periodo_ym, inicio, fim)
        print(f"  Após limpeza:  {len(df)} creators")
        all_new.append(df)

    if not all_new:
        print("[ERRO] Nenhum arquivo processado.", file=sys.stderr)
        sys.exit(1)

    new_combined = pd.concat(all_new, ignore_index=True)

    print(f"\n▶ Mesclando com histórico existente...")
    raw_full = append_to_raw_imports(new_combined, warehouse_dir)
    print(f"  Total histórico: {len(raw_full)} linhas | {raw_full['periodo'].nunique()} períodos | {raw_full['creator_id'].nunique()} creators únicas")

    print(f"\n▶ Salvando warehouse em ./{warehouse_dir}/")
    save_warehouse(raw_full, warehouse_dir)

    print("\n✅ ETL v2 concluído.")
    print(f"   Próximo passo: python agente_rhode/sync_v2.py\n")


def main():
    parser = argparse.ArgumentParser(description="Rhode ETL v2 — Data Warehouse")
    parser.add_argument("files", nargs="*", help="Arquivos .xlsx/.csv a processar")
    parser.add_argument("--dir", help="Diretório com arquivos a processar")
    parser.add_argument("--warehouse", default=str(WAREHOUSE_DIR), help="Diretório de saída")
    args = parser.parse_args()

    files = []
    if args.dir:
        d = Path(args.dir)
        files = sorted(d.glob("*.xlsx")) + sorted(d.glob("*.csv"))
        if not files:
            print(f"[ERRO] Nenhum arquivo encontrado em {args.dir}", file=sys.stderr)
            sys.exit(1)
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        # Auto-detect
        default_dir = Path("dados/creators/exports")
        files = sorted(default_dir.glob("*.xlsx")) if default_dir.exists() else []
        if not files:
            print("[ERRO] Nenhum arquivo especificado e nenhum .xlsx em dados/creators/exports/", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
        print(f"[INFO] Auto-detectado {len(files)} arquivo(s) em {default_dir}")

    run(files, Path(args.warehouse))


if __name__ == "__main__":
    main()
