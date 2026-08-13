#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reporta o PACE de agosto por canal — self-contained (só precisa de SUPABASE_URL/KEY no ambiente).
Puxa pedidos_sku + extrato_pedidos direto da fonte, roteia por content_type (mesmo critério do
coletor do workbook), computa MTD por canal ATÉ O ÚLTIMO DIA COMPLETO e imprime uma tabela markdown
de pace (meta · MTD · /dia · nec/dia · índice). Serve pra rotina cloud postar no Notion.
Não escreve em nada — só lê e imprime. Metas de agosto embutidas (o workbook fica em relatorios/, gitignore).
"""
import os, json, urllib.request, datetime
from collections import defaultdict
try:
    from dotenv import load_dotenv; load_dotenv()   # local: lê .env; cloud: vars já no ambiente
except Exception: pass

SB=os.environ.get("SUPABASE_URL"); SK=os.environ.get("SUPABASE_SERVICE_KEY")
if not SB or not SK:
    print("SEM DADO — SUPABASE_URL/SUPABASE_SERVICE_KEY ausentes no ambiente. Não consigo puxar o pace.")
    raise SystemExit(0)
H={"apikey":SK,"Authorization":f"Bearer {SK}"}

# Metas agosto por canal (peças) — reconstruídas do template Rhode_SKU_x_Canal (base jul×crescimento+ajustes).
METAS={"Live afiliada":2823,"Vídeo afiliada":1624,"Card afiliada":75,"Live loja":2796,"Vídeo loja":67,"Card loja":311}
META_NET=8847  # trava do workbook (headline)
# Split vendedor (não-afiliado) por canal — proporção do export jul (fallback estável).
_S=177660+5090+19216
PV={"Live loja":177660/_S,"Vídeo loja":5090/_S,"Card loja":19216/_S}

def pg(b,order="id"):
    out=[];off=0
    while True:
        p=json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/rest/v1/{b}&order={order}&limit=1000&offset={off}",headers=H)))
        out+=p
        if len(p)<1000:break
        off+=1000
    return out
def canc(s): return bool(s) and 'CANCEL' in str(s).upper()

hoje=datetime.date.today(); MES=hoje.strftime("%Y-%m"); MES_DIAS=31
ultimo=(hoje-datetime.timedelta(days=1)).isoformat()  # último dia COMPLETO (ontem)
DE=int(ultimo[-2:]); DR=MES_DIAS-DE

psku=pg(f"pedidos_sku?periodo=eq.{MES}&select=id,order_id,qty,data,status")
seen={};[seen.setdefault(r['id'],r) for r in psku];psku=list(seen.values())
ex=pg(f"extrato_pedidos?periodo=eq.{MES}&select=id,order_id,content_type,gmv,data,status")
exs={};[exs.setdefault(r['id'],r) for r in ex]
octg=defaultdict(lambda:defaultdict(float))
for r in exs.values():
    if not canc(r.get('status')) and r.get('content_type'): octg[str(r['order_id'])][r['content_type']]+=float(r.get('gmv') or 0)
oct_={o:max(c,key=c.get) for o,c in octg.items()}
def route(r):
    ct=oct_.get(str(r['order_id']))
    if ct=='VIDEO':return[("Vídeo afiliada",1.0)]
    if ct=='LIVE':return[("Live afiliada",1.0)]
    if ct in('SHOP','LINKSHARE'):return[("Card afiliada",1.0)]
    return list(PV.items())
mtd=defaultdict(float); hoje_pc=defaultdict(float)
for r in psku:
    if canc(r.get('status')):continue
    d=(r.get('data') or '')[:10]; qt=float(r.get('qty') or 0)
    if d<=ultimo:
        for ch,p in route(r): mtd[ch]+=qt*p
    elif d==hoje.isoformat():
        for ch,p in route(r): hoje_pc[ch]+=qt*p

def idx(m,meta): return m/(meta*DE/MES_DIAS) if meta else 0
def flag(i): return "✅" if i>=0.97 else ("🟡" if i>=0.7 else "🔴")
NET=sum(mtd.values()); NET_HOJE=sum(hoje_pc.values())
i_net=idx(NET,META_NET); proj_net=NET/DE*MES_DIAS

print(f"# Pace Agosto — Rhode (medido até {ultimo}, {DE} dias completos · {DR} restantes)\n")
print(f"**NET: {NET:.0f} peças · {NET/DE:.0f}/dia · índice {i_net:.2f}x · projeção {proj_net:.0f}** (meta {META_NET}) · +{NET_HOJE:.0f} já entraram hoje\n")
print("| Canal | Meta | MTD | /dia | nec/dia | Proj | Índice | |")
print("|---|--:|--:|--:|--:|--:|--:|:-:|")
for n in METAS:
    m=mtd[n];meta=METAS[n];i=idx(m,meta)
    print(f"| {n} | {meta} | {m:.0f} | {m/DE:.0f} | {max(0,meta-m)/DR:.0f} | {m/DE*MES_DIAS:.0f} | {i:.2f}x | {flag(i)} |")
print(f"| **NET** | **{META_NET}** | **{NET:.0f}** | **{NET/DE:.0f}** | **{(META_NET-NET)/DR:.0f}** | **{proj_net:.0f}** | **{i_net:.2f}x** | {flag(i_net)} |")
piores=sorted([(idx(mtd[n],METAS[n]),n) for n in METAS])[:2]
print(f"\n**Gargalo:** {piores[0][1]} ({piores[0][0]:.2f}x) e {piores[1][1]} ({piores[1][0]:.2f}x). Ritmo NET precisa ir de {NET/DE:.0f} → {(META_NET-NET)/DR:.0f}/dia pra bater a meta.")
