#!/usr/bin/env python3
"""VALIDACAO: custo GMV Max via /gmv_max/report/get/ vs Seller Center (mai R$48.003, jun1-15 R$38.990)."""
import os, json, urllib.request, urllib.parse, urllib.error
from dotenv import load_dotenv
load_dotenv("/Users/user/Documents/VS Claude Teste/.env")
SB_URL=os.environ["SUPABASE_URL"]; SB_KEY=os.environ["SUPABASE_SERVICE_KEY"]
BASE="https://business-api.tiktok.com"
req=urllib.request.Request(f"{SB_URL}/rest/v1/api_tokens?id=eq.tiktok_ads&select=access_token",
    headers={"apikey":SB_KEY,"Authorization":f"Bearer {SB_KEY}"})
TOKEN=json.load(urllib.request.urlopen(req))[0]["access_token"]
ADV="7504809708629344263"; STORE="7496180259574286943"
EP="/open_api/v1.3/gmv_max/report/get/"
def g(params):
    qs=urllib.parse.urlencode({k:(json.dumps(v) if isinstance(v,(list,dict)) else v) for k,v in params.items()})
    r=urllib.request.Request(f"{BASE}{EP}?{qs}", headers={"Access-Token":TOKEN})
    try: return json.load(urllib.request.urlopen(r, timeout=60))
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except: return {"_err":e.code}

def run(sd,ed,label,esperado):
    p={"advertiser_id":ADV,"store_ids":[STORE],"dimensions":["campaign_id"],
       "metrics":["cost","net_cost","gross_revenue","orders","campaign_name"],
       "start_date":sd,"end_date":ed,"page_size":100}
    r=g(p)
    print(f"\n===== {label} ({sd}..{ed}) — code={r.get('code')} =====")
    lst=r.get("data",{}).get("list",[])
    tc=tn=tg=0.0
    for x in sorted(lst,key=lambda z:-float(z['metrics'].get('cost',0) or 0)):
        m=x["metrics"]; c=float(m.get("cost",0) or 0); n=float(m.get("net_cost",0) or 0); gr=float(m.get("gross_revenue",0) or 0)
        tc+=c; tn+=n; tg+=gr
        if c>0 or n>0:
            print(f"  {x['dimensions']['campaign_id']}  cost={c:9.2f} net={n:9.2f} gmv={gr:10.2f} ord={m.get('orders')}  {m.get('campaign_name','')[:42]}")
    print(f"  --- TOTAL cost={tc:.2f}  net_cost={tn:.2f}  gmv={tg:.2f}  (Seller Center esperava {esperado}) ---")
    return tc,tn

run("2026-05-01","2026-05-31","MAIO","R$48.003")
run("2026-06-01","2026-06-15","JUNHO 1-15","R$38.990")
