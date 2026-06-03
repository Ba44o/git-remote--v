"""
Rhode Jeans — ETL Seeding REAL (Target Collaborations × vendas por produto)
============================================================================
Fonte de verdade dos convites = Target Collaborations API (não a tabela manual).
Atribuição CORRETA: GMV só dos PRODUTOS do convite, vendidos pela CREATOR convidada
(cruza affiliate orders por creator_username × product_id — mesmo namespace de id).

Grão: 1 linha por convite × creator. Mostra funil (convidou→vitrine→conteúdo),
amostra grátis, comissão, e o GMV/comissão que o produto seedado de fato gerou.

Uso:
  python agente_rhode/etl_seeding.py --dias 60

Output:
  warehouse/raw_seeding.csv  →  sync via sync_supabase.py::sync_seeding()
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


def _d(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def coletar(dias: int) -> pd.DataFrame:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_target_collaborations, buscar_affiliate_orders

    # 1) convites reais (com creators + product_ids)
    colabs = buscar_target_collaborations()

    # 2) affiliate orders → agrega por (creator_username, product_id)
    hoje = date.today()
    ini  = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim  = hoje.strftime("%Y-%m-%d")
    orders = buscar_affiliate_orders(ini, fim)
    aff = {}
    for o in orders:
        oid = o.get("id", "")
        for s in o.get("skus", []):
            cr  = (s.get("creator_username") or "").lower()
            pid = s.get("product_id") or ""
            if not cr or not pid:
                continue
            a = aff.get((cr, pid))
            if a is None:
                a = aff[(cr, pid)] = {"gmv": 0.0, "com": 0.0, "orders": set()}
            a["gmv"] += _f(s.get("estimated_commission_base", {}).get("amount"))
            a["com"] += _f(s.get("estimated_paid_commission", {}).get("amount"))
            a["orders"].add(oid)

    # 3) agrega por CREATOR, DEDUPLICANDO produtos entre os convites dela
    #    (uma creator pode ter vários convites com produtos sobrepostos →
    #     somar por convite triplicava a venda. Aqui cada produto conta 1x.)
    byc = {}
    for c in colabs:
        pids  = [p.get("id") for p in (c.get("products") or []) if p.get("id")]
        rates = [int(p["commission"]["rate"]) for p in (c.get("products") or [])
                 if p.get("commission", {}).get("rate")]
        for cr in (c.get("creators") or []):
            uname = cr.get("username") or ""
            if not uname:
                continue
            k = uname.lower()
            o = byc.get(k)
            if o is None:
                o = byc[k] = {"creator": uname, "nick": cr.get("nickname") or "",
                              "pids": set(), "free": False, "convites": 0,
                              "statuses": set(), "rates": []}
            o["pids"].update(pids)
            o["convites"] += 1
            o["free"] = o["free"] or bool(c.get("has_free_sample"))
            o["statuses"].add(c.get("status", ""))
            o["rates"].extend(rates)

    rows = []
    for k, o in byc.items():
        gmv = com = 0.0; peds = set()
        for pid in o["pids"]:                      # cada produto convidado, 1x
            a = aff.get((k, pid))
            if a:
                gmv += a["gmv"]; com += a["com"]; peds |= a["orders"]
        rows.append({
            "id":               k,
            "creator":          o["creator"],
            "creator_nick":     o["nick"],
            "convites":         o["convites"],
            "n_produtos":       len(o["pids"]),                 # produtos únicos convidados
            "has_free_sample":  o["free"],
            "status":           "·".join(sorted(s for s in o["statuses"] if s)),
            "commission_pct":   round(sum(o["rates"]) / len(o["rates"]) / 100, 1) if o["rates"] else 0.0,
            "gmv_seedado":      round(gmv, 2),                  # GMV nos produtos convidados (dedup)
            "comissao_seedada": round(com, 2),
            "pedidos_seedados": len(peds),
        })
    out = pd.DataFrame([r for r in rows if r["creator"]])
    return out.sort_values("gmv_seedado", ascending=False).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=60, help="janela de affiliate orders p/ atribuição")
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_seeding.csv"))
    args = ap.parse_args()

    out = coletar(args.dias)
    if out.empty:
        print("[ERRO] Nenhum convite/creator.")
        sys.exit(1)
    WAREHOUSE.mkdir(exist_ok=True)
    out.to_csv(args.output, index=False)

    n = len(out); conv = (out["gmv_seedado"] > 0).sum()
    print(f"\n  ✓ {n} creators com convite · {conv} venderam o produto convidado ({conv/n*100:.0f}%)")
    print(f"  ✓ GMV nos produtos convidados (dedup, total): R$ {out['gmv_seedado'].sum():,.2f}")
    print(f"  ✓ com amostra grátis: {int(out['has_free_sample'].sum())}")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
