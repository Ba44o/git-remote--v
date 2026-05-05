"""
Rhode Jeans — ETL Diário (loja toda)
=====================================
Lê todos os exports Overview_*.xlsx em dados/marketplace/tiktokshop/, junta
a aba "Diario" de cada um e salva um CSV consolidado em warehouse/raw_diario.csv.

Quando o mesmo dia aparece em múltiplos snapshots, mantém o do snapshot
mais recente (mtime do arquivo) — assume que coletas mais novas têm dados
mais corretos.

Granularidade: 1 linha por dia (loja toda agregada). Não é por creator.

Uso:
  python agente_rhode/etl_diario.py
  python agente_rhode/etl_diario.py --dir dados/marketplace/tiktokshop

Output:
  warehouse/raw_diario.csv
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEFAULT_DIR),
                    help="Diretório com os Overview_*.xlsx")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_diario.csv"))
    args = ap.parse_args()

    full = consolidar(Path(args.dir))
    out = normalizar(full)

    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    total_gmv = out["gmv_liquido"].sum()
    print(f"\n  ✓ {len(out)} dias consolidados ({out['data'].min()} → {out['data'].max()})")
    print(f"  ✓ GMV líquido total: R$ {total_gmv:,.2f}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
