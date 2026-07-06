"""
Rhode Jeans — Coletor de vendas para atribuição de ROI do Seeding (parametrizado por mês)
=========================================================================================
Fonte: Affiliate Orders API (POST /affiliate_seller/202410/orders/search) — 1 linha por
SKU vendido, com creator_username + create_time + GMV (estimated_commission_base) +
quantity (unidades) + fully_return. Roda LOCAL / CI (não dispara etl_sync.yml).

Grão de saída: creator × product_id × dia → gmv, unidades, pedidos, devolvidos.
Janela do PULL: do 1º dia do mês-alvo até `fim` (data de execução; default = hoje).
A atribuição por creator (do 1º convite dela em diante) é feita depois, no build.

Uso:
  python coletar_vendas_seeding.py --mes 2026-06 [--fim 2026-07-06]

Output: warehouse/raw_vendas_seeding_<AAAA-MM>.csv
"""
from __future__ import annotations
import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
WH = BASE / "warehouse"


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _mes_ini(mes: str) -> str:
    """1º dia do mês 'AAAA-MM' como 'AAAA-MM-01'."""
    datetime.strptime(mes, "%Y-%m")   # valida formato
    return f"{mes}-01"


def coletar(mes: str, fim: str | None = None) -> Path:
    """Coleta vendas de afiliada do 1º dia de `mes` até `fim`. Retorna o path do CSV."""
    ini = _mes_ini(mes)
    fim = fim or date.today().strftime("%Y-%m-%d")
    out = WH / f"raw_vendas_seeding_{mes}.csv"

    sys.path.insert(0, str(BASE))
    from coletar_dados import buscar_affiliate_orders  # import tardio (usa token fresco)

    orders = buscar_affiliate_orders(ini, fim)
    agg = {}
    for o in orders:
        t = int(o.get("create_time", 0) or 0)
        data = datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else ""
        for s in o.get("skus", []):
            cr = (s.get("creator_username") or "").lower().strip()
            pid = s.get("product_id") or ""
            if not cr or not data:
                continue
            key = (cr, pid, data)
            a = agg.get(key)
            if a is None:
                a = agg[key] = {"gmv": 0.0, "com": 0.0, "unid": 0, "orders": set(), "dev": 0}
            a["gmv"] += _f(s.get("estimated_commission_base", {}).get("amount"))
            a["com"] += _f(s.get("estimated_paid_commission", {}).get("amount"))
            a["unid"] += int(s.get("quantity", 0) or 0)
            a["orders"].add(o.get("id", ""))
            if str(s.get("fully_return", "")).lower() in ("yes", "y", "true"):
                a["dev"] += int(s.get("quantity", 0) or 0)

    WH.mkdir(exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["creator", "product_id", "data", "gmv", "comissao",
                    "unidades", "pedidos", "unid_devolvidas"])
        for (cr, pid, data), a in sorted(agg.items(), key=lambda x: (x[0][0], x[0][2])):
            w.writerow([cr, pid, data, round(a["gmv"], 2), round(a["com"], 2),
                        a["unid"], len(a["orders"]), a["dev"]])

    tot_gmv = sum(a["gmv"] for a in agg.values())
    tot_unid = sum(a["unid"] for a in agg.values())
    creators = len({k[0] for k in agg})
    print(f"  OK vendas: {len(agg)} linhas creator×produto×dia · {creators} creators")
    print(f"  Janela pull {ini}..{fim}: R$ {tot_gmv:,.2f} · {tot_unid} unidades")
    print(f"  Salvo em {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", required=True, help="mês-alvo AAAA-MM")
    ap.add_argument("--fim", default=None, help="fim da janela (AAAA-MM-DD); default = hoje")
    args = ap.parse_args()
    coletar(args.mes, args.fim)


if __name__ == "__main__":
    main()
