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
            "current_tier":   str(r.get("tier", "starter")).lower(),
            "gmv_live_mtd":   float(r.get("gmv_liquido", 0) or 0),
            "gmv_video_mtd":  0,
            "last_updated_at": str(r.get("last_updated_at", "")) or None,
        })
    rows = [r for r in rows if r["affiliate_id"]]
    upsert("affiliates", rows, on_conflict="affiliate_id")

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
    upsert("performance_periods", rows, on_conflict="affiliate_id,periodo")

JOBS = {
    "affiliates":           sync_affiliates,
    "performance_periods":  sync_performance_periods,
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
