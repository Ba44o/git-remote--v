import sys
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

SPREADSHEET_ID   = "1hiyu1y9G7NeiBKnwV6FNlYRjVqTCRP3jY--I0Lv0Mh0"
SHEET_TAB        = "sync_ready"
CREDENTIALS_FILE = "credentials.json"
INPUT_CSV        = "sync_ready.csv"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ── Auth ──────────────────────────────────────────────────────────────────────

def auth() -> gspread.Client:
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    return gspread.authorize(creds)


# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV não encontrado: {path}")
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
    print(f"[OK] CSV carregado: {len(df)} linhas × {len(df.columns)} colunas")
    return df


# ── Upload ────────────────────────────────────────────────────────────────────

def upload(client: gspread.Client, df: pd.DataFrame) -> None:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(SHEET_TAB)
        ws.clear()
        print(f"[OK] Aba '{SHEET_TAB}' encontrada e limpa")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=SHEET_TAB, rows=len(df) + 10, cols=len(df.columns)
        )
        print(f"[OK] Aba '{SHEET_TAB}' criada")

    data = [df.columns.tolist()] + df.values.tolist()
    ws.update(data, value_input_option="RAW")
    print(f"[OK] {len(df)} linhas enviadas para aba '{SHEET_TAB}'")


# ── ETL pipeline (auto-run se sync_ready.csv não existir) ────────────────────

def run_etl_if_needed() -> None:
    if Path(INPUT_CSV).exists():
        return
    print("[INFO] sync_ready.csv não encontrado — procurando export...")
    search_paths = [
        Path("dados/creators/exports"),
        Path("."),
    ]
    raw = None
    for sp in search_paths:
        raw = next(sp.glob("*.xlsx"), None)
        if raw:
            break
    if not raw:
        raise FileNotFoundError(
            "Nenhum .xlsx encontrado. Rode manualmente: "
            "python agente_rhode/etl_tiktok.py <arquivo.xlsx> sync_ready.csv"
        )
    print(f"[INFO] Rodando ETL em: {raw}")
    import subprocess
    subprocess.run(
        [sys.executable, "agente_rhode/etl_tiktok.py", str(raw), INPUT_CSV],
        check=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        run_etl_if_needed()

        print("[1/3] Autenticando com Google...")
        client = auth()
        print("[OK] Autenticado")

        print("[2/3] Carregando CSV...")
        df = load_csv(INPUT_CSV)

        print("[3/3] Enviando para Google Sheets...")
        upload(client, df)

        print("\n✅ Sync concluído!")
        print(f"    Planilha: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print(f"    Aba:      {SHEET_TAB}")

    except FileNotFoundError as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.APIError as e:
        print(f"[ERRO API Google] {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERRO INESPERADO] {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
