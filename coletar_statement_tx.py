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


# coluna_no_supabase -> campo_na_API. Itemiza o settlement pra separar
# taxa normal (comissão/frete/serviço) de custo de DEVOLUÇÃO e da promoção.
FIELDS = {
    "customer_payment":         "customer_payment_amount",
    "settlement":               "settlement_amount",
    "fee_total":                "fee_amount",
    "platform_commission":      "platform_commission_amount",
    "affiliate_commission":     "affiliate_commission_amount",
    "affiliate_ads_commission": "affiliate_ads_commission_amount",
    "affiliate_partner":        "affiliate_partner_commission_amount",
    "referral_fee":             "referral_fee_amount",
    "transaction_fee":          "transaction_fee_amount",
    "shipping":                 "shipping_cost_amount",
    # frete detalhado (alta frequência nos dados — ~83-91% das linhas)
    "actual_shipping_fee":       "actual_shipping_fee_amount",            # frete REAL pago à transportadora (−)
    "fbm_shipping_cost":         "fbm_shipping_cost_amount",              # frete que a LOJA banca (merchant-fulfilled, −)
    "platform_shipping_subsidy": "platform_shipping_fee_discount_amount", # subsídio de frete da plataforma (crédito +)
    "adjustment":               "adjustment_amount",
    # receita / promoção
    "gross_sales":              "gross_sales_amount",
    "seller_discount":          "seller_discount_amount",
    "platform_discount":        "platform_discount_amount",
    "revenue":                  "revenue_amount",
    # custos de DEVOLUÇÃO (separar da taxa normal!)
    "customer_refund":          "customer_refund_amount",
    "return_shipping":          "return_shipping_fee_amount",
    "refund_admin_fee":         "refund_administration_fee_amount",
}

# statement_transactions com type != 'ORDER' vêm com order_id NULL (pedido em
# adjustment_order_id) e o valor duplicado em settlement_amount E adjustment_amount.
# Tipos de REEMBOLSO (crédito +) ganham coluna própria; os demais tipos de ajuste
# (penalty/chargeback/compensation/etc.) caem no `adjustment` genérico. Todos são
# religados por adjustment_order_id pra não sumir do settlement (gap de conciliação).
REIMB_TYPES = {
    "LOGISTICS_REIMBURSEMENT": "logistics_reimbursement",  # reembolso por problema logístico (extravio/atraso)
    "PLATFORM_REIMBURSEMENT":  "platform_reimbursement",   # "refund without return": plataforma absorve e credita a loja
}


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
    ap.add_argument("--dry-run", action="store_true", help="não escreve no Supabase; só valida e mostra o breakdown")
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

    acc, ntx, unknown_types = {}, 0, {}   # (statement_id, order_id) -> linha agregada
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
                ty  = t.get("type") or ""
                oid = str(t.get("order_id") or "")
                reimb_col = REIMB_TYPES.get(ty)
                if not oid and ty and ty != "ORDER":
                    # Linha de ajuste (reembolso/penalidade/chargeback/…) vem com order_id
                    # NULL; o pedido está no adjustment_order_id. Sem religar, o coletor
                    # descartava (if not oid) → statement_tx ficava MENOR que
                    # finance_statements pelo total desses lançamentos (gap de conciliação).
                    oid = str(t.get("adjustment_order_id") or "")
                    if ty not in REIMB_TYPES:
                        unknown_types[ty] = unknown_types.get(ty, 0) + 1
                if not oid: continue
                ct = int(t.get("order_create_time") or 0)
                key = (sid, oid); row = acc.get(key)
                if row is None:
                    data = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m-%d") if ct else None
                    per  = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m") if ct else None
                    row = acc[key] = {"id": f"{sid}:{oid}", "statement_id": str(sid), "order_id": oid,
                        "order_create_time": ct, "data": data, "periodo": per,
                        "moeda": t.get("currency") or "BRL",
                        **{c: 0.0 for c in REIMB_TYPES.values()}, **{c: 0.0 for c in FIELDS}}
                for col, src in FIELDS.items():
                    # Tipos de reembolso chegam com o crédito duplicado em settlement_amount
                    # E adjustment_amount. Mantemos em `settlement` (dinheiro recebido →
                    # fecha o gap), mas fora do `adjustment` genérico: cada um vai pra sua
                    # coluna dedicada. (Outros ajustes sem coluna própria seguem em adjustment.)
                    if reimb_col and col == "adjustment": continue
                    row[col] = round(row[col] + F(t.get(src)), 2)
                if reimb_col:
                    row[reimb_col] = round(row[reimb_col] + F(t.get("settlement_amount")), 2)
                ntx += 1
            cur = d.get("next_page_token", "")
            if not cur or not txs: break
        if i % 15 == 0: print(f"  …{i}/{len(ids)} statements · {ntx} tx")

    rows = list(acc.values())
    if rows:
        tp = sum(r["customer_payment"] for r in rows); ts = sum(r["settlement"] for r in rows)
        taxa = (1 - ts / tp) * 100 if tp else 0
        print(f"  → {ntx} tx → {len(rows)} (statement×pedido) · pago R$ {tp:,.0f} · settlement R$ {ts:,.0f} · taxa média {taxa:.1f}%")
        # breakdown de cada reembolso (crédito) por período
        for col in REIMB_TYPES.values():
            tot = sum(r.get(col, 0) for r in rows)
            per = {}
            for r in rows:
                v = r.get(col, 0) or 0
                if v:
                    p = r["periodo"] or "s/ período"
                    per.setdefault(p, [0.0, 0]); per[p][0] += v; per[p][1] += 1
            print(f"     {col}: R$ {tot:,.2f}")
            for p in sorted(per):
                t0, n = per[p]; print(f"        {p}: R$ {t0:,.2f}  ({n} pedidos)")
        if unknown_types:
            print(f"  ⚠ types SEM coluna própria (foram p/ adjustment genérico): "
                  f"{dict(sorted(unknown_types.items(), key=lambda kv: -kv[1]))}")
    if args.dry_run:
        print("  ⚠ DRY-RUN: nada gravado no Supabase."); return
    upsert("statement_tx", rows, on_conflict="id")
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
