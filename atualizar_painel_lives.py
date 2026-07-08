#!/usr/bin/env python3
"""
Rhode — Atualiza a tabela `lives` (painel INTERNO dash-live) com dados frescos.
  • Funil/GMV: export do Seller Center "Creator-Live-Performance" (formato novo
    performance_detail, com Room ID). Parser próprio (o etl_lives só lê o formato antigo).
  • Ads (ads_cost/ads_gmv/ads_roas): GMV Max via API (tabela live_sessao), casado por room_id.
ROOT de propósito (fora de agente_rhode/ → NÃO dispara etl_sync.yml). Idempotente (upsert live_key).
Uso:  python3 atualizar_painel_lives.py
"""
import os, re, glob, json, urllib.request, urllib.error
from datetime import datetime
from collections import defaultdict
import openpyxl
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"}


def money(s):
    if s is None: return 0.0
    if isinstance(s, (int, float)): return float(s)
    t = re.sub(r"[^\d,.\-]", "", str(s).replace("R$", "").strip())
    if not t: return 0.0
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if re.search(r",\d{1,2}$", t) else t.replace(",", "")
    try: return float(t)
    except: return 0.0


def num(s):  # tira % e devolve número (ex "6.62%" → 6.62)
    if s is None: return 0.0
    if isinstance(s, (int, float)): return float(s)
    try: return float(re.sub(r"[^\d.\-]", "", str(s).replace("%", "").replace(",", ".")) or 0)
    except: return 0.0


def inte(s): return int(round(money(s)))


def dur_sec(s):
    if s is None: return 0
    m = re.match(r'(?:(\d+)h)?(?:(\d+)m)?', str(s).strip())
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60
    return inte(s)


def parse_dt(s):
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try: return datetime.strptime(str(s).strip(), f)
        except: pass
    return None


def read_export(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["performance_detail"] if "performance_detail" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hi = next((i for i, r in enumerate(rows) if r and any(str(c).strip() == "Room ID" for c in r if c)), None)
    if hi is None:
        return []  # formato antigo (sem Room ID) — já está na `lives` via etl_lives
    hdr = [str(c).strip() if c is not None else "" for c in rows[hi]]
    out = []
    for r in rows[hi + 1:]:
        if not r or r[0] is None: continue
        rid = str(r[0]).strip()
        if not rid.isdigit() or len(rid) < 10: continue
        out.append(dict(zip(hdr, r)))
    return out


def build_record(d):
    dt = parse_dt(d.get("Start Time"))
    gmv = money(d.get("Attributed GMV"))
    if not dt or gmv <= 0:
        return None, None
    rid = str(d.get("Room ID")).strip(); title = str(d.get("Room Title") or "").strip()
    iso = dt.isoformat(); ds = dur_sec(d.get("Duration"))
    rec = {
        "live_key": f"{iso}|{title}", "title": title[:200], "started_at": iso,
        "date": dt.strftime("%Y-%m-%d"), "month": dt.strftime("%Y-%m"),
        "day_of_week": dt.weekday(), "hour": dt.hour,
        "duration_sec": ds, "duration_min": round(ds / 60, 1),
        "gmv_bruto": round(gmv, 2), "gmv_direct": round(gmv, 2),
        "items_sold": inte(d.get("Attributed items sold")), "attributed_sku_orders": inte(d.get("Attributed SKU orders")),
        "customers": inte(d.get("Customers")), "avg_price": round(money(d.get("AOV")), 2),
        "orders": inte(d.get("Attributed orders")), "views": inte(d.get("Views")),
        "new_followers": inte(d.get("New followers")), "likes": inte(d.get("Likes")),
        "comments": inte(d.get("Comments")), "shares": inte(d.get("Shares")),
        "product_impressions": inte(d.get("Product Impressions") or d.get("Product impressions")),
        "product_clicks": inte(d.get("Product clicks")),
        "ctr": round(num(d.get("CTR")), 4), "ctor": round(num(d.get("CTOR (SKU orders)") or d.get("CTOR")), 4),
        "live_impressions": inte(d.get("Impressions") or d.get("LIVE impressions")),
        "impressions_per_hour": inte(d.get("Impressions Per Hour")),
        "gmv_per_hour": round(money(d.get("GMV per hour")), 2),
        "show_gpm": round(money(d.get("Show GPM")), 2), "watch_gpm": round(money(d.get("Watch GPM")), 2),
        "tap_through_rate": round(num(d.get("Tap through rate")) / 100, 6),
        "live_ctr": round(num(d.get("LIVE CTR")) / 100, 6),
        "follow_rate": round(num(d.get("Follow rate")) / 100, 6), "comment_rate": round(num(d.get("Comment rate")) / 100, 6),
        "share_rate": round(num(d.get("Share rate")) / 100, 6), "like_rate": round(num(d.get("Like rate")) / 100, 6),
        "sku_order_rate": round(num(d.get("SKU order rate")) / 100, 6),
        "ads_cost": None, "ads_gmv": None, "ads_roas": None,  # preenchido depois (GMV Max); keys iguais p/ todos (PostgREST)
        "schema_version": "v2-api",
    }
    return rec, rid


def upsert(rows):
    for i in range(0, len(rows), 500):
        body = json.dumps(rows[i:i + 500]).encode()
        req = urllib.request.Request(SB + "/rest/v1/lives?on_conflict=live_key", data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print("  [ERRO upsert]", e.code, e.read()[:300]); raise


def main():
    # 1) exports (formato novo, com Room ID) → registros + mapa room_id→live_key
    recs = {}; room2key = {}
    for f in sorted(glob.glob(os.path.join(BASE, "dados/lives/exports/Creator-Live-Performance_*.xlsx"))):
        for d in read_export(f):
            rec, rid = build_record(d)
            if rec:
                recs[rec["live_key"]] = rec; room2key[rid] = rec["live_key"]
    if not recs:
        print("Nenhuma live no formato novo (com Room ID). Nada a atualizar."); return
    # 2) ads do GMV Max (live_sessao) agregado por room_id
    req = urllib.request.Request(SB + "/rest/v1/live_sessao?select=room_id,cost,receita&limit=5000", headers=SBH)
    ads = defaultdict(lambda: {"cost": 0.0, "gmv": 0.0})
    for x in json.load(urllib.request.urlopen(req)):
        a = ads[str(x["room_id"])]; a["cost"] += float(x["cost"] or 0); a["gmv"] += float(x["receita"] or 0)
    filled = 0
    for rid, key in room2key.items():
        a = ads.get(rid)
        if a and (a["cost"] > 0 or a["gmv"] > 0):
            recs[key]["ads_cost"] = round(a["cost"], 2); recs[key]["ads_gmv"] = round(a["gmv"], 2)
            recs[key]["ads_roas"] = round(a["gmv"] / a["cost"], 2) if a["cost"] else None
            filled += 1
    rows = list(recs.values())
    upsert(rows)
    per = defaultdict(lambda: {"n": 0, "gmv": 0.0, "ads": 0})
    for r in rows:
        p = per[r["month"]]; p["n"] += 1; p["gmv"] += r["gmv_bruto"]; p["ads"] += 1 if r.get("ads_cost") else 0
    print(f"✓ lives atualizada: {len(rows)} sessões (formato novo) · {filled} com ads (GMV Max)")
    for m in sorted(per):
        print(f"  {m}: {per[m]['n']:>2} lives · GMV R$ {per[m]['gmv']:>11,.2f} · {per[m]['ads']} com ads")


if __name__ == "__main__":
    main()
