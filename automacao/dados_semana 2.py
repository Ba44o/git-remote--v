#!/usr/bin/env python3
"""
Rhode — camada de dados do RELATÓRIO SEMANAL HEAD (TikTok Shop, semana seg–dom).

Roda toda terça 08:00 BRT sobre a semana anterior — o dia em que o fim de semana amadurece
(funil D-2, não pagos ~48h, statement_tx coletado na segunda). Ver CLAUDE.md.

DEFINIÇÕES (fixas — o relatório cita):
  · Receita de LISTA = sub_total + platform_discount (lib/receita.py). Cupom da plataforma é
    subsídio do TikTok e volta para a loja.
  · Taxa por CANAL = settlement ÷ revenue CALIBRADA em pedidos já liquidados e sem devolução,
    criados entre 55 e 25 dias antes do fim da semana. Não é 0,7084 fixo: medido em 14/09 os
    canais vão de 0,65 (vídeo afiliada) a 0,76 (loja própria).
  · Contribuição = lista × taxa_do_canal − CPV. Antes de imposto, devolução e mídia.
  · Mídia de CAIXA = só GMV Max Tradicional (net_cost>0). A VL é cobrada dentro da taxa e já
    está no settlement — subtraí-la de novo dupla-conta (VL = 7,8% do custo em 31/08–13/09).
  · Canal por pedido: afiliada pelo content_type de extrato_pedidos (LIVE → live_afiliada;
    VIDEO/LINKSHARE/SHOP → video_afiliada); sem afiliada e dentro da janela de live própria →
    live_propria; o resto → loja_propria (card, busca, vídeo da loja).
  · Imposto: 6,4% sobre a receita de lista (Lucro Presumido). Estrutura: R$ 70.000/mês.
"""
import os, sys, json, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date

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

CPV = 45.40
IMPOSTO = 0.064
ESTRUTURA_MES = 70000.0
HORA_APRESENTADORA = 50.0
TAXA_FALLBACK = 0.7084
HERO = ("REF516", "REF525", "REF527")
CANAIS = ("live_propria", "loja_propria", "live_afiliada", "video_afiliada")
ROTULO = {"live_propria": "Live própria", "loja_propria": "Loja própria (card/busca/vídeo loja)",
          "live_afiliada": "Live de afiliada", "video_afiliada": "Vídeo de afiliada"}
# custo líquido de uma peça devolvida, medido ago/26 (reference_regua_midia_contribuicao)
CUSTO_DEVOLUCAO = {"afiliada": 6.90, "vendedor": 3.12}


def qall(p, o="id"):
    out = []; off = 0
    while True:
        for t in range(3):                       # 504 do Supabase em paginação longa: retry
            try:
                r = json.load(urllib.request.urlopen(urllib.request.Request(
                    f"{SB}/rest/v1/{p}{'&' if '?' in p else '?'}order={o}&limit=1000&offset={off}",
                    headers=H), timeout=120)); break
            except Exception:
                if t == 2: raise
        out += r
        if len(r) < 1000: break
        off += 1000
    return out


def ymd(d): return d.strftime("%Y-%m-%d")


def semana_de(ref=None):
    """Semana seg–dom ANTERIOR à data de referência (a que o relatório de terça fecha)."""
    ref = ref or datetime.now(BRT).date()
    seg_atual = ref - timedelta(days=ref.weekday())
    seg = seg_atual - timedelta(days=7)
    return seg, seg + timedelta(days=6)


def semana_id(seg):
    y, w, _ = seg.isocalendar()
    return f"{y}-W{w:02d}"


# ───────── calibração da taxa por canal ─────────
def calibrar_taxas(dom):
    ini = dom - timedelta(days=55); fim = dom - timedelta(days=25)
    st = qall(f"statement_tx?select=order_id,revenue,settlement,customer_refund,order_create_time"
              f"&data=gte.{ymd(ini)}&data=lte.{ymd(dom)}")
    por = defaultdict(lambda: [0.0, 0.0, 0.0, None])
    for x in st:
        z = por[x["order_id"]]
        z[0] += x.get("revenue") or 0; z[1] += x.get("settlement") or 0
        z[2] += abs(x.get("customer_refund") or 0)
        if x.get("order_create_time") and not z[3]: z[3] = x["order_create_time"]
    ex = {e["order_id"]: e["content_type"] for e in
          qall(f"extrato_pedidos?select=order_id,content_type&data=gte.{ymd(ini - timedelta(days=3))}&data=lte.{ymd(fim + timedelta(days=3))}")}
    salas = janelas_live(ini - timedelta(days=1), fim + timedelta(days=1))
    agg = defaultdict(lambda: [0, 0.0, 0.0])
    for oid, (rev, sett, refd, oct_) in por.items():
        try: t = datetime.fromtimestamp(int(oct_), BRT)
        except Exception: continue
        if not (ini <= t.date() <= fim) or rev <= 0 or sett <= 0 or refd > 0: continue
        a = agg[classificar(oid, t, ex, salas)]; a[0] += 1; a[1] += rev; a[2] += sett
    tot_r = sum(a[1] for a in agg.values()); tot_s = sum(a[2] for a in agg.values())
    blended = (tot_s / tot_r) if tot_r else TAXA_FALLBACK
    taxas, base = {}, {}
    for c in CANAIS:
        n, r, s_ = agg.get(c, [0, 0, 0])
        ok = n >= 150 and r > 0
        taxas[c] = (s_ / r) if ok else blended
        base[c] = dict(pedidos=n, fonte="calibrada" if ok else "blended (amostra < 150)")
    return dict(taxas=taxas, base=base, blended=blended, janela=(ymd(ini), ymd(fim)),
                pedidos=sum(a[0] for a in agg.values()))


def live_attr_semana(seg, dom):
    """Horas no ar e peças atribuídas pela API às salas próprias — barato, vale para toda
    semana da tendência (o reprocessamento completo via montar() fica só para as 2 últimas)."""
    horas = 0.0; itens = 0; gmv = 0.0; n = 0
    for s in qall(f"live_attr?select=inicio,fim,itens,gmv&data=gte.{ymd(seg)}&data=lte.{ymd(dom)}"):
        if not s["fim"]: continue
        i = datetime.fromisoformat(s["inicio"]); f = datetime.fromisoformat(s["fim"])
        dur = (f - i).total_seconds() / 3600
        if dur < 0.25: continue
        horas += dur; itens += s["itens"] or 0; gmv += s["gmv"] or 0; n += 1
    return dict(n=n, horas=horas, itens=itens, gmv=gmv)


def janelas_live(ini, fim):
    out = []
    for s in qall(f"live_attr?select=room_id,inicio,fim&data=gte.{ymd(ini)}&data=lte.{ymd(fim)}"):
        if s["fim"]:
            i = datetime.fromisoformat(s["inicio"]); f = datetime.fromisoformat(s["fim"])
            if f > i: out.append((i, f))
    return out


def classificar(oid, t, ex, salas):
    ct = ex.get(oid)
    if ct == "LIVE": return "live_afiliada"
    if ct in ("VIDEO", "LINKSHARE", "SHOP"): return "video_afiliada"
    if t and any(i <= t <= f for i, f in salas): return "live_propria"
    return "loja_propria"


# ───────── semana por canal ─────────
def por_canal(seg, dom, taxas):
    # Janela pela HORA REAL do pedido em BRT, não pelo campo `data` — a fronteira da semana
    # (dom→seg) tem que cair na meia-noite de Brasília. Busca-se 1 dia a mais de cada lado.
    bruto = qall(f"pedidos_sku?select=order_id,seller_sku,sku,qty,gmv,status,order_time"
                 f"&data=gte.{ymd(seg - timedelta(days=1))}&data=lte.{ymd(dom + timedelta(days=1))}")
    sk = [r for r in bruto if r.get("order_time")
          and seg <= datetime.fromtimestamp(int(r["order_time"]), BRT).date() <= dom]
    pag = {p["order_id"]: p for p in
           qall(f"pedido_pagamento?select=order_id,sub_total,platform_discount"
                f"&data=gte.{ymd(seg - timedelta(days=1))}&data=lte.{ymd(dom + timedelta(days=1))}", "order_id")}
    rev = receita_itens(sk, pag) if sk else {}
    ex = {e["order_id"]: e["content_type"] for e in
          qall(f"extrato_pedidos?select=order_id,content_type&data=gte.{ymd(seg - timedelta(days=1))}&data=lte.{ymd(dom + timedelta(days=1))}")}
    salas = janelas_live(seg - timedelta(days=1), dom + timedelta(days=1))
    c = {k: dict(pedidos=set(), pecas=0, pago=0.0, lista=0.0, contrib=0.0) for k in CANAIS}
    status = defaultdict(int); hero_q = 0; hero_l = 0.0
    for r in sk:
        status[r["status"]] += r["qty"] or 0
        if r["status"] in ("CANCELLED", "UNPAID") or not r["qty"]: continue
        t = datetime.fromtimestamp(int(r["order_time"]), BRT)
        k = classificar(r["order_id"], t, ex, salas); z = c[k]
        lst = rev[id(r)]
        z["pedidos"].add(r["order_id"]); z["pecas"] += r["qty"]; z["pago"] += r["gmv"] or 0
        z["lista"] += lst; z["contrib"] += lst * taxas[k] - CPV * r["qty"]
        if str(r.get("seller_sku") or r.get("sku") or "")[:6] in HERO:
            hero_q += r["qty"]; hero_l += lst
    for z in c.values(): z["pedidos"] = len(z["pedidos"])
    tot_q = sum(status.values())
    nao = status.get("UNPAID", 0) + status.get("CANCELLED", 0)
    return dict(canais=c, status=dict(status), nao_pagos_pct=(nao / tot_q) if tot_q else 0,
                pago=sum(z["pago"] for z in c.values()),
                nao_pagos=nao, hero_preco=(hero_l / hero_q) if hero_q else None, hero_pecas=hero_q)


# ───────── mídia da semana ─────────
def midia(seg, dom):
    ac = qall(f"ads_campanha?select=data,campanha,modelo,cost,net_cost,receita,pedidos&data=gte.{ymd(seg)}&data=lte.{ymd(dom)}")
    camp = defaultdict(lambda: dict(custo=0.0, receita=0.0, pedidos=0, trad=0.0, vl=0.0, dias=set()))
    for x in ac:
        z = camp[x["campanha"] or "?"]; cst = x["cost"] or 0
        z["custo"] += cst; z["receita"] += x["receita"] or 0; z["pedidos"] += x["pedidos"] or 0
        if (x["net_cost"] or 0) > 0: z["trad"] += cst
        elif cst > 0: z["vl"] += cst
        if cst > 0: z["dias"].add(x["data"])
    for z in camp.values(): z["dias"] = len(z["dias"])
    eh_live = lambda n: "LIVE" in n.upper()
    return dict(
        campanhas=dict(camp),
        caixa_live=sum(z["trad"] for n, z in camp.items() if eh_live(n)),
        caixa_produto=sum(z["trad"] for n, z in camp.items() if not eh_live(n)),
        vl_total=sum(z["vl"] for z in camp.values()),
        custo_total=sum(z["custo"] for z in camp.values()),
        receita_atrib=sum(z["receita"] for z in camp.values()))


# ───────── lives próprias (reusa o gerador do relatório de live) ─────────
def lives(seg, dom):
    from automacao.gerar_relatorio_live import montar
    salas = qall(f"live_attr?select=room_id,titulo,inicio,fim&data=gte.{ymd(seg)}&data=lte.{ymd(dom)}")
    out = []
    for s in salas:
        if not s["fim"]: continue
        i = datetime.fromisoformat(s["inicio"]); f = datetime.fromisoformat(s["fim"])
        if f <= i or (f - i).total_seconds() < 900: continue      # < 15 min = reinício técnico
        try:
            D = montar(s["room_id"])
        except SystemExit:
            continue
        except Exception as e:
            print(f"  ⚠ live {s['room_id']} não processada: {str(e)[:90]}"); continue
        F = D.get("FUN") or {}
        pagas = sum(D["LIVE"][h][3] for h in D["horas"])
        out.append(dict(room=str(s["room_id"]), inicio=D["ini"], titulo=(s["titulo"] or "").strip(),
                        dur=D["dur"], res=D["RES"], contrib=D["CONTRIB"], ads=D["ADS"], pecas=D["QTY"],
                        estouro=(D["pico"]["exc"] if D["pico"] else 0.0),
                        estouro_testavel=D.get("pico_testavel", True),
                        corte_testavel=D["dur"] >= 1.0,     # detector de corte precisa de ≥4 faixas de 15 min
                        estouro_h=(D["pico"]["h"] if D["pico"] else None),
                        corte=(D["corte"]["custo"] if D["corte"] else 0.0),
                        corte_h=(D["corte"]["quando"].strftime("%H:%M") if D["corte"] else None),
                        views=F.get("views"), views_pagas=pagas, retencao=F.get("retencao_s"),
                        ctr=F.get("ctr"), ctor=F.get("ctor")))
    return sorted(out, key=lambda x: x["inicio"])


# ───────── superfícies da API (LIVE / VÍDEO / CARD) ─────────
def superficies(seg, dom):
    try:
        from coletar_dados import chamar
        r = chamar("GET", "/analytics/202405/shop/performance",
                   params={"start_date_ge": ymd(seg), "end_date_lt": ymd(dom + timedelta(days=1)),
                           "granularity": "ALL"})
        iv = ((r.get("data") or {}).get("performance") or {}).get("intervals") or []
        if r.get("code") != 0 or not iv: return None
        iv = iv[0]
        n = lambda v: float(str((v.get("amount") if isinstance(v, dict) else v) or 0).replace(",", ""))
        gmv = {b["type"]: n(b) for b in iv.get("gmv_breakdowns") or []}
        imp = {b["type"]: n(b) for b in iv.get("product_impression_breakdowns") or []}
        pv = {b["type"]: n(b) for b in iv.get("product_page_view_breakdowns") or []}
        if not any(gmv.values()): return None
        return dict(gmv=gmv, impressoes=imp, page_views=pv, gmv_total=n(iv.get("gmv")),
                    pedidos=n(iv.get("orders")), pecas=n(iv.get("units_sold")),
                    page_views_total=n(iv.get("product_page_views")))
    except Exception as e:
        print(f"  ⚠ superfícies indisponíveis: {str(e)[:100]}"); return None


# ───────── devoluções ─────────
def devolucoes(seg, dom):
    dv = qall(f"devolucoes?select=order_id,refund_item,return_reason,seller_sku&data=gte.{ymd(seg)}&data=lte.{ymd(dom)}")
    if not dv: return dict(n=0, reembolso=0.0, custo_liquido=0.0, motivos=[])
    afil = {e["order_id"] for e in
            qall(f"extrato_pedidos?select=order_id&data=gte.{ymd(seg - timedelta(days=45))}&data=lte.{ymd(dom)}")}
    mot = defaultdict(int); custo = 0.0
    for d in dv:
        if (d.get("return_reason") or "").startswith("system_refund_sample"): continue   # amostra, não devolução
        mot[d.get("return_reason") or "(sem motivo)"] += 1
        custo += CUSTO_DEVOLUCAO["afiliada" if d["order_id"] in afil else "vendedor"]
    return dict(n=sum(mot.values()), reembolso=sum(d.get("refund_item") or 0 for d in dv),
                custo_liquido=custo, motivos=sorted(mot.items(), key=lambda x: -x[1]))


# ───────── saúde do dado ─────────
def saude(dom):
    fontes = [("pedidos_sku", "data", 1), ("extrato_pedidos", "data", 2), ("live_attr", "data", 2),
              ("ads_campanha", "data", 2), ("devolucoes", "data", 2), ("affiliate_perf", "data", 2),
              ("performance_diario", "data", 4), ("statement_tx", "data", 10)]
    out = []
    # referência nunca no futuro: num período parcial (check de sexta) o "dom" pode ainda não
    # ter chegado, e medir atraso contra ele inventa alarme de fonte atrasada.
    ref = min(dom, datetime.now(BRT).date())
    for t, col, tol in fontes:
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(
                f"{SB}/rest/v1/{t}?select={col}&order={col}.desc&limit=1", headers=H), timeout=60))
            ult = datetime.strptime(r[0][col][:10], "%Y-%m-%d").date() if r else None
        except Exception:
            ult = None
        lag = (ref - ult).days if ult else None
        out.append(dict(fonte=t, ultimo=ult, lag=lag, tolerancia=tol,
                        ok=(lag is not None and lag <= tol)))
    return out


# ───────── montagem ─────────
def montar_semana(seg=None, com_lives=True, semanas_tendencia=4):
    if seg is None: seg, dom = semana_de()
    else: dom = seg + timedelta(days=6)
    print(f"  · calibrando taxas por canal…")
    cal = calibrar_taxas(dom)
    semanas = []
    for k in range(semanas_tendencia):
        s = seg - timedelta(days=7 * k); d = s + timedelta(days=6)
        print(f"  · canais {ymd(s)} → {ymd(d)}")
        semanas.append(dict(seg=s, dom=d, id=semana_id(s), canal=por_canal(s, d, cal["taxas"]),
                            midia=midia(s, d), live_api=live_attr_semana(s, d),
                            devolucoes=devolucoes(s, d)))
    W = semanas[0]; A = semanas[1] if len(semanas) > 1 else None
    if com_lives:
        print("  · reprocessando lives da semana e da anterior (≈12s por sala)…")
        W["lives"] = lives(seg, dom)
        if A: A["lives"] = lives(A["seg"], A["dom"])
    W["superficies"] = superficies(seg, dom)
    if A: A["superficies"] = superficies(A["seg"], A["dom"])
    for S in semanas:
        cn = S["canal"]["canais"]
        S["lista"] = sum(z["lista"] for z in cn.values())
        S["pecas"] = sum(z["pecas"] for z in cn.values())
        S["pedidos"] = sum(z["pedidos"] for z in cn.values())
        S["contrib"] = sum(z["contrib"] for z in cn.values())
        S["imposto"] = S["lista"] * IMPOSTO
        S["pago"] = S["canal"]["pago"]
        # mesma régua em TODAS as semanas — senão a tendência compara conta diferente
        S["apresentadora"] = S["live_api"]["horas"] * HORA_APRESENTADORA
        dev = S["devolucoes"]["custo_liquido"]
        S["resultado_operacional"] = (S["contrib"] - S["imposto"] - dev
                                      - S["midia"]["caixa_live"] - S["midia"]["caixa_produto"]
                                      - (S["apresentadora"] or 0))
    est_sem = ESTRUTURA_MES * 7 / 30.4375
    W["estrutura_semana"] = est_sem
    W["resultado_final"] = W["resultado_operacional"] - est_sem
    return dict(seg=seg, dom=dom, id=semana_id(seg), calibracao=cal, semanas=semanas,
                saude=saude(dom), gerado_em=datetime.now(BRT))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seg", help="segunda-feira da semana (AAAA-MM-DD)")
    ap.add_argument("--sem-lives", action="store_true")
    a = ap.parse_args()
    seg = datetime.strptime(a.seg, "%Y-%m-%d").date() if a.seg else None
    R = montar_semana(seg, com_lives=not a.sem_lives)
    W = R["semanas"][0]
    print(f"\n═══ {R['id']} · {ymd(R['seg'])} → {ymd(R['dom'])} ═══")
    print(f"  taxas calibradas ({R['calibracao']['janela'][0]}→{R['calibracao']['janela'][1]}, "
          f"{R['calibracao']['pedidos']} pedidos): " +
          " · ".join(f"{k} {v:.4f}" for k, v in R["calibracao"]["taxas"].items()))
    print(f"  receita lista R$ {W['lista']:,.2f} · {W['pecas']} peças · contrib R$ {W['contrib']:,.2f}")
    print(f"  imposto R$ {W['imposto']:,.2f} · mídia caixa live R$ {W['midia']['caixa_live']:,.2f} "
          f"· produto R$ {W['midia']['caixa_produto']:,.2f} · VL (na taxa) R$ {W['midia']['vl_total']:,.2f}")
    if W.get("devolucoes"): print(f"  devoluções {W['devolucoes']['n']} · custo líq. R$ {W['devolucoes']['custo_liquido']:,.2f}")
    if W.get("apresentadora") is not None: print(f"  apresentadora R$ {W['apresentadora']:,.2f}")
    print(f"  RESULTADO OPERACIONAL R$ {W['resultado_operacional']:,.2f} · estrutura R$ {W['estrutura_semana']:,.2f}"
          f" · RESULTADO FINAL R$ {W['resultado_final']:,.2f}")
    print("\n  por canal:")
    for k in CANAIS:
        z = W["canal"]["canais"][k]
        if z["pecas"]:
            print(f"   {k:15} {z['pecas']:5} pçs · lista R$ {z['lista']:10,.2f} · contrib R$ {z['contrib']:9,.2f} "
                  f"({z['contrib']/z['pecas']:6.2f}/pç)")
    print("\n  tendência (resultado operacional):",
          " · ".join(f"{S['id']} R$ {S['resultado_operacional']:,.0f}" for S in R["semanas"]))
    if W.get("lives") is not None:
        print(f"\n  lives: {len(W['lives'])} · estouros {sum(1 for l in W['lives'] if l['estouro'])} "
              f"(R$ {sum(l['estouro'] for l in W['lives']):,.2f}) · cortes de promo {sum(1 for l in W['lives'] if l['corte'])}")
    print("\n  saúde:", " · ".join(f"{s['fonte']} {'✓' if s['ok'] else '✗'}({s['lag']}d)" for s in R["saude"]))
    import pickle
    pickle.dump(R, open("/tmp/semana_head.pkl", "wb"))
    print("\n  (dump em /tmp/semana_head.pkl)")
