#!/usr/bin/env python3
"""
Rhode — Popula a tabela live_produto (margem por produto de live) pro painel dash-live.
Fonte: relatorios/AAAA-MM/_live_margin_data.json (gerado pelo pipeline de margem por SKU
de live: _build_margem_sku.py + mapa product_id→cpv). ROOT (não dispara etl_sync).
Uso:  python3 atualizar_live_produto.py            # usa 2026-06
      python3 atualizar_live_produto.py 2026-06
"""
import os, sys, json, urllib.request, urllib.error
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"}

PER = sys.argv[1] if len(sys.argv) > 1 else "2026-06"
src = os.path.join(BASE, "relatorios", PER, "_live_margin_data.json")
if not os.path.exists(src):
    print(f"Não achei {src} — rode antes o pipeline de margem por SKU de live."); sys.exit(0)

data = json.load(open(src))
rows = []
for p in data:
    if p.get("cpv") is None:  # kits/sem custo ficam de fora
        continue
    pid = str(p.get("pid"))
    rows.append({
        "id": f"{PER}:{pid}", "periodo": PER, "product_id": pid,
        "produto": (p.get("nome") or "")[:120],
        "gmv": round(float(p.get("gmv") or 0), 2), "unidades": int(p.get("un") or 0),
        "pedidos": int(p.get("ped") or 0), "lives": int(p.get("lives") or 0),
        "cpv_un": round(float(p["cpv"]), 2),
        "margem": round(float(p.get("marg") or 0), 2),
        "margem_pct": round(float(p.get("margpct") or 0), 1),  # já em %
    })

body = json.dumps(rows).encode()
req = urllib.request.Request(SB + "/rest/v1/live_produto?on_conflict=id", data=body,
    headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
try:
    urllib.request.urlopen(req, timeout=120)
    tot = sum(r["gmv"] for r in rows); marg = sum(r["margem"] for r in rows)
    print(f"✓ live_produto ({PER}): {len(rows)} produtos · GMV R$ {tot:,.0f} · margem R$ {marg:,.0f}")
except urllib.error.HTTPError as e:
    print(f"[ERRO] {e.code}: {e.read()[:300]} (rodou live_produto.sql?)")
