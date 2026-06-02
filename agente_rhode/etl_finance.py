"""
Rhode Jeans — ETL Financeiro (statements / settlements da loja)
================================================================
Puxa os statements financeiros da TikTok Shop API via coletar_dados.buscar_finance()
e gera warehouse/raw_finance.csv (1 linha por statement = settlement).

Cada statement mostra o caminho do dinheiro:
  revenue_amount  - fee_amount(taxa TikTok) - shipping_cost_amount + adjustment_amount
  = settlement_amount  (o que a loja REALMENTE recebe)

Granularidade: por statement (PK = id). O painel agrega por dia/período.

Uso:
  python agente_rhode/etl_finance.py --dias 90

Output:
  warehouse/raw_finance.csv  →  sync via sync_supabase.py::sync_finance()
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

WAREHOUSE = Path("warehouse")


def _f(v):
    """Converte string de valor monetário (pode vir negativa) pra float."""
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0.0


def coletar(dias: int) -> pd.DataFrame:
    # coletar_dados.py está na raiz do projeto (um nível acima de agente_rhode/)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_finance
    from datetime import datetime

    hoje   = date.today()
    inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim    = hoje.strftime("%Y-%m-%d")
    statements = buscar_finance(inicio, fim)
    if not statements:
        print("[ERRO] Nenhum statement retornado.")
        sys.exit(1)

    rows = []
    for s in statements:
        t = int(s.get("statement_time", 0) or 0)
        rows.append({
            "id":              str(s.get("id", "")),
            "data":            datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else "",
            "statement_time":  t,
            "revenue_amount":  _f(s.get("revenue_amount")),
            "fee_amount":      _f(s.get("fee_amount")),            # negativo = taxa TikTok
            "shipping_cost":   _f(s.get("shipping_cost_amount")),  # negativo = frete
            "adjustment":      _f(s.get("adjustment_amount")),
            "net_sales":       _f(s.get("net_sales_amount")),
            "settlement":      _f(s.get("settlement_amount")),     # o que cai de fato
            "payment_status":  str(s.get("payment_status", "")),
            "currency":        str(s.get("currency", "BRL")),
        })
    out = pd.DataFrame(rows)
    out = out[out["id"] != ""].drop_duplicates("id", keep="last")
    return out.sort_values("statement_time").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=90, help="janela em dias")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_finance.csv"))
    args = ap.parse_args()

    out = coletar(args.dias)
    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    tot_rev  = out["revenue_amount"].sum()
    tot_fee  = out["fee_amount"].sum()
    tot_set  = out["settlement"].sum()
    pct_fee  = (abs(tot_fee) / tot_rev * 100) if tot_rev else 0
    print(f"\n  ✓ {len(out)} statements ({out['data'].min()} → {out['data'].max()})")
    print(f"  ✓ Receita bruta:   R$ {tot_rev:,.2f}")
    print(f"  ✓ Taxa TikTok:     R$ {tot_fee:,.2f}  ({pct_fee:.1f}% da receita)")
    print(f"  ✓ Settlement (líq): R$ {tot_set:,.2f}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
