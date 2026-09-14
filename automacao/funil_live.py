#!/usr/bin/env python3
"""
Rhode — FUNIL DE LIVE pela API. Use isto; não declare mais "não existe".

DESCOBERTO EM 14/09/2026 (e isto corrige relatórios anteriores): o endpoint
/analytics/202509/shop_lives/performance devolve, além de sales_performance, um bloco
`interaction_performance` com o funil INTEIRO da sala. Testado em 39/39 lives próprias
entre 25/08 e 14/09 — presente em 100%.

    views · viewers · avg_viewing_duration (s) · click_through_rate
    product_impressions · product_clicks · comments · likes · shares · new_followers
    + sales_performance.click_to_order_rate  (CTOR)

Isso estava sendo ignorado: coletar_lives_attr_api.py gravava views=0/impressions=0 e os
relatórios diziam que retenção, CTR, CTOR e pico de audiência "não existem na API" ou
"morreram". Eram apenas não-coletados.

live_attr só tem colunas para views e impressions, então o resto é buscado na hora — sem
DDL, e com o bônus de vir sempre fresco.
"""
import os, sys, json
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BRT = timezone(timedelta(hours=-3))
_CACHE = {}


def _num(v):
    if v is None: return None
    s = str(v).replace("%", "").replace(",", "").strip()
    try: return float(s)
    except Exception: return None


def funil_por_sala(dia, dias_janela=2):
    """{room_id: {...funil...}} para as salas próprias da janela. Cacheado por janela."""
    ini = (datetime.strptime(dia, "%Y-%m-%d") - timedelta(days=dias_janela)).strftime("%Y-%m-%d")
    fim = (datetime.strptime(dia, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    ck = (ini, fim)
    if ck in _CACHE: return _CACHE[ck]
    try:
        from coletar_dados import chamar
        own = (os.environ.get("RHODE_LIVE_USERNAME") or "rhodejeans").lower()
        out = {}
        # ⚠️ (14/09/2026) a janela tem 1.900+ sessões da loja inteira (afiliadas incluídas) e vem por GMV
        # DESC: sem repassar o page_token, o laço relia a página 1 e live própria de GMV baixo ficava SEM
        # funil (as duas de 14/09). Paginar até acabar o token.
        tok = None
        for _ in range(60):
            params = {"start_date_ge": ini, "end_date_lt": fim, "granularity": "ALL",
                      "page_size": 100, "sort_field": "gmv", "sort_order": "DESC"}
            if tok: params["page_token"] = tok
            r = chamar("GET", "/analytics/202509/shop_lives/performance", params=params)
            if r.get("code") != 0: break
            d = r.get("data") or {}
            for x in d.get("live_stream_sessions") or []:
                if (x.get("username") or "").lower() != own: continue
                ip = x.get("interaction_performance") or {}
                sp = x.get("sales_performance") or {}
                if not ip and not sp: continue
                out[str(x.get("id"))] = dict(
                    views=_num(ip.get("views")), viewers=_num(ip.get("viewers")),
                    retencao_s=_num(ip.get("avg_viewing_duration")),
                    ctr=_num(ip.get("click_through_rate")),
                    ctor=_num(sp.get("click_to_order_rate")),
                    prod_impressoes=_num(ip.get("product_impressions")),
                    prod_cliques=_num(ip.get("product_clicks")),
                    comentarios=_num(ip.get("comments")), curtidas=_num(ip.get("likes")),
                    compart=_num(ip.get("shares")), novos_seguidores=_num(ip.get("new_followers")),
                    produtos_vendidos=_num(sp.get("different_products_sold")),
                    produtos_no_palco=_num(sp.get("products_added")))
            tok = d.get("next_page_token")
            if not tok or not (d.get("live_stream_sessions") or []): break
        _CACHE[ck] = out
        return out
    except Exception as e:
        print(f"  ⚠ funil de live indisponível: {str(e)[:130]}")
        _CACHE[ck] = {}
        return {}


def funil_de(room_id, dia):
    return funil_por_sala(dia).get(str(room_id))


if __name__ == "__main__":
    dia = sys.argv[1] if len(sys.argv) > 1 else datetime.now(BRT).strftime("%Y-%m-%d")
    f = funil_por_sala(dia, dias_janela=4)
    print(f"{len(f)} sala(s) com funil na janela até {dia}")
    for rid, v in list(f.items())[:5]:
        print(f"  {rid}: views {v['views']} · viewers {v['viewers']} · ret {v['retencao_s']}s "
              f"· CTR {v['ctr']}% · CTOR {v['ctor']}%")
