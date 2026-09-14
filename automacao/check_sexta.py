#!/usr/bin/env python3
"""
Rhode — CHECK DE SEXTA (08:00 BRT). Curto, sem análise nova.

Pergunta só duas coisas, sobre a semana corrente de segunda a quinta:
  1. As recomendações do registro estão com sinal verde antes das lives de fim de semana?
  2. Estourou algum alarme desde terça (estouro de verba em live, fonte de dado atrasada)?

Reusa os mesmos medidores do relatório de terça (recomendacoes.py) — o sinal da sexta e o da
terça são a mesma conta, só que sobre a semana parcial.
"""
import os, sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "automacao"))
from dados_semana import calibrar_taxas, por_canal, midia, lives, saude, semana_id, BRT
from recomendacoes import medir


def executar(ref=None):
    ref = ref or datetime.now(BRT).date()
    seg = ref - timedelta(days=ref.weekday())
    qui = seg + timedelta(days=3)
    print(f"  · check de sexta sobre {seg} → {qui}")
    cal = calibrar_taxas(qui)
    W = dict(seg=seg, dom=qui, canal=por_canal(seg, qui, cal["taxas"]), midia=midia(seg, qui),
             lives=lives(seg, qui))
    cn = W["canal"]["canais"]
    W["pecas"] = sum(z["pecas"] for z in cn.values())
    W["contrib"] = sum(z["contrib"] for z in cn.values())
    medidas, _ = medir(dict(semanas=[W], calibracao=cal))
    desde_terca = [l for l in W["lives"] if l["inicio"].date() >= seg + timedelta(days=1)]
    alarmes = []
    for l in desde_terca:
        if l["estouro"]:
            alarmes.append(f"Estouro de verba na live de {l['inicio'].strftime('%d/%m %H:%M')} "
                           f"às {l['estouro_h']:02d}h — R$ {l['estouro']:,.2f} de excesso")
        if l["corte"]:
            alarmes.append(f"Promoção cortada no meio da live de {l['inicio'].strftime('%d/%m %H:%M')} "
                           f"às {l['corte_h']} — custo estimado R$ {l['corte']:,.2f}")
    for s in saude(qui):
        if not s["ok"]:
            alarmes.append(f"Fonte {s['fonte']} atrasada {s['lag']} dia(s) — números dessa fonte sob suspeita")
    vermelhos = [m for m in medidas if m["sinal"].startswith("❌")]
    return dict(id=semana_id(seg), seg=seg, qui=qui, medidas=medidas, vermelhos=vermelhos,
                alarmes=alarmes, n_lives=len(W["lives"]))


if __name__ == "__main__":
    R = executar()
    print(f"\n{R['id']} · {len(R['vermelhos'])} de {len(R['medidas'])} recomendações com sinal vermelho · "
          f"{len(R['alarmes'])} alarme(s)")
    for m in R["medidas"]: print(f"  · {m['titulo']}: {m['sinal']}")
    for a in R["alarmes"]: print(f"  ⚠ {a}")
