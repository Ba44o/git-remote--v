"""
Rhode Jeans — Sync para Supabase
Migra o warehouse local (CSVs) para as tabelas do Supabase.

Uso:
  python agente_rhode/sync_supabase.py
  python agente_rhode/sync_supabase.py --only affiliates performance_periods
"""
import os, sys, argparse, json
import pandas as pd
import requests
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
WAREHOUSE    = Path("warehouse")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERRO] Defina SUPABASE_URL e SUPABASE_SERVICE_KEY no ambiente.")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

def upsert(table: str, rows: list[dict], chunk=500, on_conflict: str = ""):
    params = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{params}"
    total = 0
    for i in range(0, len(rows), chunk):
        batch = rows[i:i+chunk]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code not in (200, 201):
            print(f"  [ERRO] {table} batch {i}: {r.status_code} {r.text[:200]}")
        else:
            total += len(batch)
    print(f"  [✓] {table} → {total} linhas")

def sync_affiliates():
    df = pd.read_csv(WAREHOUSE / "creators_master.csv").fillna("")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "affiliate_id":   str(r.get("creator_id", "")).strip(),
            "tiktok_handle":  str(r.get("creator_id", "")).strip(),
            "current_tier":   str(r.get("tier", "iniciante")).lower(),
            "gmv_live_mtd":   float(r.get("gmv_liquido", 0) or 0),
            "gmv_video_mtd":  0,
            "last_updated_at": str(r.get("last_updated_at", "")) or None,
        })
    rows = [r for r in rows if r["affiliate_id"]]
    upsert("affiliates", rows, on_conflict="affiliate_id")
    cleanup_legacy_tier_labels()


# Mapa labels do programa antigo (Ferro/Prata/Ouro/Diamante etc) → novo programa.
# Aplicado em affiliates pra cobrir rows fantasma que existiam antes do ETL alinhar
# TIER_RULES com o programa público — upsert sem delete deixa essas rows congeladas.
LEGACY_TIER_MAP = {
    "ferro":    "iniciante",
    "starter":  "iniciante",
    "prata":    "silver",
    "ouro":     "gold",
    "diamante": "diamond",
    # "bronze" é nome comum entre velho e novo programa — só threshold mudou.
    # Como o sync_affiliates re-upserta com o tier novo pra qualquer creator em
    # creators_master.csv, as rows "bronze" que sobram são creators sumidos
    # do warehouse — manter como bronze é razoável (não tem como saber o GMV atual).
}

def cleanup_legacy_tier_labels():
    """PATCH em affiliates traduzindo labels do programa antigo pro novo."""
    fixed = 0
    for old, new in LEGACY_TIER_MAP.items():
        url = f"{SUPABASE_URL}/rest/v1/affiliates?current_tier=eq.{old}"
        r = requests.patch(url, headers={**HEADERS, "Prefer": "return=minimal"},
                           json={"current_tier": new})
        if r.status_code in (200, 204):
            fixed += 1
            print(f"  [✓] cleanup current_tier: {old} → {new}")
        else:
            print(f"  [AVISO] cleanup {old} → {new}: {r.status_code} {r.text[:200]}")
    if fixed:
        print(f"  Total: {fixed} label(s) migrado(s) do programa antigo.")

def sync_performance_periods():
    df = pd.read_csv(WAREHOUSE / "raw_imports.csv").fillna("")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "affiliate_id":   str(r.get("creator_id", "")).strip(),
            "periodo":        str(r.get("periodo", "")),
            "periodo_inicio": str(r.get("periodo_inicio", "")) or None,
            "periodo_fim":    str(r.get("periodo_fim", "")) or None,
            "gmv_bruto":      float(r.get("gmv_bruto", 0) or 0),
            "gmv_liquido":    float(r.get("gmv_liquido", 0) or 0),
            "reembolso":      float(r.get("reembolso", 0) or 0),
            "refund_pct":     float(r.get("refund_pct", 0) or 0),
            "pedidos":        int(float(r.get("pedidos", 0) or 0)),
            "aov":            float(r.get("aov", 0) or 0),
            "videos":         int(float(r.get("videos", 0) or 0)),
            "lives":          int(float(r.get("lives", 0) or 0)),
            "comissao":       float(r.get("comissao_calculada", 0) or 0),
            "tier":           str(r.get("tier", "")),
        })
    rows = [r for r in rows if r["affiliate_id"] and r["periodo"]]
    # Deduplica por (affiliate_id, periodo) — mantém último registro
    seen = {}
    for r in rows:
        seen[(r["affiliate_id"], r["periodo"])] = r
    rows = list(seen.values())

    # DELETE-then-UPSERT por período: remove creators "fantasma" (linhas que existiam
    # em snapshots antigos do mesmo período mas não estão mais no export canônico).
    # Sem isso, ao reprocessar abril o sync só atualiza/insere — nunca remove.
    periodos_atuais = sorted({r["periodo"] for r in rows})
    print(f"  Limpando dados antigos de {len(periodos_atuais)} período(s) antes do upsert...")
    for p in periodos_atuais:
        url = f"{SUPABASE_URL}/rest/v1/performance_periods?periodo=eq.{p}"
        d = requests.delete(url, headers=HEADERS)
        if d.status_code not in (200, 204):
            print(f"  [AVISO] DELETE periodo={p}: {d.status_code} {d.text[:200]}")
        else:
            print(f"  [✓] DELETE periodo={p}")

    upsert("performance_periods", rows, on_conflict="affiliate_id,periodo")


def sync_performance_diario():
    """Sincroniza warehouse/raw_diario.csv → performance_diario (1 linha/dia, loja toda).
    Estratégia: UPSERT por data (PK). Não usa DELETE-then-UPSERT porque
    cada (data) é unicamente determinada e snapshots novos sempre prevalecem.
    """
    src = WAREHOUSE / "raw_diario.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_diario.py' antes.")
        return
    df = pd.read_csv(src).fillna(0)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "data":            str(r["data"]),
            "gmv_bruto":       float(r.get("gmv_bruto", 0) or 0),
            "gmv_liquido":     float(r.get("gmv_liquido", 0) or 0),
            "pedidos":         int(r.get("pedidos", 0) or 0),
            "cancelados":      int(r.get("cancelados", 0) or 0),
            "itens":           int(r.get("itens", 0) or 0),
            "clientes":        int(r.get("clientes", 0) or 0),
            "ticket":          float(r.get("ticket", 0) or 0),
            "taxa_cancel_pct": float(r.get("taxa_cancel_pct", 0) or 0),
        })
    rows = [r for r in rows if r["data"] and r["data"] != "0"]
    upsert("performance_diario", rows, on_conflict="data")


def sync_finance():
    """Sincroniza warehouse/raw_finance.csv → finance_statements (1 linha/statement).
    UPSERT por id (PK). Statements antigos não mudam; novos são adicionados."""
    src = WAREHOUSE / "raw_finance.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_finance.py' antes.")
        return
    df = pd.read_csv(src).fillna(0)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id":             str(r["id"]),
            "data":           str(r.get("data", "")) or None,
            "statement_time": int(r.get("statement_time", 0) or 0),
            "revenue_amount": float(r.get("revenue_amount", 0) or 0),
            "fee_amount":     float(r.get("fee_amount", 0) or 0),
            "shipping_cost":  float(r.get("shipping_cost", 0) or 0),
            "adjustment":     float(r.get("adjustment", 0) or 0),
            "net_sales":      float(r.get("net_sales", 0) or 0),
            "settlement":     float(r.get("settlement", 0) or 0),
            "payment_status": str(r.get("payment_status", "")),
            "currency":       str(r.get("currency", "BRL")),
        })
    rows = [r for r in rows if r["id"] and r["id"] != "0"]
    upsert("finance_statements", rows, on_conflict="id")


def sync_devolucoes():
    """Sincroniza warehouse/raw_devolucoes.csv → devolucoes (1 linha/item devolvido).
    UPSERT por id (return_line_item_id)."""
    src = WAREHOUSE / "raw_devolucoes.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_devolucoes.py' antes.")
        return
    df = pd.read_csv(src).fillna("")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id":            str(r["id"]),
            "return_id":     str(r.get("return_id", "")),
            "order_id":      str(r.get("order_id", "")),
            "data":          str(r.get("data", "")) or None,
            "product_name":  str(r.get("product_name", "")),
            "seller_sku":    str(r.get("seller_sku", "")),
            "sku_name":      str(r.get("sku_name", "")),
            "refund_item":   float(r.get("refund_item", 0) or 0),
            "refund_return": float(r.get("refund_return", 0) or 0),
            "return_reason": str(r.get("return_reason", "")),
            "return_status": str(r.get("return_status", "")),
            "return_type":   str(r.get("return_type", "")),
        })
    rows = [r for r in rows if r["id"]]
    upsert("devolucoes", rows, on_conflict="id")


def sync_affiliate_perf():
    """Sincroniza warehouse/raw_affiliate.csv → affiliate_perf (creator×dia×conteúdo).
    UPSERT por id."""
    src = WAREHOUSE / "raw_affiliate.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_affiliate.py' antes.")
        return
    df = pd.read_csv(src).fillna("")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id":           str(r["id"]),
            "creator":      str(r.get("creator", "")),
            "data":         str(r.get("data", "")) or None,
            "content_type": str(r.get("content_type", "")),
            "gmv":          float(r.get("gmv", 0) or 0),
            "comissao":     float(r.get("comissao", 0) or 0),
            "pedidos":      int(r.get("pedidos", 0) or 0),
            "itens":        int(r.get("itens", 0) or 0),
        })
    rows = [r for r in rows if r["id"]]
    upsert("affiliate_perf", rows, on_conflict="id")


def sync_seeding():
    """Sincroniza warehouse/raw_seeding.csv → seeding (convite×creator, atribuição por produto)."""
    src = WAREHOUSE / "raw_seeding.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_seeding.py' antes.")
        return
    df = pd.read_csv(src).fillna("")
    rows = []
    for _, r in df.iterrows():
        fs = str(r.get("has_free_sample", ""))
        rows.append({
            "id":               str(r["id"]),
            "creator":          str(r.get("creator", "")),
            "creator_nick":     str(r.get("creator_nick", "")),
            "convites":         int(float(r.get("convites", 0) or 0)),
            "n_produtos":       int(float(r.get("n_produtos", 0) or 0)),
            "has_free_sample":  fs not in ("", "False", "false", "0", "nan"),
            "status":           str(r.get("status", "")),
            "commission_pct":   float(r.get("commission_pct", 0) or 0),
            "product_ids":      str(r.get("product_ids", "")),
        })
    rows = [r for r in rows if r["id"]]
    upsert("seeding", rows, on_conflict="id")


def sync_creator_product():
    """Sincroniza warehouse/raw_creator_product.csv → affiliate_creator_product."""
    src = WAREHOUSE / "raw_creator_product.csv"
    if not src.exists():
        print(f"  [AVISO] {src} não existe. Rode 'python agente_rhode/etl_creator_product.py' antes.")
        return
    df = pd.read_csv(src).fillna("")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id":         str(r["id"]),
            "creator":    str(r.get("creator", "")),
            "product_id": str(r.get("product_id", "")),
            "data":       str(r.get("data", "")) or None,
            "produto":    str(r.get("produto", "")),
            "seller_sku": str(r.get("seller_sku", "")),
            "gmv":        float(r.get("gmv", 0) or 0),
            "comissao":   float(r.get("comissao", 0) or 0),
            "pedidos":    int(float(r.get("pedidos", 0) or 0)),
        })
    rows = [r for r in rows if r["id"]]
    upsert("affiliate_creator_product", rows, on_conflict="id")


JOBS = {
    "affiliates":           sync_affiliates,
    "performance_periods":  sync_performance_periods,
    "performance_diario":   sync_performance_diario,
    "finance":              sync_finance,
    "devolucoes":           sync_devolucoes,
    "affiliate_perf":       sync_affiliate_perf,
    "seeding":              sync_seeding,
    "creator_product":      sync_creator_product,
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", choices=list(JOBS.keys()))
    args = parser.parse_args()

    jobs = args.only or list(JOBS.keys())
    print("\n══════════════════════════════════════════")
    print("  Rhode Jeans — Sync Supabase")
    print("══════════════════════════════════════════\n")
    for j in jobs:
        print(f"▶ {j}")
        JOBS[j]()
    print("\n✅ Concluído.")

if __name__ == "__main__":
    main()
