#!/usr/bin/env python3
"""
Rhode — Tracker meta 10k peças/mês por canal, ATRIBUÍDO POR PEDIDO (origem real).
Cruza pedidos_sku (order_id, seller_sku, qty) × extrato_pedidos (order_id → content_type
da afiliada). Canais (cada peça 1 dono, soma ao net):
  video_afiliada = pedido de afiliada content VIDEO/SHOP/LINK · live_afiliada = LIVE
  loja_propria   = pedido SEM afiliada (venda direta: live própria não-afiliada + orgânico)
Referência à parte: live_propria_ref = lives da conta Rhode (live_attr, rooms).
Também: top SKUs por canal + semanal. Escreve tracker_canais + _tracker_data.json. ROOT.
"""
import os, json, urllib.request, urllib.error
from collections import defaultdict
from dotenv import load_dotenv
BASE=os.path.dirname(os.path.abspath(__file__)); load_dotenv(os.path.join(BASE,".env"))
SB=os.environ["SUPABASE_URL"]; SK=os.environ["SUPABASE_SERVICE_KEY"]
SBH={"apikey":SK,"Authorization":f"Bearer {SK}","Content-Type":"application/json"}
def pageall(base):
    out=[];off=0
    while True:
        b=json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/rest/v1/{base}&limit=1000&offset={off}",headers=SBH)))
        out+=b
        if len(b)<1000: break
        off+=1000
    return out
# METAS (peças) — crescer afiliada, segurar loja própria. Somam ao net 10k.
META={"video_afiliada":3600,"live_afiliada":2800,"loja_propria":3600}
META_NET=10000; META_PROPRIA_REF=2830
CHANS=["video_afiliada","live_afiliada","loja_propria"]
import datetime as _dt
_t=_dt.date.today()
MESES=[(_t.replace(day=1)-_dt.timedelta(days=1)).strftime("%Y-%m"), _t.strftime("%Y-%m")]  # mês anterior + atual (dinâmico)
NOW=_dt.datetime.utcnow().isoformat()
def wk(d):
    try: return min(5,(int(d[8:10])-1)//7+1)
    except: return 1
def canal_de(ct):
    if not ct: return "loja_propria"
    return "live_afiliada" if ct=="LIVE" else "video_afiliada"

out={"meta":META,"meta_net":META_NET,"meta_propria_ref":META_PROPRIA_REF,"meses":{}}
rows_db=[]
for mes in MESES:
    ini=mes+"-01"; y,m=int(mes[:4]),int(mes[5:7]); fim=(f"{y+1}-01-01" if m==12 else f"{y}-{m+1:02d}-01")
    ext=pageall(f"extrato_pedidos?periodo=eq.{mes}&select=order_id,content_type")
    o2c={}
    for r in ext:
        oid=str(r.get("order_id") or "")
        if oid and oid not in o2c: o2c[oid]=(r.get("content_type") or "").upper()
    ped=pageall(f"pedidos_sku?periodo=eq.{mes}&select=order_id,seller_sku,qty,produto,status,data")
    ch=defaultdict(lambda:{"pecas":0,"sem":defaultdict(int),"skus":defaultdict(lambda:[0,""])})
    net=0; net_sem=defaultdict(int)
    for p in ped:
        if 'CANCEL' in (p.get('status') or '').upper(): continue
        q=int(p.get('qty') or 0); net+=q; w=wk(p.get('data') or ini); net_sem[w]+=q
        c=canal_de(o2c.get(str(p.get('order_id') or '')))
        a=ch[c]; a["pecas"]+=q; a["sem"][w]+=q
        sku=(p.get('seller_sku') or '—'); a["skus"][sku][0]+=q; a["skus"][sku][1]=(p.get('produto') or '')[:34]
    la=pageall(f"live_attr?periodo=eq.{mes}&select=itens,pedidos")
    propria_ref=sum(int(r.get("itens") or r.get("pedidos") or 0) for r in la)
    def topskus(a): return [{"sku":s,"produto":d[1],"pecas":d[0]} for s,d in sorted(a["skus"].items(),key=lambda x:-x[1][0])[:6]]
    out["meses"][mes]={"net":net,"net_sem":{str(k):net_sem[k] for k in sorted(net_sem)},"propria_ref":propria_ref,
        "canais":{c:{"pecas":ch[c]["pecas"],"meta":META[c],"sem":{str(s):ch[c]["sem"][s] for s in sorted(ch[c]["sem"])},"top":topskus(ch[c])} for c in CHANS}}
    for c in CHANS:
        rows_db.append({"id":f"{mes}:{c}","mes":mes,"canal":c,"pecas":ch[c]["pecas"],"meta_pecas":META[c],
            "semanas":{str(s):ch[c]["sem"][s] for s in sorted(ch[c]["sem"])},"top_skus":topskus(ch[c]),"updated_at":NOW})
    rows_db.append({"id":f"{mes}:net","mes":mes,"canal":"net","pecas":net,"meta_pecas":META_NET,"semanas":{str(k):net_sem[k] for k in sorted(net_sem)},"top_skus":None,"updated_at":NOW})
    rows_db.append({"id":f"{mes}:live_propria_ref","mes":mes,"canal":"live_propria_ref","pecas":propria_ref,"meta_pecas":META_PROPRIA_REF,"semanas":None,"top_skus":None,"updated_at":NOW})

json.dump(out,open(os.path.join(BASE,"_tracker_data.json"),"w"))
try:
    urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/tracker_canais?on_conflict=id",data=json.dumps(rows_db).encode(),headers={**SBH,"Prefer":"resolution=merge-duplicates,return=minimal"},method="POST"),timeout=60)
    print("✓ tracker_canais gravada")
except urllib.error.HTTPError as e:
    print(f"(não gravada — rode tracker_canais.sql · {e.code})")
for mes in MESES:
    d=out["meses"][mes]; print(f"\n{mes} · net {d['net']:,}/{META_NET:,} ({d['net']/META_NET*100:.0f}%) · live própria(ref) {d['propria_ref']:,}")
    for c in CHANS:
        v=d["canais"][c]; print(f"  {c:<16} {v['pecas']:>5,}/{v['meta']:>5,} ({v['pecas']/v['meta']*100 if v['meta'] else 0:>3.0f}%) top: {', '.join(t['sku'] for t in v['top'][:3])}")
