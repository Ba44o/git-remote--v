#!/usr/bin/env python3
"""
Rhode — Coletor de statement_transactions (order-level) → tabela statement_tx.

Puxa o detalhe POR PEDIDO da Finance API do TikTok Shop:
  /finance/202309/statements/{statement_id}/statement_transactions
Cada linha traz a cascata completa (customer_payment → settlement + comissões),
dando o **settlement EXATO por pedido** — substitui a estimativa "GMV × eficiência".

Reusa o padrão validado do analise_liquidacao_66.py (chamar/buscar_finance + retry
no rate-limit 36009002 + paginação next_page_token). Idempotente (id=statement:order).

Uso:
  python3 coletar_statement_tx.py --dias 60
  python3 coletar_statement_tx.py --inicio 2026-01-01 --fim 2026-06-30
"""
import os, sys, json, time, argparse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar_dados import chamar, buscar_finance

SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}


def F(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0


def retry(method, path, params=None):
    """Retry no rate-limit (code 36009002) com backoff — igual ao analise_liquidacao_66."""
    r = None
    for t in range(8):
        r = chamar(method, path, params=params)
        if r.get("code") != 36009002: return r
        time.sleep(min(3 * (t + 1), 20))
    return r


def upsert(table, rows, chunk=500, on_conflict="id"):
    if not rows:
        print(f"  [SKIP] {table} sem linhas"); return
    url = f"{SB_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i + chunk]).encode()
        req = urllib.request.Request(url, data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert {table}] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=60, help="janela de statements (por statement_time)")
    ap.add_argument("--inicio"); ap.add_argument("--fim")
    args = ap.parse_args()
    if args.inicio:
        ini, fim = args.inicio, (args.fim or datetime.now().strftime("%Y-%m-%d"))
    else:
        fim = datetime.now().strftime("%Y-%m-%d")
        ini = (datetime.now() - timedelta(days=args.dias)).strftime("%Y-%m-%d")

    print(f"═════ statement_tx — statements {ini} → {fim} ═════")
    stmts = buscar_finance(ini, fim)
    ids = [s["id"] for s in stmts]
    print(f"  {len(ids)} statements a processar")

    acc, ntx = {}, 0   # (statement_id, order_id) -> linha agregada
    for i, sid in enumerate(ids, 1):
        cur = ""
        while True:
            p = {"page_size": 50, "sort_field": "order_create_time", "sort_order": "DESC"}
            if cur: p["page_token"] = cur
            r = retry("GET", f"/finance/202309/statements/{sid}/statement_transactions", params=p)
            if r.get("code") != 0:
                print(f"    ⚠ statement {sid}: code={r.get('code')} {str(r.get('message'))[:60]}"); break
            d = r.get("data", {}); txs = d.get("statement_transactions") or []
            for t in txs:
                oid = str(t.get("order_id") or "")
                if not oid: continue
                ct = int(t.get("order_create_time") or 0)
                key = (sid, oid); row = acc.get(key)
                if row is None:
                    data = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m-%d") if ct else None
                    per  = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m") if ct else None
                    row = acc[key] = {"id": f"{sid}:{oid}", "statement_id": str(sid), "order_id": oid,
                        "order_create_time": ct, "data": data, "periodo": per,
                        "customer_payment": 0.0, "settlement": 0.0, "fee_total": 0.0,
                        "platform_commission": 0.0, "affiliate_commission": 0.0,
                        "affiliate_ads_commission": 0.0, "shipping": 0.0, "adjustment": 0.0,
                        "moeda": t.get("currency") or "BRL"}
                row["customer_payment"]        = round(row["customer_payment"] + F(t.get("customer_payment_amount")), 2)
                row["settlement"]              = round(row["settlement"] + F(t.get("settlement_amount")), 2)
                row["fee_total"]               = round(row["fee_total"] + F(t.get("fee_amount")), 2)
                row["platform_commission"]     = round(row["platform_commission"] + F(t.get("platform_commission_amount")), 2)
                row["affiliate_commission"]    = round(row["affiliate_commission"] + F(t.get("affiliate_commission_amount")), 2)
                row["affiliate_ads_commission"]= round(row["affiliate_ads_commission"] + F(t.get("affiliate_ads_commission_amount")), 2)
                row["shipping"]                = round(row["shipping"] + F(t.get("shipping_cost_amount")), 2)
                row["adjustment"]              = round(row["adjustment"] + F(t.get("adjustment_amount")), 2)
                ntx += 1
            cur = d.get("next_page_token", "")
            if not cur or not txs: break
        if i % 15 == 0: print(f"  …{i}/{len(ids)} statements · {ntx} tx")

    rows = list(acc.values())
    if rows:
        tp = sum(r["customer_payment"] for r in rows); ts = sum(r["settlement"] for r in rows)
        taxa = (1 - ts / tp) * 100 if tp else 0
        print(f"  → {ntx} tx → {len(rows)} (statement×pedido) · pago R$ {tp:,.0f} · settlement R$ {ts:,.0f} · taxa média {taxa:.1f}%")
    upsert("statement_tx", rows, on_conflict="id")
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
