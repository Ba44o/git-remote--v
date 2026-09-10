#!/usr/bin/env python3
"""
Rhode — BASE DE RECEITA CANÔNICA. Use isto. Não re-derive receita à mão.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O mesmo erro de base já aconteceu TRÊS vezes (mega-live 06/08, rajada 04/09, live 10/09):
calcular taxa/margem sobre o que o CLIENTE PAGOU em vez da RECEITA DE LISTA. Ele inverte
o veredito — na live de 10/09 virou "prejuízo de R$ 1.409" o que era "+R$ 312".

A REGRA
-------
O cupom da plataforma é SUBSÍDIO DO TIKTOK, não desconto da loja. O cliente paga menos,
mas o TikTok repõe a diferença. A loja fatura sobre a LISTA:

    receita_lista = sub_total + platform_discount

  · sub_total          = o que o cliente pagou  (== soma de sale_price dos itens, 100% medido)
  · platform_discount  = subsídio do TikTok, VOLTA para a loja
  · seller_discount    = desconto que a RHODE bancou — JÁ está fora do sub_total, não somar

Toda taxa (comissão, afiliada, GMV Max VL) incide sobre a receita de lista.
Contribuição por peça = receita_lista/peça × settlement − CPV.

⚠️ NUNCA aplique um "gross-up" médio (tipo 1,0774) em cima de sub_total. Aquele fator foi
calibrado sobre live_attr.gmv, que é OUTRA base. Em 10/09 o gross-up real foi 1,1931 —
o fator médio subestimou a receita em 10,7%.

Ver docs/DECISOES-E-PREMISSAS.md P21/P24 e a memória reference_cupom_tiktok_subsidia.
"""
from collections import defaultdict

__all__ = ["receita_itens", "receita_pedido", "gross_up_real", "contribuicao_peca"]


def receita_pedido(pag):
    """Receita de lista de UM pedido, a partir da linha de pedido_pagamento."""
    return (pag.get("sub_total") or 0.0) + (pag.get("platform_discount") or 0.0)


def receita_itens(itens, pagamentos, campo_valor="gmv", campo_pedido="order_id"):
    """
    Rateia o platform_discount do PEDIDO para os ITENS, proporcional ao valor pago.

    itens        : lista de dicts de pedidos_sku (precisa de order_id e gmv)
    pagamentos   : dict {order_id: linha de pedido_pagamento}  ou lista dessas linhas
    retorna      : dict {id(item): receita_de_lista_do_item}

    O rateio é proporcional porque platform_discount vem no nível do pedido e um pedido
    pode ter vários itens. Para pedido de 1 item o rateio é exato.
    """
    if isinstance(pagamentos, list):
        pagamentos = {p[campo_pedido]: p for p in pagamentos}
    pago_por_pedido = defaultdict(float)
    for it in itens:
        pago_por_pedido[it[campo_pedido]] += it.get(campo_valor) or 0.0
    out = {}
    for it in itens:
        o = it[campo_pedido]
        pago = it.get(campo_valor) or 0.0
        total = pago_por_pedido.get(o, 0.0)
        subs = (pagamentos.get(o, {}).get("platform_discount") or 0.0)
        out[id(it)] = pago + (subs * (pago / total) if total else 0.0)
    return out


def gross_up_real(itens, pagamentos, campo_valor="gmv", campo_pedido="order_id"):
    """Fator medido receita_lista ÷ pago no conjunto. Use para AUDITAR, nunca para estimar."""
    rev = receita_itens(itens, pagamentos, campo_valor, campo_pedido)
    pago = sum(it.get(campo_valor) or 0.0 for it in itens)
    return (sum(rev.values()) / pago) if pago else 0.0


def contribuicao_peca(receita_lista_peca, settlement, cpv):
    """Contribuição unitária. receita_lista_peca já deve vir da receita de LISTA."""
    return receita_lista_peca * settlement - cpv


if __name__ == "__main__":  # canário: roda contra o dia real e falha se a identidade quebrar
    import os, json, urllib.request
    from dotenv import load_dotenv
    B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(B, ".env"))
    SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
    H = {"apikey": SK, "Authorization": "Bearer " + SK}

    def qall(p, o="id"):
        out = []; off = 0
        while True:
            r = json.load(urllib.request.urlopen(urllib.request.Request(
                f"{SB}/rest/v1/{p}{'&' if '?' in p else '?'}order={o}&limit=1000&offset={off}",
                headers=H), timeout=90)); out += r
            if len(r) < 1000: break
            off += 1000
        return out

    DIA = os.environ.get("CANARIO_DIA", "2026-09-10")
    sk = qall(f"pedidos_sku?select=order_id,qty,gmv&data=eq.{DIA}")
    pp = qall(f"pedido_pagamento?select=order_id,sub_total,platform_discount&data=eq.{DIA}", "order_id")
    pag = {p["order_id"]: p for p in pp}
    por_pedido = defaultdict(float)
    for it in sk: por_pedido[it["order_id"]] += it["gmv"] or 0.0
    n = ok = 0
    for o, p in pag.items():
        if o not in por_pedido: continue
        n += 1
        if abs(por_pedido[o] - (p.get("sub_total") or 0)) < 0.02: ok += 1
    assert n, f"sem pedidos em {DIA}"
    pct = ok / n * 100
    gu = gross_up_real(sk, pag)
    print(f"CANÁRIO {DIA}: Σsale_price == sub_total em {ok}/{n} ({pct:.1f}%) · gross-up real {gu:.4f}")
    assert pct >= 99.0, f"IDENTIDADE QUEBROU: só {pct:.1f}% — pedidos_sku.gmv deixou de ser sub_total"
    assert gu > 1.0, "gross-up <= 1: platform_discount sumiu da fonte"
    print("✓ base de receita íntegra")
