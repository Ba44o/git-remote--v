import sys
import re
import unicodedata
import numpy as np
import pandas as pd
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "creator_id": "",
    "gmv_bruto": 0.0,
    "gmv_liquido": 0.0,
    "reembolso": 0.0,
    "refund_pct": 0.0,
    "pedidos": 0,
    "aov": 0.0,
    "videos": 0,
    "lives": 0,
    "comissao": 0.0,
    "tier": "unknown",
    "status_reembolso": "sem_dado",
}

COLUMN_ALIASES = {
    # TikTok Seller Center — Transaction Analysis Creator List (PT)
    "creator_name": "creator_id",
    "gmv_atribuido_a_afiliados": "gmv_bruto",
    "reembolsos": "reembolso",
    "pedidos_atribuidos": "pedidos",
    "itens_vendidos_atribuidos_ao_afiliado": "items_vendidos",
    "itens_reembolsados": "items_reembolsados",
    "aov": "aov",
    "media_diaria_de_produtos_vendidos": "media_diaria",
    "videos": "videos",
    "transmissoes_ao_vivo": "lives",
    "comissao_estimada": "comissao",
    "amostras_enviadas": "amostras",
    # Google Sheets Creator Ranking (gviz — acentos removidos)
    "creator": "creator_id",
    "gmv_bruto": "gmv_bruto",
    "gmv_lquido": "gmv_liquido",
    "gmv_liquido": "gmv_liquido",
    "reembolso": "reembolso",
    "refund": "refund_pct",
    "refund_pct": "refund_pct",
    "videos": "videos",
    "lives": "lives",
    "comisso": "comissao",
    "comissao": "comissao",
    "tier": "tier",
    "status_reembolso": "status_reembolso",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_header(col: str) -> str:
    col = col.strip().lower()
    # Strip accents (NFD decomposes é→e+combining, then filter combining chars)
    col = unicodedata.normalize("NFD", col)
    col = "".join(c for c in col if unicodedata.category(c) != "Mn")
    col = re.sub(r"[^\w\s]", "", col)   # remove punctuation
    col = re.sub(r"\s+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def parse_brl(series: pd.Series) -> pd.Series:
    """R$ 1.234,56  →  1234.56"""
    return (
        series.astype(str)
        .str.replace(r"R\$\s*", "", regex=True)
        .str.replace(r"\.", "", regex=True)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": np.nan, "None": np.nan, "nan": np.nan, "—": np.nan})
        .astype(float)
        .fillna(0.0)
    )


def parse_pct(series: pd.Series) -> pd.Series:
    """50.1%  →  50.1"""
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "None": np.nan, "nan": np.nan})
        .astype(float)
        .fillna(0.0)
    )


def clean_creator_id(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"^@", "", regex=True)
        .replace({"NAN": "", "NONE": ""})
    )


def flag_nulls(df: pd.DataFrame, col: str, default) -> pd.DataFrame:
    mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
    if mask.any():
        df.loc[mask, col] = default
        df.loc[mask, "_flag"] = df.loc[mask, "_flag"].astype(str) + f"|{col}:null"
    return df


# ── Load ──────────────────────────────────────────────────────────────────────

def load_raw(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    suffix = p.suffix.lower()
    try:
        if suffix in (".xlsx", ".xls"):
            # TikTok exports: header often on row 3
            for header_row in (2, 1, 0):
                df = pd.read_excel(p, header=header_row, dtype=str)
                df.columns = [normalise_header(c) for c in df.columns]
                if any(c in COLUMN_ALIASES for c in df.columns):
                    break
        elif suffix == ".csv":
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    df = pd.read_csv(p, dtype=str, encoding=enc)
                    df.columns = [normalise_header(c) for c in df.columns]
                    break
                except UnicodeDecodeError:
                    continue
        else:
            raise ValueError(f"Formato não suportado: {suffix}")
    except Exception as e:
        raise RuntimeError(f"Falha ao carregar {path}: {e}") from e

    return df


# ── Transform ─────────────────────────────────────────────────────────────────

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_flag"] = ""

    # 1. Map aliases → canonical names
    df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns}, inplace=True)

    # 2. Drop completely empty rows
    df.dropna(how="all", inplace=True)

    # 3. Drop meta/title rows (TikTok exports embed report titles in first rows)
    if "creator_id" in df.columns:
        df = df[~df["creator_id"].astype(str).str.contains(
            r"RANKING|PERFORMANCE|RHODE|^#$|CREATOR_ID|AFFILIATE", flags=re.IGNORECASE, na=False
        )]
    # Drop rows where creator_id looks like a number (index artifact)
    if "creator_id" in df.columns:
        df = df[~df["creator_id"].astype(str).str.fullmatch(r"\d+", na=False)]

    # 4. Ensure all required columns exist
    for col, default in REQUIRED_COLUMNS.items():
        if col not in df.columns:
            df[col] = default

    # 5. Clean creator_id
    df["creator_id"] = clean_creator_id(df["creator_id"])
    df = flag_nulls(df, "creator_id", "SEM_CREATOR")

    # 6. Parse monetary columns
    for col in ("gmv_bruto", "gmv_liquido", "reembolso", "aov", "comissao"):
        df[col] = parse_brl(df[col])

    # 7. Parse percentage
    df["refund_pct"] = parse_pct(df["refund_pct"])

    # 8. Parse integer columns
    for col in ("pedidos", "videos", "lives"):
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    # 9. String columns — fill NaN
    for col in ("tier", "status_reembolso"):
        df[col] = df[col].astype(str).str.strip().replace(
            {"nan": REQUIRED_COLUMNS[col], "": REQUIRED_COLUMNS[col]}
        )

    # 10. Derived: gmv_liquido fallback
    mask_liq = df["gmv_liquido"] == 0
    df.loc[mask_liq, "gmv_liquido"] = df.loc[mask_liq, "gmv_bruto"]

    # 11. Derived: reembolso ↔ refund_pct (cada um como fallback do outro)
    mask_rem = (df["reembolso"] == 0) & (df["refund_pct"] > 0)
    df.loc[mask_rem, "reembolso"] = (
        df.loc[mask_rem, "gmv_bruto"] * df.loc[mask_rem, "refund_pct"] / 100
    ).round(2)
    # Calcula refund_pct a partir de reembolso quando não veio do export
    mask_pct = (df["refund_pct"] == 0) & (df["reembolso"] > 0) & (df["gmv_bruto"] > 0)
    df.loc[mask_pct, "refund_pct"] = (
        df.loc[mask_pct, "reembolso"] / df.loc[mask_pct, "gmv_bruto"] * 100
    ).round(2)

    # 12. Column order — required first, extras appended
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS and c != "_flag"]
    ordered = list(REQUIRED_COLUMNS.keys()) + extra + ["_flag"]
    df = df[[c for c in ordered if c in df.columns]]

    return df.reset_index(drop=True)


# ── Validate ──────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> None:
    errors = []

    if df["creator_id"].eq("").any() or df["creator_id"].eq("SEM_CREATOR").any():
        n = df["creator_id"].isin(["", "SEM_CREATOR"]).sum()
        errors.append(f"  - {n} linha(s) sem creator_id")

    if (df["gmv_bruto"] < 0).any():
        errors.append("  - gmv_bruto contém valores negativos")

    over100 = (df["refund_pct"] > 100).sum()
    if over100:
        print(f"[AVISO] {over100} linha(s) com refund_pct > 100% (devoluções de períodos anteriores — flagged).")
        df.loc[df["refund_pct"] > 100, "_flag"] += "|refund_pct:over100"

    dups = df["creator_id"].duplicated(keep=False) & df["creator_id"].ne("")
    if dups.any():
        n = dups.sum()
        print(f"[AVISO] {n} linha(s) com creator_id duplicado (aggregado esperado).")

    if errors:
        raise ValueError("Validação falhou:\n" + "\n".join(errors))


# ── Save ──────────────────────────────────────────────────────────────────────

def save(df: pd.DataFrame, out_path: str = "sync_ready.csv") -> None:
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[OK] {len(df)} linhas salvas → {out_path}")
    flagged = df["_flag"].ne("").sum()
    if flagged:
        print(f"[AVISO] {flagged} linha(s) com flags — verifique coluna _flag")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(input_path: str, output_path: str = "sync_ready.csv") -> pd.DataFrame:
    try:
        print(f"[1/4] Carregando: {input_path}")
        df_raw = load_raw(input_path)
        print(f"      {len(df_raw)} linhas brutas, {len(df_raw.columns)} colunas")

        print("[2/4] Transformando...")
        df = transform(df_raw)
        print(f"      {len(df)} linhas após limpeza")

        print("[3/4] Validando...")
        validate(df)
        print("      Validação OK")

        print("[4/4] Salvando...")
        save(df, output_path)

        return df

    except FileNotFoundError as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[ERRO VALIDAÇÃO] {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERRO INESPERADO] {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python etl_tiktok.py <arquivo_entrada> [sync_ready.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "sync_ready.csv"
    run(input_file, output_file)
