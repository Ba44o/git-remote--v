#!/usr/bin/env python3
"""
Rhode — Tracker da meta de 10 mil peças/mês por canal (modelo origem × conteúdo).
Realizado por canal: Live própria (live_attr) · Live de afiliada + Vídeo de afiliada
(affiliate_perf por content_type) · Orgânico (loja net − os demais). Net = pedidos_sku.
Escreve tracker_canais (pro painel) + _tracker_data.json (pro Excel). ROOT (não dispara ETL).
Uso:  python3 tracker_canais.py            # meses corrente + anterior
"""
import os, json, urllib.request, urllib.error
from collections import defaultdict
from datetime import datetime, timezone, timedelta
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
def q(p):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/"+p,headers=SBH)))
    except Exception: return []

# METAS (peças) por canal — recalibradas c/ dado real 07/07: SEGURAR live própria (margem fina),
# crescer afiliada (~+40%). Somam ao net 10k após a regra de cascata. Editáveis.
META={"live_propria":2830,"live_afiliada":2570,"video_afiliada":4600,"organico":0}
META_NET=10000
MESES=["2026-06","2026-07"]
def wk(dstr):  # semana 1..5 dentro do mês
    try: return min(5,(int(dstr[8:10])-1)//7+1)
    except: return 1

out={"meta":META,"meta_net":META_NET,"meses":{}}
rows_db=[]
for mes in MESES:
    ini=mes+"-01"; y,m=int(mes[:4]),int(mes[5:7]); fim=(f"{y+1}-01-01" if m==12 else f"{y}-{m+1:02d}-01")
    # live própria (peças = itens)
    la=pageall(f"live_attr?periodo=eq.{mes}&select=itens,pedidos,data")
    # afiliadas por content_type
    ap=pageall(f"affiliate_perf?data=gte.{ini}&data=lt.{fim}&select=content_type,itens,data")
    # loja net (peças)
    ped=pageall(f"pedidos_sku?periodo=eq.{mes}&select=qty,status,data")
    pedv=[p for p in ped if 'CANCEL' not in (p.get('status') or '').upper()]
    ch=defaultdict(lambda:{"pecas":0,"sem":defaultdict(int)})
    for r in la:
        it=int(r.get("itens") or r.get("pedidos") or 0); ch["live_propria"]["pecas"]+=it; ch["live_propria"]["sem"][wk(r.get("data") or ini)]+=it
    for r in ap:
        ct=(r.get("content_type") or "").upper(); it=int(r.get("itens") or 0)
        k="video_afiliada" if ct=="VIDEO" else "live_afiliada" if ct=="LIVE" else None
        if k: ch[k]["pecas"]+=it; ch[k]["sem"][wk(r.get("data") or ini)]+=it
    net=sum(int(p.get("qty") or 0) for p in pedv)
    net_sem=defaultdict(int)
    for p in pedv: net_sem[wk(p.get("data") or ini)]+=int(p.get("qty") or 0)
    # DEDUP (regra de cascata): a sobreposição = afiliada que vendeu NA live da Rhode → já conta
    # em Live própria (que vem primeiro). Tira da Live de afiliada pra cada peça ter 1 dono só.
    overlap=max(0,ch["live_propria"]["pecas"]+ch["live_afiliada"]["pecas"]+ch["video_afiliada"]["pecas"]-net)
    if overlap>0 and ch["live_afiliada"]["pecas"]>0:
        fac=max(0,1-overlap/ch["live_afiliada"]["pecas"])
        ch["live_afiliada"]["pecas"]=round(ch["live_afiliada"]["pecas"]*fac)
        for s in ch["live_afiliada"]["sem"]: ch["live_afiliada"]["sem"][s]=round(ch["live_afiliada"]["sem"][s]*fac)
    org=max(0,net-ch["live_propria"]["pecas"]-ch["live_afiliada"]["pecas"]-ch["video_afiliada"]["pecas"])
    ch["organico"]["pecas"]=org
    out["meses"][mes]={"net":net,"net_sem":{str(k):net_sem[k] for k in sorted(net_sem)},
        "canais":{k:{"pecas":ch[k]["pecas"],"meta":META.get(k,0),"sem":{str(s):ch[k]["sem"][s] for s in sorted(ch[k]["sem"])}} for k in ["live_propria","live_afiliada","video_afiliada","organico"]}}
    for k in ["live_propria","live_afiliada","video_afiliada","organico"]:
        rows_db.append({"id":f"{mes}:{k}","mes":mes,"canal":k,"pecas":ch[k]["pecas"],"meta_pecas":META.get(k,0),
            "semanas":json.dumps({str(s):ch[k]["sem"][s] for s in sorted(ch[k]["sem"])})})
    rows_db.append({"id":f"{mes}:net","mes":mes,"canal":"net","pecas":net,"meta_pecas":META_NET,"semanas":json.dumps({str(k):net_sem[k] for k in sorted(net_sem)})})

json.dump(out,open(os.path.join(BASE,"_tracker_data.json"),"w"))
# upsert (falha suave se tabela não existe)
try:
    urllib.request.urlopen(urllib.request.Request(SB+"/rest/v1/tracker_canais?on_conflict=id",data=json.dumps(rows_db).encode(),headers={**SBH,"Prefer":"resolution=merge-duplicates,return=minimal"},method="POST"),timeout=60)
    print("✓ tracker_canais gravada")
except urllib.error.HTTPError as e:
    print(f"(tracker_canais não gravada — rode tracker_canais.sql · {e.code})")
print("\n=== REALIZADO POR CANAL (peças) ===")
for mes in MESES:
    d=out["meses"][mes]; print(f"\n{mes} · net {d['net']:,} / meta {META_NET:,} ({d['net']/META_NET*100:.0f}%)")
    for k,v in d["canais"].items():
        pct=v['pecas']/v['meta']*100 if v['meta'] else 0
        print(f"  {k:<16} {v['pecas']:>5,} / meta {v['meta']:>5,}  ({pct:>3.0f}%)")
