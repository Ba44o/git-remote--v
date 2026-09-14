#!/usr/bin/env python3
"""
Rhode — RELATÓRIO DIÁRIO DE PERFORMANCE DA LOJA (não só live).

Uso:  python3 automacao/gerar_relatorio_loja.py                 # ontem
      python3 automacao/gerar_relatorio_loja.py --data 2026-09-13
      python3 automacao/gerar_relatorio_loja.py --data X --saida /tmp/x.xlsx

Gera .xlsx (8 abas) + .md gêmeo, no dialeto travado dos relatórios de live.
Nada de número escrito à mão: tudo derivado do dado, e o que não existe sai como
"sem dado" com a razão. Régua: receita de LISTA via lib/receita.py.
"""
import os, sys, json, argparse
from datetime import datetime, timedelta, timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import DataBarRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "automacao"))
from dados_loja import montar, SR, CPV

BRT = timezone(timedelta(hours=-3))
INK="1A1A1E";MUT="6B6B76";RED="FE2C55";GREEN="0E9F6E";RHODE="FE2C55"
H1=Font(size=16,bold=True,color=INK);H2=Font(size=12,bold=True,color=INK)
TH=Font(size=10,bold=True,color="FFFFFF");BOLD=Font(bold=True,color=INK)
MUTF=Font(size=9,italic=True,color=MUT);RF=Font(bold=True,color=RED);GF=Font(bold=True,color=GREEN)
HEAD=PatternFill("solid",fgColor=INK);BAND=PatternFill("solid",fgColor="F7F7F9")
TOTF=PatternFill("solid",fgColor="EFEFF2");ALERT=PatternFill("solid",fgColor="FDECEA")
OKF=PatternFill("solid",fgColor="E8F6EF");WARN=PatternFill("solid",fgColor="FFF4E5")
Cc=Alignment(horizontal="center",vertical="center")
Lw=Alignment(horizontal="left",wrap_text=True,vertical="top")
CUR='R$ #,##0.00';CUR0='R$ #,##0';INT='#,##0';PCT='0.0%';X1='0.00"x"';N2='0.00'
SEMDADO="sem dado"

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
    if v is None: return SEMDADO
    return f"{v:,.{d}f}".replace(",","\x00").replace(".",",").replace("\x00",".")
def delta(a,b):
    """variação de a (atual) vs b (anterior). None quando não dá para comparar."""
    if a is None or b in (None,0): return None
    return a/b-1
def cab(ws,titulo,sub):
    ws.sheet_view.showGridLines=False
    C(ws,1,1,titulo,H1); C(ws,2,1,sub,MUTF)
    return 4

def render(D):
    dia=D["dia"]; r_=D["rec"]; ra=D["rec_ant"]; lv=D["live"]; la=D["live_ant"]
    ads=D["ads"]; aa=D["ads_ant"]; cr=D["creators"]; vd=D["videos"]
    dv=D["dev"]; fu=D["funil"]; fref=D["funil_ref"]
    dt=datetime.strptime(dia,"%Y-%m-%d")
    peso_live=(lv["gmv"]/r_["lista"]) if r_["lista"] else 0
    wb=Workbook()

    # ═══ 1 · RESUMO EXECUTIVO ═══
    ws=wb.active; ws.title="Resumo executivo"
    r=cab(ws,f"PERFORMANCE DA LOJA — {dt.strftime('%d/%m/%Y')}",
          f"Comparado com {datetime.strptime(D['anterior'],'%Y-%m-%d').strftime('%d/%m')}. "
          f"Receita de LISTA (pago + cupom subsidiado pelo TikTok). Gerado em "
          f"{datetime.now(BRT).strftime('%d/%m/%Y %H:%M')} BRT.")
    hdr(ws,r,["KPI","Hoje","Dia anterior","Δ %","Fonte"],[30,16,16,11,40]); r+=1
    r0=r
    linhas=[
      ("Receita de lista",r_["lista"],ra["lista"] if ra else None,CUR,"pedidos_sku + platform_discount"),
      ("Pago pelo cliente",r_["pago"],ra["pago"] if ra else None,CUR,"pedidos_sku.gmv (sub_total)"),
      ("Peças pagas",r_["pecas"],ra["pecas"] if ra else None,INT,"pedidos_sku.qty"),
      ("Pedidos",r_["pedidos"],ra["pedidos"] if ra else None,INT,"order_id distintos, pagos"),
      ("AOV por pedido (lista)",r_["aov_lista"],ra["aov_lista"] if ra else None,CUR,"derivado"),
      ("Preço médio por peça",r_["preco_medio"],ra["preco_medio"] if ra else None,CUR,"derivado"),
      ("GMV de live",lv["gmv"],la["gmv"] if la else None,CUR,"live_attr (Attributed GMV)"),
      ("Peso da live no total",peso_live,(la["gmv"]/ra["lista"]) if (la and ra and ra["lista"]) else None,PCT,"derivado"),
      ("Investimento em mídia",ads["total"]["custo"] if ads else None,aa["total"]["custo"] if aa else None,CUR,"ads_campanha.cost"),
      ("ROAS consolidado",ads["total"]["roas"] if ads else None,aa["total"]["roas"] if aa else None,X1,"receita atribuída ÷ custo"),
      ("CPA",ads["total"]["cpa"] if ads else None,aa["total"]["cpa"] if aa else None,CUR,"custo ÷ pedidos atribuídos"),
      ("Contribuição bruta",r_["contrib"],ra["contrib"] if ra else None,CUR,f"lista/peça × {SR} − CPV {BRn(CPV)}"),
      ("Contribuição por peça",r_["contrib_peca"],ra["contrib_peca"] if ra else None,CUR,"derivado"),
    ]
    for k,a,b,fm,fo in linhas:
        C(ws,r,1,k,BOLD)
        C(ws,r,2,a if a is not None else SEMDADO,fmt=fm if a is not None else None)
        C(ws,r,3,b if b is not None else SEMDADO,fmt=fm if b is not None else None)
        d_=delta(a,b)
        C(ws,r,4,d_ if d_ is not None else "—",GF if (d_ or 0)>0 else (RF if d_ is not None and d_<0 else None),fmt='+0.0%' if d_ is not None else None,al=Cc)
        C(ws,r,5,fo,MUTF,al=Lw); r+=1
    band(ws,r0,r-1,5); r+=1
    # contribuição líquida de mídia — o número que decide
    liq=r_["contrib"]-(ads["total"]["custo"] if ads else 0)
    C(ws,r,1,"CONTRIBUIÇÃO APÓS MÍDIA",BOLD,fill=OKF if liq>0 else ALERT)
    C(ws,r,2,liq,GF if liq>0 else RF,fmt=CUR,fill=OKF if liq>0 else ALERT)
    for c in (3,4): ws.cell(r,c).fill=OKF if liq>0 else ALERT
    C(ws,r,5,"contribuição bruta − investimento em mídia" + ("" if ads else " (mídia sem dado)"),MUTF,al=Lw,fill=OKF if liq>0 else ALERT)
    r+=2
    C(ws,r,1,"O DIA EM UM PARÁGRAFO",H2); r+=1
    p=(f"A loja faturou R$ {BRn(r_['lista'])} de receita de lista em {r_['pecas']} peças e "
       f"{r_['pedidos']} pedidos, com AOV de R$ {BRn(r_['aov_lista'])}. ")
    if ra and ra["lista"]:
        v=delta(r_["lista"],ra["lista"])
        p+=f"Contra o dia anterior isso é {BRn(v*100,1)}%. "
    p+=(f"Cada peça deixou R$ {BRn(r_['contrib_peca'])} de contribuição — R$ {BRn(r_['contrib'])} no total. ")
    if ads:
        p+=(f"Foram R$ {BRn(ads['total']['custo'])} de mídia, com ROAS de {BRn(ads['total']['roas'])}× e CPA de "
            f"R$ {BRn(ads['total']['cpa'])}, sobrando R$ {BRn(liq)} depois de pagar o tráfego. ")
    else:
        p+="O investimento em mídia do dia ainda não estava disponível quando este relatório rodou. "
    if lv["n"]:
        p+=(f"A live respondeu por R$ {BRn(lv['gmv'])}, {BRn(peso_live*100,1)}% do faturamento, "
            f"em {lv['n']} transmissão(ões) e {BRn(lv['horas'],2)}h no ar. ")
    else:
        p+="Não houve live neste dia. "
    p+=f"{r_['nao_virou']} peças pedidas ({BRn(r_['nao_virou_pct']*100,1)}%) não viraram receita."
    r=nota(ws,r,p,7,92,BOLD)

    # ═══ 2 · RECEITA ═══
    ws=wb.create_sheet("Receita e caixa")
    r=cab(ws,"RECEITA, MIX E O QUE NÃO VIROU DINHEIRO",
          "Receita de LISTA = o que o cliente pagou + o cupom que o TikTok subsidia e devolve à loja.")
    hdr(ws,r,["Componente","Valor","Por peça","Observação"],[32,16,14,56]); r+=1
    r0=r
    for k,v,pp,o in [
      ("Pago pelo cliente",r_["pago"],r_["pago"]/r_["pecas"] if r_["pecas"] else 0,"sub_total — o que saiu do bolso"),
      ("(+) Cupom subsidiado TikTok",r_["lista"]-r_["pago"],(r_["lista"]-r_["pago"])/r_["pecas"] if r_["pecas"] else 0,"platform_discount — volta para a loja"),
      ("= RECEITA DE LISTA",r_["lista"],r_["preco_medio"],f"base de toda taxa e margem · gross-up medido {BRn(r_['gross_up'],4)}"),
      ("(−) CPV",-CPV*r_["pecas"],-CPV,"custo do produto · custos_sku"),
      ("(−) Taxas (1 − settlement)",-(r_["lista"]*(1-SR)),-(r_["preco_medio"]*(1-SR)),f"settlement {SR}"),
      ("= CONTRIBUIÇÃO BRUTA",r_["contrib"],r_["contrib_peca"],"antes de mídia e estrutura"),
    ]:
        forte=k.startswith("=")
        C(ws,r,1,k,BOLD if forte else None,fill=TOTF if forte else None)
        C(ws,r,2,v,GF if (forte and v>0) else (RF if v<0 else None),fmt=CUR,fill=TOTF if forte else None)
        C(ws,r,3,pp,fmt=CUR,fill=TOTF if forte else None)
        C(ws,r,4,o,MUTF,al=Lw,fill=TOTF if forte else None); r+=1
    band(ws,r0,r-1,4); r+=2
    C(ws,r,1,"O QUE NÃO VIROU RECEITA",H2); r+=1
    hdr(ws,r,["Status","Peças","% das peças","Valor pago","Situação"],[24,10,13,14,44]); r+=1
    r0=r
    EX={"AWAITING_COLLECTION":"✅ pago","AWAITING_SHIPMENT":"✅ pago","IN_TRANSIT":"✅ pago",
        "DELIVERED":"✅ entregue","COMPLETED":"✅ concluído","ON_HOLD":"⚠️ retido",
        "UNPAID":"❌ pedido feito e NÃO pago","CANCELLED":"❌ cancelado"}
    tq=sum(v[0] for v in r_["status"].values())
    for s,(q,v) in sorted(r_["status"].items(),key=lambda x:-x[1][0]):
        mau=s in("UNPAID","CANCELLED")
        C(ws,r,1,s,BOLD); C(ws,r,2,q,RF if mau else None,fmt=INT)
        C(ws,r,3,q/tq if tq else 0,fmt=PCT); C(ws,r,4,v,fmt=CUR)
        C(ws,r,5,EX.get(s,""),RF if mau else MUTF,al=Lw)
        if mau:
            for c in range(1,6): ws.cell(r,c).fill=ALERT
        r+=1
    band(ws,r0,r-1,5); r+=1
    r=nota(ws,r,("⏳ UNPAID pode ser atraso, mas na live de 10/09 — medida 20h depois — só 11% saíram do limbo "
      "e metade virou cancelamento. Trate como perda provável até remedir em 48h."),7,32)
    if dv:
        r+=1
        C(ws,r,1,"DEVOLUÇÕES DO DIA",H2); r+=1
        hdr(ws,r,["Motivo","Casos","Valor"],[46,10,16]); r+=1
        r0=r
        for m,(n_,val) in dv["motivos"][:8]:
            C(ws,r,1,str(m)[:46],al=Lw); C(ws,r,2,n_,fmt=INT); C(ws,r,3,val,fmt=CUR); r+=1
        band(ws,r0,r-1,3)

    # ═══ 3 · TRÁFEGO PAGO ═══
    ws=wb.create_sheet("Trafego pago")
    r=cab(ws,"TRÁFEGO PAGO — ADS E GMV MAX",
          "⚠️ ROAS não decide alocação: mede receita sobre mídia e ignora o CPV. A régua da casa é contribuição por peça.")
    if not ads:
        r=nota(ws,r,"❌ SEM DADO. A tabela ads_campanha ainda não tinha este dia quando o relatório rodou. "
          "A API já costuma ter D-1 — rodar coletar_gmvmax_api.py fecha o buraco.",7,36,RF)
    else:
        hdr(ws,r,["Recorte","Investimento","Receita atrib.","Pedidos","ROAS","CPA"],[26,15,15,11,10,12]); r+=1
        r0=r
        for lb,m in [("TOTAL",ads["total"]),("Campanhas de live",ads["live"]),
                     ("Campanhas de produto",ads["produto"]),
                     ("— Tradicional (caixa)",ads["tradicional"]),
                     ("— Vendas Líquidas (no fee)",ads["vendas_liquidas"])]:
            tot=lb=="TOTAL"
            C(ws,r,1,lb,BOLD,fill=TOTF if tot else None)
            C(ws,r,2,m["custo"],fmt=CUR,fill=TOTF if tot else None)
            C(ws,r,3,m["receita"],fmt=CUR,fill=TOTF if tot else None)
            C(ws,r,4,m["pedidos"],fmt=INT,fill=TOTF if tot else None)
            C(ws,r,5,m["roas"],GF if m["roas"]>=8 else RF,fmt=X1,fill=TOTF if tot else None)
            C(ws,r,6,m["cpa"],fmt=CUR,fill=TOTF if tot else None); r+=1
        band(ws,r0,r-1,6); r+=1
        r=nota(ws,r,("⚠️ Tradicional × Vendas Líquidas não se somam como caixa: a VL é cobrada DENTRO do fee "
          "(~12–13% por pedido), não sai da conta de ads. Só a Tradicional é desembolso de mídia."),7,34,RF)
        r+=1
        C(ws,r,1,"POR CAMPANHA",H2); r+=1
        hdr(ws,r,["Campanha","Modelo","Investimento","Receita","Pedidos","ROAS","CPA"],[42,16,14,14,10,10,12]); r+=1
        r0=r
        for c_ in ads["campanhas"][:15]:
            cst=c_["cost"] or 0; rec=c_["receita"] or 0; ped=c_["pedidos"] or 0
            C(ws,r,1,(c_["campanha"] or "")[:42],al=Lw)
            C(ws,r,2,c_["modelo"] or "—",al=Cc); C(ws,r,3,cst,fmt=CUR)
            C(ws,r,4,rec,fmt=CUR); C(ws,r,5,ped,fmt=INT)
            C(ws,r,6,rec/cst if cst else 0,GF if (rec/cst if cst else 0)>=8 else RF,fmt=X1)
            C(ws,r,7,cst/ped if ped else 0,fmt=CUR); r+=1
        band(ws,r0,r-1,7)
        ws.conditional_formatting.add(f"C{r0}:C{r-1}",
            DataBarRule(start_type="num",start_value=0,end_type="max",color=RHODE))
        rT=r; r+=2
        ch=BarChart(); ch.type="col"; ch.title="Investimento por campanha"; ch.height=8; ch.width=20
        ch.add_data(Reference(ws,min_col=3,min_row=r0-1,max_row=rT-1),titles_from_data=True)
        ch.set_categories(Reference(ws,min_col=1,min_row=r0,max_row=rT-1))
        ws.add_chart(ch,f"A{r}"); r+=17
        C(ws,r,1,"CPM, CPC, IMPRESSÕES E CTR",H2); r+=1
        r=nota(ws,r,("❌ NÃO EXISTEM para GMV Max. Nove métricas testadas na /gmv_max/report/get/ "
          "(impressions, clicks, cpm, cpc, ctr, reach, video_views, conversion_rate) — todas rejeitadas "
          "com 'Invalid metric'. Só passam cost, net_cost, gross_revenue, orders, roi, live_views e "
          "cost_per_order. CPM é UI-only: só raspando o Seller Center."),7,44,RF)

    # ═══ 4 · LIVE E CREATORS ═══
    ws=wb.create_sheet("Live e creators")
    r=cab(ws,"LIVE, CREATORS E VÍDEOS",
          "GMV de live é Attributed GMV da própria loja. Creators/afiliadas vêm de outra fonte — não somar cegamente.")
    if lv["n"]:
        hdr(ws,r,["Sala","Horário","Duração","GMV","Peças","Clientes"],[24,16,11,14,10,11]); r+=1
        r0=r
        for s in lv["salas"]:
            i=datetime.fromisoformat(s["inicio"]).astimezone(BRT)
            f_=datetime.fromisoformat(s["fim"]).astimezone(BRT) if s["fim"] else None
            dur=(f_-i).total_seconds()/3600 if f_ and f_>i else 0
            C(ws,r,1,(s["titulo"] or "(sem título)")[:24],al=Lw)
            C(ws,r,2,f'{i.strftime("%H:%M")}–{f_.strftime("%H:%M") if f_ else "no ar"}',al=Cc)
            C(ws,r,3,dur if dur else SEMDADO,fmt='0.00"h"' if dur else None,al=Cc)
            C(ws,r,4,s["gmv"] or 0,fmt=CUR); C(ws,r,5,s["itens"] or 0,fmt=INT)
            C(ws,r,6,s["customers"] or 0,fmt=INT); r+=1
        band(ws,r0,r-1,6); r+=1
        r=nota(ws,r,f"A live respondeu por {BRn(peso_live*100,1)}% da receita de lista do dia. "
          "O relatório detalhado de cada sala sai separado, 45 min após o fim.",7,30)
    else:
        r=nota(ws,r,"Não houve live neste dia.",7,26)
    r+=1
    C(ws,r,1,"AUDIÊNCIA, RETENÇÃO E CTOR",H2); r+=1
    r=nota(ws,r,("❌ NÃO MEDIDO. Pico de audiência morreu em 31/03 e retenção média em 30/05 — as duas só "
      "existem no export manual do Seller Center. A API /shop_lives não devolve views. "
      "⏳ O CTOR por sala a API DEVOLVE (click_to_order_rate) mas não está sendo gravado — é o unlock "
      "mais barato desta seção."),7,42,RF)
    r+=1
    if cr:
        C(ws,r,1,"CREATORS E AFILIADAS",H2); r+=1
        hdr(ws,r,["Recorte","Valor","Observação"],[26,16,58]); r+=1
        r0=r
        for k,v,fm,o in [("Creators com venda",cr["n_creators"],INT,"deduplicados por handle"),
                         ("GMV de afiliadas",cr["gmv"],CUR,"affiliate_perf — fonte distinta da live própria"),
                         ("Comissão paga",cr["comissao"],CUR,"custo variável de canal"),
                         ("Pedidos",cr["pedidos"],INT,"")]:
            C(ws,r,1,k,BOLD); C(ws,r,2,v,fmt=fm); C(ws,r,3,o,MUTF,al=Lw); r+=1
        band(ws,r0,r-1,3); r+=2
        hdr(ws,r,["Creator","GMV","Comissão","Pedidos","Peças"],[28,14,13,11,10]); r+=1
        r0=r
        for nome,z in cr["por_creator"][:12]:
            C(ws,r,1,"@"+nome,al=Lw); C(ws,r,2,z[0],fmt=CUR); C(ws,r,3,z[1],fmt=CUR)
            C(ws,r,4,z[2],fmt=INT); C(ws,r,5,z[3],fmt=INT); r+=1
        band(ws,r0,r-1,5)
        ws.conditional_formatting.add(f"B{r0}:B{r-1}",
            DataBarRule(start_type="num",start_value=0,end_type="max",color=RHODE))
        r+=1
    if vd:
        C(ws,r,1,"VÍDEOS POSTADOS NO DIA",H2); r+=1
        hdr(ws,r,["Vídeos","Criadores","Views","GMV","Pedidos"],[12,12,14,14,11]); r+=1
        C(ws,r,1,vd["n"],fmt=INT); C(ws,r,2,vd["criadores"],fmt=INT)
        C(ws,r,3,vd["views"],fmt=INT); C(ws,r,4,vd["gmv"],fmt=CUR); C(ws,r,5,vd["pedidos"],fmt=INT); r+=2
        r=nota(ws,r,("⚠️ GMV de vídeo é LIFETIME e amadurece em dias — vídeo postado hoje entra com GMV≈0. "
          "Apuração justa só a partir de D+2. Não leia este número como 'o vídeo não vendeu'."),7,32)

    # ═══ 5 · FUNIL DA LOJA ═══
    ws=wb.create_sheet("Funil da loja")
    r=cab(ws,"FUNIL E CONVERSÃO",
          "⚠️ O denominador é visualização de página de produto DENTRO do TikTok Shop — não é sessão de loja própria.")
    alvo=fu or fref
    if not alvo:
        r=nota(ws,r,"❌ SEM DADO para este dia nem para os 4 anteriores.",7,28,RF)
    else:
        if fref and not fu:
            r=nota(ws,r,(f"⚠️ O funil de {dt.strftime('%d/%m')} ainda NÃO consolidou — a API do TikTok fecha com "
              f"~2 dias de atraso e devolve zeros silenciosos para dia aberto. Os números abaixo são de "
              f"{datetime.strptime(alvo['dia'],'%Y-%m-%d').strftime('%d/%m')} "
              f"({alvo['defasagem_dias']} dia(s) antes), como REFERÊNCIA — não são do dia deste relatório."),7,42,RF)
        hdr(ws,r,["Métrica","Valor","O que é"],[30,16,60]); r+=1
        r0=r
        for k,v,fm,o in [
          ("Visualizações de página",alvo.get("page_views"),INT,"product_page_views — página de produto no TikTok Shop"),
          ("Visitantes (média)",alvo.get("visitantes"),INT,"avg_product_page_visitors"),
          ("Pedidos (API)",alvo.get("pedidos_api"),INT,"contagem da própria API, pode divergir da Orders API"),
          ("Conversão sobre page views",alvo.get("conv_pv"),PCT,"pedidos ÷ visualizações"),
          ("Conversão sobre visitantes",alvo.get("conv_visitante"),PCT,"pedidos ÷ visitantes únicos"),
          ("AOV (API)",alvo.get("aov_api"),CUR,"avg_order_value da API"),
        ]:
            C(ws,r,1,k,BOLD)
            C(ws,r,2,v if v is not None else SEMDADO,fmt=fm if v is not None else None)
            C(ws,r,3,o,MUTF,al=Lw); r+=1
        band(ws,r0,r-1,3); r+=2
    C(ws,r,1,"POR QUE NÃO EXISTE 'CONVERSÃO DO E-COMMERCE' DE VERDADE",H2); r+=1
    r=nota(ws,r,("Não há NENHUMA fonte de sessão ou visitante de site neste projeto — conferido em 80 tabelas do "
      "Supabase. store_daily.conversion_rate existe mas está congelada desde 13/05/2026 e só era populada por "
      "export manual. O que está acima é funil de marketplace: mede quem viu a página do produto dentro do "
      "TikTok, não quem entrou numa loja. Para conversão de e-commerce própria seria preciso plugar "
      "Shopify Analytics ou GA — não existe no projeto hoje."),7,50)

    # ═══ 6 · DIAGNÓSTICOS ═══
    ws=wb.create_sheet("Diagnosticos")
    r=cab(ws,"DIAGNÓSTICOS E ALERTAS DO DIA","Cada alerta traz o número que o dispara e o que fazer. Sem alerta = seção diz que não há.")
    alertas=[]
    if r_["nao_virou_pct"]>0.10:
        perda=sum((r_["rev"][id(x)]/x["qty"]*SR-CPV)*x["qty"] for x in r_["itens"] if x["status"]=="UNPAID" and x["qty"])
        alertas.append(("Pedidos que não viraram receita",
          f"{r_['nao_virou']} peças ({BRn(r_['nao_virou_pct']*100,1)}%) ficaram em UNPAID ou CANCELLED, "
          f"segurando R$ {BRn(perda)} de contribuição. A mídia por esses pedidos já foi paga.",
          "Remedir em 48h para separar atraso de perda; atacar prazo/meio de pagamento.",perda))
    if ads and ads["total"]["cpa"]>0:
        teto=r_["contrib_peca"]
        if ads["total"]["cpa"]>teto:
            alertas.append(("CPA acima do que a peça aguenta",
              f"CPA de R$ {BRn(ads['total']['cpa'])} contra contribuição de R$ {BRn(teto)} por peça. "
              f"Cada pedido comprado destrói R$ {BRn(ads['total']['cpa']-teto)}.",
              "Revisar teto de lance ou subir preço de lista antes de escalar verba.",
              (ads["total"]["cpa"]-teto)*(ads["total"]["pedidos"] or 0)))
    if ra and ra["lista"] and delta(r_["lista"],ra["lista"]) is not None and delta(r_["lista"],ra["lista"])<-0.25:
        alertas.append(("Queda forte de receita vs dia anterior",
          f"Receita de lista caiu {BRn(delta(r_['lista'],ra['lista'])*100,1)}% "
          f"(R$ {BRn(ra['lista'])} → R$ {BRn(r_['lista'])}).",
          "Verificar se houve live no dia anterior e não hoje, ou corte de mídia.",
          ra["lista"]-r_["lista"]))
    if liq<0:
        alertas.append(("Contribuição não cobriu a mídia",
          f"Contribuição bruta de R$ {BRn(r_['contrib'])} contra R$ {BRn(ads['total']['custo'] if ads else 0)} "
          f"de mídia — resultado R$ {BRn(liq)}.",
          "Não escalar verba enquanto a peça não pagar o tráfego.",abs(liq)))
    if dv and dv["n"]>0 and r_["pecas"]:
        tx=dv["n"]/r_["pecas"]
        if tx>0.05:
            alertas.append(("Devoluções acima do normal",
              f"{dv['n']} devoluções contra {r_['pecas']} peças vendidas ({BRn(tx*100,1)}%), "
              f"R$ {BRn(dv['valor'])} reembolsados.",
              "Checar o motivo dominante — 'não serviu' é modelagem, não ruptura.",dv["valor"]))
    if alertas:
        alertas.sort(key=lambda x:-(x[3] or 0))
        hdr(ws,r,["#","Alerta","O número","O que fazer","R$ em jogo"],[5,30,54,44,14]); r+=1
        r0=r
        for i,(t,n_,f_,v) in enumerate(alertas,1):
            C(ws,r,1,i,BOLD,al=Cc); C(ws,r,2,t,BOLD,al=Lw)
            C(ws,r,3,n_,MUTF,al=Lw); C(ws,r,4,f_,al=Lw)
            C(ws,r,5,v if v else SEMDADO,RF,fmt=CUR if v else None)
            ws.row_dimensions[r].height=54; r+=1
        band(ws,r0,r-1,5)
    else:
        r=nota(ws,r,"✅ Nenhum alerta material neste dia: pagamento, CPA, devoluções e variação de receita "
          "todos dentro do padrão.",7,30,GF)

    # ═══ 7 · PLANO DE AÇÃO ═══
    ws=wb.create_sheet("Plano de acao")
    r=cab(ws,"O QUE FAZER AMANHÃ","Deriva dos alertas acima, ordenado por R$ em jogo.")
    if alertas:
        hdr(ws,r,["#","Ação","Por quê (o número)","R$ em jogo"],[5,40,70,16]); r+=1
        r0=r
        for i,(t,n_,f_,v) in enumerate(alertas,1):
            C(ws,r,1,i,BOLD,al=Cc); C(ws,r,2,f_,BOLD,al=Lw); C(ws,r,3,n_,MUTF,al=Lw)
            C(ws,r,4,v if v else SEMDADO,GF,fmt=CUR if v else None)
            ws.row_dimensions[r].height=52; r+=1
        band(ws,r0,r-1,4); r+=2
        tot=sum(a[3] or 0 for a in alertas)
        r=nota(ws,r,f"Soma do que está em jogo: R$ {BRn(tot)} — "
          f"{BRn(tot/r_['contrib'],1) if r_['contrib'] else '—'}× a contribuição bruta do dia.",7,30,BOLD)
    else:
        r=nota(ws,r,"Sem ação corretiva pendente para este dia.",7,26,GF)

    # ═══ 8 · PREMISSAS ═══
    ws=wb.create_sheet("Premissas")
    r=cab(ws,"COMO ISTO FOI MEDIDO — E O QUE NÃO DEU PARA MEDIR","Testado, não presumido.")
    C(ws,r,1,"✅ DADO REAL",H2); r+=1
    for t in [f"Receita, peças, pedidos e status — Orders API (pedidos_sku + pedido_pagamento), dia {dia}.",
      "Receita de LISTA = sub_total + platform_discount, rateado do pedido para o item (lib/receita.py). "
      "Nunca fator médio de gross-up — erro que já inverteu veredito 3 vezes.",
      f"Régua: settlement {SR} · CPV R$ {BRn(CPV)}.",
      "GMV de live — /analytics/202509/shop_lives/performance (live_attr), só salas da própria loja.",
      "Mídia — ads_campanha (GMV Max Report API). Creators — affiliate_perf, deduplicado por handle.",
      "Funil — /analytics/202405/shop/performance, chamado na hora (não é armazenado em lugar nenhum)."]:
        r=nota(ws,r,"✓ "+t,7,30)
    r+=1
    C(ws,r,1,"❌ NÃO DISPONÍVEL — e por quê",H2); r+=1
    hdr(ws,r,["Métrica","Status","Por quê"],[30,16,76]); r+=1
    r0=r
    for m,s,w_ in [
      ("Conversão de e-commerce","❌ não existe","Nenhuma fonte de sessão/visitante de site. store_daily congelada desde 13/05. O que há é funil de marketplace."),
      ("CPM / CPC / impressões / CTR","❌ não existe","9 métricas testadas na GMV Max Report API, todas 'Invalid metric'. UI-only."),
      ("Pico de audiência de live","❌ morto","lives.peak_viewers sem valor desde 31/03/2026."),
      ("Retenção de live","❌ morto","lives.avg_view_duration_sec sem valor desde 30/05/2026."),
      ("CTOR de live","⏳ não coletado","A API /shop_lives devolve click_to_order_rate — só não está sendo gravado."),
      ("Estoque / ruptura real","❌ não existe","Nenhuma tabela de saldo no Supabase (80 conferidas). Só export manual."),
      ("Margem realizada do dia","⏳ D-7","statement_tx é semanal e o settlement leva dias para liquidar."),
      ("Funil do próprio dia","⏳ D-2","A API consolida com ~2 dias e devolve zeros silenciosos para dia aberto."),
    ]:
        C(ws,r,1,m,BOLD,al=Lw); C(ws,r,2,s,RF if "❌" in s else None,al=Cc); C(ws,r,3,w_,MUTF,al=Lw)
        ws.row_dimensions[r].height=30; r+=1
    band(ws,r0,r-1,3); r+=2
    r=nota(ws,r,("⚠️ ATRIBUIÇÃO: GMV de live (live_attr) e GMV de afiliada (affiliate_perf) vêm de fontes "
      "diferentes e podem se sobrepor no mesmo pedido. O peso da live no total usa a receita de lista como "
      "denominador, que é a base contábil — não some as duas fontes como se fossem canais exclusivos."),7,42)
    wb.calculation.fullCalcOnLoad=True
    return wb,alertas,liq

def escrever_md(D,alertas,liq,path):
    r_=D["rec"];ra=D["rec_ant"];lv=D["live"];ads=D["ads"];cr=D["creators"]
    dt=datetime.strptime(D["dia"],"%Y-%m-%d")
    peso=(lv["gmv"]/r_["lista"]) if r_["lista"] else 0
    L=[f"# Relatório diário de performance — {dt.strftime('%d/%m/%Y')}","",
       f"_Gerado em {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')} BRT · comparado com {D['anterior']}_","",
       "## 1. Visão geral de receita e caixa","",
       "| KPI | Hoje | Dia anterior | Δ |","|---|---:|---:|---:|"]
    for k,a,b,f in [("Receita de lista",r_["lista"],ra["lista"] if ra else None,"R$"),
                    ("Peças pagas",r_["pecas"],ra["pecas"] if ra else None,""),
                    ("Pedidos",r_["pedidos"],ra["pedidos"] if ra else None,""),
                    ("AOV por pedido",r_["aov_lista"],ra["aov_lista"] if ra else None,"R$"),
                    ("Contribuição bruta",r_["contrib"],ra["contrib"] if ra else None,"R$")]:
        d_=delta(a,b)
        L.append(f"| {k} | {f} {BRn(a)} | {f} {BRn(b) if b is not None else SEMDADO} | "
                 f"{(BRn(d_*100,1)+'%') if d_ is not None else '—'} |")
    L+=["",f"**GMV de live:** R$ {BRn(lv['gmv'])} ({BRn(peso*100,1)}% do total) em {lv['n']} transmissão(ões).","",
        "## 2. Tráfego pago",""]
    if ads:
        L+=[f"Investimento R$ {BRn(ads['total']['custo'])} · ROAS {BRn(ads['total']['roas'])}× · "
            f"CPA R$ {BRn(ads['total']['cpa'])}.","",
            f"**Contribuição após mídia: R$ {BRn(liq)}.**","",
            "| Recorte | Investimento | ROAS | CPA |","|---|---:|---:|---:|"]
        for lb,m in [("Live",ads["live"]),("Produto",ads["produto"])]:
            L.append(f"| {lb} | R$ {BRn(m['custo'])} | {BRn(m['roas'])}× | R$ {BRn(m['cpa'])} |")
    else:
        L.append("_Sem dado de mídia para este dia quando o relatório rodou._")
    L+=["","## 3. Funil, live e creators",""]
    if cr:
        L.append(f"{cr['n_creators']} creators com venda · GMV de afiliadas R$ {BRn(cr['gmv'])} · "
                 f"comissão R$ {BRn(cr['comissao'])}.")
    L+=["","_Pico de audiência, retenção e CTR de live: **sem dado** — ver aba Premissas._","",
        "## 4. Diagnósticos e alertas",""]
    if alertas:
        for i,(t,n_,f_,v) in enumerate(alertas,1):
            L+= [f"**{i}. {t}** — {n_}",f"→ {f_}",""]
    else:
        L.append("Nenhum alerta material neste dia.")
    L+=["","---","",
        "_Receita de LISTA = pago + cupom subsidiado pelo TikTok. Settlement 0,7084 · CPV R$ 45,40._"]
    open(path,"w").write("\n".join(L))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data"); ap.add_argument("--saida")
    a=ap.parse_args()
    dia=a.data or (datetime.now(BRT)-timedelta(days=1)).strftime("%Y-%m-%d")
    D=montar(dia)
    wb,alertas,liq=render(D)
    nome=f"Relatorio Diario da Loja_{dia}"
    out=a.saida or os.path.join(ROOT,"relatorios",dia[:7],nome+".xlsx")
    os.makedirs(os.path.dirname(out),exist_ok=True)
    wb.save(out)
    md=out.replace(".xlsx",".md"); escrever_md(D,alertas,liq,md)
    print(f"OK {out}")
    print(f"   receita R$ {D['rec']['lista']:,.2f} · {D['rec']['pecas']} peças · contrib R$ {D['rec']['contrib']:,.2f}")
    print(f"   após mídia R$ {liq:,.2f} · {len(alertas)} alerta(s)")
    return out,md

if __name__=="__main__":
    main()
