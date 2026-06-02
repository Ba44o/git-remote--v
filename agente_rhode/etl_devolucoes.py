"""
Rhode Jeans — ETL Devoluções / Reembolsos
===========================================
Puxa devoluções da TikTok Shop API via coletar_dados.buscar_devolucoes() e
gera warehouse/raw_devolucoes.csv.

Granularidade: 1 linha por ITEM devolvido (return_line_item) — permite análise
"valor reembolsado por produto". Cada linha carrega também o refund do return
inteiro (refund_return, denormalizado) pra somar total real deduplicando por return_id.

Uso:
  python agente_rhode/etl_devolucoes.py --dias 90

Output:
  warehouse/raw_devolucoes.csv  →  sync via sync_supabase.py::sync_devolucoes()
"""
import argparse
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

import pandas as pd

WAREHOUSE = Path("warehouse")


def _f(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0.0


def coletar(dias: int) -> pd.DataFrame:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_devolucoes

    hoje   = date.today()
    inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim    = hoje.strftime("%Y-%m-%d")
    returns = buscar_devolucoes(inicio, fim)
    if not returns:
        print("[ERRO] Nenhuma devolução retornada.")
        sys.exit(1)

    rows = []
    for r in returns:
        t    = int(r.get("create_time", 0) or 0)
        data = datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else ""
        rid  = str(r.get("return_id", ""))
        oid  = str(r.get("order_id", ""))
        refund_return = _f(r.get("refund_amount", {}).get("refund_total"))
        reason = r.get("return_reason_text", "") or ""
        status = r.get("return_status", "") or ""
        rtype  = r.get("return_type", "") or ""
        items  = r.get("return_line_items") or [{}]
        for it in items:
            iid = it.get("return_line_item_id") or f"{rid}_{it.get('order_line_item_id','')}"
            rows.append({
                "id":            str(iid),
                "return_id":     rid,
                "order_id":      oid,
                "data":          data,
                "product_name":  it.get("product_name", "") or "",
                "seller_sku":    it.get("seller_sku", "") or "",
                "refund_item":   _f(it.get("refund_amount", {}).get("refund_total")),
                "refund_return": refund_return,
                "return_reason": reason,
                "return_status": status,
                "return_type":   rtype,
            })
    out = pd.DataFrame(rows)
    out = out[out["id"] != ""].drop_duplicates("id", keep="last")
    return out.sort_values("data").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=90, help="janela em dias")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_devolucoes.csv"))
    args = ap.parse_args()

    out = coletar(args.dias)
    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    n_returns = out["return_id"].nunique()
    tot_refund = out.drop_duplicates("return_id")["refund_return"].sum()
    print(f"\n  ✓ {len(out)} itens devolvidos · {n_returns} devoluções ({out['data'].min()} → {out['data'].max()})")
    print(f"  ✓ Total reembolsado: R$ {tot_refund:,.2f}")
    top = out.groupby("product_name")["refund_item"].sum().sort_values(ascending=False).head(3)
    print(f"  ✓ Top produtos por reembolso:")
    for nome, val in top.items():
        print(f"      R$ {val:>10,.2f}  {nome[:50]}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
