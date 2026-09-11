#!/usr/bin/env python3
"""
Rhode — GERADOR AUTOMÁTICO do relatório de live (template travado da live de 10/09).

Uso:  python3 automacao/gerar_relatorio_live.py --room 7683907251237997332
      python3 automacao/gerar_relatorio_live.py --room <id> --saida /tmp/x.xlsx

Produz o mesmo workbook de 8 abas do "Relatorio Live 10-09 Analise Completa", com os
mesmos KPIs e a mesma régua — mas com TUDO derivado do dado, inclusive a narrativa.
Nada de número escrito à mão (lição da auditoria de escopo de 11/09).

Régua: receita de LISTA via lib/receita.py (cupom da plataforma é subsídio do TikTok)
       settlement 0,7084 · CPV R$ 45,40 · apresentadora R$ 50/hora.
"""
import os, re, sys, json, argparse, urllib.request, statistics as sta
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import DataBarRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from dotenv import load_dotenv; load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass
from lib.receita import receita_itens

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
HDRS = {"apikey": SK, "Authorization": "Bearer " + SK}
BRT = timezone(timedelta(hours=-3))
CPV = 45.40; SR = 0.7084; HORA = 50.0
HERO = {"REF516", "REF525", "REF527"}
TAM = ["34", "36", "38", "40", "42", "44", "46"]

# ─────────── fontes ───────────
def qall(p, o="id"):
    out = []; off = 0
    while True:
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{SB}/rest/v1/{p}{'&' if '?' in p else '?'}order={o}&limit=1000&offset={off}",
            headers=HDRS), timeout=90)); out += r
        if len(r) < 1000: break
        off += 1000
    return out

def ads_token():
    return json.load(urllib.request.urlopen(urllib.request.Request(
        f"{SB}/rest/v1/api_tokens?id=eq.tiktok_ads&select=access_token", headers=HDRS)))[0]["access_token"]

def curva_horaria(dia):
    """Gasto/receita/pedidos/roi/live_views por HORA. stat_time_hour só funciona
    pareado com uma dimensão principal — ver reference_gmvmax_sem_funil_api."""
    import urllib.parse
    tok = ads_token()
    ADV = "7504809708629344263"; STORE = "7496180259574286943"
    EP = "https://business-api.tiktok.com/open_api/v1.3/gmv_max/report/get/"
    live = defaultdict(lambda: [0.0, 0.0, 0, 0.0]); prod = defaultdict(lambda: [0.0, 0.0, 0, 0.0])
    page = 1
    while True:
        p = {"advertiser_id": ADV, "store_ids": [STORE],
             "dimensions": ["stat_time_hour", "campaign_id"],
             "metrics": ["cost", "gross_revenue", "orders", "campaign_name", "roi", "live_views"],
             "start_date": dia, "end_date": dia, "page_size": 200, "page": page}
        qs = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in p.items()})
        d = json.load(urllib.request.urlopen(urllib.request.Request(EP, headers={"Access-Token": tok}), timeout=90)
                      ) if False else json.load(urllib.request.urlopen(
                      urllib.request.Request(f"{EP}?{qs}", headers={"Access-Token": tok}), timeout=90))
        if d.get("code") != 0:
            raise RuntimeError(f"GMV Max API: {d.get('message')}")
        for r in d["data"]["list"]:
            h = int(r["dimensions"]["stat_time_hour"][11:13]); m = r["metrics"]
            tgt = live if "LIVE" in (m.get("campaign_name") or "").upper() else prod
            tgt[h][0] += float(m["cost"]); tgt[h][1] += float(m["gross_revenue"])
            tgt[h][2] += int(m["orders"]); tgt[h][3] += float(m.get("live_views") or 0)
        pi = d["data"].get("page_info", {})
        if page >= pi.get("total_page", 1): break
        page += 1
    return live, prod

def bref(s):
    m = re.match(r"^(REF\d{3})(\d{2})$", str(s or ""))
    return (m.group(1), m.group(2)) if m else (str(s or "?"), "--")

# ─────────── cálculo ───────────
def montar(room_id):
    la = qall(f"live_attr?select=room_id,titulo,inicio,fim,data,gmv,itens,customers&room_id=eq.{room_id}")
    if not la: raise SystemExit(f"sala {room_id} não está em live_attr")
    L = la[0]
    ini = datetime.fromisoformat(L["inicio"]).astimezone(BRT)
    fim = datetime.fromisoformat(L["fim"]).astimezone(BRT) if L["fim"] else None
    if not fim: raise SystemExit(f"sala {room_id} ainda não tem fim registrado")
    dur = (fim - ini).total_seconds() / 3600
    dia = ini.strftime("%Y-%m-%d")
    horas = list(range(ini.hour, fim.hour + 1))

    LIVE, PROD = curva_horaria(dia)
    sk = qall(f"pedidos_sku?select=order_id,sku,seller_sku,produto,qty,gmv,status,order_time&data=eq.{dia}")
    PAG = {p["order_id"]: p for p in qall(f"pedido_pagamento?select=*&data=eq.{dia}", "order_id")}
    RM = receita_itens(sk, PAG)
    def t(r): return datetime.fromtimestamp(int(r["order_time"]), BRT)
    inw = [r for r in sk if ini <= t(r) <= fim]
    ok = [r for r in inw if r["status"] not in ("CANCELLED", "UNPAID")]
    if not ok: raise SystemExit(f"sala {room_id}: nenhum pedido pago na janela — nada a reportar")

    QTY = sum(r["qty"] for r in ok); PAGO = sum(r["gmv"] for r in ok)
    REV = sum(RM[id(r)] for r in ok); SUBS = REV - PAGO; GU = REV / PAGO if PAGO else 1
    PED = len({r["order_id"] for r in ok})
    CONTRIB = sum((RM[id(r)] / r["qty"] * SR - CPV) * r["qty"] for r in ok if r["qty"])
    ADS = sum(LIVE[h][0] for h in horas); REC = sum(LIVE[h][1] for h in horas)
    APRE = dur * HORA; RES = CONTRIB - ADS - APRE
    CPED = CONTRIB / PED if PED else 0

    # ── detecção 1: a hora fora da curva (maior CPA com gasto material) ──
    cand = [(h, LIVE[h]) for h in horas if LIVE[h][2] >= 3 and LIVE[h][0] > 1]
    pico = None
    if len(cand) >= 3:
        cpas = sorted((v[0] / v[2], h) for h, v in cand)
        pior_cpa, pior_h = cpas[-1]
        base = [h for h, v in cand if h != pior_h]
        bc = sum(LIVE[h][0] for h in base) / len(base); bp = sum(LIVE[h][2] for h in base) / len(base)
        cpa_base = bc / bp if bp else 0
        if cpa_base and pior_cpa > 2 * cpa_base:          # só é "estouro" se destoar de verdade
            c, rv, p, v = LIVE[pior_h]
            exc = c - cpa_base * p
            cpam = (c - bc) / (p - bp) if (p - bp) > 0 else 0
            pico = dict(h=pior_h, c=c, p=p, v=v, roi=rv / c if c else 0, cpa=pior_cpa,
                        bc=bc, bp=bp, cpa_base=cpa_base, exc=exc, cpam=cpam,
                        share=c / ADS if ADS else 0,
                        cv=c / v if v else 0, cv_base=(sum(LIVE[h][0] for h in base) /
                        sum(LIVE[h][3] for h in base)) if sum(LIVE[h][3] for h in base) else 0)

    # ── detecção 2: corte de promoção (piso de preço por faixa de 15 min) ──
    def buck(d): return d.replace(minute=(d.minute // 15) * 15, second=0, microsecond=0)
    piso = defaultdict(dict)
    for r in ok:
        if not r["qty"]: continue
        b, _ = bref(r["seller_sku"] or r["sku"])
        k = buck(t(r)); pr = r["gmv"] / r["qty"]
        piso[b][k] = min(piso[b].get(k, 9e9), pr)
    corte = None
    votos = []
    for b, d in piso.items():
        ks = sorted(d)
        if len(ks) < 4: continue
        p0 = min(d[k] for k in ks[:max(2, len(ks) // 3)])          # piso do começo
        for k in ks[1:]:
            if d[k] > p0 * 1.07 and all(d[k2] > p0 * 1.03 for k2 in ks if k2 >= k):
                votos.append(k); break
    if votos:
        votos.sort(); mediana = votos[len(votos) // 2]
        if len(votos) >= 2 and mediana > ini + timedelta(minutes=20) and mediana < fim - timedelta(minutes=20):
            antes = [r for r in ok if t(r) < mediana]; dep = [r for r in ok if t(r) >= mediana]
            ma = (mediana - ini).total_seconds() / 60; md = (fim - mediana).total_seconds() / 60
            def blk(rs, mins, hs):
                q = sum(r["qty"] for r in rs)
                c = sum((RM[id(r)] / r["qty"] * SR - CPV) * r["qty"] for r in rs if r["qty"])
                return dict(q=q, c=c, pm=q / mins if mins else 0, cm=c / mins if mins else 0)
            A = blk(antes, ma, None); B = blk(dep, md, None)
            corte = dict(quando=mediana, n_produtos=len(votos), A=A, B=B, ma=ma, md=md,
                         custo=(A["cm"] - B["cm"]) * md if A["cm"] > B["cm"] else 0)

    # ── por produto ──
    g = defaultdict(lambda: [0, 0.0, set(), defaultdict(int), "", 0.0])
    for r in ok:
        b, tm = bref(r["seller_sku"] or r["sku"]); z = g[b]
        z[0] += r["qty"] or 0; z[1] += RM[id(r)]; z[5] += r["gmv"] or 0
        z[2].add(r["order_id"]); z[3][tm] += r["qty"] or 0
        if not z[4]: z[4] = (r["produto"] or "")[:46]
    hq = sum(z[0] for b, z in g.items() if b in HERO)
    hv = sum(z[1] for b, z in g.items() if b in HERO)
    hc = sum((z[1] / z[0] * SR - CPV) * z[0] for b, z in g.items() if b in HERO and z[0])

    # ── furos de grade (zero ENTRE tamanhos que vendem) ──
    furos = []
    for b, z in sorted(g.items(), key=lambda x: -x[1][1])[:10]:
        d = z[3]; idx = [i for i, tm in enumerate(TAM) if d.get(tm, 0) > 0]
        if not idx: continue
        meio = [TAM[i] for i in range(min(idx), max(idx) + 1) if d.get(TAM[i], 0) == 0]
        if meio: furos.append((b, meio, z[0]))

    # ── pagamento ──
    stt = defaultdict(lambda: [0, 0.0])
    for r in inw: stt[r["status"]][0] += r["qty"] or 0; stt[r["status"]][1] += r["gmv"] or 0
    unp = [r for r in inw if r["status"] == "UNPAID"]
    cperda = sum((RM[id(r)] / r["qty"] * SR - CPV) * r["qty"] for r in unp if r["qty"])

    # ── preço mediano por hora ──
    prh = {}
    for h in horas:
        sub = [r for r in ok if t(r).hour == h and r["qty"]]
        prh[h] = sta.median([r["gmv"] / r["qty"] for r in sub]) if sub else 0

    return dict(L=L, ini=ini, fim=fim, dur=dur, dia=dia, horas=horas, LIVE=LIVE, PROD=PROD,
                QTY=QTY, PAGO=PAGO, REV=REV, SUBS=SUBS, GU=GU, PED=PED, CONTRIB=CONTRIB,
                ADS=ADS, REC=REC, APRE=APRE, RES=RES, CPED=CPED, pico=pico, corte=corte,
                g=g, hq=hq, hv=hv, hc=hc, furos=furos, stt=stt, cperda=cperda, prh=prh,
                inw=inw, ok=ok, room=str(room_id))


# ─────────── render ───────────
INK="1A1A1E";MUT="6B6B76";RED="FE2C55";GREEN="0E9F6E";RHODE="FE2C55"
H1=Font(size=16,bold=True,color=INK);H2=Font(size=12,bold=True,color=INK)
TH=Font(size=10,bold=True,color="FFFFFF");BOLD=Font(bold=True,color=INK)
MUTF=Font(size=9,italic=True,color=MUT);RF=Font(bold=True,color=RED);GF=Font(bold=True,color=GREEN)
HEAD=PatternFill("solid",fgColor=INK);BAND=PatternFill("solid",fgColor="F7F7F9")
TOTF=PatternFill("solid",fgColor="EFEFF2");ALERT=PatternFill("solid",fgColor="FDECEA")
OKF=PatternFill("solid",fgColor="E8F6EF");WARN=PatternFill("solid",fgColor="FFF4E5")
Cc=Alignment(horizontal="center",vertical="center")
Lw=Alignment(horizontal="left",wrap_text=True,vertical="top")
CUR='R$ #,##0.00';INT='#,##0';PCT='0.0%';X1='0.00"x"';N2='0.00';N4='0.0000'

def C(ws,r,c,v=None,f=None,fmt=None,fill=None,al=None):
    x=ws.cell(r,c,v)
    if f:x.font=f
    if fmt:x.number_format=fmt
    if fill:x.fill=fill
    if al:x.alignment=al
    return x
def hdr(ws,r,cols,w=None):
    for i,tt in enumerate(cols,1): C(ws,r,i,tt,TH,fill=HEAD,al=Cc)
    if w:
        for i,x in enumerate(w,1): ws.column_dimensions[ws.cell(1,i).column_letter].width=x
def band(ws,a,b,n):
    for r in range(a,b+1):
        if (r-a)%2==1:
            for c in range(1,n+1):
                cl=ws.cell(r,c)
                if cl.fill.fgColor.rgb in (None,"00000000"): cl.fill=BAND
def nota(ws,r,tx,n=7,h=30,f=None):
    C(ws,r,1,tx,f or MUTF,al=Lw); ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=n)
    ws.row_dimensions[r].height=h; return r+1
def BRn(v,d=2):
    return f"{v:,.{d}f}".replace(",","\x00").replace(".",",").replace("\x00",".")

def render(D):
    wb=Workbook()
    L=D["L"];ini=D["ini"];fim=D["fim"];horas=D["horas"];LIVE=D["LIVE"];PROD=D["PROD"]
    pico=D["pico"];corte=D["corte"];RES=D["RES"];ADS=D["ADS"];QTY=D["QTY"];REV=D["REV"]
    titulo=(L["titulo"] or "(sala sem título)").strip()

    # ═══ 1 · RESUMO ═══
    ws=wb.active; ws.title="Resumo executivo"; ws.sheet_view.showGridLines=False
    C(ws,1,1,f'LIVE {ini.strftime("%d/%m/%Y")} — {ini.strftime("%H:%M")} às {fim.strftime("%H:%M")} ({D["dur"]:.2f}h)',H1)
    C(ws,2,1,f'Sala {D["room"]} · "{titulo}"',MUTF)
    C(ws,3,1,f'Gerado automaticamente em {datetime.now(BRT).strftime("%d/%m/%Y %H:%M")} BRT · ESCOPO: só esta sala. Outras lives do mesmo dia não entram em nenhum número.',
      Font(size=9,italic=True,color=GREEN))
    r=5
    hdr(ws,r,["Indicador","Valor","Leitura"],[30,20,84]); r+=1; r0=r
    veredito=("A live PAGOU." if RES>0 else "A live deu PREJUÍZO.")+f" {BRn(abs(RES))} em {D['dur']:.2f}h = R$ {BRn(RES/D['dur'])} por hora no ar."
    for k,v,fm,nt,fn in [
     ("Pago pelo cliente",D["PAGO"],CUR,f"{QTY} peças pagas em {D['PED']} pedidos. É o sub_total — o que saiu do bolso do cliente.",None),
     ("(+) Cupom subsidiado pelo TikTok",D["SUBS"],CUR,f"R$ {BRn(D['SUBS']/QTY)} por peça. O TikTok banca esse gap e ele VOLTA para a loja.",None),
     ("= RECEITA DE LISTA",REV,CUR,f"Base de toda taxa e de toda margem. Gross-up medido nesta live: {D['GU']:.4f}.","V"),
     ("Total de pedidos",D["PED"],INT,"Pedidos PAGOS gerados na janela desta live.",None),
     ("AOV por pedido (lista)",REV/D["PED"],CUR,f"Preço de lista médio por peça: R$ {BRn(REV/QTY)} (pago: R$ {BRn(D['PAGO']/QTY)}).",None),
     ("Custo de Ads (live)",ADS,CUR,f"Só campanhas de live. Campanhas de produto rodaram R$ {BRn(sum(PROD[h][0] for h in horas))} nas mesmas horas.",None),
     ("ROAS",D["REC"]/ADS if ADS else 0,X1,"Receita atribuída ÷ custo. Correto, mas não decide nada sozinho — ver contribuição.",None),
     ("Contribuição bruta",D["CONTRIB"],CUR,f"(receita de lista/peça × {SR} − CPV {BRn(CPV)}) por peça. R$ {BRn(D['CONTRIB']/QTY)} por peça.",None),
     ("(−) Mídia de live",-ADS,CUR,"",None),
     (f"(−) Apresentadora ({D['dur']:.2f}h × R$ {BRn(HORA)})",-D["APRE"],CUR,"",None),
     ("RESULTADO DA LIVE",RES,CUR,veredito,"V" if RES>0 else "R"),
    ]:
        C(ws,r,1,k,BOLD)
        C(ws,r,2,v,GF if fn=="V" else (RF if fn=="R" or (isinstance(v,(int,float)) and v<0) else None),fmt=fm)
        C(ws,r,3,nt,MUTF,al=Lw)
        if fn in("V","R"):
            fl=OKF if fn=="V" else ALERT
            for c in (1,2,3): ws.cell(r,c).fill=fl
            ws.cell(r,1).font=BOLD; ws.cell(r,2).font=GF if fn=="V" else RF
        ws.row_dimensions[r].height=30; r+=1
    band(ws,r0,r-1,3); r+=1
    C(ws,r,1,"A SAÚDE DA MARGEM EM UM PARÁGRAFO",H2); r+=1
    p=(f"O cliente pagou R$ {BRn(D['PAGO'])} pelas {QTY} peças; o TikTok subsidiou mais R$ {BRn(D['SUBS'])} em cupom, que volta para a loja. "
       f"A receita de lista, base de toda taxa e de toda margem, foi de R$ {BRn(REV)} (R$ {BRn(REV/QTY)} por peça). "
       f"Com settlement de {SR*100:.2f}% e CPV de R$ {BRn(CPV)}, cada peça deixou R$ {BRn(D['CONTRIB']/QTY)} de contribuição — R$ {BRn(D['CONTRIB'])} no total. "
       f"Contra isso entraram R$ {BRn(ADS)} de mídia e R$ {BRn(D['APRE'])} de apresentadora. "
       f"Resultado: R$ {BRn(RES)}, ou R$ {BRn(RES/D['dur'])} por hora no ar.")
    if pico:
        p+=(f" E há um endereço claro para o que pesou: a hora das {pico['h']:02d}:00 consumiu R$ {BRn(pico['c'])}, "
            f"{pico['share']*100:.0f}% de toda a mídia desta live, a um CPA de R$ {BRn(pico['cpa'])} contra R$ {BRn(pico['cpa_base'])} nas demais horas.")
    r=nota(ws,r,p,7,92,BOLD); r+=1
    if pico:
        C(ws,r,1,"O NÚMERO QUE EXPLICA A LIVE INTEIRA",H2); r+=1
        hdr(ws,r,["","Demais horas (base)",f"Hora {pico['h']:02d}:00","Diferença"],[34,26,20,26]); r+=1; r0=r
        for k,a,b,fm in [("Gasto de mídia",pico["bc"],pico["c"],CUR),("Pedidos",pico["bp"],pico["p"],INT),
                         ("CPA",pico["cpa_base"],pico["cpa"],CUR)]+(
                         [("Custo por live view",pico["cv_base"],pico["cv"],N4)] if pico["cv"] else []):
            C(ws,r,1,k,BOLD); C(ws,r,2,a,fmt=fm); C(ws,r,3,b,RF,fmt=fm)
            C(ws,r,4,f"{b/a:.1f}× maior" if a else "—",MUTF); r+=1
        band(ws,r0,r-1,4); r+=1
        if pico["cpam"]>0:
            r=nota(ws,r,(f"Cada pedido A MAIS na hora das {pico['h']:02d}:00 custou R$ {BRn(pico['cpam'])} e vale R$ {BRn(D['CPED'])} de contribuição — "
              f"destruiu R$ {BRn(pico['cpam']-D['CPED'])} cada. É a curva de saturação da live medida DENTRO de uma única transmissão: "
              f"o inventário de audiência não cresce na velocidade do orçamento."),7,44,RF)
        r=nota(ws,r,(f"CONTRAFACTUAL: no CPA das demais horas, aquela hora teria custado R$ {BRn(pico['cpa_base']*pico['p'])} "
          f"em vez de R$ {BRn(pico['c'])}. A live fecharia em R$ {BRn(RES+pico['exc'])}."),7,34,GF)
    else:
        r=nota(ws,r,"✓ Nenhuma hora destoou do padrão de CPA — a entrega de mídia ficou estável durante a live inteira.",7,30,GF)

    # ═══ 2 · CURVA HORÁRIA ═══
    ws=wb.create_sheet("Curva horária"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"FUNIL E TRÁFEGO HORA A HORA",H1)
    C(ws,2,1,"Granularidade de 1 HORA — é o piso da GMV Max Report API (stat_time_hour). 15 minutos não existe na API.",MUTF)
    r=4
    hdr(ws,r,["Hora","Gasto","Receita atrib.","Pedidos","ROAS","CPA","Live views","Custo/view","Preço mediano"],
        [10,13,15,10,10,11,12,12,14]); r+=1; r0=r
    for h in horas:
        c,rv,pp,v=LIVE[h]; mau=bool(pico and h==pico["h"])
        C(ws,r,1,f"{h:02d}:00",BOLD,al=Cc); C(ws,r,2,c,RF if mau else None,fmt=CUR)
        C(ws,r,3,rv,fmt=CUR); C(ws,r,4,pp,fmt=INT)
        C(ws,r,5,rv/c if c else 0,RF if mau else GF,fmt=X1); C(ws,r,6,c/pp if pp else 0,RF if mau else None,fmt=CUR)
        C(ws,r,7,v,fmt=INT); C(ws,r,8,c/v if v else 0,RF if mau else None,fmt=N4)
        C(ws,r,9,D["prh"][h],fmt=CUR)
        if mau:
            for cc in range(1,10): ws.cell(r,cc).fill=ALERT
        r+=1
    band(ws,r0,r-1,9)
    tp=sum(LIVE[h][2] for h in horas); tv=sum(LIVE[h][3] for h in horas)
    C(ws,r,1,"TOTAL",BOLD,fill=TOTF); C(ws,r,2,ADS,BOLD,fmt=CUR,fill=TOTF); C(ws,r,3,D["REC"],BOLD,fmt=CUR,fill=TOTF)
    C(ws,r,4,tp,BOLD,fmt=INT,fill=TOTF); C(ws,r,5,D["REC"]/ADS if ADS else 0,BOLD,fmt=X1,fill=TOTF)
    C(ws,r,6,ADS/tp if tp else 0,BOLD,fmt=CUR,fill=TOTF); C(ws,r,7,tv,BOLD,fmt=INT,fill=TOTF)
    for cc in (8,9): ws.cell(r,cc).fill=TOTF
    rT=r; r+=2
    ch=LineChart(); ch.title="CPA por hora"; ch.height=8; ch.width=20
    ch.add_data(Reference(ws,min_col=6,min_row=r0-1,max_row=rT-1),titles_from_data=True)
    ch.set_categories(Reference(ws,min_col=1,min_row=r0,max_row=rT-1))
    ws.add_chart(ch,f"A{r}"); r+=17
    C(ws,r,1,"O LEILÃO INFLACIONOU DURANTE A TRANSMISSÃO?",H2); r+=1
    if pico and pico["cv"] and pico["cv_base"]:
        r=nota(ws,r,(f"O preço do tráfego (custo por live view) foi R$ {BRn(pico['cv_base'],4)} nas horas normais e R$ {BRn(pico['cv'],4)} "
          f"na hora das {pico['h']:02d}:00 — {pico['cv']/pico['cv_base']:.1f}× mais caro — e voltou ao normal depois. "
          "Um leilão que inflaciona por concorrência não desinflaciona em uma hora. O que sobe e desce assim é a própria curva de entrega: "
          "ao despejar orçamento na mesma janela, o sistema compra audiência progressivamente pior para gastar a verba."),7,46)
        pc=[(h,PROD[h]) for h in horas if PROD[h][0]>1]
        if pc:
            det=" · ".join(f"{h:02d}h R$ {BRn(v[0])} (CPA {BRn(v[0]/v[2]) if v[2] else '—'})" for h,v in pc)
            r=nota(ws,r,("PROVA DE CONTROLE: as campanhas de PRODUTO rodaram nas mesmas horas — "+det+
              ". Se o leilão do TikTok tivesse inflacionado, elas teriam sentido junto. O evento é da campanha de live."),7,44,BOLD)
    else:
        r=nota(ws,r,"Não houve hora com preço de tráfego fora da curva. A entrega ficou estável.",7,30)
    r+=1
    C(ws,r,1,"TRÁFEGO PAGO x ORGÂNICO NA RETENÇÃO",H2); r+=1
    r=nota(ws,r,"❌ NÃO MEDIDO. A separação pago/orgânico e a retenção (views > 1 min) só existem no export do Seller Center "
     "(performance_detail). A API de GMV Max não expõe impressões, retenção nem origem de tráfego — só live_views atribuídas.",7,38,RF)

    # ═══ 3 · POR PRODUTO ═══
    ws=wb.create_sheet("Por produto"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"PERFORMANCE POR PRODUTO",H1)
    C(ws,2,1,"Peças PAGAS na janela da live, por REF-base (o sufixo do SKU é o tamanho). Contribuição = receita de LISTA/peça × settlement − CPV.",MUTF)
    r=4
    C(ws,r,1,"RANKING POR RECEITA",H2); r+=1
    hdr(ws,r,["#","REF","Produto","Tipo","Peças","% das peças","Receita de lista","Pago/peça","Lista/peça","Contrib/peça","CONTRIBUIÇÃO"],
        [5,10,40,11,8,11,15,11,11,12,15]); r+=1; r0=r
    srt=sorted(D["g"].items(),key=lambda x:-x[1][1])
    for i,(b,z) in enumerate(srt,1):
        lp=z[1]/z[0] if z[0] else 0; cpc=lp*SR-CPV
        C(ws,r,1,i,al=Cc); C(ws,r,2,b,BOLD); C(ws,r,3,z[4],al=Lw)
        C(ws,r,4,"HERO" if b in HERO else "não-hero",BOLD if b in HERO else None,al=Cc)
        C(ws,r,5,z[0],fmt=INT); C(ws,r,6,z[0]/QTY,fmt=PCT); C(ws,r,7,z[1],fmt=CUR)
        C(ws,r,8,z[5]/z[0] if z[0] else 0,fmt=CUR); C(ws,r,9,lp,fmt=CUR)
        C(ws,r,10,cpc,GF if cpc>0 else RF,fmt=CUR); C(ws,r,11,cpc*z[0],GF if cpc>0 else RF,fmt=CUR)
        if i<=3:
            for cc in range(1,12): ws.cell(r,cc).fill=OKF
        r+=1
    band(ws,r0,r-1,11)
    ws.conditional_formatting.add(f"E{r0}:E{r-1}",DataBarRule(start_type="num",start_value=0,end_type="max",color=RHODE))
    C(ws,r,1,"TOTAL",BOLD,fill=TOTF); C(ws,r,5,QTY,BOLD,fmt=INT,fill=TOTF)
    C(ws,r,7,REV,BOLD,fmt=CUR,fill=TOTF); C(ws,r,8,D["PAGO"]/QTY,BOLD,fmt=CUR,fill=TOTF)
    C(ws,r,9,REV/QTY,BOLD,fmt=CUR,fill=TOTF); C(ws,r,11,D["CONTRIB"],BOLD,fmt=CUR,fill=TOTF)
    for cc in (2,3,4,6,10): ws.cell(r,cc).fill=TOTF
    r+=2
    hq,hv,hc=D["hq"],D["hv"],D["hc"]
    if hq and QTY-hq:
        C(ws,r,1,"HERO x NÃO-HERO",H2); r+=1
        hdr(ws,r,["Grupo","Peças","% peças","Receita de lista","Lista/peça","Contrib/peça","CONTRIBUIÇÃO"],[18,10,11,16,13,13,16]); r+=1; r0=r
        for lb,q,v,c in [("HERO (516/525/527)",hq,hv,hc),("não-hero",QTY-hq,REV-hv,D["CONTRIB"]-hc)]:
            C(ws,r,1,lb,BOLD); C(ws,r,2,q,fmt=INT); C(ws,r,3,q/QTY,fmt=PCT); C(ws,r,4,v,fmt=CUR)
            C(ws,r,5,v/q,fmt=CUR); C(ws,r,6,c/q,GF if c/q>0 else RF,fmt=CUR); C(ws,r,7,c,fmt=CUR); r+=1
        band(ws,r0,r-1,7); r+=1
        ch_,cn=hc/hq,(D["CONTRIB"]-hc)/(QTY-hq)
        if cn>ch_:
            r=nota(ws,r,(f"INVERSÃO: o hero é {hq/QTY*100:.0f}% das peças e entrega R$ {BRn(ch_)} de contribuição por peça. "
              f"O não-hero entrega R$ {BRn(cn)} — {cn/ch_:.1f}× mais. Motivo: o hero saiu a R$ {BRn(hv/hq)} de lista e o não-hero a "
              f"R$ {BRn((REV-hv)/(QTY-hq))}. Com CPV fixo, a diferença de preço vai quase inteira para a contribuição."),7,44,BOLD)
        else:
            r=nota(ws,r,f"✓ O hero entrega R$ {BRn(ch_)} por peça contra R$ {BRn(cn)} do não-hero — sem inversão de margem nesta live.",7,30,GF)
    r+=1
    C(ws,r,1,"CTOR POR PRODUTO",H2); r+=1
    r=nota(ws,r,"❌ NÃO MEDIDO — e não é possível medir. As métricas impressions, clicks, ctr, cpm, cpc, product_impressions e "
     "conversion_rate são todas rejeitadas pelo endpoint /gmv_max/report/get/ ('Invalid metric'). A única métrica de tráfego aceita é "
     "live_views. CTOR existe no export do Seller Center, mas só no nível da SALA — nunca por SKU.",7,46,RF)

    # ═══ 4 · GRADE ═══
    ws=wb.create_sheet("Grade de tamanho"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"FURO DE GRADE — onde o produto chamou atenção e não converteu",H1)
    C(ws,2,1,"Peças pagas por tamanho. Um zero ENTRE dois tamanhos que vendem é assinatura de ruptura, não de demanda.",MUTF)
    r=4
    hdr(ws,r,["REF","Tipo"]+[f"Tam {t}" for t in TAM]+["Total","Buracos no MEIO da curva"],[10,11]+[8]*7+[9,34]); r+=1; r0=r
    for b,z in srt[:10]:
        d=z[3]; C(ws,r,1,b,BOLD); C(ws,r,2,"HERO" if b in HERO else "não-hero",al=Cc)
        idx=[i for i,tm in enumerate(TAM) if d.get(tm,0)>0]
        meio=[TAM[i] for i in range(min(idx),max(idx)+1) if d.get(TAM[i],0)==0] if idx else []
        for i,tm in enumerate(TAM):
            v=d.get(tm,0); cel=C(ws,r,3+i,v,fmt=INT,al=Cc)
            if v==0 and tm in meio: cel.fill=ALERT; cel.font=RF
            elif v>0: cel.fill=OKF
        C(ws,r,10,z[0],BOLD,fmt=INT); C(ws,r,11,", ".join(meio) if meio else "—",RF if meio else MUTF,al=Lw)
        r+=1
    band(ws,r0,r-1,11); r+=2
    C(ws,r,1,"LEITURA",H2); r+=1
    if D["furos"]:
        for b,meio,q in D["furos"]:
            r=nota(ws,r,f"⚠ {b} — vendeu {q} peças mas ZERO nos tamanhos {', '.join(meio)}, que ficam NO MEIO da curva de vendas. "
              "Tamanhos vizinhos venderam normalmente. Demanda não some só no meio: o padrão é ruptura de grade.",7,32,RF)
    else:
        r=nota(ws,r,"✓ Nenhum furo no meio da curva nos 10 produtos mais vendidos — a grade cobriu a demanda.",7,28,GF)
    r=nota(ws,r,"Método: inferência a partir do padrão de vendas, não leitura de estoque. Para confirmar, cruzar com o saldo por SKU "
     "no Seller Center — se o tamanho tinha saldo e não vendeu, aí é problema de oferta/exposição, não de ruptura.",7,32)

    # ═══ 5 · GMV MAX ═══
    ws=wb.create_sheet("Comportamento GMV Max"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"COMO O ALGORITMO SE COMPORTOU",H1)
    r=3
    hdr(ws,r,["Hora","Gasto","ROI entregue","CPA","Custo/view","Live views"],[9,13,13,11,12,12]); r+=1; r0=r
    for h in horas:
        c,rv,pp,v=LIVE[h]; mau=bool(pico and h==pico["h"])
        C(ws,r,1,f"{h:02d}:00",BOLD,al=Cc); C(ws,r,2,c,RF if mau else None,fmt=CUR)
        C(ws,r,3,rv/c if c else 0,RF if mau else GF,fmt=X1); C(ws,r,4,c/pp if pp else 0,fmt=CUR)
        C(ws,r,5,c/v if v else 0,fmt=N4); C(ws,r,6,v,fmt=INT); r+=1
    band(ws,r0,r-1,6); r+=2
    rois=[(h,LIVE[h][1]/LIVE[h][0]) for h in horas if LIVE[h][0]>1]
    if rois:
        disp=max(x[1] for x in rois)/min(x[1] for x in rois) if min(x[1] for x in rois)>0 else 0
        C(ws,r,1,"O QUE A DISPERSÃO DO ROI DIZ",H2); r+=1
        r=nota(ws,r,(f"O ROI entregue variou de {min(x[1] for x in rois):.2f}× a {max(x[1] for x in rois):.2f}× entre as horas desta live "
          f"({disp:.1f}× de dispersão). Uma meta de ROI é um TETO de agressividade de lance: quanto mais alta, menos o sistema se permite "
          "pagar por impressão. Horas MUITO acima da meta indicam que ele estava sendo conservador e deixou volume na mesa; "
          "horas abaixo indicam que ele pagou caro demais para gastar a verba."),7,46)
    r=nota(ws,r,("⚠ RESSALVA DE CAUSALIDADE: não existe log de alterações na API (11 endpoints testados, todos 404), e o campo modify_time "
     "não serve — ele registra varreduras do próprio TikTok, não ações humanas. Metas de ROI e tetos de verba produzem o MESMO efeito "
     "observável, então não são separáveis pelo dado. Para fechar causalidade, anote horário + o que mudou a cada intervenção."),7,44,RF)
    r+=1
    if corte:
        C(ws,r,1,"DESATIVAÇÃO DE PROMOÇÃO — detectada pelo preço",H2); r+=1
        A,Bq=corte["A"],corte["B"]
        hdr(ws,r,["","Antes do corte","Depois do corte","Variação"],[26,20,20,16]); r+=1; r0=r
        for lb,a,b,fm in [("Peças por minuto",A["pm"],Bq["pm"],N2),("Contribuição por minuto",A["cm"],Bq["cm"],CUR),
                          ("Peças no período",A["q"],Bq["q"],INT),("Minutos",corte["ma"],corte["md"],INT)]:
            C(ws,r,1,lb,BOLD); C(ws,r,2,a,fmt=fm); C(ws,r,3,b,RF if b<a else GF,fmt=fm)
            C(ws,r,4,(b/a-1) if a else 0,RF if b<a else GF,fmt='+0.0%'); r+=1
        band(ws,r0,r-1,4); r+=1
        r=nota(ws,r,(f"Detectado em ≈{corte['quando'].strftime('%H:%M')}: o PISO de preço subiu e não voltou, simultaneamente em "
          f"{corte['n_produtos']} produtos. Depois do corte a velocidade foi de {A['pm']:.2f} para {Bq['pm']:.2f} peças/min "
          f"e a contribuição por minuto de R$ {BRn(A['cm'])} para R$ {BRn(Bq['cm'])}."),7,40,BOLD)
        if corte["custo"]>0:
            r=nota(ws,r,(f"Custo de oportunidade estimado: R$ {BRn(corte['custo'])} nos {corte['md']:.0f} minutos finais. "
              "⚠ É ESTIMATIVA: audiência de live decai perto do fim e a mídia costuma cair junto, então parte da queda não é da promoção."),7,36,RF)
    else:
        r=nota(ws,r,"Nenhum corte de promoção detectado: o piso de preço por produto ficou estável durante a live.",7,28)

    # ═══ 6 · PAGAMENTO ═══
    ws=wb.create_sheet("Vazamento de pagamento"); ws.sheet_view.showGridLines=False
    stt=D["stt"]; tq=sum(v[0] for v in stt.values())
    ruim=sum(v[0] for k,v in stt.items() if k in("UNPAID","CANCELLED"))
    C(ws,1,1,f"{ruim/tq*100:.1f}% DAS PEÇAS PEDIDAS NÃO VIRARAM RECEITA" if tq else "STATUS DOS PEDIDOS",H1)
    C(ws,2,1,f"Status medido em {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')} BRT, logo após a live. Pedidos ainda podem mudar de status.",MUTF)
    r=4
    hdr(ws,r,["Status","Peças","% das peças","Valor pago","Situação"],[24,10,13,14,52]); r+=1; r0=r
    EX={"AWAITING_COLLECTION":"✅ pago, aguardando coleta","AWAITING_SHIPMENT":"✅ pago, aguardando envio",
        "IN_TRANSIT":"✅ pago, em trânsito","DELIVERED":"✅ entregue","COMPLETED":"✅ concluído",
        "ON_HOLD":"⚠️ retido","UNPAID":"❌ pedido feito e NÃO pago","CANCELLED":"❌ cancelado"}
    for s,(q,v) in sorted(stt.items(),key=lambda x:-x[1][0]):
        bad=s in("UNPAID","CANCELLED")
        C(ws,r,1,s,BOLD); C(ws,r,2,q,RF if bad else None,fmt=INT); C(ws,r,3,q/tq,fmt=PCT)
        C(ws,r,4,v,fmt=CUR); C(ws,r,5,EX.get(s,""),RF if bad else MUTF,al=Lw)
        if bad:
            for cc in range(1,6): ws.cell(r,cc).fill=ALERT
        r+=1
    band(ws,r0,r-1,5); r+=2
    if D["cperda"]>0:
        rel=f" — {D['cperda']/RES:.1f}× o resultado inteiro da live" if RES>0 else ""
        r=nota(ws,r,(f"A contribuição travada nos pedidos NÃO PAGOS é de R$ {BRn(D['cperda'])}{rel}. "
          "A mídia por esses pedidos JÁ FOI PAGA, independentemente de virarem receita."),7,36,RF)
    r=nota(ws,r,("⏳ REMEDIR EM 48H. Parte dos UNPAID pode ser só atraso de pagamento — mas na live de 10/09, medida 20h depois, "
     "apenas 11% saíram do limbo e METADE virou cancelamento. Trate como perda provável até a remedição provar o contrário."),7,36)

    # ═══ 7 · PLANO ═══
    ws=wb.create_sheet("Plano de ação"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"O QUE FAZER NA PRÓXIMA LIVE",H1)
    C(ws,2,1,"Gerado dos achados desta live, ordenado por R$ em jogo.",MUTF)
    r=4
    acoes=[]
    if pico:
        acoes.append((f"Teto de gasto por hora (~R$ {BRn(pico['bc']*1.2,0)}) na campanha de live",
          f"A hora das {pico['h']:02d}:00 gastou R$ {BRn(pico['c'])} ({pico['share']*100:.0f}% da mídia da live) a um CPA de R$ {BRn(pico['cpa'])}, "
          f"contra R$ {BRn(pico['cpa_base'])} nas demais. Um teto nesse patamar teria evitado o estouro sem tocar nas horas boas.",pico["exc"]))
    if corte and corte["custo"]>0:
        acoes.append(("Manter a promoção até o FIM da live",
          f"Antes do corte: {corte['A']['pm']:.2f} peças/min e R$ {BRn(corte['A']['cm'])} de contribuição/min. Depois: {corte['B']['pm']:.2f} e R$ {BRn(corte['B']['cm'])}. "
          "O ganho de margem por peça não pagou a perda de ritmo.",corte["custo"]))
    if D["cperda"]>0:
        acoes.append(("Atacar os pedidos não pagos",
          f"{sum(r_['qty'] for r_ in D['inw'] if r_['status']=='UNPAID')} peças pedidas e não pagas seguram R$ {BRn(D['cperda'])} de contribuição. "
          "A mídia por elas já foi paga. Remedir em 48h e atacar a causa (prazo, meio de pagamento, frete).",D["cperda"]))
    if D["furos"]:
        acoes.append(("Checar saldo dos tamanhos centrais antes de fixar o pin",
          f"{len(D['furos'])} dos produtos mais vendidos têm buraco NO MEIO da curva de tamanhos "
          f"({'; '.join(b+' sem '+'/'.join(m) for b,m,_ in D['furos'][:3])}). Fixar produto com grade furada gasta palco em algo que não pode converter.","sem dado"))
    ch_=D["hc"]/D["hq"] if D["hq"] else 0; cn=(D["CONTRIB"]-D["hc"])/(QTY-D["hq"]) if QTY-D["hq"] else 0
    if ch_ and cn>ch_*1.2:
        acoes.append(("Rever o preço de lista do hero",
          f"O hero deixa R$ {BRn(ch_)} por peça contra R$ {BRn(cn)} do não-hero. Subir a lista em R$ 5 adicionaria "
          f"~R$ {BRn(5*SR*D['hq'],0)} de contribuição no volume desta live, sem tocar em mídia.",5*SR*D["hq"]))
    acoes.sort(key=lambda x:-(x[2] if isinstance(x[2],(int,float)) else 0))
    hdr(ws,r,["#","Ação","O número que sustenta","Em jogo"],[5,34,72,16]); r+=1; r0=r
    for i,(a,p_,v) in enumerate(acoes,1):
        C(ws,r,1,i,BOLD,al=Cc); C(ws,r,2,a,BOLD,al=Lw); C(ws,r,3,p_,MUTF,al=Lw)
        if isinstance(v,str): C(ws,r,4,v,MUTF,al=Cc)
        else: C(ws,r,4,v,GF,fmt=CUR)
        ws.row_dimensions[r].height=62; r+=1
    if not acoes:
        C(ws,r,1,"—",al=Cc); C(ws,r,2,"Nenhum problema material detectado nesta live.",GF,al=Lw); r+=1
    band(ws,r0,r-1,4); r+=2
    emjogo=sum(v for _,_,v in acoes if isinstance(v,(int,float)))
    if emjogo>0:
        r=nota(ws,r,(f"SÍNTESE: a live fechou em R$ {BRn(RES)}. Os itens acima somam R$ {BRn(emjogo)} em jogo — "
          f"{emjogo/abs(RES):.1f}× o resultado, se RES != 0. O dinheiro raramente está em vender mais: está em não desmontar o que funciona."
          ),7,40,BOLD)

    # ═══ 8 · PREMISSAS ═══
    ws=wb.create_sheet("Premissas"); ws.sheet_view.showGridLines=False
    C(ws,1,1,"COMO ISTO FOI MEDIDO — E O QUE NÃO DEU PARA MEDIR",H1)
    r=3
    C(ws,r,1,"✅ DADO REAL",H2); r+=1
    for tx in [f"Curva HORÁRIA — GMV Max Report API, dimensões stat_time_hour × campaign_id, dia {D['dia']}.",
     f"GMV, peças e clientes da sala — /analytics/202509/shop_lives/performance (live_attr), sala {D['room']}.",
     "SKU, tamanho, preço pago e status — Orders API (pedidos_sku + pedido_pagamento).",
     f"Receita de LISTA = sub_total + platform_discount, rateado do pedido para o item. Calculado por lib/receita.py — nunca por fator médio.",
     f"Régua: settlement {SR} · CPV R$ {BRn(CPV)} · apresentadora R$ {BRn(HORA)}/hora.",
     f"Janela: {ini.strftime('%H:%M')}–{fim.strftime('%H:%M')} BRT, de live_attr. Só pedidos dentro dela entram."]:
        r=nota(ws,r,"✓ "+tx,7,28)
    r+=1
    C(ws,r,1,"❌ PEDIDO E NÃO DISPONÍVEL — testado, não presumido",H2); r+=1
    hdr(ws,r,["Métrica","Status","Por quê"],[30,18,74]); r+=1; r0=r
    for m,s,w in [("Curva de 15 em 15 min","❌ não existe","stat_time_hour é a menor granularidade da API."),
     ("CPM / CPC","❌ não existe","Rejeitadas pelo endpoint: 'Invalid metric'."),
     ("Impressões","❌ não existe","Rejeitada. Só live_views é aceita."),
     ("CTR / CTOR","❌ não existe","Rejeitadas na API. No export do Seller Center só por SALA, nunca por SKU."),
     ("ATC (add-to-cart)","❌ não existe","Nenhuma métrica de carrinho é exposta."),
     ("PCU (pico de simultâneos)","❌ não existe","Nem na API nem no export. Só na UI ao vivo."),
     ("Pago x orgânico","❌ não existe","A API só reporta o atribuído à campanha."),
     ("Log de alterações","❌ não existe","11 endpoints testados, todos 404. modify_time é varredura do TikTok."),
     ("Retenção (views > 1 min)","⏳ possível","Está no export do Seller Center, que não é gerado automaticamente.")]:
        C(ws,r,1,m,BOLD,al=Lw); C(ws,r,2,s,RF if "❌" in s else None,al=Cc); C(ws,r,3,w,MUTF,al=Lw)
        ws.row_dimensions[r].height=28; r+=1
    band(ws,r0,r-1,3); r+=2
    r=nota(ws,r,("⚠ LIMITE DE ATRIBUIÇÃO: a análise por SKU usa a JANELA DE TEMPO da live como recorte, porque nenhuma fonte liga pedido a "
     f"room_id no nível de SKU. Isso inclui pedidos da loja que teriam acontecido sem a live e exclui os da live que fecharam depois do fim. "
     f"Tamanho do viés nesta live: o pago na janela é R$ {BRn(D['PAGO'])} e o GMV que a API atribui à sala é R$ {BRn(L['gmv'] or 0)} "
     f"({abs(D['PAGO']/(L['gmv'] or 1)-1)*100:.1f}% de diferença)."),7,46)
    wb.calculation.fullCalcOnLoad=True
    return wb

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--room",required=True)
    ap.add_argument("--saida")
    a=ap.parse_args()
    D=montar(a.room)
    wb=render(D)
    nome=f"Relatorio Live {D['ini'].strftime('%d-%m')} {D['ini'].strftime('%Hh%M')}_{D['dia']}.xlsx"
    out=a.saida or os.path.join(ROOT,"relatorios",D["dia"][:7],nome)
    os.makedirs(os.path.dirname(out),exist_ok=True)
    wb.save(out)
    print(f"OK {out}")
    print(f"   resultado R$ {D['RES']:,.2f} · contrib R$ {D['CONTRIB']:,.2f} · ads R$ {D['ADS']:,.2f} · {D['QTY']} peças")
    if D["pico"]: print(f"   ⚠ estouro detectado às {D['pico']['h']:02d}:00 — excesso R$ {D['pico']['exc']:,.2f}")
    if D["corte"]: print(f"   ⚠ corte de promo detectado às {D['corte']['quando'].strftime('%H:%M')} — custo R$ {D['corte']['custo']:,.2f}")
    return out

if __name__=="__main__":
    main()
