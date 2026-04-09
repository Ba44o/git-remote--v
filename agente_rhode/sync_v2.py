"""
Rhode Jeans — Sync v2
=====================
Envia as 4 tabelas do warehouse local para o Google Sheets.

Abas criadas/atualizadas:
  raw_imports      → histórico completo
  creators_master  → 1 linha por creator
  period_summary   → KPIs por período
  sync_ready       → período mais recente (compatibilidade)

Uso:
  python agente_rhode/sync_v2.py
  python agente_rhode/sync_v2.py --warehouse warehouse/
"""

import sys
import argparse
import gspread
import pandas as pd
from pathlib import Path
from oauth2client.service_account import ServiceAccountCredentials

# ── Config ────────────────────────────────────────────────────────────────────

SPREADSHEET_ID   = "1hiyu1y9G7NeiBKnwV6FNlYRjVqTCRP3jY--I0Lv0Mh0"
CREDENTIALS_FILE = "credentials.json"
WAREHOUSE_DIR    = Path("warehouse")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

TABS = [
    ("raw_imports",     "raw_imports.csv"),
    ("creators_master", "creators_master.csv"),
    ("period_summary",  "period_summary.csv"),
    ("sync_ready",      "sync_ready.csv"),
]


# ── Auth ──────────────────────────────────────────────────────────────────────

def auth() -> gspread.Client:
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    return gspread.authorize(creds)


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_tab(spreadsheet: gspread.Spreadsheet, tab_name: str, df: pd.DataFrame) -> None:
    # Converte tudo para string limpa (Sheets não aceita NaN/inf)
    df_str = df.fillna("").astype(str).replace({"nan": "", "None": "", "inf": "", "-inf": ""})

    try:
        ws = spreadsheet.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name,
            rows=max(len(df_str) + 10, 100),
            cols=max(len(df_str.columns), 10)
        )

    data = [df_str.columns.tolist()] + df_str.values.tolist()

    # Batch update em chunks (limite da API: 40k células por request)
    CHUNK = 10_000
    if len(data) <= CHUNK:
        ws.update(data, value_input_option="RAW")
    else:
        ws.update([data[0]], value_input_option="RAW")  # header
        for i in range(1, len(data), CHUNK):
            chunk = data[i:i + CHUNK]
            ws.append_rows(chunk, value_input_option="RAW")

    print(f"  [✓] '{tab_name}' → {len(df_str)} linhas × {len(df_str.columns)} colunas")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rhode Sync v2 — Google Sheets")
    parser.add_argument("--warehouse", default=str(WAREHOUSE_DIR))
    parser.add_argument("--only", nargs="+", help="Sincronizar apenas estas abas")
    args = parser.parse_args()

    wdir = Path(args.warehouse)
    tabs_to_sync = args.only or [t[0] for t in TABS]

    print("\n" + "═" * 56)
    print("  Rhode Jeans — Sync v2 · Google Sheets")
    print("═" * 56)

    # Verifica warehouse
    missing = [csv for tab, csv in TABS if tab in tabs_to_sync and not (wdir / csv).exists()]
    if missing:
        print(f"\n[ERRO] Arquivos não encontrados em {wdir}/:")
        for f in missing: print(f"  - {f}")
        print("\nRode primeiro: python agente_rhode/etl_v2.py")
        sys.exit(1)

    print("\n▶ Autenticando com Google Sheets...")
    try:
        client = auth()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"  [✓] Planilha: {spreadsheet.title}")
    except Exception as e:
        print(f"[ERRO] Autenticação falhou: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"\n▶ Enviando {len(tabs_to_sync)} aba(s)...")
    for tab_name, csv_file in TABS:
        if tab_name not in tabs_to_sync:
            continue
        csv_path = wdir / csv_file
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig").fillna("")
        upload_tab(spreadsheet, tab_name, df)

    # Envia insights.json para aba analyst_insights (célula única A1)
    insights_path = wdir / "insights.json"
    if insights_path.exists():
        import json
        print("  [✓] Enviando insights.json → aba analyst_insights")
        with open(insights_path, encoding="utf-8") as f:
            insights_str = f.read()
        try:
            ws_ins = spreadsheet.worksheet("analyst_insights")
            ws_ins.clear()
        except gspread.WorksheetNotFound:
            ws_ins = spreadsheet.add_worksheet(title="analyst_insights", rows=2, cols=1)
        ws_ins.update([[insights_str]], "A1")

    print(f"\n✅ Sync concluído!")
    print(f"   Planilha: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"   Abas: {', '.join(tabs_to_sync)}\n")


if __name__ == "__main__":
    main()
