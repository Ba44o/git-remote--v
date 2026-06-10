#!/usr/bin/env python3
"""
Rhode — Coletor de pedidos por SKU (lado LOJA) → tabela pedidos_sku (admin/CFO).

Puxa os pedidos da loja via TikTok Shop API (/order/202309/orders/search, reusando
coletar_dados.buscar_pedidos) e persiste o detalhe POR SKU — o que hoje não existe
no Supabase (o etl_diario só salva o agregado diário). É a base de GMV por produto
da conciliação de margem.

Granularidade: 1 linha por (order_id, sku_name). Cada line_item da API = 1 unidade
(não há campo quantity), então qty = contagem e gmv = soma dos sale_price.

Idempotente: id = "{order_id}:{sku}" + upsert merge-duplicates. Rodar de novo no
mesmo período não duplica e atualiza status/valores.

Uso:  python3 coletar_pedidos_sku.py --dias 21
"""
import os, sys, json, argparse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coletar_dados import buscar_pedidos

SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}


def fnum(s):
    """sale_price/seller_discount vêm como string (ex '99.90'). Parse tolerante."""
    if s in (None, ""):
        return 0.0
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def extrair_cor(sku_name):
    """Heurística leve: variação TikTok costuma ser 'Cor, Tam' ou 'Cor'.
    Pega o 1º trecho antes da vírgula quando há vírgula. Refinável no import do CPV."""
    if not sku_name:
        return ""
    parts = [p.strip() for p in str(sku_name).split(",")]
    return parts[0] if len(parts) >= 2 else ""


def upsert(table, rows, chunk=500, on_conflict=None):
    if not rows:
        return
    url = f"{SB_URL}/rest/v1/{table}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i + chunk]).encode()
        req = urllib.request.Request(url, data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert {table}] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas")


def agregar_por_sku(pedidos):
    """pedidos (lista de orders da API) → linhas por (order_id, sku_name)."""
    acc = {}  # (order_id, sku) -> linha agregada
    for o in pedidos:
        order_id = str(o.get("id") or "")
        if not order_id:
            continue
        status = o.get("status", "") or ""
        ct = int(o.get("create_time", 0) or 0)
        data = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m-%d") if ct else None
        periodo = datetime.fromtimestamp(ct, tz=timezone.utc).strftime("%Y-%m") if ct else None
        for item in o.get("line_items", []):
            sku = (item.get("sku_name") or "")[:120]
            key = (order_id, sku)
            row = acc.get(key)
            if row is None:
                row = {
                    "id": f"{order_id}:{sku}",
                    "order_id": order_id,
                    "sku": sku,
                    "seller_sku": (item.get("seller_sku") or "")[:120],
                    "produto": (item.get("product_name") or "")[:160],
                    "cor": extrair_cor(sku),
                    "qty": 0,
                    "gmv": 0.0,
                    "status": status,
                    "order_time": ct,
                    "data": data,
                    "periodo": periodo,
                }
                acc[key] = row
            row["qty"] += 1
            row["gmv"] = round(row["gmv"] + fnum(item.get("sale_price")), 2)
    return list(acc.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=21, help="janela retroativa em dias (default 21)")
    ap.add_argument("--inicio", help="data inicial YYYY-MM-DD (sobrepõe --dias)")
    ap.add_argument("--fim", help="data final YYYY-MM-DD (default hoje)")
    args = ap.parse_args()

    if args.inicio:
        ini_s = args.inicio
        fim_s = args.fim or datetime.now().strftime("%Y-%m-%d")
    else:
        fim = datetime.now()
        ini = fim - timedelta(days=args.dias)
        ini_s, fim_s = ini.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d")
    print(f"═════ Coleta pedidos_sku — {ini_s} → {fim_s} ═════")

    pedidos = buscar_pedidos(ini_s, fim_s)
    if not pedidos:
        print("  ⚠ Nenhum pedido no período — nada a fazer.")
        return

    rows = agregar_por_sku(pedidos)
    print(f"  → {len(pedidos)} pedidos → {len(rows)} linhas (order×sku)")
    if rows:
        gmv_total = sum(r["gmv"] for r in rows)
        print(f"  → GMV bruto agregado: R$ {gmv_total:,.2f}")
    upsert("pedidos_sku", rows, on_conflict="id")
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
