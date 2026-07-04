#!/usr/bin/env python3
"""
Rhode — Coletor AUTOMÁTICO do custo GMV Max via Business/Ads API (mata o import manual).

Fonte: GET business-api.tiktok.com/open_api/v1.3/gmv_max/report/get/ — metric `cost` =
a coluna "Custo do GMV máximo" do Seller Center (validado ao centavo: mai R$48.003,
jun1-15 R$38.990). net_cost=0 + cost>0 = campanha Vendas Líquidas (pay-with-GMV);
net_cost>0 = Tradicional (Receita bruta). Custo total (tradicional+VL) entra no lucro.

Popula: ads_custo (total diário, id=data) — mesma tabela do import antigo.
Uso:  python3 coletar_gmvmax_api.py --inicio 2026-05-01 --fim 2026-06-30
      python3 coletar_gmvmax_api.py --dias 30            # janela retroativa
"""
import os, sys, json, argparse, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
SB_URL = os.environ["SUPABASE_URL"]; SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}
BASE = "https://business-api.tiktok.com"
EP = "/open_api/v1.3/gmv_max/report/get/"
# Rhode Jeans — advertiser + loja (sob BC NARAA). TODO: buscar dinâmico via /bc/asset/get/.
ADV = "7504809708629344263"; STORE = "7496180259574286943"


def token():
    req = urllib.request.Request(f"{SB_URL}/rest/v1/api_tokens?id=eq.tiktok_ads&select=access_token", headers=SBH)
    return json.load(urllib.request.urlopen(req))[0]["access_token"]


def report(tok, sd, ed, dims):
    p = {"advertiser_id": ADV, "store_ids": [STORE], "dimensions": dims,
         "metrics": ["cost", "net_cost", "gross_revenue", "orders", "campaign_name"],
         "start_date": sd, "end_date": ed, "page_size": 200, "page": 1}
    out = []
    while True:
        qs = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in p.items()})
        r = urllib.request.Request(f"{BASE}{EP}?{qs}", headers={"Access-Token": tok})
        try:
            d = json.load(urllib.request.urlopen(r, timeout=90))
        except urllib.error.HTTPError as e:
            print(f"  [ERRO API] {e.code}: {e.read()[:300]}"); raise
        if d.get("code") != 0:
            print(f"  [API code={d.get('code')}] {d.get('message')}"); return out
        lst = d.get("data", {}).get("list", [])
        out += lst
        pi = d.get("data", {}).get("page_info", {})
        if not pi or p["page"] >= pi.get("total_page", 1):
            break
        p["page"] += 1
    return out


def upsert(rows):
    if not rows:
        return
    url = f"{SB_URL}/rest/v1/ads_custo?on_conflict=id"
    body = json.dumps(rows).encode()
    req = urllib.request.Request(url, data=body, headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        print(f"  [ERRO upsert] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ ads_custo: {len(rows)} dias upsertados")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio"); ap.add_argument("--fim")
    ap.add_argument("--dias", type=int, default=30)
    args = ap.parse_args()
    if args.inicio:
        sd, ed = args.inicio, (args.fim or datetime.now().strftime("%Y-%m-%d"))
    else:
        ed = datetime.now().strftime("%Y-%m-%d")
        sd = (datetime.now() - timedelta(days=args.dias)).strftime("%Y-%m-%d")
    print(f"═════ GMV Max custo (API) — {sd} → {ed} ═════")
    tok = token()
    # dimensão diária × campanha — a API limita stat_time_day a 30 dias/chamada → chunk
    lst = []
    d0 = datetime.strptime(sd, "%Y-%m-%d"); d1 = datetime.strptime(ed, "%Y-%m-%d"); cur = d0
    while cur <= d1:
        ce = min(cur + timedelta(days=29), d1)
        lst += report(tok, cur.strftime("%Y-%m-%d"), ce.strftime("%Y-%m-%d"), ["stat_time_day", "campaign_id"])
        cur = ce + timedelta(days=1)
    if not lst:
        print("  ⚠ sem dados no período."); return
    # detecta o campo de data no dimensions
    dkey = next((k for k in lst[0]["dimensions"] if "time" in k or "day" in k or "date" in k), None)
    if not dkey:
        print(f"  ⚠ API não retornou dimensão diária (dims: {list(lst[0]['dimensions'].keys())}). Abortando."); return
    byday = defaultdict(lambda: {"custo": 0.0, "receita": 0.0, "pedidos": 0, "trad": 0.0, "vl": 0.0})
    for x in lst:
        dm, m = x["dimensions"], x["metrics"]
        dia = str(dm[dkey])[:10]
        c = float(m.get("cost", 0) or 0); n = float(m.get("net_cost", 0) or 0)
        a = byday[dia]
        a["custo"] += c; a["receita"] += float(m.get("gross_revenue", 0) or 0); a["pedidos"] += int(float(m.get("orders", 0) or 0))
        if c > 0 and n == 0:
            a["vl"] += c            # Vendas Líquidas (net_cost=0)
        else:
            a["trad"] += c          # Tradicional
    rows = []
    for dia, a in sorted(byday.items()):
        rows.append({"id": dia, "data": dia, "periodo": dia[:7],
                     "custo": round(a["custo"], 2), "receita": round(a["receita"], 2),
                     "pedidos": a["pedidos"],
                     "roi": round(a["receita"] / a["custo"], 2) if a["custo"] else 0})
    tot = sum(r["custo"] for r in rows)
    tvl = sum(a["vl"] for a in byday.values()); ttr = sum(a["trad"] for a in byday.values())
    print(f"  → {len(rows)} dias · custo total R$ {tot:,.2f}  (Tradicional R$ {ttr:,.0f} · Vendas Líquidas R$ {tvl:,.0f})")
    upsert(rows)
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
