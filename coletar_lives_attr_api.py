#!/usr/bin/env python3
"""
Rhode — Coletor de LIVE (atribuição do Seller Center) via API. Mata o import manual.

Fonte: Partner Analytics /analytics/202509/shop_lives/performance (única versão válida).
  Retorna TODAS as salas de live atribuídas à loja (creators + própria), ordenadas por GMV.
  Filtramos username == "rhodejeans" (lives da própria Rhode) → bate com o export do
  Seller Center a ~0,02% (é snapshot ao vivo; converge conforme a atribuição liquida).
  sales_performance.gmv.amount = "Attributed GMV". NÃO traz views (o export traz — o
  importar_live_performance.py enriquece views por cima, casando por room_id).

Popula live_attr. Uso:  python3 coletar_lives_attr_api.py --inicio 2026-01-01 --fim 2026-07-06
                        python3 coletar_lives_attr_api.py --dias 40
"""
import os, sys, json, time, argparse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
sys.path.insert(0, BASE)
from coletar_dados import chamar  # Partner API (HMAC)

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"}
OWN = os.environ.get("RHODE_LIVE_USERNAME", "rhodejeans").lower()  # conta da própria loja
BRT = timezone(timedelta(hours=-3))  # Seller Center usa horário de Brasília


def f(x):
    try: return float(x)
    except: return 0.0


def dt_brt(unix):
    try: return datetime.fromtimestamp(int(unix), BRT)
    except: return None


def page_mes(sd, ed):
    """Pagina todas as salas do intervalo [sd, ed) e devolve só as da própria loja."""
    own = []; tok = None; pg = 0
    while pg < 400:
        params = {"start_date_ge": sd, "end_date_lt": ed, "granularity": "ALL", "page_size": 50}
        if tok: params["page_token"] = tok
        r = None
        for attempt in range(6):  # analytics é instável (36009007 timeout) — retry
            r = chamar("GET", "/analytics/202509/shop_lives/performance", params=params)
            if r.get("code") == 0: break
            time.sleep(1.5)
        if not r or r.get("code") != 0:
            print(f"    [shop_lives code={(r or {}).get('code')}] {(r or {}).get('message','')[:70]}"); break
        d = r.get("data") or {}
        for x in d.get("live_stream_sessions") or []:
            if (x.get("username") or "").lower() != OWN:
                continue
            sp = x.get("sales_performance") or {}
            dt = dt_brt(x.get("start_time"))
            if not dt: continue
            gmv = f((sp.get("gmv") or {}).get("amount"))
            own.append({
                "id": str(x.get("id")), "room_id": str(x.get("id")),
                "titulo": (x.get("title") or "").strip()[:200],
                "inicio": dt.isoformat(),
                "fim": (dt_brt(x.get("end_time")).isoformat() if dt_brt(x.get("end_time")) else None),
                "duracao": "", "data": dt.strftime("%Y-%m-%d"), "periodo": dt.strftime("%Y-%m"),
                "origem": "propria", "gmv": round(gmv, 2),
                "pedidos": int(f(sp.get("created_sku_orders")) or f(sp.get("sku_orders"))),
                "itens": int(f(sp.get("items_sold"))),
                "sku_orders": int(f(sp.get("sku_orders"))),
                "customers": int(f(sp.get("customers"))),
                "aov": round(f((sp.get("avg_price") or {}).get("amount")), 2),
                "views": 0, "impressions": 0,
            })
        tok = d.get("next_page_token"); pg += 1
        if not tok: break
        time.sleep(0.1)
    return own


def upsert(rows, chunk=500):
    if not rows: return
    # não zera views se já existem (o export pode ter enriquecido): merge deixa a coluna,
    # mas mandamos views=0 → sobrescreveria. Então buscamos views atuais e preservamos.
    ids = [r["id"] for r in rows]
    have = {}
    for i in range(0, len(ids), 200):
        q = ",".join(ids[i:i+200])
        req = urllib.request.Request(f"{SB}/rest/v1/live_attr?id=in.({q})&select=id,views,impressions", headers=SBH)
        try:
            for x in json.load(urllib.request.urlopen(req, timeout=60)):
                have[x["id"]] = (x.get("views") or 0, x.get("impressions") or 0)
        except Exception:
            pass
    for r in rows:
        v = have.get(r["id"])
        if v and v[0] and not r["views"]: r["views"] = v[0]
        if v and v[1] and not r["impressions"]: r["impressions"] = v[1]
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i+chunk]).encode()
        req = urllib.request.Request(f"{SB}/rest/v1/live_attr?on_conflict=id", data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert] {e.code}: {e.read()[:300]} (rodou live_attr.sql?)"); raise
    print(f"  ✓ live_attr: {len(rows)} salas gravadas (views preservadas)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio"); ap.add_argument("--fim"); ap.add_argument("--dias", type=int, default=40)
    args = ap.parse_args()
    if args.inicio:
        sd, ed = args.inicio, (args.fim or datetime.now(BRT).strftime("%Y-%m-%d"))
    else:
        ed = datetime.now(BRT).strftime("%Y-%m-%d"); sd = (datetime.now(BRT) - timedelta(days=args.dias)).strftime("%Y-%m-%d")
    print(f"═════ LIVE attr (Seller Center via API) — {sd} → {ed} · own={OWN} ═════")
    # itera mês a mês (janela grande estoura paginação)
    d0 = datetime.strptime(sd, "%Y-%m-%d").replace(day=1); d1 = datetime.strptime(ed, "%Y-%m-%d")
    cur = d0; todas = {}
    while cur <= d1:
        nxt = (cur.replace(day=28) + timedelta(days=8)).replace(day=1)
        rows = page_mes(cur.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d"))
        gmv = sum(r["gmv"] for r in rows)
        print(f"  {cur.strftime('%Y-%m')}: {len(rows):>3} salas próprias · GMV R$ {gmv:>13,.2f}")
        for r in rows: todas[r["id"]] = r
        cur = nxt
    rows = list(todas.values())
    print(f"  → total {len(rows)} salas próprias")
    upsert(rows)
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
