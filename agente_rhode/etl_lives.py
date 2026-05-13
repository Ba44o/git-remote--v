"""
Rhode Jeans — ETL Lives
Processa exports do TikTok Shop Seller Center e sincroniza com Supabase.

Exports suportados (colocar em dados/lives/exports/):
  Creator-Live-Performance_*.xlsx  → tabela `lives`
  Overview_My Business Performance_*.xlsx → tabela `store_daily`

Auto-detecta DOIS schemas em cada tipo:
  • Creator-Live-Performance: v1 (até ~abr/2026) e v2 (mai/2026+)
  • Overview: v1 (PT-BR longo) e v2 (PT-BR curto / EN curto)

Uso:
  python agente_rhode/etl_lives.py
  python agente_rhode/etl_lives.py --dir dados/lives/exports
"""
import os, sys, argparse
import pandas as pd
import requests
from pathlib import Path

# ── Auto-carrega .env da raiz do projeto (procura subindo a árvore) ─────────
def _load_dotenv():
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        env = parent / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # Não sobrescreve variáveis já definidas no shell
                os.environ.setdefault(k, v)
            return env
    return None

_load_dotenv()

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
    """'R$ 1.686,71' → 1686.71  |  '1234.56' → 1234.56"""
    if pd.isna(val) or val == "":
        return 0.0
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return 0.0
    s = s.replace("R$", "").replace(" ", "")
    # Heurística: se tem vírgula, é formato BR (ponto = milhar, vírgula = decimal)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def safe_int(val) -> int:
    if pd.isna(val) or val == "" or str(val).lower() == "nan":
        return 0
    try:
        return int(float(str(val).replace(",", ".").replace(" ", "") or 0))
    except (ValueError, TypeError):
        return 0


def safe_float(val):
    """Retorna None se vazio/NaN; senão float."""
    if pd.isna(val) or val == "" or str(val).lower() == "nan":
        return None
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def safe_int_or_none(val):
    """Retorna None se vazio/NaN; senão int."""
    if pd.isna(val) or val == "" or str(val).lower() == "nan":
        return None
    try:
        return int(float(str(val).replace(",", ".").replace(" ", "")))
    except (ValueError, TypeError):
        return None


def pct_from_decimal(val):
    """0.335836 → 33.5836  |  None → None"""
    v = safe_float(val)
    return round(v * 100, 4) if v is not None else None


def make_live_key(started_at: str, title: str) -> str:
    """Chave única por live: datetime + título."""
    raw = f"{started_at}|{title.strip()}"
    return raw[:120]


# ═══════════════════════════════════════════════════════════════════════════
# Creator-Live-Performance parser
# ═══════════════════════════════════════════════════════════════════════════

# Colunas que aparecem APENAS em v1 (antigo)
V1_LIVES_MARKERS = {"Gross revenue", "Direct GMV", "Peak viewers", "Viewers"}
# Colunas que aparecem APENAS em v2 (novo)
V2_LIVES_MARKERS = {"Attributed GMV", "AOV", "LIVE impressions", "GMV Per Hour", "Show GPM"}


def detect_lives_schema(columns: set) -> str:
    """Detecta 'v1' ou 'v2' do export Creator-Live-Performance."""
    v1_hits = len(columns & V1_LIVES_MARKERS)
    v2_hits = len(columns & V2_LIVES_MARKERS)
    if v2_hits > v1_hits:
        return "v2"
    if v1_hits > 0:
        return "v1"
    return "v1"  # fallback


def parse_lives_v1(row) -> dict:
    """Schema antigo (até abr/2026)."""
    gmv_bruto  = parse_brl(row.get("Gross revenue", 0))
    gmv_direct = parse_brl(row.get("Direct GMV", 0))
    avg_price  = parse_brl(row.get("Avg. price", 0))
    viewers    = safe_int(row.get("Viewers", 0))
    ctr        = safe_float(row.get("CTR", 0)) or 0
    ctor       = safe_float(row.get("CTOR (SKU orders)", 0)) or 0

    return {
        "gmv_bruto":             gmv_bruto,
        "gmv_direct":            gmv_direct,
        "items_sold":            safe_int(row.get("Items sold", 0)),
        "customers":             safe_int(row.get("Customers", 0)),
        "avg_price":             avg_price,
        "orders":                safe_int(row.get("Orders paid for", 0)),
        "views":                 safe_int(row.get("Views", 0)),
        "viewers":               viewers,
        "peak_viewers":          safe_int(row.get("Peak viewers", 0)),
        "new_followers":         safe_int(row.get("New followers", 0)),
        "avg_view_duration_sec": safe_int(row.get("Avg. view duration", 0)),
        "likes":                 safe_int(row.get("Likes", 0)),
        "comments":              safe_int(row.get("Comments", 0)),
        "shares":                safe_int(row.get("Shares", 0)),
        "product_impressions":   safe_int(row.get("Product impressions", 0)),
        "product_clicks":        safe_int(row.get("Product clicks", 0)),
        "ctr":                   round(ctr * 100, 4),
        "ctor":                  round(ctor * 100, 4),
        "gmv_per_viewer":        round(gmv_direct / viewers, 4) if viewers > 0 else 0,
        "schema_version":        "v1",
    }


def parse_lives_v2(row) -> dict:
    """Schema novo (mai/2026+).

    Diferenças semânticas importantes:
    - 'Attributed GMV' substitui 'Direct GMV'. Aqui mapeamos pra AMBOS
      gmv_bruto e gmv_direct (mesmo valor) — o TikTok não publica mais o
      gross revenue total da live. Documentar essa quebra de série temporal.
    - 'Viewers' e 'Peak viewers' não existem mais → NULL.
    - 'AOV' substitui 'Avg. price'.
    - Rates (CTR, CTOR, follow rate etc.) vêm como decimal 0-1 → converter %.
    """
    attr_gmv   = parse_brl(row.get("Attributed GMV", 0))
    avg_price  = parse_brl(row.get("AOV", 0))
    # No v2 não temos Viewers — usar Views como proxy pra calcular gmv_per_viewer
    # mas guardar viewers/peak como NULL pra ficar explícito que é dado ausente.
    views      = safe_int(row.get("Views", 0))

    return {
        "gmv_bruto":             attr_gmv,        # ⚠️ mudança semântica vs v1
        "gmv_direct":            attr_gmv,
        "items_sold":            safe_int(row.get("Attributed items sold", 0)),
        "customers":             safe_int(row.get("Customers", 0)),
        "avg_price":             avg_price,
        "orders":                safe_int(row.get("Attributed orders", 0)),
        "views":                 views,
        "viewers":               None,            # 🚫 removido do export
        "peak_viewers":          None,            # 🚫 removido do export
        "new_followers":         safe_int(row.get("New followers", 0)),
        # No v2: "Avg. viewing duration per viewer" vem em segundos (= antigo Avg. view duration)
        "avg_view_duration_sec": safe_int(row.get("Avg. viewing duration per viewer", 0)),
        "likes":                 safe_int(row.get("Likes", 0)),
        "comments":              safe_int(row.get("Comments", 0)),
        "shares":                safe_int(row.get("Shares", 0)),
        "product_impressions":   safe_int(row.get("Product impressions", 0)),
        "product_clicks":        safe_int(row.get("Product clicks", 0)),
        "ctr":                   pct_from_decimal(row.get("CTR", 0)),
        "ctor":                  pct_from_decimal(row.get("CTOR (SKU order)", 0))
                                 or pct_from_decimal(row.get("CTOR", 0)),
        "gmv_per_viewer":        None,            # sem viewers, não dá pra calcular
        # ── métricas novas (v2) ──
        "live_impressions":      safe_int_or_none(row.get("LIVE impressions", 0)),
        "impressions_per_hour":  safe_int_or_none(row.get("Impressions per hour", 0)),
        "gmv_per_hour":          parse_brl(row.get("GMV Per Hour", 0)) or None,
        "show_gpm":              parse_brl(row.get("Show GPM", 0)) or None,
        "watch_gpm":             parse_brl(row.get("Watch GPM", 0)) or None,
        "ads_roas":              safe_float(row.get("Ads ROAS")),
        "ads_cost":              parse_brl(row.get("Ads Cost", 0)) or None,
        "ads_gmv":               parse_brl(row.get("Ads GMV", 0)) or None,
        "follow_rate":           safe_float(row.get("Follow rate")),
        "comment_rate":          safe_float(row.get("Comment rate")),
        "share_rate":            safe_float(row.get("Share rate")),
        "like_rate":             safe_float(row.get("Like rate")),
        "tap_through_rate":      safe_float(row.get("Tap-through rate")),
        "sku_order_rate":        safe_float(row.get("SKU order rate")),
        "live_ctr":              safe_float(row.get("LIVE CTR")),
        "attributed_sku_orders": safe_int_or_none(row.get("Attributed SKU orders", 0)),
        "schema_version":        "v2",
    }


def process_lives_export(filepath: str) -> list:
    """Lê Creator-Live-Performance_*.xlsx e retorna lista pra upsert em `lives`."""
    print(f"  → {Path(filepath).name}")
    try:
        df = pd.read_excel(filepath, header=None, skiprows=2)
    except Exception as e:
        print(f"    [ERRO] ao ler arquivo: {e}")
        return []

    headers = df.iloc[0].tolist()
    df.columns = [str(h).strip() if not pd.isna(h) else f"_col{i}" for i, h in enumerate(headers)]
    df = df.iloc[1:].reset_index(drop=True)

    schema = detect_lives_schema(set(df.columns))
    parser = parse_lives_v2 if schema == "v2" else parse_lives_v1
    print(f"    schema detectado: {schema}")

    rows = []
    skipped = 0

    for _, r in df.iterrows():
        dur_sec = safe_int(r.get("Duration", 0))
        if dur_sec <= 300:
            skipped += 1
            continue

        raw_dt = str(r.get("Start time", "")).strip()
        started_at = pd.to_datetime(raw_dt, errors="coerce")
        if pd.isna(started_at):
            skipped += 1
            continue

        title = str(r.get("Livestream", "")).strip()
        iso = started_at.isoformat()

        record = {
            "live_key":     make_live_key(iso, title),
            "title":        title,
            "started_at":   iso,
            "date":         started_at.date().isoformat(),
            "month":        started_at.strftime("%Y-%m"),
            "day_of_week":  int(started_at.weekday()),
            "hour":         int(started_at.hour),
            "duration_sec": dur_sec,
            "duration_min": round(dur_sec / 60, 1),
        }
        record.update(parser(r))
        rows.append(record)

    print(f"    {len(rows)} lives válidas · {skipped} ignoradas (curtas/inválidas)")
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Overview (store daily) parser
# ═══════════════════════════════════════════════════════════════════════════

# v1 (PT-BR longo, jan-mar/26): "Valor bruto da mercadoria (R$)", "Reembolsos (R$)" etc.
# v2 (PT-BR curto, mar+): "GMV Bruto", "GMV Líquido", "Views", "Visitas" etc.

V1_OVERVIEW_MARKERS = {"Valor bruto da mercadoria (R$)", "Reembolsos (R$)",
                       "Visualizações de página", "Visitas à página da loja",
                       "Pedido de SKU"}
V2_OVERVIEW_MARKERS = {"GMV Bruto", "GMV Líquido", "Views", "Visitas",
                       "Pedido SKU", "Taxa Cancelamento"}
# v3 = "Shop Analytics_Key metrics_*" (mai/2026+)
V3_OVERVIEW_MARKERS = {"Receita bruta", "Itens reembolsados", "Pedidos de SKU",
                       "Impressões únicas do produto", "Cliques únicos", "Visitantes"}


def detect_overview_schema(columns: set) -> str:
    v1_hits = len(columns & V1_OVERVIEW_MARKERS)
    v2_hits = len(columns & V2_OVERVIEW_MARKERS)
    v3_hits = len(columns & V3_OVERVIEW_MARKERS)
    best = max(v1_hits, v2_hits, v3_hits)
    if best == 0:
        return "v1"
    if best == v3_hits:
        return "v3"
    if best == v2_hits:
        return "v2"
    return "v1"


def parse_overview_v1(row) -> dict:
    gmv     = parse_brl(row.get("Valor bruto da mercadoria (R$)", 0))
    reimb   = parse_brl(row.get("Reembolsos (R$)", 0))
    gmv_cof = parse_brl(row.get("Valor bruto da mercadoria (com cofinanciamento do TikTok)", 0))
    conv = safe_float(str(row.get("Taxa de conversão", "0")).replace("%", "").replace(",", ".")) or 0.0

    return {
        "gmv_bruto":        gmv,
        "reembolsos":       reimb,
        "gmv_cofinanciado": gmv_cof,
        "items_sold":       safe_int(row.get("Itens vendidos", 0)),
        "unique_customers": safe_int(row.get("Clientes únicos", 0)),
        "page_views":       safe_int(row.get("Visualizações de página", 0)),
        "store_visits":     safe_int(row.get("Visitas à página da loja", 0)),
        "sku_orders":       safe_int(row.get("Pedido de SKU", 0)),
        "orders":           safe_int(row.get("Pedidos", 0)),
        "conversion_rate":  conv,
    }


def parse_overview_v3(row) -> dict:
    """Schema 'Shop Analytics_Key metrics' (a partir de abr/2026).

    Diferenças vs v1/v2:
    - 'GMV' (não 'GMV Bruto' nem 'Valor bruto...')
    - 'Receita bruta' separada do GMV (provavelmente é o gross faturamento antes de cancel)
    - 'Visitantes' (em vez de 'Visitas')
    - 'Visualizações de página' (volta o nome da v1)
    - 'Taxa de conversão' vem como decimal 0-1 (0.015 = 1.5%)
    - Métricas novas: impressões/cliques de produto (úteis pro funil)
    """
    gmv          = parse_brl(row.get("GMV", 0))
    receita      = parse_brl(row.get("Receita bruta", 0))
    # Reembolsos: temos "Itens reembolsados" (count, não valor). Estimativa de valor =
    # receita_bruta - gmv (gross menos líquido), se positivo.
    reimb        = max(0.0, receita - gmv) if receita and gmv else 0.0
    conv_decimal = safe_float(row.get("Taxa de conversão"))
    # Vem como decimal (0.015). Converter pra percentual (1.5).
    conv = round(conv_decimal * 100, 4) if conv_decimal is not None else 0.0

    return {
        "gmv_bruto":        gmv,
        "reembolsos":       reimb,
        "gmv_cofinanciado": 0.0,
        "items_sold":       safe_int(row.get("Itens vendidos", 0)),
        "unique_customers": safe_int(row.get("Clientes", 0)),
        "page_views":       safe_int(row.get("Visualizações de página", 0)),
        "store_visits":     safe_int(row.get("Visitantes", 0)),
        "sku_orders":       safe_int(row.get("Pedidos de SKU", 0)),
        "orders":           safe_int(row.get("Pedidos", 0)),
        "conversion_rate":  conv,
    }


def parse_overview_v2(row) -> dict:
    """Schema novo. Tem 'GMV Líquido' (= bruto - reembolsos) em vez de Reembolsos explícito.
    Reembolsos derivado: GMV Bruto - GMV Líquido."""
    gmv_bruto   = parse_brl(row.get("GMV Bruto", 0))
    gmv_liquido = parse_brl(row.get("GMV Líquido", 0))
    reembolsos  = max(0.0, gmv_bruto - gmv_liquido) if gmv_bruto and gmv_liquido else 0.0
    # Taxa de cancelamento ≠ taxa de conversão. Não dá pra mapear direto. Deixa 0.
    return {
        "gmv_bruto":        gmv_bruto,
        "reembolsos":       reembolsos,
        "gmv_cofinanciado": 0.0,  # não presente no v2
        "items_sold":       safe_int(row.get("Itens Vendidos", 0)),
        "unique_customers": safe_int(row.get("Clientes Únicos", 0)),
        "page_views":       safe_int(row.get("Views", 0)),
        "store_visits":     safe_int(row.get("Visitas", 0)),
        "sku_orders":       safe_int(row.get("Pedido SKU", 0)),
        "orders":           safe_int(row.get("Pedidos", 0)),
        "conversion_rate":  0.0,
    }


def process_overview_export(filepath: str) -> list:
    """Lê Overview_*.xlsx e retorna lista pra upsert em `store_daily`."""
    print(f"  → {Path(filepath).name}")
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        print(f"    [ERRO] ao ler arquivo: {e}")
        return []

    # Encontra linha header (contém 'Data')
    header_row = None
    for i, row in df.iterrows():
        if "Data" in [str(v).strip() for v in row.tolist()]:
            header_row = i
            break

    if header_row is None:
        print("    [AVISO] Não encontrou seção 'Dados diários'")
        return []

    headers = df.iloc[header_row].tolist()
    data    = df.iloc[header_row + 1:].reset_index(drop=True)
    data.columns = [str(h).strip() if not pd.isna(h) else f"_c{i}" for i, h in enumerate(headers)]

    schema = detect_overview_schema(set(data.columns))
    parser = {"v1": parse_overview_v1, "v2": parse_overview_v2, "v3": parse_overview_v3}[schema]
    print(f"    schema detectado: {schema}")

    rows = []
    for _, r in data.iterrows():
        raw_date = str(r.get("Data", "")).strip()
        if not raw_date or raw_date == "nan":
            continue

        dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            continue

        record = {
            "date":  dt.date().isoformat(),
            "month": dt.strftime("%Y-%m"),
        }
        record.update(parser(r))
        rows.append(record)

    print(f"    {len(rows)} dias processados")
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

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
        elif name.lower().startswith("overview") or name.lower().startswith("shop analytics_key metrics"):
            all_store_daily.extend(process_overview_export(str(f)))
        else:
            print(f"  [SKIP] {name} — tipo não reconhecido")

    # Dedup: prioriza schema v2 (mais novo) em caso de empate por live_key.
    seen_lives = {}
    for r in all_lives:
        existing = seen_lives.get(r["live_key"])
        if existing is None or (existing.get("schema_version") == "v1" and r.get("schema_version") == "v2"):
            seen_lives[r["live_key"]] = r
    lives_dedup = list(seen_lives.values())

    # Normalização: PostgREST exige todas as chaves iguais em batch upsert.
    # Coleta união de chaves e preenche None onde falta.
    if lives_dedup:
        all_keys = set()
        for r in lives_dedup:
            all_keys.update(r.keys())
        for r in lives_dedup:
            for k in all_keys:
                if k not in r:
                    r[k] = None

    seen_daily = {}
    for r in all_store_daily:
        seen_daily[r["date"]] = r
    daily_dedup = list(seen_daily.values())

    # Quebra por schema (sanity)
    v1_count = sum(1 for r in lives_dedup if r.get("schema_version") == "v1")
    v2_count = sum(1 for r in lives_dedup if r.get("schema_version") == "v2")

    print(f"\n{'─'*40}")
    print(f"Lives únicas: {len(lives_dedup)}  (v1: {v1_count} · v2: {v2_count})")
    print(f"Dias de loja únicos: {len(daily_dedup)}")
    print(f"{'─'*40}\n")

    print("Sincronizando com Supabase...")
    upsert("lives",       lives_dedup, on_conflict="live_key")
    upsert("store_daily", daily_dedup, on_conflict="date")

    print("\n✓ ETL Lives concluído.\n")


if __name__ == "__main__":
    main()
