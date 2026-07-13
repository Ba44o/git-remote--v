#!/usr/bin/env python3
"""
Rhode — Liquidação REAL por Corte × Cor (lavagem) × Canal → tabela liquidacao_cor_canal.
Alimenta a aba "Liquidação SKU" do console de conciliação (creators.rhodejeans.com.br/conciliacao.html).

Cor/lavagem vem do SKU (sku_name via seller_sku REF), NÃO do nome do anúncio.
  REF516 = Marmorizada = HERO (Wide Leg). Anúncio genérico "Wide Leg Cintura Alta" = 1 product_id, N cores.
Liquidação = settlement REAL por pedido (conciliacao_pedido), rateado por linha (share do GMV).
  Comissão de afiliada já está embutida no fee do settlement — não subtrair de novo.
Guarda SOMAS (pecas, pecas_liq, settlement_real, gmv, cpv_total) → cliente agrega multi-mês certo.
Cada cor ganha também uma linha canal='TOTAL' (blend). ROOT (não dispara etl_sync).
"""
import os, json, re, urllib.request, urllib.error
from collections import defaultdict
from dotenv import load_dotenv
BASE=os.path.dirname(os.path.abspath(__file__)); load_dotenv(os.path.join(BASE,".env"))
SB=os.environ["SUPABASE_URL"]; SK=os.environ["SUPABASE_SERVICE_KEY"]
SBH={"apikey":SK,"Authorization":f"Bearer {SK}","Content-Type":"application/json"}
MESES=["2026-06","2026-07"]

def pageall(base):
    out=[];off=0
    while True:
        b=json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/rest/v1/{base}&limit=1000&offset={off}",headers=SBH)))
        out+=b
        if len(b)<1000: break
        off+=1000
    return out

def corte(n):
    n=(n or '').lower()
    if 'short' in n or 'saia' in n or 'body' in n or 'bata' in n or 'blusa' in n: return None
    if 'baggy' in n: return 'Baggy'
    if 'mom' in n: return 'Mom'
    if 'wide leg' in n: return 'Wide Leg'
    return None

def cor_de(sku_name):
    s=(sku_name or "").strip(); s=re.split(r',',s)[0].strip(); s=re.sub(r'\s*\d{2}\s*$','',s).strip()
    return (s.title() if s and not s.isdigit() else "—")

def canal_de(ct): return "loja" if not ct else ("live_afil" if ct=="LIVE" else "video_afil")

# CPV por REF (base + variação)
CPV={}
for r in pageall("custos_sku?select=ref,cpv"): CPV[(r.get("ref") or "").upper()]=float(r.get("cpv") or 0)
def cpv_de(sku):
    m=re.match(r'(REF\d{3})',(sku or "").upper())
    for k in ([sku.upper()] if sku else [])+([m.group(1)] if m else []):
        for ref,c in CPV.items():
            if ref.startswith(k) and c>0: return c
    return 45.0

rows_db=[]
for mes in MESES:
    # settlement real por pedido
    cp=pageall(f"conciliacao_pedido?periodo=eq.{mes}&select=order_id,settlement")
    o2set={str(r["order_id"]):float(r.get("settlement") or 0) for r in cp if r.get("settlement") is not None}
    # canal do pedido (afiliada)
    ext=pageall(f"extrato_pedidos?periodo=eq.{mes}&select=order_id,content_type")
    o2c={}
    for r in ext:
        oid=str(r.get("order_id") or "")
        if oid and oid not in o2c: o2c[oid]=(r.get("content_type") or "").upper()
    # pedidos_sku (lado loja, todas as peças)
    ped=pageall(f"pedidos_sku?periodo=eq.{mes}&select=order_id,seller_sku,sku,produto,qty,gmv,status")
    o2gmv=defaultdict(float)
    for p in ped:
        if 'CANCEL' in (p.get('status') or '').upper(): continue
        o2gmv[str(p.get("order_id"))]+=float(p.get("gmv") or 0)
    # agrega (corte,cor,canal)
    A=defaultdict(lambda:{"pecas":0,"pecas_liq":0,"settle":0.0,"gmv":0.0,"cpv":0.0,"hero":False})
    for p in ped:
        if 'CANCEL' in (p.get('status') or '').upper(): continue
        cut=corte(p.get("produto"))
        if not cut: continue
        oid=str(p.get("order_id")); q=int(p.get("qty") or 0); g=float(p.get("gmv") or 0)
        cor=cor_de(p.get("sku")); ch=canal_de(o2c.get(oid))
        hero=(p.get("seller_sku") or "").upper().startswith("REF516")
        for key in [(cut,cor,ch),(cut,cor,"TOTAL")]:
            a=A[key]; a["pecas"]+=q; a["gmv"]+=g; a["cpv"]+=cpv_de(p.get("seller_sku"))*q
            if hero: a["hero"]=True
            if oid in o2set and o2gmv[oid]>0:
                a["pecas_liq"]+=q; a["settle"]+=o2set[oid]*(g/o2gmv[oid])
    for (cut,cor,ch),a in A.items():
        if a["pecas"]<3: continue
        rows_db.append({"id":f"{mes}:{cut}:{cor}:{ch}","periodo":mes,"corte":cut,"cor":cor,"canal":ch,
            "pecas":a["pecas"],"pecas_liq":a["pecas_liq"],"settlement_real":round(a["settle"],2),
            "gmv":round(a["gmv"],2),"cpv_total":round(a["cpv"],2),"is_hero":a["hero"]})

# grava (merge-duplicates). Se a tabela não existir ainda → instruir a rodar o .sql.
gravou=False
try:
    urllib.request.urlopen(urllib.request.Request(
        SB+"/rest/v1/liquidacao_cor_canal?on_conflict=id",
        data=json.dumps(rows_db).encode(),
        headers={**SBH,"Prefer":"resolution=merge-duplicates,return=minimal"},method="POST"),timeout=90)
    gravou=True; print(f"✓ liquidacao_cor_canal gravada — {len(rows_db)} linhas")
except urllib.error.HTTPError as e:
    print(f"(NÃO gravada — rode rhode-vercel/sql/liquidacao_cor_canal.sql no Supabase · HTTP {e.code})")

# conferência: hero + Wide Leg (bate com o Excel validado)
print("\n── Conferência (junho) ──")
for mes in ["2026-06"]:
    tot={}
    for r in rows_db:
        if r["periodo"]!=mes or r["corte"]!="Wide Leg" or r["canal"]!="TOTAL": continue
        pc=r["pecas"]; plq=r["pecas_liq"]
        liq=r["settlement_real"]/plq if plq else 0; cpv=r["cpv_total"]/pc
        tag=" ⭐HERO" if r["is_hero"] and r["cor"]=="Marmorizada" else ""
        if r["cor"] in ("Marmorizada","Chocolate","Rosa Bebê","Sky Used","Stone Used"):
            print(f"  {r['cor']:<16} pç {pc:>5} · liq/pç R$ {liq:>6.2f} · cov {plq/pc*100:>3.0f}% · margem R$ {liq-cpv:>6.2f}{tag}")
