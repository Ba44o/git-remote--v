#!/usr/bin/env python3
"""
Rhode — Coletor de LIVE (por sessão/sala + totais por período), via API. Mata export manual.

Por SESSÃO: Business API /gmv_max/report/get/ dimensions=[campaign_id,room_id,stat_time_day]
  filtering.campaign_ids=[campanhas LIVE_GMV_MAX] → cost/GMV/pedidos/live_views por sala.
Por PERÍODO: Partner Analytics /analytics/202405/shop/performance → GMV de live (org+ads)
  vs vídeo/card + GMV da loja. origem: 'creator' se nome tem "MEGA LIVE", senão 'propria'.

Uso:  python3 coletar_lives_api.py --inicio 2026-01-01 --fim 2026-07-06
      python3 coletar_lives_api.py --dias 35
"""
import os, sys, json, argparse, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar_dados import chamar  # Partner API (HMAC)

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"}
BASE = "https://business-api.tiktok.com"
ADV = "7504809708629344263"; STORE = "7496180259574286943"


def token():
    r = urllib.request.Request(SB + "/rest/v1/api_tokens?id=eq.tiktok_ads&select=access_token", headers=SBH)
    return json.load(urllib.request.urlopen(r))[0]["access_token"]


def biz(tok, ep, params):
    qs = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in params.items()})
    r = urllib.request.Request(f"{BASE}{ep}?{qs}", headers={"Access-Token": tok})
    try:
        return json.load(urllib.request.urlopen(r, timeout=90))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def upsert(table, rows, chunk=500):
    if not rows:
        return
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i + chunk]).encode()
        req = urllib.request.Request(f"{SB}/rest/v1/{table}?on_conflict={'periodo' if table=='live_periodo' else 'id'}",
            data=body, headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert {table}] {e.code}: {e.read()[:300]} (rode live_sessao.sql?)"); raise
    print(f"  ✓ {table}: {len(rows)} linhas")


def f(x):
    try: return float(x)
    except: return 0.0


def coletar_sessoes(tok, sd, ed):
    # 1) campanhas de LIVE
    d = biz(tok, "/open_api/v1.3/gmv_max/campaign/get/", {"advertiser_id": ADV, "filtering": {"gmv_max_promotion_types": ["LIVE_GMV_MAX"]}, "page_size": 100})
    live_ids = [str(c.get("campaign_id")) for c in d.get("data", {}).get("list", [])]
    names = {str(c.get("campaign_id")): c.get("campaign_name", "") for c in d.get("data", {}).get("list", [])}
    if not live_ids:
        print("  ⚠ nenhuma campanha LIVE."); return []
    print(f"  {len(live_ids)} campanhas de live")
    # 2) report por sala × dia (chunk 30d)
    rows = {}
    d0 = datetime.strptime(sd, "%Y-%m-%d"); d1 = datetime.strptime(ed, "%Y-%m-%d"); cur = d0
    while cur <= d1:
        ce = min(cur + timedelta(days=29), d1)
        page = 1
        while True:
            r = biz(tok, "/open_api/v1.3/gmv_max/report/get/", {"advertiser_id": ADV, "store_ids": [STORE],
                "dimensions": ["campaign_id", "room_id", "stat_time_day"], "filtering": {"campaign_ids": live_ids},
                "metrics": ["cost", "net_cost", "gross_revenue", "orders", "live_views"],
                "start_date": cur.strftime("%Y-%m-%d"), "end_date": ce.strftime("%Y-%m-%d"), "page_size": 200, "page": page})
            if r.get("code") != 0:
                print(f"    [live report code={r.get('code')}] {r.get('message','')[:80]}"); break
            lst = r.get("data", {}).get("list", [])
            for x in lst:
                dm, m = x["dimensions"], x["metrics"]
                rid = str(dm.get("room_id", "")); dia = str(dm.get("stat_time_day", ""))[:10]; cid = str(dm.get("campaign_id", ""))
                cost = f(m.get("cost")); rec = f(m.get("gross_revenue")); ped = int(f(m.get("orders"))); vw = int(f(m.get("live_views")))
                if cost <= 0 and rec <= 0 and ped <= 0 and vw <= 0:
                    continue
                nm = names.get(cid, "")
                rows[f"{rid}:{dia}"] = {"id": f"{rid}:{dia}", "room_id": rid, "data": dia, "periodo": dia[:7],
                    "campaign_id": cid, "campanha": nm[:160],
                    "origem": "creator" if "mega live" in nm.lower() else "propria",
                    "cost": round(cost, 2), "net_cost": round(f(m.get("net_cost")), 2), "receita": round(rec, 2),
                    "pedidos": ped, "views": vw}
            pi = r.get("data", {}).get("page_info", {})
            if not pi or page >= pi.get("total_page", 1):
                break
            page += 1; time.sleep(0.2)
        cur = ce + timedelta(days=1)
    return list(rows.values())


def coletar_periodo(sd, ed):
    # GMV de live por mês via Partner Analytics (org + ads)
    out = []
    d0 = datetime.strptime(sd, "%Y-%m-%d").replace(day=1); d1 = datetime.strptime(ed, "%Y-%m-%d")
    cur = d0
    while cur <= d1:
        nxt = (cur.replace(day=28) + timedelta(days=8)).replace(day=1)
        per = cur.strftime("%Y-%m")
        r = None
        for attempt in range(3):
            r = chamar("GET", "/analytics/202405/shop/performance", params={
                "start_date_ge": cur.strftime("%Y-%m-%d"), "end_date_lt": nxt.strftime("%Y-%m-%d"), "granularity": "ALL"})
            if r.get("code") == 0:
                break
            time.sleep(2.5)
        iv = ((r or {}).get("data", {}).get("performance", {}) or {}).get("intervals", [])
        if iv:
            p = iv[0]
            gmv_loja = f(p.get("gmv", {}).get("amount") if isinstance(p.get("gmv"), dict) else p.get("gmv"))
            row = {"periodo": per, "gmv_loja": round(gmv_loja, 2), "gmv_live": 0, "gmv_video": 0, "gmv_card": 0, "pedidos_live": 0, "buyers_live": 0}
            for b in p.get("gmv_breakdowns", []):
                amt = f(b.get("gmv", {}).get("amount") if isinstance(b.get("gmv"), dict) else b.get("amount") or b.get("gmv"))
                t = b.get("type", "")
                if t == "LIVE": row["gmv_live"] = round(amt, 2)
                elif t == "VIDEO": row["gmv_video"] = round(amt, 2)
                elif t == "PRODUCT_CARD": row["gmv_card"] = round(amt, 2)
            for b in p.get("buyer_breakdowns", []):
                if b.get("type") == "LIVE": row["buyers_live"] = int(f(b.get("value") or b.get("buyers")))
            out.append(row)
        cur = nxt
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio"); ap.add_argument("--fim"); ap.add_argument("--dias", type=int, default=35)
    args = ap.parse_args()
    if args.inicio:
        sd, ed = args.inicio, (args.fim or datetime.now().strftime("%Y-%m-%d"))
    else:
        ed = datetime.now().strftime("%Y-%m-%d"); sd = (datetime.now() - timedelta(days=args.dias)).strftime("%Y-%m-%d")
    print(f"═════ LIVE — {sd} → {ed} ═════")
    tok = token()
    ses = coletar_sessoes(tok, sd, ed)
    tot = sum(r["cost"] for r in ses); gmv = sum(r["receita"] for r in ses); vw = sum(r["views"] for r in ses)
    print(f"  → {len(ses)} sessões · invest R$ {tot:,.0f} · GMV R$ {gmv:,.0f} · {vw:,} views")
    upsert("live_sessao", ses)
    per = coletar_periodo(sd, ed)
    print(f"  → {len(per)} períodos (GMV live total via analytics)")
    upsert("live_periodo", per)
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
