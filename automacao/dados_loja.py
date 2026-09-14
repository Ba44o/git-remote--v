#!/usr/bin/env python3
"""
Rhode — camada de dados do Relatório Diário da Loja.

Junta, para UM dia, tudo que existe de verdade sobre a operação inteira (não só live).
Cada métrica carrega de onde veio e qual o viés — quem consome NUNCA deve inventar o que
não está aqui. Métrica ausente vem como None e o relatório escreve "sem dado".

Régua: receita de LISTA (sub_total + platform_discount) via lib/receita.py.
Ver docs/DECISOES-E-PREMISSAS.md P21/P24 — errar essa base já inverteu veredito 3×.
"""
import os, sys, json, urllib.request, urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from dotenv import load_dotenv; load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass
from lib.receita import receita_itens

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SK, "Authorization": "Bearer " + SK}
BRT = timezone(timedelta(hours=-3))
SR = 0.7084; CPV = 45.40
PAGO_OK = lambda s: s not in ("CANCELLED", "UNPAID")


def qall(p, o="id"):
    out = []; off = 0
    while True:
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{SB}/rest/v1/{p}{'&' if '?' in p else '?'}order={o}&limit=1000&offset={off}",
            headers=H), timeout=90)); out += r
        if len(r) < 1000: break
        off += 1000
    return out


# ───────── 1. receita ─────────
def receita_do_dia(dia):
    sk = qall(f"pedidos_sku?select=order_id,seller_sku,sku,produto,qty,gmv,status,order_time&data=eq.{dia}")
    if not sk:
        return None
    pag = {p["order_id"]: p for p in qall(f"pedido_pagamento?select=*&data=eq.{dia}", "order_id")}
    rev = receita_itens(sk, pag)
    ok = [r for r in sk if PAGO_OK(r["status"])]
    qty = sum(r["qty"] or 0 for r in ok)
    pago = sum(r["gmv"] or 0 for r in ok)
    lista = sum(rev[id(r)] for r in ok)
    ped = len({r["order_id"] for r in ok})
    contrib = sum((rev[id(r)] / r["qty"] * SR - CPV) * r["qty"] for r in ok if r["qty"])
    st = defaultdict(lambda: [0, 0.0])
    for r in sk:
        st[r["status"]][0] += r["qty"] or 0; st[r["status"]][1] += r["gmv"] or 0
    nao_virou = sum(v[0] for k, v in st.items() if k in ("UNPAID", "CANCELLED"))
    tot_q = sum(v[0] for v in st.values())
    return dict(pecas=qty, pago=pago, lista=lista, pedidos=ped, contrib=contrib,
                aov_lista=lista / ped if ped else 0, aov_pago=pago / ped if ped else 0,
                preco_medio=lista / qty if qty else 0,
                contrib_peca=contrib / qty if qty else 0,
                gross_up=lista / pago if pago else 0,
                status=dict(st), nao_virou=nao_virou,
                nao_virou_pct=nao_virou / tot_q if tot_q else 0, itens=sk, rev=rev)


# ───────── 2. live ─────────
def live_do_dia(dia):
    salas = qall(f"live_attr?select=room_id,titulo,inicio,fim,gmv,itens,customers,views&data=eq.{dia}")
    tot = sum(s["gmv"] or 0 for s in salas)
    horas = 0.0
    for s in salas:
        if s["fim"]:
            i = datetime.fromisoformat(s["inicio"]); f = datetime.fromisoformat(s["fim"])
            if f > i: horas += (f - i).total_seconds() / 3600
    return dict(n=len(salas), gmv=tot, itens=sum(s["itens"] or 0 for s in salas),
                horas=horas, salas=salas)


# ───────── 3. mídia ─────────
def midia_do_dia(dia):
    ac = qall(f"ads_campanha?select=campanha,modelo,cost,net_cost,receita,pedidos&data=eq.{dia}")
    if not ac:
        return None
    def bl(rs):
        c = sum(x["cost"] or 0 for x in rs); r = sum(x["receita"] or 0 for x in rs)
        p = sum(x["pedidos"] or 0 for x in rs)
        return dict(custo=c, receita=r, pedidos=p, roas=r / c if c else 0, cpa=c / p if p else 0)
    live = [x for x in ac if "LIVE" in (x["campanha"] or "").upper()]
    prod = [x for x in ac if "LIVE" not in (x["campanha"] or "").upper()]
    # ⚠️ VL (net_cost=0) cobra DENTRO do fee — não é caixa de mídia. Ver memória
    # reference_gmvmax_vl_dentro_do_fee. Somar VL com Tradicional conta duas vezes.
    trad = [x for x in ac if (x["net_cost"] or 0) > 0]
    vl = [x for x in ac if (x["net_cost"] or 0) == 0 and (x["cost"] or 0) > 0]
    return dict(total=bl(ac), live=bl(live), produto=bl(prod),
                tradicional=bl(trad), vendas_liquidas=bl(vl),
                campanhas=sorted(ac, key=lambda x: -(x["cost"] or 0)))


# ───────── 4. creators e vídeos ─────────
def creators_do_dia(dia):
    af = qall(f"affiliate_perf?select=creator,data,content_type,gmv,comissao,pedidos,itens&data=eq.{dia}")
    if not af: return None
    # 🐞 deduplicar por creator: handles duplicados já inflaram R$504k
    # (memória project_bug_affiliate_perf_handles)
    porc = defaultdict(lambda: [0.0, 0.0, 0, 0])
    portipo = defaultdict(lambda: [0.0, 0])
    for a in af:
        z = porc[(a["creator"] or "").lower().lstrip("@")]
        z[0] += a["gmv"] or 0; z[1] += a["comissao"] or 0
        z[2] += a["pedidos"] or 0; z[3] += a["itens"] or 0
        t = portipo[a["content_type"] or "?"]
        t[0] += a["gmv"] or 0; t[1] += a["pedidos"] or 0
    return dict(n_creators=len(porc), gmv=sum(z[0] for z in porc.values()),
                comissao=sum(z[1] for z in porc.values()),
                pedidos=sum(z[2] for z in porc.values()),
                por_creator=sorted(((k, v) for k, v in porc.items()), key=lambda x: -x[1][0]),
                por_tipo=dict(portipo))


def videos_do_dia(dia):
    try:
        vp = qall(f"video_perf?select=username,title,post_time,views,ctr,gmv,sku_orders&post_time=gte.{dia}T00:00:00&post_time=lt.{dia}T23:59:59", "id")
    except Exception:
        return None
    if not vp: return None
    return dict(n=len(vp), views=sum(v["views"] or 0 for v in vp),
                gmv=sum(v["gmv"] or 0 for v in vp),
                pedidos=sum(v["sku_orders"] or 0 for v in vp),
                criadores=len({(v["username"] or "").lower() for v in vp}))


# ───────── 5. devoluções ─────────
def devolucoes_do_dia(dia):
    try:
        dv = qall(f"devolucoes?select=return_reason,return_status,refund_item&data=eq.{dia}")
    except Exception:
        return None
    if not dv: return None
    mot = defaultdict(lambda: [0, 0.0])
    for d in dv:
        r = d.get("return_reason") or "(sem motivo)"
        mot[r][0] += 1; mot[r][1] += d.get("refund_item") or 0
    return dict(n=len(dv), valor=sum(d.get("refund_item") or 0 for d in dv),
                motivos=sorted(mot.items(), key=lambda x: -x[1][0]))


# ───────── 6. funil da loja (API, não armazenado) ─────────
def funil_loja(dia):
    """product_page_views / visitantes vêm da API e NÃO são gravados em lugar nenhum.
    ⚠️ VIÉS: é visualização de página de produto DENTRO do TikTok Shop, não sessão de
    loja própria. Não existe fonte de sessão de site neste projeto — conferido.
    A API consolida com ~2 dias de atraso e devolve ZEROS silenciosos para dia não
    consolidado (nunca omite) — por isso o teste de 'tudo zerado'."""
    try:
        sys.path.insert(0, ROOT)
        from coletar_dados import chamar
        fim = (datetime.strptime(dia, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        r = chamar("GET", "/analytics/202405/shop/performance",
                   params={"start_date_ge": dia, "end_date_lt": fim, "granularity": "1D"})
        if r.get("code") != 0: return None
        ivs = r.get("data", {}).get("performance", {}).get("intervals", [])
        if not ivs: return None
        iv = ivs[0]
        def g(k):
            v = iv.get(k)
            try: return float(str(v).replace(",", ""))
            except Exception: return None
        pv, vis, ped = g("product_page_views"), g("avg_product_page_visitors"), g("orders")
        if not any([pv, vis, ped]):
            return None                      # dia não consolidado = zeros silenciosos
        return dict(page_views=pv, visitantes=vis, pedidos_api=ped,
                    gmv_api=g("gmv"), aov_api=g("avg_order_value"),
                    conv_pv=(ped / pv) if (pv and ped) else None,
                    conv_visitante=(ped / vis) if (vis and ped) else None,
                    breakdowns=iv.get("gmv_breakdowns"))
    except Exception as e:
        print(f"  ⚠ funil da loja indisponível: {str(e)[:120]}")
        return None


# ───────── montagem ─────────
def montar(dia):
    ant = (datetime.strptime(dia, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    d = dict(dia=dia, anterior=ant,
             rec=receita_do_dia(dia), rec_ant=receita_do_dia(ant),
             live=live_do_dia(dia), live_ant=live_do_dia(ant),
             ads=midia_do_dia(dia), ads_ant=midia_do_dia(ant),
             creators=creators_do_dia(dia), videos=videos_do_dia(dia),
             dev=devolucoes_do_dia(dia), funil=funil_loja(dia))
    # O funil da loja consolida só em D-2. Num relatório de D-1 ele quase sempre vem
    # vazio — então buscamos o dia consolidado mais recente e ROTULAMOS como referência,
    # em vez de deixar a seção muda ou (pior) fingir que é do dia.
    d["funil_ref"] = None
    if not d["funil"]:
        for k in range(1, 5):
            alvo = (datetime.strptime(dia, "%Y-%m-%d") - timedelta(days=k)).strftime("%Y-%m-%d")
            f = funil_loja(alvo)
            if f:
                f["dia"] = alvo; f["defasagem_dias"] = k
                d["funil_ref"] = f
                break
    if not d["rec"]:
        raise SystemExit(f"sem pedidos em {dia} — nada a reportar")
    return d


if __name__ == "__main__":
    dia = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(BRT) - timedelta(days=1)).strftime("%Y-%m-%d")
    d = montar(dia)
    r = d["rec"]
    print(f"=== {dia} ===")
    print(f"  receita lista R$ {r['lista']:,.2f} · {r['pecas']} peças · {r['pedidos']} pedidos")
    print(f"  AOV lista R$ {r['aov_lista']:,.2f} · contrib R$ {r['contrib']:,.2f} ({r['contrib_peca']:,.2f}/pç)")
    print(f"  não virou receita: {r['nao_virou']} pçs ({r['nao_virou_pct']*100:.1f}%)")
    print(f"  live: {d['live']['n']} sala(s) · GMV R$ {d['live']['gmv']:,.2f}")
    print(f"  ads: {'R$ %.2f' % d['ads']['total']['custo'] if d['ads'] else 'sem dado'}")
    print(f"  creators: {d['creators']['n_creators'] if d['creators'] else 'sem dado'}")
    print(f"  funil: {d['funil']['page_views'] if d['funil'] else 'sem dado'} page views")
