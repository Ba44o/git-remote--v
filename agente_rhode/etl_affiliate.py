"""
Rhode Jeans — ETL Performance de Afiliadas (creator)
=====================================================
Puxa pedidos de afiliado da TikTok Shop API (coletar_dados.buscar_affiliate_orders)
e agrega em creator × dia × tipo de conteúdo.

GMV  = soma de estimated_commission_base (a base de comissão = valor de venda
       atribuído à creator, métrica padrão de "GMV de afiliado" do TikTok).
Comissão = soma de estimated_paid_commission (o que a creator ganha).

Uso:
  python agente_rhode/etl_affiliate.py --dias 30

Output:
  warehouse/raw_affiliate.csv  →  sync via sync_supabase.py::sync_affiliate_perf()
"""
import argparse
import sys
from datetime import date, timedelta, datetime
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
    from coletar_dados import buscar_affiliate_orders

    hoje   = date.today()
    inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim    = hoje.strftime("%Y-%m-%d")
    orders = buscar_affiliate_orders(inicio, fim)
    if not orders:
        print("[ERRO] Nenhum pedido de afiliado retornado.")
        sys.exit(1)

    agg = {}
    for o in orders:
        t    = int(o.get("create_time", 0) or 0)
        data = datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else ""
        oid  = o.get("id", "")
        for s in o.get("skus", []):
            cr = (s.get("creator_username") or "—").strip() or "—"
            ct = (s.get("content_type") or "—").strip() or "—"
            key = (cr, data, ct)
            a = agg.get(key)
            if a is None:
                a = agg[key] = {"creator": cr, "data": data, "content_type": ct,
                                "gmv": 0.0, "comissao": 0.0, "itens": 0, "orders": set()}
            a["gmv"]      += _f(s.get("estimated_commission_base", {}).get("amount"))
            a["comissao"] += _f(s.get("estimated_paid_commission", {}).get("amount"))
            a["itens"]    += int(s.get("quantity", 0) or 0)
            a["orders"].add(oid)

    rows = []
    for (cr, data, ct), a in agg.items():
        if not cr or not data:
            continue
        rows.append({
            "id":           f"{cr}|{data}|{ct}",
            "creator":      cr,
            "data":         data,
            "content_type": ct,
            "gmv":          round(a["gmv"], 2),
            "comissao":     round(a["comissao"], 2),
            "pedidos":      len(a["orders"]),
            "itens":        a["itens"],
        })
    return pd.DataFrame(rows).sort_values(["data", "gmv"], ascending=[True, False]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=30, help="janela em dias (volume alto de afiliado)")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_affiliate.csv"))
    args = ap.parse_args()

    out = coletar(args.dias)
    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    tot_gmv = out["gmv"].sum(); tot_com = out["comissao"].sum()
    ncreators = out["creator"].nunique()
    print(f"\n  ✓ {len(out)} linhas · {ncreators} creators ({out['data'].min()} → {out['data'].max()})")
    print(f"  ✓ GMV afiliado:  R$ {tot_gmv:,.2f}")
    print(f"  ✓ Comissão:      R$ {tot_com:,.2f}  ({tot_com/tot_gmv*100:.1f}% do GMV)" if tot_gmv else "")
    top = out.groupby("creator")["gmv"].sum().sort_values(ascending=False).head(5)
    print(f"  ✓ Top creators por GMV:")
    for nome, val in top.items():
        print(f"      R$ {val:>11,.2f}  @{nome}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
