#!/usr/bin/env python3
"""
Rhode — Importador GMV Max → tabela ads_gmvmax (admin/CFO).

Lê o export "creative data for product campaigns ... .xlsx" do Seller Center
(gasto/GMV/ROAS por criativo) e agrega por (período, campanha, produto).
Período vem do NOME do arquivo. Idempotente.

Uso:
  python3 importar_gmvmax.py                       # todos em dados/campanhas/tiktok/
  python3 importar_gmvmax.py "caminho/arquivo.xlsx"
"""
import os, sys, re, json, glob, urllib.request, urllib.error
import pandas as pd
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SB_URL=os.environ["SUPABASE_URL"]; SB_KEY=os.environ["SUPABASE_SERVICE_KEY"]
SBH={"apikey":SB_KEY,"Authorization":f"Bearer {SB_KEY}","Content-Type":"application/json"}
DEFAULT_DIR="dados/campanhas/tiktok"
DATE_RE=re.compile(r"(\d{4}-\d{2}-\d{2})\s+\d{2}\s*~\s*(\d{4}-\d{2}-\d{2})")

def fnum(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
    s=str(v).strip().replace("R$","").replace(" ","")
    if s in ("","-","nan","NaN"): return 0.0
    if "," in s and "." in s: s=s.replace(".","").replace(",",".")
    elif "," in s: s=s.replace(",",".")
    try: return float(s)
    except ValueError: return 0.0

def upsert(table, rows, chunk=500, on_conflict="id"):
    if not rows: print(f"  [SKIP] {table} sem linhas"); return
    url=f"{SB_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    for i in range(0,len(rows),chunk):
        body=json.dumps(rows[i:i+chunk]).encode()
        req=urllib.request.Request(url,data=body,headers={**SBH,"Prefer":"resolution=merge-duplicates,return=minimal"},method="POST")
        try: urllib.request.urlopen(req,timeout=120)
        except urllib.error.HTTPError as e: print(f"  [ERRO {table}] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas")

def proc(path):
    m=DATE_RE.search(os.path.basename(path))
    if not m: print(f"  [SKIP] sem datas no nome: {os.path.basename(path)}"); return []
    pini, pfim = m.group(1), m.group(2)
    periodo=pini[:7]
    # IDs grandes (16-17 dígitos) → ler como string pra não perder precisão
    df=pd.read_excel(path, sheet_name="Data", header=0,
                     dtype={"ID da campanha":str,"ID do produto":str})
    agg={}
    for _,r in df.iterrows():
        cid=str(r.get("ID da campanha") or "").strip()
        pid=str(r.get("ID do produto") or "").strip()
        if not cid: continue
        key=(cid,pid)
        a=agg.get(key)
        if a is None:
            nome=str(r.get("Nome da campanha") or "").strip()
            a=agg[key]={"id":f"{pini}|{cid}|{pid}","periodo":periodo,"periodo_ini":pini,"periodo_fim":pfim,
                "campanha":nome[:120],"campaign_id":cid,"product_id":pid,
                "is_gmvmax":"GMV-MAX" in nome.upper() or "GMV MAX" in nome.upper(),
                "custo":0.0,"pedidos":0,"receita_bruta":0.0,"impressoes":0,"cliques":0,"moeda":"BRL"}
        a["custo"]=round(a["custo"]+fnum(r.get("Custo")),2)
        a["pedidos"]+=int(fnum(r.get("Pedidos de SKU")))
        a["receita_bruta"]=round(a["receita_bruta"]+fnum(r.get("Receita bruta")),2)
        a["impressoes"]+=int(fnum(r.get("Impressões de anúncio de produto")))
        a["cliques"]+=int(fnum(r.get("Cliques em anúncio de produto")))
    for a in agg.values():
        a["roi"]=round(a["receita_bruta"]/a["custo"],2) if a["custo"]>0 else 0.0
    print(f"  → {os.path.basename(path)[:50]} · {periodo} ({pini}→{pfim}) · {len(df)} criativos → {len(agg)} campanha×produto")
    return list(agg.values())

def main():
    args=sys.argv[1:]
    files = args if args else sorted(glob.glob(os.path.join(DEFAULT_DIR,"creative data for product campaigns*.xlsx")))
    if not files: print(f"[ERRO] nenhum arquivo em {DEFAULT_DIR}"); sys.exit(1)
    print(f"═════ Importar GMV Max — {len(files)} arquivo(s) ═════")
    rows=[]
    for f in files: rows+=proc(f)
    if rows:
        tc=sum(x["custo"] for x in rows); tr=sum(x["receita_bruta"] for x in rows)
        print(f"  → TOTAL: custo R$ {tc:,.0f} · receita R$ {tr:,.0f} · ROI {tr/tc:.2f}" if tc else "  → sem custo")
    upsert("ads_gmvmax", rows, on_conflict="id")
    print("  ✓ concluído.")

if __name__=="__main__":
    main()
