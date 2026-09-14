#!/usr/bin/env python3
"""
Rhode — MEDIDORES do registro de recomendações (Relatório Semanal Head).

Cada recomendação em recomendacoes.json aponta para um medidor. Toda semana o relatório
mede o sinal SOZINHO — a recomendação não fica só apontada, que era a falha de 10–14/09
(o teto de gasto por hora foi recomendado em todo relatório de live e ninguém acompanhou).

O status do JSON é do DONO (aberta/feita/descartada/contrariada). O medidor não muda o
status: ele mostra o SINAL, e o relatório aponta quando sinal e status discordam.
"""
import os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = os.path.join(ROOT, "automacao", "recomendacoes.json")


def carregar():
    with open(ARQ, encoding="utf-8") as f:
        return json.load(f)


def _contrib_pc_liquida(S, canal=None, imposto=0.064):
    """contribuição por peça depois de imposto — o teto que um CPA de caixa pode atingir."""
    cn = S["canal"]["canais"]
    zs = [cn[canal]] if canal else list(cn.values())
    pecas = sum(z["pecas"] for z in zs); contrib = sum(z["contrib"] for z in zs)
    lista = sum(z["lista"] for z in zs)
    return ((contrib - lista * imposto) / pecas) if pecas else None


def _camp(S, nome):
    return (S.get("midia") or {}).get("campanhas", {}).get(nome)


def medir(R):
    led = carregar()
    W = R["semanas"][0]; A = R["semanas"][1] if len(R["semanas"]) > 1 else None
    out = []
    for rec in led["recomendacoes"]:
        m = rec["medidor"]; d = dict(rec)
        d.update(sinal="sem dado", semana=None, anterior=None, em_jogo=0.0, discorda=False)

        if m == "estouros_live" and W.get("lives") is not None:
            if not W["lives"]:
                # zero estouro sem live nenhuma NÃO é evidência de que o teto funciona
                d["semana"] = "nenhuma live própria no período"
                d["sinal"] = "sem evidência — não houve live para medir"
                out.append(d); continue
            w_n = sum(1 for l in W["lives"] if l["estouro"]); w_r = sum(l["estouro"] for l in W["lives"])
            mens = sum(1 for l in W["lives"] if l.get("estouro_testavel", True))
            a_n = sum(1 for l in A.get("lives", []) if l["estouro"]) if A else None
            a_r = sum(l["estouro"] for l in A.get("lives", [])) if A else None
            d["semana"] = f"{w_n} de {len(W['lives'])} lives · R$ {w_r:,.2f} de excesso"
            d["anterior"] = f"{a_n} lives · R$ {a_r:,.2f}" if A and A.get("lives") is not None else None
            d["em_jogo"] = w_r
            if w_n > 0 and a_r is not None and w_r < a_r * 0.7: d["sinal"] = "⚠️ melhorou, mas ainda estoura"
            elif w_n > 0: d["sinal"] = "❌ segue estourando"
            elif mens >= 3: d["sinal"] = f"✅ nenhum estouro em {mens} lives mensuráveis — o teto parece funcionar"
            else: d["sinal"] = f"evidência insuficiente — só {mens} live(s) onde dava para medir estouro"
            d["discorda"] = (rec["status"] == "feita" and w_n > 0)

        elif m == "campanha_live_0909":
            if sum(z["custo"] for z in (W.get("midia") or {}).get("campanhas", {}).values()) == 0:
                # sem nenhum gasto registrado, "campanha sem gasto" pode ser só coleta atrasada
                d["semana"] = "nenhum gasto de mídia registrado no período"
                d["sinal"] = "sem dado de mídia — não dá para afirmar nada"
                out.append(d); continue
            c = _camp(W, rec.get("campanha", ""))
            teto = _contrib_pc_liquida(W, "live_propria")
            if c and c["custo"] > 0:
                cpa = (c["trad"] / c["pedidos"]) if c["pedidos"] else None
                d["semana"] = (f"R$ {c['custo']:,.2f} gastos ({c['dias']} dias) · ROAS "
                               f"{c['receita']/c['custo']:.2f}× · CPA de caixa "
                               + (f"R$ {cpa:,.2f}" if cpa else "sem dado"))
                if cpa and teto is not None:
                    if cpa <= teto:
                        d["sinal"] = f"✅ se paga — CPA R$ {cpa:,.2f} ≤ contribuição líquida de R$ {teto:,.2f}/peça"
                    else:
                        d["sinal"] = f"❌ não se paga — CPA R$ {cpa:,.2f} > contribuição líquida de R$ {teto:,.2f}/peça"
                        d["em_jogo"] = (cpa - teto) * c["pedidos"]
            else:
                d["semana"] = "sem gasto na semana"; d["sinal"] = "campanha parada"
            ca = _camp(A, rec.get("campanha", "")) if A else None
            if ca: d["anterior"] = f"R$ {ca['custo']:,.2f} · ROAS {ca['receita']/ca['custo']:.2f}×" if ca["custo"] else "sem gasto"

        elif m == "campanha_desligada":
            if sum(z["custo"] for z in (W.get("midia") or {}).get("campanhas", {}).values()) == 0:
                # sem nenhum gasto registrado, "campanha sem gasto" pode ser só coleta atrasada
                d["semana"] = "nenhum gasto de mídia registrado no período"
                d["sinal"] = "sem dado de mídia — não dá para afirmar nada"
                out.append(d); continue
            c = _camp(W, rec.get("campanha", ""))
            gasto = c["custo"] if c else 0.0
            d["semana"] = f"R$ {gasto:,.2f} gastos" + (f" em {c['dias']} dias" if c and gasto else "")
            ca = _camp(A, rec.get("campanha", "")) if A else None
            d["anterior"] = f"R$ {(ca['custo'] if ca else 0):,.2f}"
            if gasto == 0:
                d["sinal"] = "✅ desligada — sem gasto na semana"
                d["discorda"] = rec["status"] not in ("feita", "descartada")
            else:
                d["sinal"] = "❌ ainda rodando"; d["em_jogo"] = gasto
                d["discorda"] = rec["status"] == "feita"

        elif m == "cortes_promo" and W.get("lives") is not None:
            if not W["lives"]:
                d["semana"] = "nenhuma live própria no período"
                d["sinal"] = "sem evidência — não houve live para medir"
                out.append(d); continue
            w_n = sum(1 for l in W["lives"] if l["corte"]); w_r = sum(l["corte"] for l in W["lives"])
            mens = sum(1 for l in W["lives"] if l.get("corte_testavel", True))
            a_n = sum(1 for l in A.get("lives", []) if l["corte"]) if A else None
            d["semana"] = f"{w_n} corte(s) detectado(s) · custo estimado R$ {w_r:,.2f}"
            d["anterior"] = f"{a_n} corte(s)" if a_n is not None else None
            d["em_jogo"] = w_r
            if w_n > 0: d["sinal"] = "❌ promoção cortada no meio da live"
            elif mens >= 3: d["sinal"] = f"✅ nenhum corte em {mens} lives mensuráveis"
            else: d["sinal"] = f"evidência insuficiente — só {mens} live(s) longa(s) o bastante para medir corte"

        elif m == "nao_pagos":
            w = W["canal"]["nao_pagos_pct"]; a = A["canal"]["nao_pagos_pct"] if A else None
            d["semana"] = f"{w*100:.1f}% das peças pedidas ({W['canal']['nao_pagos']} peças)"
            d["anterior"] = f"{a*100:.1f}%" if a is not None else None
            pc = (W["contrib"] / W["pecas"]) if W["pecas"] else 0
            d["em_jogo"] = W["canal"]["nao_pagos"] * pc
            if a is None: d["sinal"] = "sem base de comparação"
            elif w < a * 0.85: d["sinal"] = "✅ caiu"
            elif w > a * 1.15: d["sinal"] = "❌ subiu"
            else: d["sinal"] = "➖ estável"

        elif m == "preco_hero":
            w = W["canal"]["hero_preco"]; a = A["canal"]["hero_preco"] if A else None
            d["semana"] = f"R$ {w:,.2f} de lista por peça · {W['canal']['hero_pecas']} peças" if w else "sem venda de hero"
            d["anterior"] = f"R$ {a:,.2f}" if a else None
            taxa = R["calibracao"]["blended"]
            d["em_jogo"] = W["canal"]["hero_pecas"] * 5 * taxa   # +R$5 de lista, no volume da semana
            if w and a:
                if w > a * 1.02: d["sinal"] = f"✅ subiu {((w/a)-1)*100:.1f}%"
                elif w < a * 0.98: d["sinal"] = f"❌ caiu {((w/a)-1)*100:.1f}%"
                else: d["sinal"] = "➖ estável — nada mudou no preço"

        out.append(d)
    return out, led.get("perguntas_abertas", [])


def decisoes_da_semana(R, medidas, n=3):
    """As N decisões em jogo: recomendações abertas/contrariadas com mais R$ em jogo +
    o gap estrutural. Um head chega com a pauta — não com a lista inteira."""
    W = R["semanas"][0]
    cand = []
    if W["resultado_final"] < 0 and W["pecas"]:
        gap = -W["resultado_final"]
        cand.append(dict(titulo="Fechar o buraco da estrutura",
                         porque=(f"A semana ficou R$ {gap:,.2f} abaixo do que paga a estrutura — "
                                 f"R$ {gap/W['pecas']:,.2f} por peça faltando nas {W['pecas']} peças vendidas. "
                                 "Volume sozinho não fecha isso: é preço de lista ou CPV."),
                         em_jogo=gap, dono="a definir", tipo="estrutural"))
    for m in medidas:
        if m["status"] in ("aberta", "contrariada") and m["em_jogo"] > 0 and not m["sinal"].startswith("✅"):
            cand.append(dict(titulo=m["titulo"], porque=f"{m['sinal']} — {m['semana']}",
                             em_jogo=m["em_jogo"], dono=m["dono"], tipo="recomendação"))
    return sorted(cand, key=lambda x: -x["em_jogo"])[:n]
