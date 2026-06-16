"""
Protótipo v3 (estático, navegável) do painel Seeding consolidado — validação visual.
FILTROS TEMPORAIS em tudo: Janela (30/60/90/Tudo, escala GMV/ROAS/lucro) + Mês do
convite + Período (data de/até). Segmentos = lentes de ação sobrepostas. Colunas
detalhadas, números exatos, ordenação decrescente com seta. NÃO toca no hub.
Saída: tools/prototipo-seeding/seeding.html
"""
import json
from pathlib import Path
from datetime import date as _date, timedelta
from collections import defaultdict
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
WH = BASE / "warehouse"
OUT = Path(__file__).resolve().parent / "seeding.html"
TODAY = _date(2026, 6, 12)
CUT14 = "2026-05-29"
CU, FR, MG = 40, 25, 0.55
DELIVERED = {"COMPLETED", "CONTENT_PENDING"}
INTRANSIT = {"SHIPPED"}
PENDING = {"PENDING", "AWAITING_SHIPMENT"}
SENT = DELIVERED | INTRANSIT
WINS = [("30", 30), ("60", 60), ("90", 90), ("0", 0)]
CUTW = {k: ((TODAY - timedelta(days=d)).isoformat() if d else "0000-00-00") for k, d in WINS}

led = pd.read_csv(WH / "raw_sample_applications.csv", dtype=str).fillna("")
cp = pd.read_csv(WH / "raw_creator_product.csv", dtype={"product_id": str})
cp["ck"] = cp.creator.str.lower().str.strip()
led["ck"] = led.creator.str.lower().str.strip()

sampled = defaultdict(set)
for _, x in led.iterrows():
    if x.status in SENT and x.product_id:
        sampled[x.ck].add(str(x.product_id))

def dmin(s):
    v = [d for d in s if d]; return min(v) if v else ""
def dmax(s):
    v = [d for d in s if d]; return max(v) if v else ""

ACAO = {
    "aguardando": lambda p, t: f"aprovar {p} amostra(s) pendente(s)",
    "ativar":     lambda p, t: "recebeu, nunca vendeu — ativar",
    "reativar":   lambda p, t: "vendeu e esfriou — reativar",
    "cancelada":  lambda p, t: "nada chegou — re-ofertar",
    "caminho":    lambda p, t: f"{t} a caminho — aguardar entrega",
    "vendeubem":  lambda p, t: "top — próxima amostra / subir tier",
    "ativa":      lambda p, t: "ativa, vende pouco — monitorar",
}
PRIO = ["aguardando", "ativar", "reativar", "cancelada", "caminho", "vendeubem", "ativa"]

rows = []
for ck, grp in led.groupby("ck"):
    deliv = int(grp.status.isin(DELIVERED).sum())
    transit = int(grp.status.isin(INTRANSIT).sum())
    pend = int(grp.status.isin(PENDING).sum())
    canc = int(len(grp) - deliv - transit - pend)
    env = deliv + transit
    rates = pd.to_numeric(grp.commission_rate, errors="coerce").dropna().tolist()
    med = sorted(rates)[len(rates) // 2] if rates else 0
    custo = env * CU + (FR if env > 0 else 0)
    pids = sampled.get(ck, set())
    sub = cp[(cp.ck == ck) & (cp.product_id.isin(pids))] if pids else cp.iloc[0:0]
    gmv_all = float(sub.gmv.sum())
    last = (sub[sub.gmv > 0].data.max() if (sub.gmv > 0).any() else "")
    # números por JANELA
    w = {}
    for k, _d in WINS:
        sw = sub[sub.data >= CUTW[k]]
        g = round(float(sw.gmv.sum()), 2); cm = round(float(sw.comissao.sum()), 2)
        w[k] = dict(gmv=g, com=cm, pedidos=int(sw.pedidos.sum()),
                    lucro=round(g * MG - cm - custo, 2), roas=round(g / custo, 1) if custo else 0)
    roas_all = gmv_all / custo if custo else 0
    ci = dmin(grp.convite_data.tolist()); cf = dmax(grp.convite_data.tolist())
    estagio = ("Recebida" if deliv > 0 else "A caminho" if transit > 0 else
               "Aguardando" if pend > 0 else "Cancelada" if canc > 0 else "—")
    flags = []
    if pend > 0: flags.append("aguardando")
    if transit > 0: flags.append("caminho")
    if canc > 0 and deliv == 0 and transit == 0 and pend == 0: flags.append("cancelada")
    if deliv > 0:
        flags.append("ativar" if gmv_all == 0 else "reativar" if (last and last < CUT14)
                     else "vendeubem" if roas_all >= 2 else "ativa")
    seg = next((s for s in PRIO if s in flags), "ativa")
    rows.append(dict(
        creator=grp.creator.iloc[0], nick=grp.nickname.iloc[0] or grp.creator.iloc[0],
        estagio=estagio, mes=(ci[:7] if ci else "—"), ci=ci or "—", cf=cf or "—",
        env=env, transit=transit, pend=pend, canc=canc, skus=int(grp.product_id.nunique()),
        faixa=8 if med < 0.115 else 12, custo=custo, last=last or "—",
        flags=flags, seg=seg, acao=ACAO[seg](pend, transit), w=w))

rows.sort(key=lambda r: (-r["w"]["90"]["gmv"], r["creator"]))
for i, r in enumerate(rows, 1):
    r["n"] = i
months = sorted({r["mes"] for r in rows if r["mes"] != "—"})
DATA = dict(rows=rows, months=months, hoje=TODAY.isoformat())

HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Protótipo · Seeding</title>
<style>
:root{--ink:#1a1a1a;--ink-48:#9b9b9b;--body:#444;--muted:#777;--canvas:#fafafa;--hairline:#ececec;
--rhode-red:#d83b3b;--green:#0a8a4f;--amber:#b45309;--blue:#2563eb;--violet:#7c3aed;--cyan:#0891b2;--card:#fff;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;background:#f4f4f5;color:var(--ink);padding:26px 30px;font-size:13.5px}
.mono{font-family:'JetBrains Mono','SF Mono',ui-monospace,monospace}
h1{font-size:19px;font-weight:680;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:12px;margin-top:3px}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0 16px}
.kc{background:var(--card);border:1px solid var(--hairline);border-radius:12px;padding:15px 18px;min-width:160px;flex:1}
.kc .l{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-48)}
.kc .v{font-size:25px;font-weight:680;margin-top:6px;letter-spacing:-.02em}
.kc .s{font-size:11px;color:var(--muted);margin-top:4px}
.kc.alert{border-color:#f3d3a0;background:#fffaf2}.kc.alert .v{color:var(--amber)}.kc.good .v{color:var(--green)}
.bar{display:flex;gap:14px;flex-wrap:wrap;align-items:center;background:#fff;border:1px solid var(--hairline);border-radius:11px;padding:11px 15px;margin-bottom:14px}
.grp{display:flex;gap:6px;align-items:center}
.grp .lab{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-48);margin-right:3px}
.pill-f{border:1px solid var(--hairline);background:#fff;border-radius:999px;padding:5px 12px;font-size:12.5px;cursor:pointer;user-select:none;transition:.12s}
.pill-f:hover{border-color:#cfcfcf}.pill-f.on{background:var(--ink);color:#fff;border-color:var(--ink)}
select,input[type=date]{border:1px solid var(--hairline);border-radius:8px;padding:6px 10px;font-size:12.5px;font-family:inherit;background:#fff;color:var(--ink);outline:none}
select:focus,input:focus{border-color:#bbb}
.sep{width:1px;height:22px;background:var(--hairline)}
.clr{font-size:12px;color:var(--blue);cursor:pointer;user-select:none}.clr:hover{text-decoration:underline}
.segbar{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-bottom:13px}
.seg{border:1px solid var(--hairline);background:#fff;border-radius:999px;padding:7px 14px;font-size:12.5px;cursor:pointer;display:flex;align-items:center;gap:7px;transition:.12s;user-select:none}
.seg:hover{border-color:#cfcfcf}.seg.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.seg .n{font-size:11px;opacity:.6;font-weight:600}.seg.on .n{opacity:.82}
.seg.ativar.on{background:var(--amber);border-color:var(--amber)}.seg.reativar.on{background:var(--blue);border-color:var(--blue)}
.seg.vendeubem.on{background:var(--green);border-color:var(--green)}.seg.aguardando.on{background:var(--violet);border-color:var(--violet)}
.seg.caminho.on{background:var(--cyan);border-color:var(--cyan)}.seg.cancelada.on{background:var(--rhode-red);border-color:var(--rhode-red)}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:13px;flex-wrap:wrap}
.search{flex:1;min-width:200px;max-width:320px;border:1px solid var(--hairline);border-radius:9px;padding:9px 13px;font-size:13px;outline:none;background:#fff}
.search:focus{border-color:#bbb}.meta{color:var(--ink-48);font-size:12px;margin-left:auto}
.card{background:var(--card);border:1px solid var(--hairline);border-radius:13px;margin-bottom:18px}
.card .h{padding:13px 18px;border-bottom:1px solid var(--hairline);font-weight:620;font-size:13.5px}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:10px 12px;font-size:10px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-48);border-bottom:1px solid var(--hairline);cursor:pointer;white-space:nowrap;user-select:none;position:sticky;top:0;background:#fff;z-index:1}
th:hover{color:var(--body)}th.on{color:var(--ink)}th .ar{font-size:9px;margin-left:2px}
th.num,td.num{text-align:right}
td{padding:9px 12px;border-bottom:1px solid #f5f5f5;white-space:nowrap}
tbody tr:hover{background:#fafafa}
.bd{display:inline-block;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:600}
.bd.rec{background:#e7f6ee;color:var(--green)}.bd.cam{background:#e0f2f7;color:var(--cyan)}
.bd.agu{background:#f1e9fd;color:var(--violet)}.bd.can{background:#fdeaea;color:var(--rhode-red)}.bd.nul{background:#f1f1f1;color:#888}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600}
.pill.ativar{color:var(--amber)}.pill.reativar{color:var(--blue)}.pill.vendeubem{color:var(--green)}
.pill.aguardando{color:var(--violet)}.pill.caminho{color:var(--cyan)}.pill.cancelada{color:var(--rhode-red)}.pill.ativa{color:var(--muted);font-weight:500}
.creator{font-weight:560}.handle{color:var(--ink-48);font-size:11px}
.neg{color:var(--rhode-red)}.pos{color:var(--green)}.z{color:#bbb}
.note{background:#fff;border:1px solid var(--hairline);border-radius:10px;padding:11px 15px;font-size:12px;color:var(--muted);line-height:1.55;margin-bottom:14px}
.mesgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:1px;background:var(--hairline);border-radius:0 0 13px 13px;overflow:hidden}
.mesc{background:#fff;padding:11px 14px;cursor:pointer}.mesc:hover{background:#fafafa}.mesc.on{background:#fff7ed}
.mesc .m{font-size:11px;color:var(--ink-48)}.mesc .g{font-size:16px;font-weight:640;color:var(--rhode-red);margin-top:3px}.mesc .s{font-size:11px;color:var(--muted);margin-top:2px}
</style></head><body>
<h1>Seeding <span style="color:var(--ink-48);font-weight:400">· protótipo v3</span></h1>
<div class="sub">Free sample real (API) · 1 painel consolidado · dados de __HOJE__ · ESTÁTICO (validação) · ao ir pro hub, atualiza diário</div>
<div class="kpis" id="kpis"></div>
<div class="bar">
  <div class="grp"><span class="lab">Janela</span>
    <span class="pill-f" data-win="30" onclick="setWin('30')">30d</span>
    <span class="pill-f" data-win="60" onclick="setWin('60')">60d</span>
    <span class="pill-f on" data-win="90" onclick="setWin('90')">90d</span>
    <span class="pill-f" data-win="0" onclick="setWin('0')">Tudo</span></div>
  <div class="sep"></div>
  <div class="grp"><span class="lab">Mês convite</span><select id="mes" onchange="MES=this.value;render()"></select></div>
  <div class="sep"></div>
  <div class="grp"><span class="lab">Período convite</span>
    <input type="date" id="de" onchange="render()"> <span style="color:var(--ink-48)">até</span> <input type="date" id="ate" onchange="render()"></div>
  <span class="clr" onclick="clearF()">limpar filtros</span>
</div>
<div class="note">💡 <b>Janela</b> escala GMV/ROAS/lucro (sales no período) · <b>Mês</b>/<b>Período</b> filtram por data do convite. <b>Lentes</b> (abaixo) = baldes de ação sobrepostos. <b>Ativar</b> = recebeu, nunca vendeu · <b>Reativar</b> = vendeu e esfriou (&lt;14d) · <b>Vendeu bem</b> = ROAS≥2 · <b>A caminho</b>/<b>Aguardando</b> = operacional. Custo = R$40/peça+R$25 frete · margem 55%. Cabeçalhos ordenam (↓ decrescente).</div>
<div class="segbar" id="segbar"></div>
<div class="toolbar"><input class="search" id="q" placeholder="🔎 buscar creator…" oninput="render()"><span class="meta" id="meta"></span></div>
<div class="card"><div class="tw"><table><thead><tr id="hr"></tr></thead><tbody id="tb"></tbody></table></div></div>
<div class="card"><div class="h">Resumo por mês do convite <span style="font-weight:400;color:var(--ink-48);font-size:12px">· clique pra filtrar</span></div><div class="mesgrid" id="mes2"></div></div>
<script>
const D=__DATA__;
let WIN='90', SEG='acao', MES='', SORT='gmv', DIR=-1;
const WF=new Set(['gmv','com','pedidos','lucro','roas']);
const v=(x,k)=>WF.has(k)?x.w[WIN][k]:x[k];
const SEGDEF=[['acao','⚡ Precisam de ação'],['ativar','🟡 Ativar'],['reativar','🔵 Reativar'],
['vendeubem','⭐ Vendeu bem'],['caminho','📦 A caminho'],['aguardando','⏳ Aguardando'],
['cancelada','✕ Cancelada'],['todas','Todas']];
const ACT=['ativar','reativar','aguardando','cancelada'];
const COLS=[['n','#','num'],['creator','Creator','t'],['estagio','Status','t'],['mes','Mês conv.','t'],
['ci','1º convite','t'],['cf','Últ. convite','t'],['env','Peças','num'],['transit','A cam.','num'],
['pend','Aguard.','num'],['canc','Canc.','num'],['skus','SKUs','num'],['faixa','Com.%','num'],
['pedidos','Pedidos','num'],['gmv','GMV atrib.','num'],['com','Comissão paga','num'],['custo','Custo','num'],
['lucro','Lucro líq.','num'],['roas','ROAS','num'],['last','Últ. venda','t'],['acao','Próxima ação','t']];
const fmtK=x=>{x=+x||0;const a=Math.abs(x);if(a>=1e6)return'R$ '+(x/1e6).toFixed(2)+'M';if(a>=1e3)return'R$ '+(x/1e3).toFixed(0)+'K';return'R$ '+x.toFixed(0);};
const RS=x=>'R$ '+(+x||0).toLocaleString('pt-BR',{maximumFractionDigits:0});
const Z=x=>x?x:'<span class="z">0</span>';
function setWin(w){WIN=w;document.querySelectorAll('[data-win]').forEach(b=>b.classList.toggle('on',b.dataset.win===w));render();}
function clearF(){MES='';document.getElementById('mes').value='';document.getElementById('de').value='';document.getElementById('ate').value='';document.getElementById('q').value='';SEG='acao';render();}
function tempBase(){ // filtra por MÊS + PERÍODO (data do convite) — contexto temporal
  const de=document.getElementById('de').value, ate=document.getElementById('ate').value;
  return D.rows.filter(x=>(!MES||x.mes===MES)&&(!de||(x.ci!=='—'&&x.ci>=de))&&(!ate||(x.ci!=='—'&&x.ci<=ate)));}
function kpis(base){
  const env=base.reduce((s,x)=>s+x.env,0),gmv=base.reduce((s,x)=>s+v(x,'gmv'),0),
        custo=base.reduce((s,x)=>s+x.custo,0),lucro=base.reduce((s,x)=>s+v(x,'lucro'),0),
        an=base.filter(x=>x.flags.some(f=>ACT.includes(f))).length;
  document.getElementById('kpis').innerHTML=[
   ['Peças enviadas',env.toLocaleString('pt-BR'),base.length+' creators',''],
   ['GMV atribuído',fmtK(gmv),'janela '+(WIN==='0'?'tudo':WIN+'d'),'good'],
   ['ROAS',(custo?(gmv/custo).toFixed(1):'0')+'x','custo '+fmtK(custo),''],
   ['Lucro líquido',fmtK(lucro),'margem 55% − com. − custo',''],
   ['⚡ Precisam de ação',an,'ativar+reativar+aguard.+cancel.','alert'],
  ].map(([l,val,s,c])=>`<div class="kc ${c}"><div class="l">${l}</div><div class="v">${val}</div><div class="s">${s}</div></div>`).join('');}
function segbar(base){
  const cnt=f=>f==='todas'?base.length:f==='acao'?base.filter(x=>x.flags.some(g=>ACT.includes(g))).length:base.filter(x=>x.flags.includes(f)).length;
  document.getElementById('segbar').innerHTML=SEGDEF.map(([k,l])=>
   `<div class="seg ${k} ${SEG===k?'on':''}" onclick="SEG='${k}';render()">${l} <span class="n">${cnt(k)}</span></div>`).join('');}
function header(){document.getElementById('hr').innerHTML=COLS.map(([k,l,t])=>
 `<th class="${t==='num'?'num ':''}${SORT===k?'on':''}" onclick="sortBy('${k}')">${l}<span class="ar">${SORT===k?(DIR<0?'↓':'↑'):''}</span></th>`).join('');}
function sortBy(k){if(SORT===k)DIR=-DIR;else{SORT=k;DIR=['creator','estagio','mes','ci','cf','last','acao'].includes(k)?1:-1;}render();}
const STB={Recebida:'rec','A caminho':'cam',Aguardando:'agu',Cancelada:'can','—':'nul'};
const ICON={ativar:'🟡',reativar:'🔵',vendeubem:'⭐',aguardando:'⏳',caminho:'📦',cancelada:'✕',ativa:'•'};
function render(){
  const base=tempBase(); kpis(base); segbar(base); header();
  let r=base.slice();
  if(SEG==='acao')r=r.filter(x=>x.flags.some(f=>ACT.includes(f)));
  else if(SEG!=='todas')r=r.filter(x=>x.flags.includes(SEG));
  const q=document.getElementById('q').value.trim().toLowerCase();
  if(q)r=r.filter(x=>(x.creator+' '+x.nick).toLowerCase().includes(q));
  r.sort((a,b)=>{let av=v(a,SORT),bv=v(b,SORT);if(typeof av==='string')return DIR*av.localeCompare(bv);return DIR*((av||0)-(bv||0));});
  const sc=(COLS.find(c=>c[0]===SORT)||[])[1];
  document.getElementById('meta').textContent=r.length+' creators · '+sc+' '+(DIR<0?'↓':'↑');
  document.getElementById('tb').innerHTML=r.map(x=>`<tr>
   <td class="num mono" style="color:var(--ink-48)">${x.n}</td>
   <td><span class="creator">${x.nick}</span><br><span class="handle">@${x.creator}</span></td>
   <td><span class="bd ${STB[x.estagio]||'nul'}">${x.estagio}</span></td>
   <td class="mono">${x.mes}</td><td class="mono">${x.ci}</td><td class="mono">${x.cf}</td>
   <td class="num mono">${x.env}</td><td class="num mono">${Z(x.transit)}</td>
   <td class="num mono">${Z(x.pend)}</td><td class="num mono">${Z(x.canc)}</td>
   <td class="num mono">${x.skus}</td><td class="num mono">${x.faixa}%</td>
   <td class="num mono">${v(x,'pedidos').toLocaleString('pt-BR')}</td>
   <td class="num mono" style="font-weight:600;color:var(--rhode-red)">${RS(v(x,'gmv'))}</td>
   <td class="num mono">${RS(v(x,'com'))}</td><td class="num mono">${RS(x.custo)}</td>
   <td class="num mono ${v(x,'lucro')<0?'neg':'pos'}">${RS(v(x,'lucro'))}</td>
   <td class="num mono">${x.custo>0?v(x,'roas')+'x':'—'}</td><td class="mono">${x.last}</td>
   <td><span class="pill ${x.seg}">${ICON[x.seg]||''} ${x.acao}</span></td></tr>`).join('')
   ||`<tr><td colspan="${COLS.length}" style="text-align:center;color:var(--ink-48);padding:30px">Nada neste recorte 🎉</td></tr>`;
  mes2(base);
}
function mes2(base){
  const by={};base.forEach(x=>{const o=by[x.mes]||(by[x.mes]={cre:0,env:0,gmv:0});o.cre++;o.env+=x.env;o.gmv+=v(x,'gmv');});
  const ms=Object.entries(by).sort((a,b)=>(a[0]==='—')-(b[0]==='—')||a[0].localeCompare(b[0]));
  document.getElementById('mes2').innerHTML=ms.map(([m,o])=>
   `<div class="mesc ${MES===m?'on':''}" onclick="MES=(MES==='${m}'?'':'${m}');document.getElementById('mes').value=MES;render()">
     <div class="m">${m}</div><div class="g">${fmtK(o.gmv)}</div><div class="s">${o.cre} creators · ${o.env} peças</div></div>`).join('');}
document.getElementById('mes').innerHTML='<option value="">Todos</option>'+D.months.map(m=>`<option value="${m}">${m}</option>`).join('');
render();
</script></body></html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__HOJE__", TODAY.isoformat()), encoding="utf-8")
print("OK:", OUT)
print(f"creators={len(rows)} | meses={len(months)} | janelas={[k for k,_ in WINS]}")
