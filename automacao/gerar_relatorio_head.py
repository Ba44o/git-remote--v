#!/usr/bin/env python3
"""
Rhode — RELATÓRIO SEMANAL HEAD (TikTok Shop). Toda terça 08:00 BRT, semana seg–dom anterior.

Uso:  python3 automacao/gerar_relatorio_head.py                       # semana passada
      python3 automacao/gerar_relatorio_head.py --seg 2026-09-07
      python3 automacao/gerar_relatorio_head.py --pkl /tmp/semana_head.pkl --saida /tmp/h.xlsx

Não é mais um relatório de monitoramento — esses já existem (live e loja). É a pauta do head:
o veredito contra a estrutura, as 3 decisões em jogo, o registro de recomendações com sinal
medido, a economia por motor e a saúde do dado. Números vêm de dados_semana.py; nada à mão.
"""
import os, sys, pickle, argparse
from datetime import datetime, timedelta, timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import DataBarRule, CellIsRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "automacao"))
from dados_semana import (montar_semana, CANAIS, ROTULO, CPV, IMPOSTO, ESTRUTURA_MES,
                          HORA_APRESENTADORA, BRT)
from recomendacoes import medir, decisoes_da_semana

INK="1A1A1E";MUT="6B6B76";RED="FE2C55";GREEN="0E9F6E";RHODE="FE2C55"
H1=Font(size=16,bold=True,color=INK);H2=Font(size=12,bold=True,color=INK)
TH=Font(size=10,bold=True,color="FFFFFF");BOLD=Font(bold=True,color=INK)
MUTF=Font(size=9,italic=True,color=MUT);RF=Font(bold=True,color=RED);GF=Font(bold=True,color=GREEN)
HEAD=PatternFill("solid",fgColor=INK);BAND=PatternFill("solid",fgColor="F7F7F9")
TOTF=PatternFill("solid",fgColor="EFEFF2");ALERT=PatternFill("solid",fgColor="FDECEA")
OKF=PatternFill("solid",fgColor="E8F6EF");WARN=PatternFill("solid",fgColor="FFF4E5")
Cc=Alignment(horizontal="center",vertical="center")
Lw=Alignment(horizontal="left",wrap_text=True,vertical="top")
CUR='R$ #,##0.00';CUR0='R$ #,##0';INT='#,##0';PCT='0.0%';X1='0.00"x"';N4='0.0000'
SEMDADO="sem dado"


def C(ws,r,c,v=None,f=None,fmt=None,fill=None,al=None):
    x=ws.cell(r,c,v)
    if isinstance(v,str) and v.startswith("= "): x.data_type="s"   # rótulo, não fórmula
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
def nota(ws,r,tx,n=8,h=30,f=None):
    C(ws,r,1,tx,f or MUTF,al=Lw); ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=n)
    ws.row_dimensions[r].height=h; return r+1
def BRn(v,d=2):
    if v is None: return SEMDADO
    return f"{v:,.{d}f}".replace(",","\x00").replace(".",",").replace("\x00",".")
def dm(d): return d.strftime("%d/%m")
def cab(ws,t,sub):
    ws.sheet_view.showGridLines=False
    C(ws,1,1,t,H1); C(ws,2,1,sub,MUTF); return 4


def render(R, medidas, perguntas, decisoes):
    W=R["semanas"][0]; A=R["semanas"][1] if len(R["semanas"])>1 else None
    EST=W["estrutura_semana"]; periodo=f"{dm(R['seg'])} a {dm(R['dom'])}"
    wb=Workbook()

    # ═══ 1 · VEREDITO ═══
    ws=wb.active; ws.title="Veredito da semana"
    r=cab(ws,f"SEMANA {R['id'][-3:]} — {periodo}",
          f"TikTok Shop · semana seg–dom · fechada terça {datetime.now(BRT).strftime('%d/%m %H:%M')} BRT · "
          f"só dado maduro. Estrutura R$ {BRn(ESTRUTURA_MES,0)}/mês = R$ {BRn(EST)} por semana.")
    ruins=[s["fonte"] for s in R["saude"] if not s["ok"]]
    if ruins:
        C(ws,3,1,f"⚠ Fonte(s) atrasada(s) no fechamento: {', '.join(ruins)} — confira a aba Saúde do dado antes de decidir.",RF)
    hdr(ws,r,["Cascata","Esta semana","Semana anterior","Δ R$","O que é"],[34,17,17,15,52]); r+=1
    A_op=A["resultado_operacional"] if A else None
    linhas=[("Receita de lista (memo)",W["lista"],A["lista"] if A else None,"pago + cupom subsidiado pelo TikTok",False),
            ("Contribuição",W["contrib"],A["contrib"] if A else None,"lista × taxa do canal − CPV",True),
            ("(−) Imposto 6,4%",-W["imposto"],-A["imposto"] if A else None,"Lucro Presumido, sobre a lista",True),
            ("(−) Devoluções (custo líquido)",-W["devolucoes"]["custo_liquido"],-A["devolucoes"]["custo_liquido"] if A else None,
             "peças devolvidas × custo medido ago/26",True),
            ("(−) Mídia de live (caixa)",-W["midia"]["caixa_live"],-A["midia"]["caixa_live"] if A else None,"GMV Max Tradicional",True),
            ("(−) Mídia de produto (caixa)",-W["midia"]["caixa_produto"],-A["midia"]["caixa_produto"] if A else None,"GMV Max Tradicional",True),
            ("(−) Apresentadora",-W["apresentadora"],-A["apresentadora"] if A else None,f"horas de live × R$ {BRn(HORA_APRESENTADORA,0)}",True)]
    r_first=r+1; rows={}
    for k,a,b,o,soma in linhas:
        C(ws,r,1,k,BOLD if soma else MUTF)
        C(ws,r,2,a,fmt=CUR); C(ws,r,3,b if b is not None else SEMDADO,fmt=CUR if b is not None else None)
        if b is not None: C(ws,r,4,f"=B{r}-C{r}",fmt=CUR)
        C(ws,r,5,o,MUTF,al=Lw); rows[k]=r; r+=1
    r_last=r-1
    band(ws,r_first-1,r_last,5)
    r_op=r
    C(ws,r,1,"= RESULTADO OPERACIONAL",BOLD,fill=TOTF)
    C(ws,r,2,f"=SUM(B{r_first}:B{r_last})",BOLD,fmt=CUR,fill=TOTF)
    C(ws,r,3,f"=SUM(C{r_first}:C{r_last})" if A else SEMDADO,BOLD,fmt=CUR,fill=TOTF)
    if A: C(ws,r,4,f"=B{r}-C{r}",fmt=CUR,fill=TOTF)
    C(ws,r,5,"antes de pagar a estrutura",MUTF,fill=TOTF); r+=1
    r_est=r
    C(ws,r,1,"(−) Estrutura da semana",BOLD); C(ws,r,2,-EST,fmt=CUR); C(ws,r,3,-EST if A else SEMDADO,fmt=CUR if A else None)
    C(ws,r,5,f"R$ {BRn(ESTRUTURA_MES,0)}/mês × 7 ÷ 30,44 dias",MUTF); r+=1
    fin_ok=W["resultado_final"]>=0; fl=OKF if fin_ok else ALERT
    C(ws,r,1,"= RESULTADO FINAL",BOLD,fill=fl)
    C(ws,r,2,f"=B{r_op}+B{r_est}",GF if fin_ok else RF,fmt=CUR,fill=fl)
    C(ws,r,3,f"=C{r_op}+C{r_est}" if A else SEMDADO,BOLD,fmt=CUR,fill=fl)
    if A: C(ws,r,4,f"=B{r}-C{r}",fmt=CUR,fill=fl)
    C(ws,r,5,"a operação pagou a estrutura?",MUTF,fill=fl); r_fin=r; r+=1
    ws.conditional_formatting.add(f"B{r_first}:D{r_fin}",CellIsRule(operator="lessThan",formula=["0"],font=RF))
    r+=1
    ritmo=W["resultado_operacional"]*30.4375/7
    gap_pc=(-W["resultado_final"]/W["pecas"]) if W["pecas"] and W["resultado_final"]<0 else 0
    ops=[S["resultado_operacional"] for S in R["semanas"]]
    tend=("piorando" if ops[0]<ops[-1] else "melhorando")
    neg=sum(1 for o in ops if o<0)
    C(ws,r,1,"A SEMANA EM 5 LINHAS",H2); r+=1
    p=(f"O TikTok Shop vendeu {BRn(W['pecas'],0)} peças e R$ {BRn(W['lista'])} de receita de lista entre {periodo}. "
       f"Depois de imposto, devoluções, mídia e apresentadora sobraram R$ {BRn(W['resultado_operacional'])} — "
       f"{'antes' if W['resultado_operacional']<EST else 'e isso'} de pagar os R$ {BRn(EST)} de estrutura da semana. "
       f"Resultado final: R$ {BRn(W['resultado_final'])}. "
       + (f"Faltaram R$ {BRn(gap_pc)} por peça para empatar. " if gap_pc else "A semana pagou a estrutura. ")
       + f"Nas últimas {len(ops)} semanas o operacional está {tend} ({' → '.join('R$ '+BRn(o,0) for o in reversed(ops))}), "
       f"com {neg} semana(s) negativa(s). No ritmo desta semana o mês fecha em R$ {BRn(ritmo,0)} de operacional "
       f"contra R$ {BRn(ESTRUTURA_MES,0)} de estrutura.")
    r=nota(ws,r,p,5,112,BOLD)

    # ═══ 2 · DECISÕES ═══
    ws=wb.create_sheet("Decisoes da semana")
    r=cab(ws,"AS DECISÕES EM JOGO","Não é a lista inteira — são as que movem mais dinheiro. Dono vazio = precisa ser atribuído.")
    hdr(ws,r,["#","Decisão","Por quê (o número)","R$ em jogo/semana","Dono"],[5,34,66,17,14]); r+=1; r0=r
    for i,d in enumerate(decisoes,1):
        C(ws,r,1,i,BOLD,al=Cc); C(ws,r,2,d["titulo"],BOLD,al=Lw); C(ws,r,3,d["porque"],MUTF,al=Lw)
        C(ws,r,4,d["em_jogo"],RF,fmt=CUR)
        C(ws,r,5,d["dono"],RF if d["dono"]=="a definir" else None,al=Cc,fill=WARN if d["dono"]=="a definir" else None)
        ws.row_dimensions[r].height=62; r+=1
    if not decisoes:
        C(ws,r,2,"Nenhuma decisão material em jogo nesta semana.",GF); r+=1
    band(ws,r0,r-1,5); r+=1
    r=nota(ws,r,("O buraco da estrutura não se fecha com volume: a conta de agosto mostrou que zerar devolução cobre 28% "
                 "e zerar mídia 49% — e nenhuma sozinha resolve. As alavancas que fecham são preço de lista e CPV."),5,34)

    # ═══ 3 · REGISTRO DE RECOMENDAÇÕES ═══
    ws=wb.create_sheet("Registro de recomendacoes")
    r=cab(ws,"O QUE FOI RECOMENDADO — E O QUE ACONTECEU",
          "O status é do dono. O SINAL é medido sozinho toda semana. ⚠ = status e sinal discordam.")
    hdr(ws,r,["Recomendação","Desde","Origem","Status","Dono","Sinal medido","Esta semana","Anterior","R$ em jogo"],
        [32,10,16,12,11,40,34,20,14]); r+=1; r0=r
    for m in medidas:
        C(ws,r,1,("⚠ " if m["discorda"] else "")+m["titulo"],RF if m["discorda"] else BOLD,al=Lw)
        C(ws,r,2,datetime.strptime(m["recomendado_em"],"%Y-%m-%d").strftime("%d/%m"),al=Cc)
        C(ws,r,3,m["origem"],MUTF,al=Lw)
        C(ws,r,4,m["status"],RF if m["status"] in("contrariada",) else None,al=Cc)
        C(ws,r,5,m["dono"],RF if m["dono"]=="a definir" else None,al=Cc)
        s=m["sinal"]; C(ws,r,6,s,GF if s.startswith("✅") else (RF if s.startswith("❌") else None),al=Lw)
        C(ws,r,7,m["semana"] or SEMDADO,al=Lw); C(ws,r,8,m["anterior"] or "—",MUTF,al=Lw)
        C(ws,r,9,m["em_jogo"] if m["em_jogo"] else "—",fmt=CUR if m["em_jogo"] else None)
        ws.row_dimensions[r].height=48; r+=1
    band(ws,r0,r-1,9); r+=1
    C(ws,r,1,"PERGUNTAS EM ABERTO",H2); r+=1
    hdr(ws,r,["Pergunta","Aberta desde"],None); r+=1; r0=r
    for q in perguntas:
        C(ws,r,1,q["pergunta"],al=Lw); ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=7)
        C(ws,r,8,datetime.strptime(q["aberta_desde"],"%Y-%m-%d").strftime("%d/%m/%Y"),RF,al=Cc)
        ws.row_dimensions[r].height=40; r+=1
    band(ws,r0,r-1,8)

    # ═══ 4 · MOTORES ═══
    ws=wb.create_sheet("Motores TikTok Shop")
    cal=R["calibracao"]
    r=cab(ws,"A ECONOMIA DE CADA MOTOR",
          f"Taxa por canal calibrada em {BRn(cal['pedidos'],0)} pedidos liquidados e sem devolução, criados de "
          f"{datetime.strptime(cal['janela'][0],'%Y-%m-%d').strftime('%d/%m')} a {datetime.strptime(cal['janela'][1],'%Y-%m-%d').strftime('%d/%m')}.")
    hdr(ws,r,["Motor","Peças","% peças","Receita lista","Taxa do canal","Contribuição","Contrib/peça","Após mídia de live"],
        [34,10,10,16,13,15,13,17]); r+=1; r0=r
    cn=W["canal"]["canais"]
    for k in CANAIS:
        z=cn[k]; pc=z["contrib"]/z["pecas"] if z["pecas"] else 0
        C(ws,r,1,ROTULO[k],BOLD); C(ws,r,2,z["pecas"],fmt=INT)
        C(ws,r,3,f"=B{r}/SUM(B{r0}:B{r0+len(CANAIS)-1})",fmt=PCT)
        C(ws,r,4,z["lista"],fmt=CUR); C(ws,r,5,cal["taxas"][k],fmt=N4)
        C(ws,r,6,z["contrib"],fmt=CUR); C(ws,r,7,f"=IF(B{r}=0,0,F{r}/B{r})",fmt=CUR)
        if k=="live_propria": C(ws,r,8,f"=F{r}-{W['midia']['caixa_live']:.2f}",fmt=CUR)
        else: C(ws,r,8,"—",MUTF,al=Cc)
        r+=1
    rT=r
    C(ws,r,1,"TOTAL",BOLD,fill=TOTF); C(ws,r,2,f"=SUM(B{r0}:B{r-1})",BOLD,fmt=INT,fill=TOTF)
    C(ws,r,4,f"=SUM(D{r0}:D{r-1})",BOLD,fmt=CUR,fill=TOTF); C(ws,r,6,f"=SUM(F{r0}:F{r-1})",BOLD,fmt=CUR,fill=TOTF)
    C(ws,r,7,f"=IF(B{r}=0,0,F{r}/B{r})",BOLD,fmt=CUR,fill=TOTF)
    for c in (3,5,8): ws.cell(r,c).fill=TOTF
    band(ws,r0,r-1,8)
    ws.conditional_formatting.add(f"B{r0}:B{r-1}",DataBarRule(start_type="num",start_value=0,end_type="max",color=RHODE))
    ws.conditional_formatting.add(f"H{r0}:H{r-1}",CellIsRule(operator="lessThan",formula=["0"],font=RF))
    r+=2
    melhor=max(CANAIS,key=lambda k:(cn[k]["contrib"]/cn[k]["pecas"]) if cn[k]["pecas"] else -1e9)
    pior=min(CANAIS,key=lambda k:(cn[k]["contrib"]/cn[k]["pecas"]) if cn[k]["pecas"] else 1e9)
    lp=cn["live_propria"]
    r=nota(ws,r,(f"Melhor motor por peça: {ROTULO[melhor]} (R$ {BRn(cn[melhor]['contrib']/cn[melhor]['pecas'])}). "
                 f"Pior: {ROTULO[pior]} (R$ {BRn(cn[pior]['contrib']/cn[pior]['pecas'])}). "
                 f"A live própria gera R$ {BRn(lp['contrib'])} de contribuição e consome R$ {BRn(W['midia']['caixa_live'])} "
                 f"de mídia de live — sobram R$ {BRn(lp['contrib']-W['midia']['caixa_live'])} antes de imposto e apresentadora. "
                 f"A mídia de produto (R$ {BRn(W['midia']['caixa_produto'])}) não é atribuível a um canal só e fica fora desta coluna."),8,62,BOLD)
    r+=1
    C(ws,r,1,"CONTRIBUIÇÃO POR MOTOR — 4 SEMANAS",H2); r+=1
    sems=list(reversed(R["semanas"]))
    hdr(ws,r,["Motor"]+[f"{S['id'][-3:]} ({dm(S['seg'])})" for S in sems],None); r+=1; rt0=r
    for k in CANAIS:
        C(ws,r,1,ROTULO[k],BOLD)
        for j,S in enumerate(sems): C(ws,r,2+j,S["canal"]["canais"][k]["contrib"],fmt=CUR)
        r+=1
    band(ws,rt0,r-1,1+len(sems))
    ch=BarChart(); ch.type="col"; ch.grouping="clustered"; ch.title="Contribuição por motor, semana a semana"
    ch.height=8; ch.width=22
    ch.add_data(Reference(ws,min_col=2,max_col=1+len(sems),min_row=rt0-1,max_row=r-1),titles_from_data=True)
    ch.set_categories(Reference(ws,min_col=1,min_row=rt0,max_row=r-1))
    ws.add_chart(ch,f"A{r+1}"); r+=18
    sup=W.get("superficies")
    C(ws,r,1,"MEMO — SUPERFÍCIES DA API (não somam com os motores acima)",H2); r+=1
    if sup:
        As=A.get("superficies") if A else None
        hdr(ws,r,["Superfície","GMV bruto","Semana anterior","Impressões de produto","Page views"],None); r+=1; r0=r
        for t,lb in (("LIVE","Live"),("VIDEO","Vídeo"),("PRODUCT_CARD","Card de produto")):
            C(ws,r,1,lb,BOLD); C(ws,r,2,sup["gmv"].get(t,0),fmt=CUR)
            C(ws,r,3,(As["gmv"].get(t,0) if As else SEMDADO),fmt=CUR if As else None)
            C(ws,r,4,sup["impressoes"].get(t,0),fmt=INT); C(ws,r,5,sup["page_views"].get(t,0),fmt=INT); r+=1
        band(ws,r0,r-1,5); r+=1
        r=nota(ws,r,("GMV bruto da API inclui pedido que depois cancela e mistura afiliada e loja — é superfície de "
                     "exibição, não canal de atribuição. Use para ler tráfego e mix, não para margem."),8,32)
    else:
        r=nota(ws,r,"Superfícies ainda não consolidadas na API para esta semana.",8,24)

    # ═══ 5 · LIVES ═══
    ws=wb.create_sheet("Lives da semana")
    L=W.get("lives") or []
    r=cab(ws,"LIVES PRÓPRIAS DA SEMANA",
          "Resultado por live vem do relatório automático de live (mesma régua). KPI-mãe: contribuição por HORA no ar.")
    if L:
        hdr(ws,r,["Live","Duração","Peças","Resultado","R$/hora","Estouro de verba","Corte de promo","Views","% pagas","Retenção","CTR","CTOR"],
            [30,9,8,13,11,20,16,10,9,10,8,8]); r+=1; r0=r
        for l in L:
            C(ws,r,1,f"{l['inicio'].strftime('%d/%m %H:%M')} · {(l['titulo'] or '(sem título)')[:18]}",al=Lw)
            C(ws,r,2,l["dur"],fmt='0.00"h"'); C(ws,r,3,l["pecas"],fmt=INT)
            C(ws,r,4,l["res"],GF if l["res"]>0 else RF,fmt=CUR)
            C(ws,r,5,f"=IF(B{r}=0,0,D{r}/B{r})",fmt=CUR)
            C(ws,r,6,(f"{l['estouro_h']:02d}h · R$ {BRn(l['estouro'])}" if l["estouro"] else "—"),RF if l["estouro"] else MUTF,al=Cc)
            C(ws,r,7,(f"{l['corte_h']} · R$ {BRn(l['corte'])}" if l["corte"] else "—"),RF if l["corte"] else MUTF,al=Cc)
            C(ws,r,8,l["views"] if l["views"] is not None else SEMDADO,fmt=INT if l["views"] is not None else None)
            C(ws,r,9,(l["views_pagas"]/l["views"]) if l["views"] else SEMDADO,fmt=PCT if l["views"] else None)
            C(ws,r,10,l["retencao"] if l["retencao"] is not None else SEMDADO,fmt='0"s"' if l["retencao"] is not None else None)
            C(ws,r,11,(l["ctr"]/100) if l["ctr"] is not None else SEMDADO,fmt=PCT if l["ctr"] is not None else None)
            C(ws,r,12,(l["ctor"]/100) if l["ctor"] is not None else SEMDADO,fmt='0.00%' if l["ctor"] is not None else None)
            r+=1
        C(ws,r,1,"TOTAL",BOLD,fill=TOTF); C(ws,r,2,f"=SUM(B{r0}:B{r-1})",BOLD,fmt='0.00"h"',fill=TOTF)
        C(ws,r,3,f"=SUM(C{r0}:C{r-1})",BOLD,fmt=INT,fill=TOTF); C(ws,r,4,f"=SUM(D{r0}:D{r-1})",BOLD,fmt=CUR,fill=TOTF)
        C(ws,r,5,f"=IF(B{r}=0,0,D{r}/B{r})",BOLD,fmt=CUR,fill=TOTF)
        for c in range(6,13): ws.cell(r,c).fill=TOTF
        band(ws,r0,r-1,12)
        ws.conditional_formatting.add(f"E{r0}:E{r-1}",CellIsRule(operator="lessThan",formula=["0"],font=RF,fill=ALERT))
        r+=2
        n_est=sum(1 for l in L if l["estouro"]); r_est=sum(l["estouro"] for l in L)
        res_tot=sum(l["res"] for l in L); h_tot=sum(l["dur"] for l in L)
        r=nota(ws,r,(f"{len(L)} lives, {BRn(h_tot,1)}h no ar, resultado somado de R$ {BRn(res_tot)} — R$ {BRn(res_tot/h_tot if h_tot else 0)} "
                     f"por hora. {n_est} de {len(L)} tiveram estouro de verba numa hora, somando R$ {BRn(r_est)} de excesso: "
                     f"é o mesmo padrão semana após semana, e o teto de gasto por hora segue sem ser aplicado."),8,48,BOLD)
    else:
        r=nota(ws,r,"Sem lives próprias processadas nesta semana.",8,24)

    # ═══ 6 · TENDÊNCIA ═══
    ws=wb.create_sheet("Tendencia 4 semanas")
    r=cab(ws,"4 SEMANAS, MESMA RÉGUA","Todas as semanas com a mesma conta — apresentadora e devoluções incluídas em todas.")
    hdr(ws,r,["Linha"]+[f"{S['id'][-3:]} ({dm(S['seg'])})" for S in sems],[30]+[16]*len(sems)); r+=1; r0=r
    met=[("Receita de lista",lambda S:S["lista"],CUR),("Peças",lambda S:S["pecas"],INT),
         ("Contribuição",lambda S:S["contrib"],CUR),("(−) Imposto",lambda S:-S["imposto"],CUR),
         ("(−) Devoluções",lambda S:-S["devolucoes"]["custo_liquido"],CUR),
         ("(−) Mídia caixa",lambda S:-(S["midia"]["caixa_live"]+S["midia"]["caixa_produto"]),CUR),
         ("(−) Apresentadora",lambda S:-S["apresentadora"],CUR)]
    rr={}
    for nome,fn,fm in met:
        C(ws,r,1,nome,BOLD)
        for j,S in enumerate(sems): C(ws,r,2+j,fn(S),fmt=fm)
        rr[nome]=r; r+=1
    r_opt=r; C(ws,r,1,"= Resultado operacional",BOLD,fill=TOTF)
    for j in range(len(sems)):
        col=ws.cell(1,2+j).column_letter
        C(ws,r,2+j,f"=SUM({col}{rr['Contribuição']}:{col}{rr['(−) Apresentadora']})",BOLD,fmt=CUR,fill=TOTF)
    r+=1
    C(ws,r,1,"(−) Estrutura",BOLD)
    for j in range(len(sems)): C(ws,r,2+j,-EST,fmt=CUR)
    r_estt=r; r+=1
    C(ws,r,1,"= Resultado final",BOLD,fill=ALERT)
    for j in range(len(sems)):
        col=ws.cell(1,2+j).column_letter
        C(ws,r,2+j,f"={col}{r_opt}+{col}{r_estt}",BOLD,fmt=CUR,fill=ALERT)
    r+=1
    C(ws,r,1,"Contribuição por peça",BOLD)
    for j in range(len(sems)):
        col=ws.cell(1,2+j).column_letter
        C(ws,r,2+j,f"=IF({col}{rr['Peças']}=0,0,{col}{rr['Contribuição']}/{col}{rr['Peças']})",fmt=CUR)
    r+=1
    band(ws,r0,r-1,1+len(sems))
    ws.conditional_formatting.add(f"B{r_opt}:{ws.cell(1,1+len(sems)).column_letter}{r-2}",
                                  CellIsRule(operator="lessThan",formula=["0"],font=RF))
    lc=LineChart(); lc.title="Resultado operacional por semana"; lc.height=8; lc.width=20
    lc.add_data(Reference(ws,min_col=1,max_col=1+len(sems),min_row=r_opt,max_row=r_opt),from_rows=True,titles_from_data=True)
    lc.set_categories(Reference(ws,min_col=2,max_col=1+len(sems),min_row=r0-1,max_row=r0-1))
    ws.add_chart(lc,f"A{r+1}")

    # ═══ 7 · SAÚDE DO DADO ═══
    ws=wb.create_sheet("Saude do dado")
    r=cab(ws,"DÁ PARA CONFIAR NESTES NÚMEROS?","Frescor de cada fonte no fechamento. Fonte fora da tolerância = número daquela seção sob suspeita.")
    hdr(ws,r,["Fonte","Último dia","Atraso","Tolerância","Situação"],[24,14,10,12,40]); r+=1; r0=r
    for s in R["saude"]:
        C(ws,r,1,s["fonte"],BOLD); C(ws,r,2,s["ultimo"].strftime("%d/%m/%Y") if s["ultimo"] else SEMDADO,al=Cc)
        C(ws,r,3,f"{s['lag']}d" if s["lag"] is not None else "—",al=Cc); C(ws,r,4,f"{s['tolerancia']}d",al=Cc)
        C(ws,r,5,"✅ em dia" if s["ok"] else "❌ ATRASADA — seção afetada sob suspeita",GF if s["ok"] else RF,
          fill=None if s["ok"] else ALERT); r+=1
    band(ws,r0,r-1,5); r+=1
    C(ws,r,1,"CALIBRAÇÃO DA TAXA POR CANAL",H2); r+=1
    hdr(ws,r,["Canal","Taxa","Pedidos na amostra","Fonte"],None); r+=1; r0=r
    for k in CANAIS:
        b=cal["base"][k]; C(ws,r,1,ROTULO[k],BOLD); C(ws,r,2,cal["taxas"][k],fmt=N4)
        C(ws,r,3,b["pedidos"],fmt=INT); C(ws,r,4,b["fonte"],MUTF); r+=1
    band(ws,r0,r-1,4); r+=1
    la=W["live_api"]; lp=W["canal"]["canais"]["live_propria"]
    r=nota(ws,r,(f"Viés de atribuição da live própria: a classificação por janela de horário deu {BRn(lp['pecas'],0)} peças; "
                 f"a API atribui {BRn(la['itens'],0)} peças às salas ({(lp['pecas']/la['itens']) if la['itens'] else 0:.2f}×). "
                 "Perto de 1 = a janela não está roubando venda de outros canais."),8,40)
    r=nota(ws,r,("Gotcha corrigido em 14/09: o campo `data` de pedidos_sku é a data UTC — 18,6% das peças (as feitas depois "
                 "das 21h BRT) caíam no dia seguinte. O semanal usa a hora real do pedido em Brasília."),8,34)
    r=nota(ws,r,("Gotcha corrigido em 14/09: extrato_pedidos estava incompleto em vários dias; sem ele, pedido de afiliada "
                 "vira 'loja própria'. Por isso o fechamento coleta o extrato antes de medir."),8,34)

    # ═══ 8 · DEFINIÇÕES ═══
    ws=wb.create_sheet("Definicoes e premissas")
    r=cab(ws,"DICIONÁRIO — O MESMO NÚMERO PARA TODO MUNDO","Todos os relatórios automáticos usam estas definições.")
    hdr(ws,r,["Termo","Definição","Por quê"],[24,56,60]); r+=1; r0=r
    for t,d_,w_ in [
      ("Receita de lista","sub_total + platform_discount, rateado do pedido para o item (lib/receita.py).",
       "O cupom da plataforma é subsídio do TikTok e volta para a loja. Errar essa base já inverteu veredito 3 vezes."),
      ("GMV bruto (API)","gmv da /shop/performance: inclui pedido que depois cancela.","Serve para tráfego e mix. Nunca para margem."),
      ("Taxa do canal","settlement ÷ revenue de pedidos já liquidados e sem devolução, por canal, calibrada toda semana.",
       "Os canais vão de 0,65 a 0,76 — um número único esconde 10 pontos de diferença."),
      ("Contribuição","receita de lista × taxa do canal − CPV (R$ 45,40).","Antes de imposto, devolução e mídia."),
      ("Mídia de caixa","GMV Max Tradicional (net_cost > 0).","A VL é cobrada dentro da taxa e já está no settlement — somar de novo dupla-conta."),
      ("ROAS","receita atribuída ÷ custo de mídia.","Não decide alocação: ignora o CPV. Já inverteu a leitura de campanha (P23)."),
      ("Resultado operacional","contribuição − imposto − devoluções − mídia de caixa − apresentadora.","O que a operação deixa antes da estrutura."),
      ("Resultado final","resultado operacional − estrutura semanal (R$ 70.000 × 7 ÷ 30,44).","A operação se paga?"),
      ("Canal (motor)","afiliada pelo content_type do extrato; sem afiliada e dentro de live própria = live própria; resto = loja própria.",
       "Atribuição exata por pedido para afiliada; por janela de horário para live própria."),
    ]:
        C(ws,r,1,t,BOLD,al=Lw); C(ws,r,2,d_,al=Lw); C(ws,r,3,w_,MUTF,al=Lw); ws.row_dimensions[r].height=44; r+=1
    band(ws,r0,r-1,3); r+=1
    C(ws,r,1,"O QUE NÃO ESTÁ AQUI — e por quê",H2); r+=1
    for t in ["Site, Shopee, Shein, Meta e Google Ads: nenhuma das 80 tabelas tem dado desses canais. Todo o resultado é 100% TikTok Shop.",
              "Margem REALIZADA da semana: statement_tx liquida com 2–4 semanas de atraso; por isso a taxa é calibrada em semanas já liquidadas.",
              "CPM, CPC e CTR de anúncio: a GMV Max Report API rejeita. O funil que existe é o da SALA de live (retenção, CTR de produto, CTOR).",
              "Conversão de e-commerce com sessões: não há fonte de sessão de site. O funil disponível é de marketplace, em D-2."]:
        r=nota(ws,r,"✗ "+t,3,32)
    wb.calculation.fullCalcOnLoad=True
    return wb


def escrever_md(R, medidas, perguntas, decisoes, path):
    W=R["semanas"][0]; periodo=f"{dm(R['seg'])} a {dm(R['dom'])}"
    L=[f"# Relatório Semanal Head — {R['id']} ({periodo})","",
       f"_TikTok Shop · fechado {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')} BRT_","",
       "## Veredito","",
       f"- Receita de lista: **R$ {BRn(W['lista'])}** · {BRn(W['pecas'],0)} peças",
       f"- Contribuição: R$ {BRn(W['contrib'])}",
       f"- Resultado operacional: **R$ {BRn(W['resultado_operacional'])}**",
       f"- Estrutura da semana: R$ {BRn(W['estrutura_semana'])}",
       f"- **Resultado final: R$ {BRn(W['resultado_final'])}**","",
       "## As decisões em jogo",""]
    for i,d in enumerate(decisoes,1):
        L+=[f"**{i}. {d['titulo']}** — R$ {BRn(d['em_jogo'])}/semana · dono: {d['dono']}", f"{d['porque']}",""]
    L+=["## Registro de recomendações","","| Recomendação | Status | Sinal medido |","|---|---|---|"]
    for m in medidas:
        L.append(f"| {'⚠ ' if m['discorda'] else ''}{m['titulo']} | {m['status']} | {m['sinal']} |")
    L+=["","## Motores","","| Motor | Peças | Contrib/peça |","|---|---:|---:|"]
    for k in CANAIS:
        z=W["canal"]["canais"][k]
        L.append(f"| {ROTULO[k]} | {z['pecas']} | R$ {BRn(z['contrib']/z['pecas'] if z['pecas'] else 0)} |")
    L+=["","## Perguntas em aberto",""]+[f"- {q['pergunta']}" for q in perguntas]
    open(path,"w").write("\n".join(L))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seg"); ap.add_argument("--pkl"); ap.add_argument("--saida")
    a=ap.parse_args()
    if a.pkl: R=pickle.load(open(a.pkl,"rb"))
    else:
        seg=datetime.strptime(a.seg,"%Y-%m-%d").date() if a.seg else None
        R=montar_semana(seg)
    medidas,perguntas=medir(R); decisoes=decisoes_da_semana(R,medidas)
    wb=render(R,medidas,perguntas,decisoes)
    hoje=datetime.now(BRT).strftime("%Y-%m-%d")
    nome=f"Relatorio Semanal Head {R['id']} ({R['seg'].strftime('%d-%m')} a {R['dom'].strftime('%d-%m')})_{hoje}"
    out=a.saida or os.path.join(ROOT,"relatorios",R["dom"].strftime("%Y-%m"),nome+".xlsx")
    os.makedirs(os.path.dirname(out),exist_ok=True)
    wb.save(out); md=out.replace(".xlsx",".md"); escrever_md(R,medidas,perguntas,decisoes,md)
    W=R["semanas"][0]
    print(f"OK {out}")
    print(f"   operacional R$ {W['resultado_operacional']:,.2f} · final R$ {W['resultado_final']:,.2f} · {len(decisoes)} decisões")
    for i,d in enumerate(decisoes,1): print(f"   {i}. {d['titulo']} — R$ {d['em_jogo']:,.2f}")
    for m in medidas: print(f"   · {m['id']}: {m['sinal']}")
    return out,md

if __name__=="__main__":
    main()
