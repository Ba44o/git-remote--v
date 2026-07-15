#!/usr/bin/env python3
"""
Análise de RECOMPRA / LTV por cliente (CPF) — TikTok Shop Orders API, abr-jun/26.
Privacidade: o CPF é HASHEADO (sha256) na entrada — NÃO guarda PII crua; só agrega.
Mede: clientes únicos, taxa de recompra, distribuição de frequência, LTV, AOV,
% da receita vinda de clientes recorrentes. Decimal nos valores.
"""
import os, sys, json, hashlib, urllib.request
from decimal import Decimal as D
from collections import defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar_dados import chamar

def ep(s): return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
GE, LT = ep("2026-04-01"), ep("2026-07-01")
def h(x): return hashlib.sha256(str(x).encode()).hexdigest()[:16] if x else None
def dec(v):
    try: return D(str(v)) if v not in (None, "") else D(0)
    except Exception: return D(0)

cust = defaultdict(lambda: {"n": 0, "gmv": D(0)})   # cpf_hash -> pedidos, gasto
n_ord = 0; n_sem_cpf = 0; token = None; page = 0
while True:
    p = {"page_size": 100, "sort_field": "create_time", "sort_order": "ASC"}
    if token: p["page_token"] = token
    r = chamar("POST", "/order/202309/orders/search", params=p,
               body={"create_time_ge": GE, "create_time_lt": LT})
    if r.get("code") != 0:
        print(f"  [API code={r.get('code')}] {str(r.get('message'))[:80]}"); break
    d = r.get("data", {}); orders = d.get("orders", [])
    for o in orders:
        st = (o.get("status") or "").upper()
        if "CANCEL" in st: continue                      # só vendas válidas
        cpf = o.get("cpf")
        pay = o.get("payment") or {}
        tot = dec(pay.get("total_amount"))
        n_ord += 1
        if not cpf: n_sem_cpf += 1; continue
        c = cust[h(cpf)]; c["n"] += 1; c["gmv"] += tot
    token = d.get("next_page_token"); page += 1
    if page % 10 == 0: print(f"  …{page} páginas · {n_ord} pedidos válidos · {len(cust)} clientes", flush=True)
    if not token or not orders: break

# ---- métricas ----
ncli = len(cust)
tot_gmv = sum((c["gmv"] for c in cust.values()), D(0))
tot_ped = sum(c["n"] for c in cust.values())
recorrentes = {k: c for k, c in cust.items() if c["n"] >= 2}
gmv_rec = sum((c["gmv"] for c in recorrentes.values()), D(0))
ped_rec = sum(c["n"] for c in recorrentes.values())
# distribuição de frequência
dist = defaultdict(int)
for c in cust.values():
    b = "1x" if c["n"] == 1 else ("2x" if c["n"] == 2 else ("3-4x" if c["n"] <= 4 else "5x+"))
    dist[b] += 1

print("\n" + "=" * 66)
print("RECOMPRA / LTV — TikTok Shop, abr-jun/26 (só válidos · CPF hasheado)")
print("=" * 66)
print(f"pedidos válidos: {n_ord:,}  (sem CPF: {n_sem_cpf})")
print(f"clientes únicos (CPF): {ncli:,}")
print(f"pedidos/cliente (média): {tot_ped/ncli:.2f}" if ncli else "—")
print(f"AOV: R$ {tot_gmv/tot_ped:,.2f}" if tot_ped else "—")
print(f"LTV médio 3m (gasto/cliente): R$ {tot_gmv/ncli:,.2f}" if ncli else "—")
print(f"\nRECOMPRA:")
print(f"  clientes recorrentes (2+ pedidos): {len(recorrentes):,} = {len(recorrentes)/ncli*100:.1f}% dos clientes" if ncli else "—")
print(f"  % dos PEDIDOS de recorrentes: {ped_rec/tot_ped*100:.1f}%" if tot_ped else "—")
print(f"  % da RECEITA de recorrentes: {gmv_rec/tot_gmv*100:.1f}%" if tot_gmv else "—")
print(f"  LTV médio do recorrente: R$ {gmv_rec/len(recorrentes):,.2f}" if recorrentes else "—")
print(f"\nDISTRIBUIÇÃO de frequência (3 meses):")
for b in ["1x", "2x", "3-4x", "5x+"]:
    print(f"  {b:<6} {dist[b]:>7,} clientes ({dist[b]/ncli*100:>4.1f}%)" if ncli else b)
