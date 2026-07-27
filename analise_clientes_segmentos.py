#!/usr/bin/env python3
"""
Módulo Clientes — segmentos, geo e LTV POR CREATOR (abr-jun/26).
Privacidade: CPF é HASHEADO na entrada; nome/CPF cru NUNCA saem. Só agregados + id hash.

Segmentação (realidade discovery-commerce, não o modelo de recompra do Dashboardly):
  VIP            = 3+ pedidos
  Recorrente     = 2 pedidos
  Único recente  = 1 pedido, último <= 60d  (ainda pode voltar)
  Único frio     = 1 pedido, último > 60d   (churn real)

Diferencial que o Dashboardly NÃO tem: cliente → creator que o trouxe (1º pedido),
via extrato_pedidos (order_id → creator). Responde "que creator traz cliente que VOLTA".
"""
import os, sys, json, hashlib, urllib.request
from decimal import Decimal as D
from collections import defaultdict
from datetime import datetime, timezone, date
from dotenv import load_dotenv
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
load_dotenv(os.path.join(BASE, ".env"))
from coletar_dados import chamar

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SK, "Authorization": f"Bearer {SK}"}
SCR = "/private/tmp/claude-501/-Users-user-Documents-VS-Claude-Teste/8ca2de48-2449-4f41-aa50-1f0f3434200f/scratchpad"
HOJE = date.today()

def ep(s): return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
def h8(x): return hashlib.sha256(str(x).encode()).hexdigest()[:8]
def f(v):
    try: return float(D(str(v))) if v not in (None, "") else 0.0
    except Exception: return 0.0
def pageall(b, order="id"):
    """Paginação DETERMINÍSTICA: sem order=<coluna única> o offset pula/duplica linhas."""
    out = []; off = 0
    sep = "&" if "?" in b else "?"
    while True:
        r = json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/rest/v1/{b}{sep}order={order}&limit=1000&offset={off}", headers=H)))
        out += r
        if len(r) < 1000: break
        off += 1000
    return out

# 1) pedidos abr-jun (Orders API)
cust = defaultdict(lambda: {"n":0,"gmv":0.0,"first":"9999","last":"0000","uf":None,"cid":None,"o1":None})
tok = None; page = 0; n_ord = 0
GE, LT = ep("2026-04-01"), ep("2026-07-01")
while True:
    p = {"page_size":100,"sort_field":"create_time","sort_order":"ASC"}
    if tok: p["page_token"] = tok
    r = chamar("POST", "/order/202309/orders/search", params=p, body={"create_time_ge":GE,"create_time_lt":LT})
    if r.get("code") != 0:
        print(f"[API {r.get('code')}] {str(r.get('message'))[:70]}"); break
    d = r.get("data", {}); orders = d.get("orders", [])
    for o in orders:
        if "CANCEL" in (o.get("status") or "").upper(): continue
        cpf = o.get("cpf")
        if not cpf: continue
        k = h8(cpf); c = cust[k]; n_ord += 1
        c["n"] += 1; c["gmv"] += f((o.get("payment") or {}).get("total_amount"))
        dt = datetime.fromtimestamp(int(o.get("create_time") or 0), timezone.utc).strftime("%Y-%m-%d")
        if dt < c["first"]: c["first"] = dt; c["o1"] = str(o.get("id"))
        if dt > c["last"]: c["last"] = dt
        ra = o.get("recipient_address") or {}; di = ra.get("district_info") or []
        uf = next((x.get("address_name") for x in di if x.get("address_level")=="L1"), None)
        cid = next((x.get("address_name") for x in di if x.get("address_level")=="L2"), None)
        if uf and not c["uf"]: c["uf"] = uf; c["cid"] = cid
    tok = d.get("next_page_token"); page += 1
    if page % 20 == 0: print(f"  …{page}p · {n_ord} pedidos · {len(cust)} clientes", flush=True)
    if not tok or not orders: break

# 2) atribuição creator (order_id → creator) via extrato de afiliada
ext = pageall("extrato_pedidos?periodo=in.(2026-04,2026-05,2026-06)&select=order_id,creator")
o2c = {}
for r in ext:
    oid = str(r.get("order_id") or "")
    if oid and oid not in o2c: o2c[oid] = r.get("creator") or ""

# 3) segmenta
def seg(c):
    if c["n"] >= 3: return "vip"
    if c["n"] == 2: return "recorrente"
    dias = (HOJE - date.fromisoformat(c["last"])).days if c["last"] != "0000" else 999
    return "unico_recente" if dias <= 60 else "unico_frio"

SEGS = ["vip","recorrente","unico_recente","unico_frio"]
segst = {s: {"n":0,"gmv":0.0} for s in SEGS}
uf_ag = defaultdict(lambda: {"n":0,"gmv":0.0})
cre_ag = defaultdict(lambda: {"n":0,"gmv":0.0,"volta":0})
rows = []
for k, c in cust.items():
    s = seg(c); segst[s]["n"] += 1; segst[s]["gmv"] += c["gmv"]
    if c["uf"]: uf_ag[c["uf"]]["n"] += 1; uf_ag[c["uf"]]["gmv"] += c["gmv"]
    cr = o2c.get(c["o1"] or "", "")
    key = cr if cr else "(loja / sem afiliada)"
    a = cre_ag[key]; a["n"] += 1; a["gmv"] += c["gmv"]
    if c["n"] >= 2: a["volta"] += 1
    rows.append({"id":k,"seg":s,"n":c["n"],"gmv":round(c["gmv"],2),
                 "aov":round(c["gmv"]/c["n"],2) if c["n"] else 0,
                 "first":c["first"],"last":c["last"],"uf":c["uf"],"cid":c["cid"],"cre":cr})
rows.sort(key=lambda r: -r["gmv"])
tot_gmv = sum(c["gmv"] for c in cust.values())
# creators: só os com base relevante
cre = sorted([{"c":k,"n":v["n"],"gmv":round(v["gmv"]),"ltv":round(v["gmv"]/v["n"],2),
               "volta":round(v["volta"]/v["n"]*100,1)} for k,v in cre_ag.items() if v["n"]>=20],
             key=lambda x:-x["n"])[:12]
out = {"tot_cli":len(cust),"tot_gmv":round(tot_gmv,2),"tot_ped":n_ord,
       "seg":{s:{"n":segst[s]["n"],"gmv":round(segst[s]["gmv"],2),
                 "ltv":round(segst[s]["gmv"]/segst[s]["n"],2) if segst[s]["n"] else 0} for s in SEGS},
       "uf":{k:{"n":v["n"],"gmv":round(v["gmv"])} for k,v in uf_ag.items()},
       "cre":cre,"top":rows[:14]}
json.dump(out, open(f"{SCR}/clientes.json","w"), ensure_ascii=False)
print(f"\n✓ {len(cust)} clientes · {n_ord} pedidos · GMV R$ {tot_gmv:,.0f}")
for s in SEGS:
    v = segst[s]; print(f"  {s:<14} {v['n']:>6} ({v['n']/len(cust)*100:>4.1f}%) · LTV R$ {v['gmv']/v['n'] if v['n'] else 0:>7.2f} · receita R$ {v['gmv']:>10,.0f}")
print(f"\nUFs: {len(uf_ag)} · creators com 20+ clientes: {len(cre)}")
for c in cre[:5]: print(f"  {c['c'][:24]:<25} {c['n']:>4} clientes · LTV R$ {c['ltv']:>7.2f} · volta {c['volta']:>4.1f}%")
