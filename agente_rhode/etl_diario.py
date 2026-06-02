"""
Rhode Jeans — ETL Diário (loja toda)
=====================================
Gera warehouse/raw_diario.csv (1 linha por dia, loja toda agregada — NÃO por
creator). Duas fontes:

  --source api   (DEFAULT) → TikTok Shop API GET /analytics/202405/shop/performance
                  via coletar_dados.buscar_analytics(). Respeita o lag de ~2 dias
                  (só dias finalizados). Esta é a fonte canônica de ativação do 4.1.

  --source xlsx  (legado) → junta a aba "Diario" dos Overview_*.xlsx. Quando o mesmo
                  dia aparece em múltiplos snapshots, mantém o de mtime mais recente.

Uso:
  python agente_rhode/etl_diario.py --source api --dias 90
  python agente_rhode/etl_diario.py --source xlsx --dir dados/marketplace/tiktokshop

Output:
  warehouse/raw_diario.csv  →  sync via sync_supabase.py::sync_performance_diario()
"""

import argparse
import glob
import os
import sys
from pathlib import Path

import pandas as pd

WAREHOUSE = Path("warehouse")
DEFAULT_DIR = Path("dados/marketplace/tiktokshop")

EXPECTED_COLS = ["Data", "GMV", "GMV_CF", "Pedidos", "Cancelados",
                 "Itens", "Clientes", "Ticket", "Taxa_Cancel"]


def read_diario_sheet(xlsx_path: str) -> pd.DataFrame:
    """Lê a aba 'Diario' de um Overview xlsx. Retorna DF vazio se não existir."""
    try:
        xl = pd.ExcelFile(xlsx_path)
        if "Diario" not in xl.sheet_names:
            return pd.DataFrame()
        df = pd.read_excel(xlsx_path, sheet_name="Diario")
    except Exception as e:
        print(f"  [AVISO] {xlsx_path}: {e}")
        return pd.DataFrame()
    if df.empty:
        return df
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        print(f"  [AVISO] {xlsx_path} sem colunas: {missing}")
        return pd.DataFrame()
    df["_source"] = os.path.basename(xlsx_path)
    df["_mtime"] = os.path.getmtime(xlsx_path)
    return df


def consolidar(input_dir: Path) -> pd.DataFrame:
    files = sorted(glob.glob(str(input_dir / "Overview_*.xlsx")),
                   key=os.path.getmtime)
    if not files:
        print(f"[ERRO] Nenhum Overview_*.xlsx em {input_dir}")
        sys.exit(1)
    print(f"  Lendo {len(files)} arquivos Overview...")
    parts = []
    for f in files:
        df = read_diario_sheet(f)
        if not df.empty:
            parts.append(df)
            print(f"    ✓ {os.path.basename(f)}: {len(df)} dias")
    if not parts:
        print("[ERRO] Nenhum dia extraído.")
        sys.exit(1)
    full = pd.concat(parts, ignore_index=True)
    full["Data"] = pd.to_datetime(full["Data"]).dt.strftime("%Y-%m-%d")
    # Para cada Data, mantém o snapshot com _mtime mais recente
    full = full.sort_values("_mtime").drop_duplicates("Data", keep="last")
    full = full.sort_values("Data").reset_index(drop=True)
    return full


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas pro snake_case do Supabase + casts."""
    out = pd.DataFrame({
        "data":            df["Data"],
        "gmv_bruto":       pd.to_numeric(df["GMV"], errors="coerce").fillna(0).round(2),
        "gmv_liquido":     pd.to_numeric(df["GMV_CF"], errors="coerce").fillna(0).round(2),
        "pedidos":         pd.to_numeric(df["Pedidos"], errors="coerce").fillna(0).astype(int),
        "cancelados":      pd.to_numeric(df["Cancelados"], errors="coerce").fillna(0).astype(int),
        "itens":           pd.to_numeric(df["Itens"], errors="coerce").fillna(0).astype(int),
        "clientes":        pd.to_numeric(df["Clientes"], errors="coerce").fillna(0).astype(int),
        "ticket":          pd.to_numeric(df["Ticket"], errors="coerce").fillna(0).round(2),
        "taxa_cancel_pct": pd.to_numeric(df["Taxa_Cancel"], errors="coerce").fillna(0).round(2),
    })
    return out


def _map_interval(iv: dict) -> dict:
    """Mapeia 1 intervalo da API pro schema do CSV (documentado — ajuste aqui
    se a definição de um KPI mudar):
      gmv_bruto       = gmv.amount
      gmv_liquido     = gmv.amount - refunds.amount      (líquido de devoluções)
      pedidos         = orders
      cancelados      = cancellations_and_returns
      itens           = units_sold
      clientes        = buyers
      ticket          = avg_order_value.amount           (AOV oficial do TikTok)
      taxa_cancel_pct = cancelados / pedidos * 100
    """
    gmv     = float(iv.get("gmv", {}).get("amount", 0) or 0)
    refunds = float(iv.get("refunds", {}).get("amount", 0) or 0)
    pedidos = int(iv.get("orders", 0) or 0)
    cancel  = int(iv.get("cancellations_and_returns", 0) or 0)
    return {
        "data":            iv.get("start_date"),
        "gmv_bruto":       round(gmv, 2),
        "gmv_liquido":     round(gmv - refunds, 2),
        "pedidos":         pedidos,
        "cancelados":      cancel,
        "itens":           int(iv.get("units_sold", 0) or 0),
        "clientes":        int(iv.get("buyers", 0) or 0),
        "ticket":          round(float(iv.get("avg_order_value", {}).get("amount", 0) or 0), 2),
        "taxa_cancel_pct": round(cancel / pedidos * 100, 2) if pedidos else 0.0,
    }


def coletar_api(dias: int, chunk_dias: int = 10, chunk_retries: int = 3) -> pd.DataFrame:
    """Busca Performance da loja via API em janelas de `chunk_dias` (a API estoura
    timeout em janelas grandes de granularidade diária) e concatena os dias.
    Cada chunk é re-tentado até `chunk_retries` vezes; gaps em território já
    finalizado são logados explicitamente (nunca truncados em silêncio)."""
    # coletar_dados.py está na raiz do projeto (um nível acima de agente_rhode/)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_analytics
    from datetime import date, timedelta

    hoje   = date.today()
    cursor = hoje - timedelta(days=dias)
    rows, gaps = [], []
    while cursor <= hoje:
        chunk_fim = min(cursor + timedelta(days=chunk_dias - 1), hoje)
        ini_s, fim_s = cursor.strftime("%Y-%m-%d"), chunk_fim.strftime("%Y-%m-%d")
        ivs = []
        for _ in range(chunk_retries):
            ivs = buscar_analytics(ini_s, fim_s, "1D")
            if ivs:
                break
        if ivs:
            rows.extend(_map_interval(iv) for iv in ivs)
        elif chunk_fim < hoje - timedelta(days=1):   # ignora janela do lag (esperada vazia)
            gaps.append(f"{ini_s}→{fim_s}")
        cursor = chunk_fim + timedelta(days=1)

    if gaps:
        print(f"  ⚠  {len(gaps)} janela(s) sem dados mesmo após retries (rode de novo p/ preencher): {', '.join(gaps)}")
    if not rows:
        print("[ERRO] API não retornou nenhum intervalo finalizado.")
        sys.exit(1)

    out = pd.DataFrame(rows).drop_duplicates("data", keep="last")
    return out.sort_values("data").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["api", "xlsx"], default="api",
                    help="api (default) = TikTok Shop API; xlsx = Overview_*.xlsx (legado)")
    ap.add_argument("--dias", type=int, default=90, help="janela em dias (modo api)")
    ap.add_argument("--dir", default=str(DEFAULT_DIR),
                    help="Diretório com os Overview_*.xlsx (modo xlsx)")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_diario.csv"))
    args = ap.parse_args()

    if args.source == "api":
        out = coletar_api(args.dias)
    else:
        out = normalizar(consolidar(Path(args.dir)))

    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    total_gmv = out["gmv_liquido"].sum()
    print(f"\n  ✓ {len(out)} dias consolidados ({out['data'].min()} → {out['data'].max()})")
    print(f"  ✓ GMV líquido total: R$ {total_gmv:,.2f}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
