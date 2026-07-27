#!/usr/bin/env python3
"""
MOTOR DE CONCILIAÇÃO — divergência esperado × real do repasse TikTok Shop (Rhode).
Base reprodutível do SaaS de conciliação. NÃO é análise ad-hoc.

O que faz (pedido a pedido, tudo em Decimal — nunca float):
  1. Agrega statement_tx por order_id (soma COM SINAL — venda+devolução não infla).
  2. Repasse ESPERADO (regras contratadas TikTok BR, pré-15/07):
       esperado = revenue − comissão 6% − serviço/SFP (6% + R$4/item)
                  − comissão de afiliada (real) − comissão de ads (real) − frete (real)
                  + reembolsos (logística + plataforma)
     NÃO inclui GMV Max (a mídia sai da conta de ads, não do settlement).
     margem SEMPRE sobre revenue (net_sales), nunca gross_sales.
  3. Compara com o repasse REAL (statement_tx.settlement, campo exato).
  4. Classifica cada pedido em: timing | cancelado | devolucao |
     comissao_divergente | taxa_divergente(serviço/SFP) | nao_explicado | ok
  5. Circuit breaker: se 'nao_explicado' > 20% da divergência total → PARA e mostra exemplos.

Identidade validada nos dados: settlement = revenue + fee_total + shipping
                               + logistics_reimbursement + platform_reimbursement
                               (fee_total, shipping negativos; reembolsos positivos)
comissão de plataforma = 6,00% da revenue ao centavo (validado abr–jun/26).

Uso: python3 motor_conciliacao_divergencia.py [--periodos 2026-04,2026-05,2026-06]
"""
import os, sys, json, argparse, urllib.request
from decimal import Decimal as D, getcontext, ROUND_HALF_UP
from collections import defaultdict
from datetime import date
from dotenv import load_dotenv

getcontext().prec = 28
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SK, "Authorization": f"Bearer {SK}"}

# ---- regras contratadas (parametrizáveis — viram config do SaaS) ----
COMMISSION_RATE = D("0.06")   # comissão de plataforma
SERVICE_RATE    = D("0.06")   # serviço/SFP (frete-grátis-plataforma) — % da revenue
PER_ITEM_FEE    = D("4.00")   # R$/item (pré-15/07)
THRESH_COMISSAO = D("0.50")   # divergência de comissão material (R$/pedido)
THRESH_SERVICO  = D("2.00")   # divergência de serviço material (R$/pedido)
THRESH_NAOEXPL  = D("1.00")   # residual não-explicado material (R$/pedido)
CENT = D("0.01")

def dec(v):
    try: return D(str(v)) if v is not None else D(0)
    except Exception: return D(0)

def r2(x): return x.quantize(CENT, rounding=ROUND_HALF_UP)

def pageall(base, order="id"):
    """Paginação DETERMINÍSTICA: sem order=<coluna única> o offset pula/duplica linhas
    (o total volta certo, o conteúdo não) → a divergência calculada fica errada."""
    out = []; off = 0
    sep = "&" if "?" in base else "?"
    while True:
        req = urllib.request.Request(f"{SB}/rest/v1/{base}{sep}order={order}&limit=1000&offset={off}", headers=H)
        b = json.load(urllib.request.urlopen(req))
        out += b
        if len(b) < 1000: break
        off += 1000
    return out

def carregar(periodos):
    inlist = ",".join(periodos)
    cols = ("order_id,periodo,customer_payment,settlement,fee_total,platform_commission,"
            "affiliate_commission,affiliate_ads_commission,shipping,adjustment,revenue,gross_sales,"
            "customer_refund,return_shipping,refund_admin_fee,logistics_reimbursement,platform_reimbursement")
    st = pageall(f"statement_tx?periodo=in.({inlist})&select={cols}")
    ps = pageall(f"pedidos_sku?periodo=in.({inlist})&select=order_id,periodo,gmv,qty,status,data")
    return st, ps

def agregar_por_pedido(st, ps):
    # pedidos_sku por order_id: qty, status, gmv, período de venda
    ped = defaultdict(lambda: {"qty": 0, "status": "", "gmv": D(0), "periodo": None, "data": None})
    for r in ps:
        o = r["order_id"]; p = ped[o]
        p["qty"] += int(r.get("qty") or 0)
        p["gmv"] += dec(r.get("gmv"))
        if 'CANCEL' in (r.get("status") or "").upper(): p["status"] = "CANCEL"
        p["periodo"] = r["periodo"]; p["data"] = r.get("data")
    # statement_tx por order_id (soma com sinal)
    F = ["customer_payment","settlement","fee_total","platform_commission","affiliate_commission",
         "affiliate_ads_commission","shipping","adjustment","revenue","gross_sales","customer_refund",
         "return_shipping","refund_admin_fee","logistics_reimbursement","platform_reimbursement"]
    tx = defaultdict(lambda: {k: D(0) for k in F} | {"periodo": None})
    for r in st:
        o = r["order_id"]; t = tx[o]
        for k in F: t[k] += dec(r.get(k))
        t["periodo"] = r["periodo"]  # período de venda (max não importa, é o mesmo)
    return ped, tx

def classificar(tx, ped, sfp_rate=SERVICE_RATE):
    """Retorna dict por order_id com esperado, real, divergências e bucket.
    sfp_rate = taxa de serviço/SFP contratada (parametrizável: 6% ou 12% p/ os 2 cenários)."""
    res = {}
    for o, t in tx.items():
        p = ped.get(o, {"qty": 0, "status": "", "gmv": D(0)})
        qty = D(p["qty"] or 1)  # fallback 1 item se pedidos_sku não cobre
        # revenue robusto: coluna itemizada; se 0, deriva pela identidade
        rev = t["revenue"]
        if abs(rev) < CENT:
            rev = t["settlement"] + abs(t["fee_total"]) + abs(t["shipping"]) \
                  - t["logistics_reimbursement"] - t["platform_reimbursement"]
        pago = t["customer_payment"]; real = t["settlement"]
        reimb = t["logistics_reimbursement"] + t["platform_reimbursement"]
        # componentes REAIS (valor absoluto — são deduções)
        comissao_real = abs(t["platform_commission"])
        afiliada_real = abs(t["affiliate_commission"])
        ads_real      = abs(t["affiliate_ads_commission"])
        fee_real      = abs(t["fee_total"])
        frete_real    = abs(t["shipping"])
        servico_real  = fee_real - comissao_real - afiliada_real - ads_real   # SFP + R$4/item (resíduo)
        tem_devolucao = (abs(t["customer_refund"]) > CENT or abs(t["return_shipping"]) > CENT
                         or abs(t["refund_admin_fee"]) > CENT)
        # ESPERADO (contratado)
        comissao_esp = rev * COMMISSION_RATE
        servico_esp  = rev * sfp_rate + PER_ITEM_FEE * qty
        esperado = (rev - comissao_esp - servico_esp - afiliada_real - ads_real - frete_real + reimb)
        # DIVERGÊNCIAS
        div_comissao = comissao_real - comissao_esp
        div_servico  = servico_real - servico_esp
        total_div    = esperado - real                      # >0 = TikTok repassou MENOS que o esperado
        nao_expl     = total_div - div_comissao - div_servico  # resíduo não atribuído a taxa/comissão
        # BUCKET (mutuamente exclusivo)
        if abs(real) <= CENT and pago > CENT:
            bucket = "cancelado" if p["status"] == "CANCEL" else "timing"
        elif tem_devolucao or real < -CENT:
            bucket = "devolucao"
        elif abs(nao_expl) > THRESH_NAOEXPL:
            bucket = "nao_explicado"
        elif div_comissao > THRESH_COMISSAO:
            bucket = "comissao_divergente"
        elif div_servico > THRESH_SERVICO:
            bucket = "taxa_divergente"      # serviço/SFP (frete-grátis-plataforma)
        else:
            bucket = "ok"
        res[o] = dict(periodo=t["periodo"], qty=qty, gmv=p["gmv"], pago=pago, revenue=rev,
                      real=real, esperado=esperado, total_div=total_div,
                      div_comissao=div_comissao, div_servico=div_servico, nao_expl=nao_expl,
                      comissao_real=comissao_real, comissao_esp=comissao_esp,
                      servico_real=servico_real, servico_esp=servico_esp,
                      afiliada_real=afiliada_real, frete_real=frete_real, bucket=bucket,
                      status=p["status"])
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periodos", default="2026-04,2026-05,2026-06")
    args = ap.parse_args()
    periodos = args.periodos.split(",")

    st, ps = carregar(periodos)
    ped, tx = agregar_por_pedido(st, ps)
    # DUAS versões de SFP lado a lado (6% vs 12%) — quando o Lucas confirmar a taxa, a resposta já está pronta
    res6  = classificar(tx, ped, D("0.06"))
    res12 = classificar(tx, ped, D("0.12"))

    # denominadores: revenue (REGRA: revenue como denominador nos buckets) + GMV (p/ o faltante)
    revenue_periodo = defaultdict(lambda: D(0))
    for o, x in res6.items(): revenue_periodo[x["periodo"]] += x["revenue"]
    gmv_periodo = defaultdict(lambda: D(0)); ord_venda = defaultdict(set)
    for r in ps:
        if 'CANCEL' in (r.get("status") or "").upper(): continue
        gmv_periodo[r["periodo"]] += dec(r.get("gmv")); ord_venda[r["periodo"]].add(r["order_id"])

    BUCKETS = ["ok","timing","cancelado","devolucao","comissao_divergente","taxa_divergente","nao_explicado"]
    ACIONAVEL = {"comissao_divergente","taxa_divergente","nao_explicado"}
    def agg_por(res):
        por = defaultdict(lambda: defaultdict(lambda: {"n":0,"div":D(0)}))
        for o, x in res.items():
            por[x["periodo"]][x["bucket"]]["n"] += 1; por[x["periodo"]][x["bucket"]]["div"] += x["total_div"]
        return por
    por6, por12 = agg_por(res6), agg_por(res12)
    def money(x): return f"{x:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    print("="*92)
    print("MOTOR DE CONCILIAÇÃO — esperado × real ·", ",".join(periodos), "· denominador=revenue · Decimal")
    print("Duas versões de SFP contratada: 6% | 12% (só muda taxa_divergente; nao_explicado é SFP-independente)")
    print("="*92)
    linhas_md = ["# Conciliação — divergência esperado × real (TikTok Shop / Rhode)",
                 f"\n_Períodos: {', '.join(periodos)} · comissão {COMMISSION_RATE*100:.0f}% + R${PER_ITEM_FEE}/item · SFP **6% vs 12%** · GMV Max fora · denominador=**revenue** · Decimal_\n"]
    for p in periodos:
        rev = revenue_periodo[p]; gmv = gmv_periodo[p]
        cov = D(len([o for o,x in res6.items() if x["periodo"]==p]))/D(len(ord_venda[p]))*100 if ord_venda[p] else D(0)
        print(f"\n── {p} · revenue R$ {money(rev)} · GMV R$ {money(gmv)} · cobertura {cov:.0f}% ──")
        print(f"   {'bucket':<20}│ {'6%: ped':>9}{'div R$':>13}{'%rev':>8}  │ {'12%: ped':>9}{'div R$':>13}{'%rev':>8}")
        for b in BUCKETS:
            d6=por6[p][b]; d12=por12[p][b]
            p6=(d6['div']/rev*100) if rev else D(0); p12=(d12['div']/rev*100) if rev else D(0)
            print(f"   {b:<20}│ {d6['n']:>9}{money(d6['div']):>13}{p6:>7.2f}%  │ {d12['n']:>9}{money(d12['div']):>13}{p12:>7.2f}%")
        tot6=sum((por6[p][b]['div'] for b in BUCKETS),D(0)); tot12=sum((por12[p][b]['div'] for b in BUCKETS),D(0))
        aci6=sum((por6[p][b]['div'] for b in ACIONAVEL),D(0)); aci12=sum((por12[p][b]['div'] for b in ACIONAVEL),D(0))
        rt=lambda v: (v/rev*100) if rev else D(0)
        print(f"   {'-'*80}")
        print(f"   {'TOTAL':<20}│ {'':>9}{money(tot6):>13}{rt(tot6):>7.2f}%  │ {'':>9}{money(tot12):>13}{rt(tot12):>7.2f}%")
        print(f"   {'ACIONÁVEL':<20}│ {'':>9}{money(aci6):>13}{rt(aci6):>7.2f}%  │ {'':>9}{money(aci12):>13}{rt(aci12):>7.2f}%")
        linhas_md.append(f"\n## {p} — revenue R$ {rev:,.2f} · GMV R$ {gmv:,.2f} · cobertura {cov:.0f}%\n")
        linhas_md.append("| bucket | ped (6%) | div R$ (6%) | %rev (6%) | ped (12%) | div R$ (12%) | %rev (12%) |\n|---|--:|--:|--:|--:|--:|--:|")
        for b in BUCKETS:
            d6=por6[p][b]; d12=por12[p][b]
            linhas_md.append(f"| {b} | {d6['n']} | {d6['div']:,.2f} | {rt(d6['div']):.2f}% | {d12['n']} | {d12['div']:,.2f} | {rt(d12['div']):.2f}% |")
        linhas_md.append(f"| **TOTAL** | | **{tot6:,.2f}** | **{rt(tot6):.2f}%** | | **{tot12:,.2f}** | **{rt(tot12):.2f}%** |")
        linhas_md.append(f"| **ACIONÁVEL** | | **{aci6:,.2f}** | **{rt(aci6):.2f}%** | | **{aci12:,.2f}** | **{rt(aci12):.2f}%** |")

    res = res6  # faltante e circuit breaker (nao_explicado é SFP-independente) usam a base 6%
    por = por6

    # ---- REPASSE FALTANTE (definição ESTRITA — decide o success fee) ----
    # "Entregue/concluído há >30d que NUNCA apareceu no settlement." Returns NÃO contam
    # (apareceram e voltaram — não é dinheiro retido). Classes por pedido >30d não-cancel:
    #   nunca_apareceu   → sem NENHUMA linha em statement_tx (TikTok não pagou)   ⟵ recuperável
    #   apareceu_zerado  → tem linha, settlement≈0, SEM refund (unpaid)           ⟵ recuperável
    #   devolucao        → tem refund ou settlement<0 (voltou pro cliente)        ✗ não é faltante
    #   liquidado        → settlement>0                                            ✓ pago
    hoje = date.today()
    present = set(tx.keys())
    CLS = ["nunca_apareceu","apareceu_zerado","devolucao","liquidado"]
    fal = defaultdict(lambda: defaultdict(lambda: [0, D(0)]))
    recuperaveis = []  # (order_id, periodo, gmv, idade) — só nunca_apareceu + apareceu_zerado
    for o, pd in ped.items():
        if pd["status"] == "CANCEL": continue
        try: idade = (hoje - date.fromisoformat((pd["data"] or "")[:10])).days
        except Exception: idade = 999
        if idade <= 30: continue
        per = pd["periodo"]; g = pd["gmv"]
        if o not in present:
            cls = "nunca_apareceu"; recuperaveis.append((o, per, g, idade))
        else:
            t = tx[o]
            if t["settlement"] > CENT: cls = "liquidado"
            elif abs(t["customer_refund"]) > CENT or t["settlement"] < -CENT: cls = "devolucao"
            else: cls = "apareceu_zerado"; recuperaveis.append((o, per, g, idade))
        fal[per][cls][0] += 1; fal[per][cls][1] += g
    print("\n" + "="*78)
    print("REPASSE FALTANTE (estrito) — concluído >30d que NUNCA liquidou · returns fora")
    print(f"   {'período':<10}{'nunca_apar':>12}{'apar_zerado':>12}{'devolucao':>14}{'RECUP R$':>13}{'%GMV':>7}")
    linhas_md.append("\n## Repasse faltante ESTRITO (concluído >30d, nunca liquidou) — decide o success fee\n")
    linhas_md.append("| período | nunca apareceu | apareceu zerado | devolução (não conta) | **RECUPERÁVEL R$** | % do GMV |\n|---|--:|--:|--:|--:|--:|")
    for p in periodos:
        gmv = gmv_periodo[p]; f = fal[p]
        rec_n = f["nunca_apareceu"][0] + f["apareceu_zerado"][0]
        rec_g = f["nunca_apareceu"][1] + f["apareceu_zerado"][1]
        pgmv = (rec_g/gmv*100) if gmv else D(0)
        print(f"   {p:<10}{f['nunca_apareceu'][0]:>12}{f['apareceu_zerado'][0]:>12}{f['devolucao'][0]:>14}{money(rec_g):>13}{pgmv:>6.2f}%")
        linhas_md.append(f"| {p} | {f['nunca_apareceu'][0]} | {f['apareceu_zerado'][0]} | {f['devolucao'][0]} | **{rec_g:,.2f}** | {pgmv:.2f}% |")
    tot_rec = sum((f["nunca_apareceu"][1] + f["apareceu_zerado"][1] for f in fal.values()), D(0))
    tot_gmv = sum((gmv_periodo[p] for p in periodos), D(0))
    print(f"   {'-'*68}")
    print(f"   RECUPERÁVEL TOTAL (3 meses): R$ {money(tot_rec)} = {(tot_rec/tot_gmv*100 if tot_gmv else 0):.2f}% do GMV")
    recuperaveis.sort(key=lambda x:-x[2])
    print(f"\n   TOP 20 recuperável (nunca liquidou · abrir chamado):" if recuperaveis else "\n   (nenhum pedido recuperável — TikTok liquidou tudo)")
    linhas_md.append(f"\n**Recuperável total 3 meses: R$ {tot_rec:,.2f} = {(tot_rec/tot_gmv*100 if tot_gmv else 0):.2f}% do GMV.**")
    if recuperaveis:
        print(f"   {'order_id':<22}{'periodo':<9}{'GMV':>10}{'idade(d)':>9}")
        linhas_md.append("\n### Top 20 recuperável (order_id · abrir chamado)\n\n| order_id | período | GMV | idade (d) |\n|---|---|--:|--:|")
        for o, p, g, idade in recuperaveis[:20]:
            print(f"   {o:<22}{p:<9}{money(g):>10}{idade:>9}")
            linhas_md.append(f"| {o} | {p} | {g:,.2f} | {idade} |")
    else:
        linhas_md.append("\n_Nenhum pedido recuperável: com a base completa, todo pedido concluído liquidou._")

    # ---- CIRCUIT BREAKER: nao_explicado > 20% da divergência total ----
    tot_div_all = sum((por[p][b]["div"] for p in periodos for b in BUCKETS), D(0))
    tot_naoexpl = sum((por[p]["nao_explicado"]["div"] for p in periodos), D(0))
    share = (tot_naoexpl/tot_div_all*100) if abs(tot_div_all)>CENT else D(0)
    print("\n" + "="*78)
    print(f"CIRCUIT BREAKER · nao_explicado = R$ {tot_naoexpl:,.2f} = {share:.1f}% da divergência total")
    top = sorted([x for x in res.values() if x["bucket"]=="nao_explicado"], key=lambda x:-abs(x["nao_expl"]))[:10]
    if abs(share) > 20:
        print("🛑 PAROU: nao_explicado > 20% — pode ser bug no cálculo, não buraco real. Exemplos:")
    else:
        print(f"✅ nao_explicado sob controle (<20%). Top 10 divergências não-explicadas:")
    print(f"   {'order_id':<22}{'periodo':<9}{'nao_expl R$':>12}{'real':>10}{'esperado':>10}")
    for x in top:
        oid=[o for o,v in res.items() if v is x][0]
        print(f"   {oid:<22}{x['periodo']:<9}{x['nao_expl']:>12,.2f}{x['real']:>10,.2f}{x['esperado']:>10,.2f}")

    # salva markdown
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios",
                       "conciliacao_divergencia.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write("\n".join(linhas_md))
    print(f"\n✓ resumo markdown → {out}")

if __name__ == "__main__":
    main()
