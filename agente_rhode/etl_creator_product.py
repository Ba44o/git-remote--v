"""
Rhode Jeans — ETL Creator × Produto
====================================
Agrega affiliate orders por (creator × product_id) e junta o título do produto
(via Product API). Base pra: matriz creator×produto, drill-down de creator
(produtos que ela vende), e direcionamento de convites.

Uso:
  python agente_rhode/etl_creator_product.py --dias 60

Output:
  warehouse/raw_creator_product.csv  →  sync via sync_supabase.py::sync_creator_product()
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

WAREHOUSE = Path("warehouse")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def coletar(dias: int) -> pd.DataFrame:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_affiliate_orders, buscar_produtos
    from datetime import datetime

    prod = buscar_produtos()                                   # product_id → {title,...}
    hoje = date.today()
    ini  = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim  = hoje.strftime("%Y-%m-%d")
    orders = buscar_affiliate_orders(ini, fim)

    # grão = creator × produto × DIA (permite janela global ajustável nos painéis)
    agg = {}
    for o in orders:
        oid = o.get("id", "")
        t   = int(o.get("create_time", 0) or 0)
        data = datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else ""
        for s in o.get("skus", []):
            cr  = (s.get("creator_username") or "").lower()
            pid = s.get("product_id") or ""
            if not cr or not pid or not data:
                continue
            a = agg.get((cr, pid, data))
            if a is None:
                a = agg[(cr, pid, data)] = {"gmv": 0.0, "com": 0.0, "orders": set()}
            a["gmv"] += _f(s.get("estimated_commission_base", {}).get("amount"))
            a["com"] += _f(s.get("estimated_paid_commission", {}).get("amount"))
            a["orders"].add(oid)

    rows = []
    for (cr, pid, data), a in agg.items():
        info = prod.get(pid, {})
        rows.append({
            "id":         f"{cr}|{pid}|{data}",
            "creator":    cr,
            "product_id": pid,
            "data":       data,
            "produto":    info.get("title", "") or f"(id {pid})",
            "seller_sku": info.get("seller_sku", ""),
            "gmv":        round(a["gmv"], 2),
            "comissao":   round(a["com"], 2),
            "pedidos":    len(a["orders"]),
        })
    if not rows:
        print("[ERRO] Nenhum registro creator×produto×dia.")
        sys.exit(1)
    return pd.DataFrame(rows).sort_values(["data", "gmv"], ascending=[True, False]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=90, help="máx 90 = limite da API por request")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_creator_product.csv"))
    args = ap.parse_args()

    out = coletar(args.dias)
    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"\n  ✓ {len(out)} registros creator×produto×dia · {out['creator'].nunique()} creators · {out['product_id'].nunique()} produtos · {out['data'].min()}→{out['data'].max()}")
    print(f"  ✓ GMV total: R$ {out['gmv'].sum():,.2f}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
