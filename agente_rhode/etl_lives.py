"""
Rhode Jeans — ETL Lives
Processa exports do TikTok Shop Seller Center e sincroniza com Supabase.

Exports suportados (colocar em dados/lives/exports/):
  Creator-Live-Performance_*.xlsx  → tabela `lives`
  Overview_My Business Performance_*.xlsx → tabela `store_daily`

Uso:
  python agente_rhode/etl_lives.py
  python agente_rhode/etl_lives.py --dir dados/lives/exports
"""
import os, sys, argparse, glob, hashlib
import pandas as pd
import requests
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERRO] Defina SUPABASE_URL e SUPABASE_SERVICE_KEY no ambiente.")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}


# ─── helpers ────────────────────────────────────────────────────────────────

def upsert(table: str, rows: list, on_conflict: str, chunk=500):
    if not rows:
        print(f"  [SKIP] {table} — sem linhas")
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    total = 0
    for i in range(0, len(rows), chunk):
        batch = rows[i:i + chunk]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code not in (200, 201):
            print(f"  [ERRO] {table} batch {i}: {r.status_code} {r.text[:300]}")
        else:
            total += len(batch)
    print(f"  [✓] {table} → {total} linhas")


def parse_brl(val) -> float:
    """'R$ 1.686,71' → 1686.71"""
    if pd.isna(val) or val == "":
        return 0.0
    s = str(val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def safe_int(val) -> int:
    try:
        return int(float(val or 0))
    except (ValueError, TypeError):
        return 0


def safe_float(val) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def make_live_key(started_at: str, title: str) -> str:
    """Chave única por live: datetime + título (hash curto para evitar colisões)."""
    raw = f"{started_at}|{title.strip()}"
    return raw[:120]


# ─── Creator-Live-Performance parser ────────────────────────────────────────

def process_lives_export(filepath: str) -> list:
    """
    Lê um arquivo Creator-Live-Performance_*.xlsx e retorna lista de dicts
    prontos para upsert na tabela `lives`.
    """
    print(f"  → {Path(filepath).name}")
    try:
        df = pd.read_excel(filepath, header=None, skiprows=2)
    except Exception as e:
        print(f"    [ERRO] ao ler arquivo: {e}")
        return []

    # Linha 0 = headers reais
    headers = df.iloc[0].tolist()
    df.columns = [str(h).strip() if not pd.isna(h) else f"_col{i}" for i, h in enumerate(headers)]
    df = df.iloc[1:].reset_index(drop=True)

    rows = []
    skipped = 0

    for _, r in df.iterrows():
        # Parse duração (segundos)
        dur_sec = safe_int(r.get("Duration", 0))
        if dur_sec <= 300:          # ignora sessões teste / falhas
            skipped += 1
            continue

        raw_dt = str(r.get("Start time", "")).strip()
        started_at = pd.to_datetime(raw_dt, errors="coerce")
        if pd.isna(started_at):
            skipped += 1
            continue

        title = str(r.get("Livestream", "")).strip()
        iso = started_at.isoformat()
        live_key = make_live_key(iso, title)

        gmv_bruto  = parse_brl(r.get("Gross revenue", 0))
        gmv_direct = parse_brl(r.get("Direct GMV", 0))
        avg_price  = parse_brl(r.get("Avg. price", 0))
        ctr        = safe_float(r.get("CTR", 0))
        ctor       = safe_float(r.get("CTOR (SKU orders)", 0))
        viewers    = safe_int(r.get("Viewers", 0))

        rows.append({
            "live_key":              live_key,
            "title":                 title,
            "started_at":            iso,
            "date":                  started_at.date().isoformat(),
            "month":                 started_at.strftime("%Y-%m"),
            "day_of_week":           int(started_at.weekday()),   # 0=seg, 6=dom
            "hour":                  int(started_at.hour),
            "duration_sec":          dur_sec,
            "duration_min":          round(dur_sec / 60, 1),
            "gmv_bruto":             gmv_bruto,
            "gmv_direct":            gmv_direct,
            "items_sold":            safe_int(r.get("Items sold", 0)),
            "customers":             safe_int(r.get("Customers", 0)),
            "avg_price":             avg_price,
            "orders":                safe_int(r.get("Orders paid for", 0)),
            "views":                 safe_int(r.get("Views", 0)),
            "viewers":               viewers,
            "peak_viewers":          safe_int(r.get("Peak viewers", 0)),
            "new_followers":         safe_int(r.get("New followers", 0)),
            "avg_view_duration_sec": safe_int(r.get("Avg. view duration", 0)),
            "likes":                 safe_int(r.get("Likes", 0)),
            "comments":              safe_int(r.get("Comments", 0)),
            "shares":                safe_int(r.get("Shares", 0)),
            "product_impressions":   safe_int(r.get("Product impressions", 0)),
            "product_clicks":        safe_int(r.get("Product clicks", 0)),
            "ctr":                   round(ctr * 100, 4),    # → percentual (22.7)
            "ctor":                  round(ctor * 100, 4),   # → percentual (2.9)
            "gmv_per_viewer":        round(gmv_direct / viewers, 4) if viewers > 0 else 0,
        })

    print(f"    {len(rows)} lives válidas · {skipped} ignoradas (curtas/inválidas)")
    return rows


# ─── Overview (store daily) parser ──────────────────────────────────────────

def process_overview_export(filepath: str) -> list:
    """
    Lê um arquivo 'Overview_My Business Performance_*.xlsx' e retorna
    lista de dicts para upsert na tabela `store_daily`.
    """
    print(f"  → {Path(filepath).name}")
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        print(f"    [ERRO] ao ler arquivo: {e}")
        return []

    # Encontrar a linha header dos dados diários (contém 'Data')
    header_row = None
    for i, row in df.iterrows():
        vals = [str(v).strip() for v in row.tolist()]
        if "Data" in vals:
            header_row = i
            break

    if header_row is None:
        print("    [AVISO] Não encontrou seção 'Dados diários'")
        return []

    headers = df.iloc[header_row].tolist()
    data    = df.iloc[header_row + 1:].reset_index(drop=True)
    data.columns = [str(h).strip() if not pd.isna(h) else f"_col{i}" for i, h in enumerate(headers)]

    rows = []
    for _, r in data.iterrows():
        raw_date = str(r.get("Data", "")).strip()
        if not raw_date or raw_date == "nan":
            continue

        dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            continue

        gmv     = parse_brl(r.get("Valor bruto da mercadoria (R$)", 0))
        reimb   = parse_brl(r.get("Reembolsos (R$)", 0))
        gmv_cof = parse_brl(r.get("Valor bruto da mercadoria (com cofinanciamento do TikTok)", 0))

        conv_str = str(r.get("Taxa de conversão", "0")).replace("%", "").replace(",", ".").strip()
        try:
            conv = float(conv_str)
        except ValueError:
            conv = 0.0

        rows.append({
            "date":             dt.date().isoformat(),
            "month":            dt.strftime("%Y-%m"),
            "gmv_bruto":        gmv,
            "reembolsos":       reimb,
            "gmv_cofinanciado": gmv_cof,
            "items_sold":       safe_int(r.get("Itens vendidos", 0)),
            "unique_customers": safe_int(r.get("Clientes únicos", 0)),
            "page_views":       safe_int(r.get("Visualizações de página", 0)),
            "store_visits":     safe_int(r.get("Visitas à página da loja", 0)),
            "sku_orders":       safe_int(r.get("Pedido de SKU", 0)),
            "orders":           safe_int(r.get("Pedidos", 0)),
            "conversion_rate":  conv,
        })

    print(f"    {len(rows)} dias processados")
    return rows


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="dados/lives/exports",
                        help="Pasta com os exports do Seller Center")
    args = parser.parse_args()

    export_dir = Path(args.dir)
    if not export_dir.exists():
        print(f"[ERRO] Pasta não encontrada: {export_dir}")
        sys.exit(1)

    xlsx_files = sorted(export_dir.glob("*.xlsx"))
    if not xlsx_files:
        print(f"[AVISO] Nenhum .xlsx em {export_dir}")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Rhode ETL Lives — {len(xlsx_files)} arquivo(s) em {export_dir}")
    print(f"{'='*60}\n")

    all_lives       = []
    all_store_daily = []

    for f in xlsx_files:
        name = f.name
        if name.startswith("Creator-Live-Performance"):
            all_lives.extend(process_lives_export(str(f)))
        elif name.startswith("Overview_My Business Performance") or name.lower().startswith("overview"):
            all_store_daily.extend(process_overview_export(str(f)))
        else:
            print(f"  [SKIP] {name} — tipo não reconhecido")

    # Deduplicação antes do upsert
    seen_lives = {}
    for r in all_lives:
        seen_lives[r["live_key"]] = r
    lives_dedup = list(seen_lives.values())

    seen_daily = {}
    for r in all_store_daily:
        seen_daily[r["date"]] = r
    daily_dedup = list(seen_daily.values())

    print(f"\n{'─'*40}")
    print(f"Lives únicas: {len(lives_dedup)}")
    print(f"Dias de loja únicos: {len(daily_dedup)}")
    print(f"{'─'*40}\n")

    print("Sincronizando com Supabase...")
    upsert("lives",       lives_dedup, on_conflict="live_key")
    upsert("store_daily", daily_dedup, on_conflict="date")

    print("\n✓ ETL Lives concluído.\n")


if __name__ == "__main__":
    main()
