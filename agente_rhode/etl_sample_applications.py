"""
Rhode Jeans — ETL Sample Applications (free sample REAL do TikTok Shop)
======================================================================
Fonte de verdade das PEÇAS de seeding: endpoint sample_applications.
Grão: 1 linha por creator × SKU pedido, com status de envio + data do convite.

Peça "enviada" = status COMPLETED / SHIPPED / CONTENT_PENDING.
(NÃO enviada = *_CANCELLED ou AWAITING_SHIPMENT.)

Uso:
  python agente_rhode/etl_sample_applications.py
  python agente_rhode/etl_sample_applications.py --no-dates   # pula enriquecimento de data

Output:
  warehouse/raw_sample_applications.csv  →  sync via sync_supabase.py::sync_sample_applications()
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

WAREHOUSE = Path("warehouse")
SENT = {"COMPLETED", "SHIPPED", "CONTENT_PENDING"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(WAREHOUSE / "raw_sample_applications.csv"))
    ap.add_argument("--no-dates", action="store_true", help="pula enriquecimento da data do convite")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from coletar_dados import buscar_sample_applications

    apps = buscar_sample_applications(enrich_dates=not args.no_dates)
    if not apps:
        print("[ERRO] Nenhum pedido de amostra retornado.")
        sys.exit(1)

    df = pd.DataFrame(apps)
    WAREHOUSE.mkdir(exist_ok=True)
    df.to_csv(args.output, index=False)

    enviadas = int(df.status.isin(SENT).sum())
    print(f"\n  ✓ {len(df)} pedidos de amostra · {enviadas} enviadas · {df.creator.nunique()} creators")
    print(f"  ✓ Salvo em {args.output}")


if __name__ == "__main__":
    main()
