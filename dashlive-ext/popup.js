"use strict";
const KEY = "dashlive";
const LIB = self.DashLiveLib;
const BENCH_SRC = LIB.getBenchmarkSource();   // benchmarks.js — fonte única, sem constante local
const SYNC_URL = "https://dash.rhodejeans.com.br/api/get-hub";
const VERSAO = "1.2.0";
const FW_NAMES = { urgencia:"Urgência (escassez real)", flash:"Flash sale (janela curta)", bundle:"Bundle (escada de valor)", prova:"Prova social ao vivo", rehook:"Re-hook (quem chegou agora)", retencao:"Retenção (segurar audiência)" };

let state = null;
let tick = null;

function defaults(){
  return { goal:0, plannedMin:240, startTime:null, endTime:null, snapshots:[], events:[], frameworksUsed:[], violations:[],
    current:{err:null,impressions:null,clicks:null,viewers:null,liveViewers:null,ctr:null,co:null,gmv:null,orders:null,comments:null,t:null}, calib:{}, lastSnapAt:null, cueSheet:null, ctrProfile:null, demo:false,
    ui:{x:null,y:null,min:false,hidden:false,tab:"monitor"} };
}
function load(cb){ chrome.storage.local.get(KEY, r=>{ state=Object.assign(defaults(), r[KEY]||{}); cb&&cb(); }); }
function save(){ chrome.storage.local.set({[KEY]:state}); }

const $ = id => document.getElementById(id);
function hhmmss(ms){ const s=Math.max(0,Math.floor(ms/1000)),h=Math.floor(s/3600),m=Math.floor(s%3600/60),ss=s%60,p=x=>String(x).padStart(2,"0"); return `${p(h)}:${p(m)}:${p(ss)}`; }
function avg(a){ const v=a.filter(x=>x!=null&&!isNaN(x)); return v.length? v.reduce((x,y)=>x+y,0)/v.length : 0; }

function reflect(){
  const running = state.startTime && !state.endTime;
  const ended = state.startTime && state.endTime;
  $("status").classList.toggle("live", !!running);
  $("statusLbl").textContent = running ? "Ao vivo" : ended ? "Encerrada" : "Fora do ar";
  $("setupBlock").classList.toggle("hide", !!running);
  $("liveBlock").classList.toggle("hide", !running);
  if(state.startTime){ const end=state.endTime||Date.now(); $("statusTm").textContent=hhmmss(end-state.startTime); }
  else $("statusTm").textContent="";
  $("btnToggle") && ($("btnToggle").textContent = state.ui && state.ui.hidden ? "Mostrar painel" : "Ocultar painel");
}

function startLive(){
  const goal = parseFloat(($("goal").value||"").replace(",",".")); const dur = +$("dur").value;
  if(!goal || goal<=0){ $("goal").focus(); $("goal").style.borderColor="#FF4D4D"; return; }
  state = Object.assign(defaults(), { calib: state.calib||{}, ui: state.ui||defaults().ui });
  state.goal=goal; state.plannedMin=dur; state.startTime=Date.now(); state.endTime=null;
  save(); reflect();
}
function endLive(){
  if(!state.startTime) return;
  state.endTime=Date.now(); save(); reflect();
  if(adminToken) pushReport(true);   // DoD: encerrar a live grava o relatório
}

function reportObj(){
  const s=state.current||{}; const snaps=state.snapshots||[];
  const peak = snaps.reduce((m,x)=>Math.max(m,x.viewers||0),0);
  const ctrM=+avg(snaps.map(x=>x.ctr)).toFixed(2), coM=+avg(snaps.map(x=>x.co)).toFixed(2);
  const ticket = (s.orders>0 && s.gmv!=null) ? +(s.gmv/s.orders).toFixed(2) : 0;
  // Régua usada no julgamento — sem ela o relatório não é comparável com outro mês (R11).
  const bench = state.ctrProfile ? LIB.resolveBenchmarks(BENCH_SRC, state.ctrProfile) : null;
  return {
    meta:state.goal, inicio:state.startTime?new Date(state.startTime).toISOString():null, fim:state.endTime?new Date(state.endTime).toISOString():null,
    duracao_h:+(((state.endTime||Date.now())-(state.startTime||Date.now()))/3600000).toFixed(2),
    gmv_final:s.gmv||0, pct_meta: state.goal? Math.round((s.gmv||0)/state.goal*100):0,
    pico_viewers:peak,
    err_medio:+avg(snaps.map(x=>x.err)).toFixed(2),
    ctr_medio:ctrM, co_medio:coM,   // CO é medido (lives.ctor) — não é mais derivado/provisório
    conv_por_visualizacao_medio:+(LIB.deriveConvView(ctrM,coM)||0).toFixed(3),  // DERIVADO
    ticket_medio:ticket, pedidos:s.orders||0,
    ctr_perfil: state.ctrProfile || null,
    bench_janela: bench && bench.janela ? `${bench.janela.de}→${bench.janela.ate} (${bench.janela.lives} lives)` : null,
    bench_gerado_em: BENCH_SRC.gerado_em || null,
    versao: VERSAO,
    snapshots:snaps,
    frameworks_usados:(state.frameworksUsed||[]).map(f=>({key:f.key,nome:FW_NAMES[f.key]||f.key,t:new Date(f.t).toISOString()})),
    violacoes:(state.violations||[]).map(v=>({t:new Date(v.t).toISOString(),motivo:v.motivo,acao:v.acao||null}))
  };
}
function exportReport(){
  const data = JSON.stringify(reportObj(), null, 2);
  const blob = new Blob([data], {type:"application/json"});
  const a = document.createElement("a"); a.href=URL.createObjectURL(blob);
  a.download = "dashlive-relatorio-"+new Date(state.startTime||Date.now()).toISOString().slice(0,10)+".json";
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
  const b=$("btnExport"); const o=b.textContent; b.textContent="Baixado ✓"; setTimeout(()=>b.textContent=o,1400);
}
/* ============ sync com o Supabase (via /api/get-hub, service_role no servidor) ============
   O token vem de admin_login (mesma senha do painel admin) e fica no storage local do
   operador. A extensão nunca vê a service key — mesmo contrato do resto do projeto.
   O JSON continua saindo sempre: se a rede falhar, a live não fica sem relatório. */
const AUTH_KEY = "dashlive_auth";
let adminToken = null;

function loadAuth(cb){ chrome.storage.local.get(AUTH_KEY, r => { adminToken=(r[AUTH_KEY]||{}).token||null; cb&&cb(); }); }
function saveAuth(t){ adminToken=t; chrome.storage.local.set({[AUTH_KEY]:{token:t}}); }

function setSync(msg, cls){
  const n=$("syncNote"); if(!n) return;
  n.textContent=msg;
  n.style.color = cls==="ok" ? "#2ECC71" : cls==="err" ? "#FF4D4D" : "";
}
function reflectSync(){
  const on=!!adminToken;
  $("syncAuth").classList.toggle("hide", on);
  $("btnSync").classList.toggle("hide", !on || !state.startTime);
  if(on && !$("syncNote").dataset.busy)
    setSync("Conectado — ao encerrar, o relatório vai pro Supabase automaticamente.", "ok");
}

async function post(payload){
  const r = await fetch(SYNC_URL, {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)
  });
  const j = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}

async function connect(){
  const pass=($("pass").value||"").trim(); if(!pass){ $("pass").focus(); return; }
  setSync("Conectando…");
  try {
    const j = await post({ action:"admin_login", pass });
    if(!j.token) throw new Error("sem token");
    saveAuth(j.token); $("pass").value=""; reflectSync();
    setSync("Conectado — ao encerrar, o relatório vai pro Supabase automaticamente.", "ok");
  } catch(e){ setSync("Falhou: "+e.message, "err"); }
}

async function pushReport(auto){
  if(!adminToken){ setSync("Conecte primeiro para gravar no Supabase.", "err"); return false; }
  if(!state.startTime){ setSync("Nenhuma live para enviar.", "err"); return false; }
  // Dado fabricado não vira histórico. Sai do demo (aba Dados) antes de gravar.
  if(state.demo){ setSync("Modo demo ligado — não gravo números fabricados.", "err"); return false; }
  const n=$("syncNote"); n.dataset.busy="1"; setSync(auto?"Encerrando e gravando…":"Enviando…");
  try {
    const j = await post({ action:"live_monitor", adminToken, relatorio:reportObj() });
    setSync(`Gravado ✓ ${j.snapshots} snapshot(s) · ${j.id}`, "ok");
    return true;
  } catch(e){
    // 401 = token expirado/senha trocada: derruba pra pedir a senha de novo.
    if(/não autorizado|401/i.test(e.message)){ saveAuth(null); reflectSync(); }
    setSync("Não gravou: "+e.message+" — exporte o JSON.", "err");
    return false;
  } finally { delete n.dataset.busy; }
}

function toggleOverlay(){ state.ui=state.ui||defaults().ui; state.ui.hidden=!state.ui.hidden; save(); reflect(); }

document.addEventListener("DOMContentLoaded", ()=>{
  load(()=>{ loadAuth(()=>{
    reflect(); reflectSync();
    $("btnAuth").onclick=connect;
    $("pass").addEventListener("keydown",e=>{ if(e.key==="Enter") connect(); });
    $("btnSync").onclick=()=>pushReport(false);
    $("btnStart").onclick=startLive;
    $("btnEnd").onclick=()=>{ if(confirm(adminToken?"Encerrar a live? O relatório será gravado no Supabase.":"Encerrar a live e liberar o relatório?")) endLive(); };
    $("btnExport").onclick=exportReport;
    $("btnToggle").onclick=toggleOverlay;
    $("goal").addEventListener("keydown",e=>{ if(e.key==="Enter") startLive(); });
    tick=setInterval(()=>{ if(state && state.startTime && !state.endTime){ $("statusTm").textContent=hhmmss(Date.now()-state.startTime); } }, 1000);
  }); });
  chrome.storage.onChanged.addListener((ch,area)=>{ if(area==="local"&&ch[KEY]){ state=Object.assign(defaults(),ch[KEY].newValue||{}); reflect(); reflectSync(); } });
});
