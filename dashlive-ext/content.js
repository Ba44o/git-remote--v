"use strict";
/* DashLive · Monitor Ao Vivo — content script (v1.1)
   Alinhado ao guia oficial de métricas de lives do TikTok Shop BR:
   modelo GMV = Impressões × GPM · funil ERR → CTR → CO → AOV · prioridade ⭐⭐⭐/⭐⭐/⭐.
   Lê as métricas calibradas direto do DOM do Seller Center e roda o semáforo em cascata. */
(() => {
  if (window.__dashliveLoaded) return;
  window.__dashliveLoaded = true;

  /* ===== benchmarks — fonte única (benchmarks.js, gerado da tabela `lives`) =====
     Nada de constante chumbada aqui: os números saem de gerar_benchmarks_live.py.
     Dois perfis, porque o CTR da tela troca de denominador conforme a versão do
     Seller Center (R11) — o perfil ativo é DETECTADO, nunca presumido. */
  // Se lib.js/benchmarks.js falharem por qualquer motivo, o painel NÃO pode morrer
  // junto: um TypeError aqui mata o content script inteiro e a tela fica sem nada,
  // sem erro visível pro operador. Melhor abrir com bench de fallback e avisar.
  const LIB = self.DashLiveLib;
  if (!LIB) { console.error("[DashLive] lib.js não carregou — verifique a ordem em content_scripts do manifest."); return; }
  const BENCH_SRC = LIB.getBenchmarkSource();
  let BM = null;                                                  // bench do perfil ativo
  let BM_DET = { profile:null, method:"sem-ctr", confident:false }; // como foi decidido

  function resolveProfile(){
    const s = state.current;
    // "CTR por LIVE" já declara o denominador — vale mais que qualquer inferência.
    const peloRotulo = state.calib.ctr && state.calib.ctr.perfilCtr;
    if (peloRotulo){
      state.ctrProfile = peloRotulo;
      BM_DET = { profile:peloRotulo, method:"rotulo", confident:true };
      BM = LIB.resolveBenchmarks(BENCH_SRC, peloRotulo);
      return BM;
    }
    const det = LIB.detectCtrProfile(
      { ctr:s.ctr, clicks:s.clicks, views:s.viewers, impressions:s.impressions }, BENCH_SRC);
    BM_DET = det;
    // Troca de perfil só com prova (identidade) ou na primeira vez: sem isso o
    // painel oscilaria de bench a cada tick quando a leitura ficasse ambígua.
    if (det.profile && (det.confident || !state.ctrProfile) && state.ctrProfile !== det.profile){
      state.ctrProfile = det.profile;
    }
    BM = state.ctrProfile ? LIB.resolveBenchmarks(BENCH_SRC, state.ctrProfile) : null;
    return BM;
  }
  const benchPct  = v => v==null ? "—" : pct1(v)+"%";
  const benchBRL  = v => v==null ? "—" : fmtBRL(v);

  /* ===== frameworks (voz de operador, PT-BR) ===== */
  const FRAMEWORKS = {
    urgencia:{ name:"Urgência (escassez real)", icon:"⏳",
      script:`"Gente, restam X peças nessa numeração. Quando acabar, acabou — sem reposição essa semana. Quem tá na dúvida, garante agora que eu não seguro."` },
    flash:{ name:"Flash sale (janela curta)", icon:"⚡",
      script:`"Próximos 10 minutos: [SKU] por R$XX,XX. Só nessa janela. Passou do horário, volta pro preço cheio. Corre no link fixado."` },
    bundle:{ name:"Bundle (escada de valor)", icon:"🎁",
      script:`"Fecha o look: [peça A] + [peça B] por R$XXX em vez de R$YYY separado. Economiza R$ZZ e já vai montada. Combo no link."` },
    prova:{ name:"Prova social ao vivo", icon:"🔥",
      script:`"Óh, a [nome] fechou 2. A [nome] levou o kit. Já são X pedidos só nessa live. Se todo mundo garante é porque o caimento entrega."` },
    rehook:{ name:"Re-hook (quem chegou agora)", icon:"🔁",
      script:`"Quem chegou agora: tá rolando [oferta]. Deixa eu mostrar rapidão o produto e por que ele some do estoque." (repete o gancho)` },
    retencao:{ name:"Retenção (segurar audiência)", icon:"🧲",
      script:`"Fica mais 5 comigo que daqui a pouco solto o [SKU desejado] no melhor preço da live. Quem sair perde. Comenta 🔥 quem espera."` }
  };

  /* ===== métricas calibráveis (ordem do funil) ===== */
  const METRICS = [
    // Ordem = o que a tela do Console de LIVE realmente mostra, do essencial ao extra.
    // Tudo que pode não existir na tela é opcional: melhor pular do que calibrar errado.
    { key:"gmv",         label:"GMV atribuído (R$)",                 type:"money", star:3 },
    { key:"orders",      label:"Pedidos — NÃO é \"itens\"",           type:"int",   star:2 },
    { key:"liveViewers", label:"Espectadores ao vivo (agora)",       type:"int",   star:2, opt:true },
    { key:"ctr",         label:"% de cliques no produto (CTR)",      type:"pct",   star:2, opt:true },
    { key:"clicks",      label:"Cliques no produto",                 type:"int",   star:2, opt:true },
    { key:"co",          label:"Compra após clique — CO (%)",        type:"pct",   star:2, opt:true },
    { key:"convView",    label:"Taxa de pedidos (SKU) / conversão por visualização", type:"pct", star:2, opt:true },
    { key:"viewers",     label:"Views acumuladas (se a tela tiver)", type:"int",   star:2, opt:true },
    { key:"impressions", label:"Impressões da live",                 type:"int",   star:3, opt:true },
    { key:"err",         label:"ERR — taxa de entrada",              type:"pct",   star:2, opt:true, prov:true },
    { key:"comments",    label:"Comentários",                        type:"int",   star:1, opt:true }
  ];

  const CUE_TYPES = ["Gerador de Tráfego", "Herói", "Valor Agregado"];
  const CUE_DEFAULT = [
    { nome:"Isca — SKU âncora", tipo:"Gerador de Tráfego", hook:"Preço de entrada pra puxar tráfego e ativar GMV Max", preco:"65,90" },
    { nome:"Wide Leg Marmorizada", tipo:"Herói", hook:"Parei de comprar jeans barato quando achei esse caimento", preco:"89,90" },
    { nome:"Wide Leg Amarela (limitada)", tipo:"Herói", hook:"Essa cor é lote limitado — não volta", preco:"89,90" },
    { nome:"Baggy Marmorizada", tipo:"Herói", hook:"Mesmo tecido da wide, pegada mais larga", preco:"89,90" },
    { nome:"Mom Marmorizada", tipo:"Valor Agregado", hook:"Cintura alta que valoriza e não marca", preco:"79,90" },
    { nome:"Bucket Hat (beirada)", tipo:"Valor Agregado", hook:"Fecha o look, entra no combo", preco:"39,90" }
  ];

  const KEY = "dashlive";
  let state = null, readInt = null, uiInt = null, orfao = false;

  /* ===== contexto órfão =====
     Quando a extensão é recarregada (ou atualizada pelo Chrome), o content script
     que já estava na página perde a ligação com ela: qualquer chamada a
     chrome.storage passa a lançar "Extension context invalidated".
     O perigo não é o erro — é o que vinha depois: o painel continuava na tela com
     os últimos números, parecendo ao vivo, sem ler mais nada. Num live isso é pior
     que sumir. Agora ele para os timers e diz o que houve. */
  function contextoVivo(){
    try { return !!(chrome.runtime && chrome.runtime.id); } catch(e){ return false; }
  }
  function marcarOrfao(){
    if (orfao) return;
    orfao = true;
    if (readInt){ clearInterval(readInt); readInt = null; }
    if (uiInt){ clearInterval(uiInt); uiInt = null; }
    try { renderOrfao(); } catch(e){}
  }
  function renderOrfao(){
    if (!root) return;
    const body = root.getElementById("dl-body"); if (!body) return;
    const panel = root.getElementById("dl-panel"); if (panel) panel.style.display = "block";
    body.innerHTML = `<div class="orfao"><b>Painel desconectado</b>
      A extensão foi recarregada ou atualizada e esta aba ficou com a versão antiga.
      Os números pararam de atualizar — <b>não são mais ao vivo</b>.
      <button id="dl-reload">Recarregar a página</button>
      <span class="dica">Se estiver transmitindo por esta aba, abra a live numa aba nova em vez de recarregar.</span></div>`;
    const b = body.querySelector("#dl-reload");
    if (b) b.onclick = () => location.reload();
  }

  /* ================= storage ================= */
  function defaults(){
    return { goal:0, plannedMin:240, startTime:null, endTime:null,
      snapshots:[], events:[], frameworksUsed:[], violations:[],
      current:{ err:null,impressions:null,clicks:null,viewers:null,liveViewers:null,ctr:null,co:null,convView:null,gmv:null,orders:null,comments:null, t:null },
      calib:{}, lastSnapAt:null, cueSheet:null, ctrProfile:null, demo:false,
      ui:{ x:null, y:null, min:false, hidden:false, tab:"monitor" } };
  }
  function migrate(s){
    const d = defaults();
    s = Object.assign(d, s||{});
    s.ui = Object.assign(d.ui, s.ui||{});
    s.current = Object.assign(d.current, s.current||{});
    s.violations = s.violations || [];
    if (!Array.isArray(s.cueSheet)) s.cueSheet = JSON.parse(JSON.stringify(CUE_DEFAULT));
    s.cueSheet = s.cueSheet.map(c => Object.assign({ nome:"", tipo:"Herói", hook:"", preco:"" }, c));
    return s;
  }
  function loadState(cb){
    if (!contextoVivo()) return marcarOrfao();
    try {
      chrome.storage.local.get(KEY, r => {
        if (chrome.runtime.lastError) return marcarOrfao();
        state = migrate(r[KEY]); cb && cb();
      });
    } catch(e){ marcarOrfao(); }
  }
  function saveState(){
    if (orfao) return;
    if (!contextoVivo()) return marcarOrfao();
    try { chrome.storage.local.set({ [KEY]: state }); } catch(e){ marcarOrfao(); }
  }

  try {
    chrome.storage.onChanged.addListener((ch, area) => {
      if (orfao) return;
      if (area==="local" && ch[KEY]) {
        state = migrate(ch[KEY].newValue);
        applyLiveLoop(); render();
      }
    });
  } catch(e){ marcarOrfao(); }

  /* ================= number parsing ================= */
  // Implementação única em lib.js (coberta por tests/test_dashlive_lib.mjs).
  const parseTyped = (raw, type) => LIB.parseNumberPtBR(raw, type);

  /* ================= DOM locator ================= */
  function cssPath(el){
    if (!el || el.nodeType!==1) return null;
    if (el.id) return "#"+CSS.escape(el.id);
    const parts=[]; let node=el, depth=0;
    while (node && node.nodeType===1 && node!==document.body && depth<7){
      let sel = node.nodeName.toLowerCase();
      const parent = node.parentNode;
      if (parent){ const sib = Array.from(parent.children).filter(c=>c.nodeName===node.nodeName);
        if (sib.length>1) sel += `:nth-of-type(${sib.indexOf(node)+1})`; }
      parts.unshift(sel); node=parent; depth++;
    }
    return parts.join(">");
  }
  // O painel do TikTok é React: o seletor CSS capturado na calibração morre no
  // primeiro re-render e a métrica passa a ler "—" sem avisar. O RÓTULO, esse
  // sobrevive — então ele vira a âncora principal e o seletor fica de reserva
  // (útil quando o operador aponta um número que não tem rótulo ao lado).
  function acharRotulo(label){
    const alvo = LIB.normalizarRotulo(label);
    if (!alvo) return null;
    const cands = Array.from(document.querySelectorAll("body *")).filter(el =>
      !elDoPainel(el) && el.children.length<=3 && visivel(el) &&
      LIB.normalizarRotulo(el.textContent)===alvo);
    // o mais alto na tela: mesma regra do mapeamento, senão a leitura ao vivo
    // poderia ancorar num rótulo repetido dentro da tabela
    cands.sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top);
    return cands[0]||null;
  }
  function prof(el){ let n=0; while((el=el.parentElement)) n++; return n; }

  // Duas vias, nesta ordem: o irmão do rótulo (limpo na maioria dos cards) e,
  // se ele vier vazio ou envenenado (contador animado), o texto do CARD inteiro
  // menos o rótulo — que é como "CTR por LIVE6,57%7,61%" entrega 6,57.
  function textoValorDe(rotEl, tipo){
    const alvo = valorPertoDe(rotEl);
    if (alvo){
      const t = textoVisivelDe(alvo).trim();
      if (parseTyped(t, tipo)!=null) return t;
    }
    const rot = (rotEl.textContent||"").trim();
    let node = rotEl;
    for (let up=0; up<3 && node; up++){
      const cont = node.parentElement;
      if (!cont || cont===document.body) break;
      const inteiro = textoVisivelDe(cont).trim();
      if (inteiro.startsWith(rot) && inteiro.length>rot.length){
        const resto = inteiro.slice(rot.length).trim();
        if (parseTyped(resto, tipo)!=null) return resto;
      }
      node = cont;
    }
    return null;
  }

  function readMetric(m){
    const c = state.calib[m.key];
    if (!c) return null;
    if (c.label){
      const rot = acharRotulo(c.label);
      if (rot){ const t = textoValorDe(rot, m.type); if (t!=null){ const n = parseTyped(t, m.type); if (n!=null) return n; } }
    }
    if (c.selector){
      let el=null; try { el = document.querySelector(c.selector); } catch(e){ el=null; }
      if (el && !elDoPainel(el)) return parseTyped(el.textContent, m.type);
    }
    return null;
  }

  /* ================= auto-mapeamento da tela =================
     O TikTok ofusca as classes, mas não os rótulos: "GMV atribuído", "Cliques no
     produto", "Espectadores ativos" são texto em português e mudam pouco. A extensão
     varre a página, reconhece o que consegue e só deixa o resto pro clique manual.
     Calibração manual continua valendo e sempre vence a automática. */
  function elDoPainel(el){ return host && (el===host || host.contains(el)); }

  // Contador animado do TikTok: cada dígito é uma coluna com o valor ANTIGO em
  // position:static e o NOVO por cima em position:absolute. textContent junta os
  // dois — o card mostrando 71 entrega "8781" (8→7 e 8→1).
  //
  // Percorre childNodes, não children: o número vem partido entre texto solto e
  // elementos ("14" + text ".48" + <span>K</span>), e olhar só os elementos come
  // o ".48". E o absoluto só substitui quando COBRE um estático na mesma coluna;
  // sem isso, os decimais (que não têm nada por cima) eram descartados.
  function textoVisivelDe(no, prof){
    prof = prof || 0;
    if (!no) return "";
    if (no.nodeType === 3) return no.nodeValue || "";        // texto solto
    if (no.nodeType !== 1) return "";
    if (prof > 8) return no.textContent || "";
    const filhos = Array.from(no.childNodes);
    if (!filhos.length) return no.textContent || "";

    let info;
    try {
      info = filhos.map(n => n.nodeType === 1
        ? { n, r:n.getBoundingClientRect(), pos:getComputedStyle(n).position }
        : { n, r:null, pos:"texto" });
    } catch(e){ return no.textContent || ""; }

    const abs = info.filter(x => x.pos === "absolute" && x.r && x.r.width > 0);
    if (!abs.length) return filhos.map(n => textoVisivelDe(n, prof+1)).join("");

    const out = [], usados = new Set();
    for (const x of info){
      if (x.pos === "absolute") continue;
      if (x.r){
        const cobre = abs.find(a => !usados.has(a.n) && Math.abs(a.r.left - x.r.left) <= 2);
        if (cobre){ usados.add(cobre.n); out.push(textoVisivelDe(cobre.n, prof+1)); continue; }
      }
      out.push(textoVisivelDe(x.n, prof+1));
    }
    for (const a of abs) if (!usados.has(a.n)) out.push(textoVisivelDe(a.n, prof+1));
    return out.join("");
  }
  function visivel(el){
    if (!el || !el.getBoundingClientRect) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  // Num card de KPI o valor é IRMÃO do rótulo, quase sempre logo abaixo.
  // Duas coisas que a primeira versão errava:
  //  · varria todos os descendentes do container e pegava o primeiro com dígito —
  //    num card com ícone ou badge numerado, pegava o lixo;
  //  · pegava só folhas, mas o TikTok quebra o número em pedaços ("402" + ".62"),
  //    então a folha traz "402" e o valor sai errado. Lendo o irmão inteiro, o
  //    textContent junta os pedaços de volta.
  function valorPertoDe(rotEl){
    const txtRot = LIB.normalizarRotulo(rotEl.textContent);
    let node = rotEl;
    for (let up=0; up<3 && node; up++){
      const cont = node.parentElement;
      if (!cont || cont===document.body) break;
      const irmaos = Array.from(cont.children).filter(x => x!==node && !elDoPainel(x) && visivel(x));
      // depois do rótulo primeiro: em card, o valor vem embaixo
      const pos = x => (node.compareDocumentPosition(x) & Node.DOCUMENT_POSITION_FOLLOWING) ? 0 : 1;
      irmaos.sort((a,b)=>pos(a)-pos(b));
      for (const cand of irmaos){
        const t = (cand.textContent||"").trim();
        if (!t || t.length>28 || !/\d/.test(t)) continue;
        if (LIB.normalizarRotulo(t) === txtRot) continue;      // é outra cópia do rótulo
        return cand;
      }
      node = cont;
    }
    return null;
  }

  function mapearTela(){
    const achados = {};
    // Ordem VISUAL, não estrutural. Ordenar por profundidade fazia o mapa ler a
    // tabela de produtos do rodapé — cada célula é mais funda que os cards de
    // resumo, e as colunas repetem os mesmos nomes ("Pedidos de SKU", "Taxa de
    // pagamento") com valor por linha. Daí os zeros. Os cards ficam no topo, então
    // varrer de cima pra baixo resolve, e o filtro de visibilidade descarta o que
    // está em aba fechada ou fora de tela.
    const folhas = Array.from(document.querySelectorAll("body *"))
      // <=3 filhos: "GMV (R$)" vem como <div><span>GMV</span><span>(R$)</span></div>
      // e ficava de fora com o limite antigo. O ruído que isso abre (card inteiro
      // com valor colado) é barrado pelo ehRotuloPuro, que recusa texto terminado
      // em número ou %.
      .filter(el => el.children.length<=3 && !elDoPainel(el) && visivel(el))
      .map(el => { const r = el.getBoundingClientRect(); return { el, top:Math.round(r.top), left:Math.round(r.left) }; })
      .sort((a,b) => a.top-b.top || a.left-b.left)
      .map(x => x.el);
    for (const el of folhas){
      const txt = (el.textContent||"").trim();
      if (!txt || txt.length>60 || /^\d/.test(txt)) continue;   // valor não é rótulo
      const key = LIB.metricaDoRotulo(txt);
      if (!key || achados[key]) continue;                        // 1º achado ganha
      const m = METRICS.find(x=>x.key===key);
      if (!m) continue;
      const texto = textoValorDe(el, m.type);
      if (texto==null || LIB.ehValorSuspeito(texto)) continue;
      const val = parseTyped(texto, m.type);
      if (val==null) continue;
      const alvo = valorPertoDe(el);
      achados[key] = { selector: alvo?cssPath(alvo):null, label:txt,
                       sample: texto.slice(0,40), origem:"auto", val,
                       perfilCtr: key==="ctr" ? LIB.perfilPeloRotulo(txt) : undefined };
    }
    return achados;
  }

  // Só preenche o que ainda não existe: calibração feita na mão nunca é sobrescrita.
  function aplicarAutoMapa(){
    const achados = mapearTela();
    let novos = 0;
    for (const [k,v] of Object.entries(achados)){
      if (state.calib[k] && state.calib[k].origem!=="auto") continue;
      state.calib[k] = v; novos++;
    }
    state.autoMapAt = Date.now();
    saveState(); readTick(); render();
    return { novos, total:Object.keys(achados).length };
  }

  /* ================= health — cascata do funil ================= */
  function elapsedMin(){ if(!state.startTime) return 0; const end=state.endTime||Date.now(); return (end-state.startTime)/60000; }
  function grade(r,warnAt,badAt){ if(r>=warnAt) return "good"; if(r>=badAt) return "warn"; return "bad"; }
  function lastSnap(){ return state.snapshots.length ? state.snapshots[state.snapshots.length-1] : null; }
  function trendGrade(cur, ref, warn, bad){ if(ref==null||ref<=0||cur==null) return {grade:"good", drop:0};
    const drop=(cur-ref)/ref; return { grade: drop>=warn?"good":drop>=bad?"warn":"bad", drop }; }

  function evaluateHealth(){
    const s = state.current;
    if (s.gmv==null && s.viewers==null && s.liveViewers==null && s.err==null && s.ctr==null) return null;
    const d = {}; const ref = lastSnap();
    resolveProfile();                       // define BM/BM_DET antes de qualquer comparação
    const B = BM || {};
    d.bench = { profile: state.ctrProfile, det: BM_DET, janela: B.janela||null, stale: !!B.stale };

    // ⭐⭐⭐ desfecho: ritmo de GMV/hora vs meta
    const expected = (state.goal>0 ? state.goal*Math.min(1, elapsedMin()/state.plannedMin) : 0) || 1;
    const pace = s.gmv!=null ? s.gmv/expected : 1;
    d.gmvPace = { grade: s.gmv!=null?grade(pace,0.9,0.7):"na", ratio:pace, expected, star:3 };

    // ⭐⭐ drivers do funil (ordem: ERR → CTR → CO → AOV)
    if (s.err!=null){ const t=trendGrade(s.err, ref?ref.err:null, -0.15, -0.30); d.err={grade:t.grade, drop:t.drop, val:s.err, star:2, prov:true}; }
    else d.err={grade:"na", star:2, prov:true};
    // Sem perfil resolvido não há bench comparável — vira "na" em vez de acusar
    // vermelho contra um denominador que pode não ser o da tela.
    d.ctr = (s.ctr!=null && B.ctr) ? { grade:grade(s.ctr/B.ctr,1.0,0.8), ratio:s.ctr/B.ctr, star:2 } : { grade:"na", star:2 };
    // Esta tela dá "Taxa de pedidos (SKU)" (= conv/visualização) e o CTR, mas não o
    // CO. Ele sai da identidade CTR × CO = convView — derivação legítima, e o card
    // marca "deriv" pra ninguém confundir com leitura direta.
    let coVal = s.co, coDeriv = false;
    if (coVal==null){ const dc = LIB.deriveCO(s.convView, s.ctr); if (dc!=null){ coVal = dc; coDeriv = true; } }
    d.co  = (coVal!=null && B.co) ? { grade:grade(coVal/B.co,1.0,0.8), ratio:coVal/B.co, star:2, val:coVal, deriv:coDeriv } : { grade:"na", star:2 };
    const ticket = (s.orders>0 && s.gmv!=null) ? s.gmv/s.orders : 0;
    d.aov = { grade: (ticket>0 && B.ticket)?grade(ticket/B.ticket,1.0,0.8):"na", ticket, star:2 };

    // contexto / secundárias
    // Duas audiências com o mesmo nome na cabeça de todo mundo: "views" é o acumulado
    // da live (tem bench) e "espectadores ao vivo" é o simultâneo (não tem — 15 ao vivo
    // contra 8.284 de bench acusaria vermelho a live inteira). Só com o simultâneo, o
    // painel julga por TENDÊNCIA e diz isso no card.
    const audVal = s.viewers!=null ? s.viewers : s.liveViewers;
    const audRef = ref ? (ref.viewers!=null ? ref.viewers : ref.liveViewers) : null;
    d.aud = { val:audVal, modo: s.viewers!=null ? "bench" : (s.liveViewers!=null ? "trend" : "na") };
    // Views é ACUMULADO: comparar o total de 13 minutos de live contra a média de
    // uma live inteira acusa vermelho em toda live nova. O bench é prorrateado pelo
    // tempo decorrido — mesma lógica que o ritmo de GMV já usava contra a meta.
    const fracao = state.plannedMin>0 ? Math.min(1, Math.max(0.02, elapsedMin()/state.plannedMin)) : 1;
    const benchViewsAgora = B.views ? B.views*fracao : null;
    d.viewersVol = (d.aud.modo==="bench" && benchViewsAgora) ? { grade:grade(s.viewers/benchViewsAgora,0.6,0.4), ratio:s.viewers/benchViewsAgora, star:2, benchAgora:benchViewsAgora } : { grade:"na" };
    d.viewersTrend = (audVal!=null && audRef) ? (t=>({grade:t.grade, drop:t.drop}))(trendGrade(audVal, audRef, -0.15, -0.30)) : { grade:"good", drop:0 };
    // ⭐ antecedente: engajamento (comentários) por tendência
    d.eng = (s.comments!=null && ref) ? (t=>({grade:t.grade==="bad"?"warn":t.grade, drop:t.drop}))(trendGrade(s.comments, ref.comments, -0.20, -0.40)) : { grade:"na" };

    // derivados
    // conv/visualização = CTR × CO (produto das etapas). Exibida, nunca calibrada — R10.
    const cvVal = s.convView!=null ? s.convView : LIB.deriveConvView(s.ctr, coVal);
    d.convView = cvVal!=null ? { val:cvVal, ratio: B.convView ? cvVal/B.convView : null } : null;
    d.gpm = LIB.computeGpm(s.gmv, s.impressions);

    // overall — cascata
    const drivers=[d.err,d.ctr,d.co,d.aov].filter(x=>x.grade&&x.grade!=="na");
    const bad=drivers.filter(x=>x.grade==="bad").length, warn=drivers.filter(x=>x.grade==="warn").length;
    const secondary = ["warn","bad"].includes(d.viewersVol.grade) || ["warn","bad"].includes(d.viewersTrend.grade) || d.eng.grade==="warn";
    let overall="green";
    if (d.gmvPace.grade==="bad" || bad>=2 || (bad>=1 && d.gmvPace.grade==="warn")) overall="red";
    else if (d.gmvPace.grade==="warn" || bad>=1 || warn>=1 || secondary) overall="amber";
    return { overall, dims:d, ticket };
  }

  function heroReason(h){
    const d=h.dims;
    if(h.overall==="green") return "Funil saudável em todas as etapas. Mantém a cadência de ofertas e a frequência.";
    const chain=[["err",d.err,"entrada (ERR) caindo — 1ª impressão fraca"],["ctr",d.ctr,"CTR abaixo do padrão — apresentação/sacola"],
      ["co",d.co,"conversão pós-clique baixa — preço/oferta"],["aov",d.aov,"ticket abaixo — falta escada de valor"]];
    const brk = chain.find(([k,dd])=>dd&&(dd.grade==="bad"||dd.grade==="warn"));
    let msg = brk ? "Gargalo mais acima no funil: "+brk[2]+"." : "";
    if(d.gmvPace.grade!=="good"&&d.gmvPace.grade!=="na") msg = `GMV/hora em ${Math.round(d.gmvPace.ratio*100)}% do ritmo. `+msg;
    return msg || "Atenção em métrica secundária (audiência/engajamento).";
  }

  function buildTriggers(h){
    const d=h.dims, T=[];
    if(d.gmvPace.grade!=="good"&&d.gmvPace.grade!=="na"){
      const diag = d.gpm!=null ? ` GPM atual ~${Math.round(d.gpm)}/1k impr.` : "";
      T.push({sev:d.gmvPace.grade,icon:"📉",title:d.gmvPace.grade==="bad"?"GMV/hora muito atrás":"GMV/hora abaixo do ritmo",
        action:`${Math.round(d.gmvPace.ratio*100)}% do esperado. Decompõe: é ALCANCE (impressões baixas → GMV Max / aquecer) ou EFICIÊNCIA (GPM baixo → CTR/CO/AOV)?${diag}`,fw:"flash"});
    }
    if(d.err.grade!=="good"&&d.err.grade!=="na")
      T.push({sev:d.err.grade,icon:"🚪",title:"Entrada (ERR) caindo",action:`1ª impressão fraca. Aquece com vídeo ~40min antes, melhora cenário/background, revisa câmera-mic-luz.`,fw:"rehook"});
    if(d.ctr.grade!=="good"&&d.ctr.grade!=="na")
      T.push({sev:d.ctr.grade,icon:"👆",title:d.ctr.grade==="bad"?"CTR despencou":"CTR abaixo do padrão",action:`${Math.round(d.ctr.ratio*100)}% do bench (${benchPct(BM&&BM.ctr)}). ≤30 itens na sacola, reordena (heróis nas posições 1-5 e 26-30), fixa TODOS os produtos, descrição assertiva.`,fw:"rehook"});
    if(d.co.grade!=="good"&&d.co.grade!=="na")
      T.push({sev:d.co.grade,icon:"🛒",title:"Conversão pós-clique baixa",action:`CO em ${Math.round(d.co.ratio*100)}% do bench. Preço competitivo, oferta relâmpago com estoque limitado, comunica cupom + frete grátis.`,fw:"prova"});
    if(d.aov.grade!=="good"&&d.aov.grade!=="na")
      T.push({sev:d.aov.grade,icon:"💰",title:"Ticket abaixo da média",action:`Sobe o AOV: combo, kit, variação premium, desconto progressivo.`,fw:"bundle"});
    if(d.viewersTrend.grade!=="good")
      T.push({sev:d.viewersTrend.grade,icon:"📥",title:"Viewers caindo",action:`Queda de ${Math.round(Math.abs(d.viewersTrend.drop)*100)}% desde o último snapshot. Ativa retenção: anuncia o próximo drop de preço.`,fw:"retencao"});
    else if(d.viewersVol.grade!=="good"&&d.viewersVol.grade!=="na")
      T.push({sev:d.viewersVol.grade,icon:"👥",title:"Audiência abaixo da média",action:`Views em ${Math.round(d.viewersVol.ratio*100)}% do esperado para este ponto da live. Boost / GMV Max + re-hook pra quem chega.`,fw:"rehook"});
    if(d.eng.grade==="warn")
      T.push({sev:"warn",icon:"💬",title:"Engajamento esfriando",action:`Conecta: faz pergunta, responde pelo @, meta de curtidas p/ liberar sorteio.`,fw:"retencao"});
    return T;
  }

  /* ================= shadow overlay ================= */
  let root, host;
  const STYLE = `
    .orfao{font-size:12px;line-height:1.55;color:#F2F2F7;background:rgba(255,77,77,.1);border:1px solid rgba(255,77,77,.35);border-radius:9px;padding:12px}
    .orfao b{display:block;color:#FF7A7A;font-size:13px;margin-bottom:5px}
    .orfao button{width:100%;margin-top:10px;background:#7C5CFF;color:#fff;border:none;border-radius:8px;padding:9px;font-size:12px;font-weight:600;cursor:pointer}
    .orfao .dica{display:block;margin-top:8px;color:#8A8A9A;font-size:11px}
    .cm .anc{display:block;font-size:10px;color:#7C5CFF;margin-top:2px;font-weight:500}
    .diag{width:100%;height:150px;margin-top:8px;background:#0B0B0F;color:#8A8A9A;border:1px solid #2A2A38;border-radius:8px;padding:8px;font:11px ui-monospace,Menlo,monospace;resize:vertical}
    .demo-flag{font-size:11px;font-weight:600;color:#0B0B0F;background:#FFC53D;border-radius:7px;padding:7px 9px;margin-bottom:9px;line-height:1.4}
    .prov-src{font-size:10px;color:#8A8A9A;line-height:1.5;margin:6px 2px 0;padding:6px 8px;background:rgba(124,92,255,.07);border-radius:7px}
    :host{ all:initial; }
    *{ box-sizing:border-box; margin:0; padding:0; font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; }
    .panel{ position:fixed; width:344px; background:#15151C; color:#F2F2F7; border:1px solid #2A2A38; border-radius:14px; box-shadow:0 18px 50px rgba(0,0,0,.55); z-index:2147483647; overflow:hidden; font-size:13px; }
    .hd{ display:flex; align-items:center; gap:8px; padding:11px 13px; cursor:grab; background:#1E1E28; border-bottom:1px solid #2A2A38; user-select:none; }
    .hd.drag{ cursor:grabbing; }
    .hd .b{ width:8px;height:8px;border-radius:50%;background:#7C5CFF;box-shadow:0 0 0 3px rgba(124,92,255,.15); }
    .hd .ti{ font-weight:700; font-size:13px; letter-spacing:-.01em; } .hd .ti small{ color:#8A8A9A; font-weight:500; }
    .hd .sp{ flex:1; } .hd .tm{ font-variant-numeric:tabular-nums; color:#8A8A9A; font-size:12px; }
    .hd button{ background:none;border:none;color:#8A8A9A;cursor:pointer;font-size:15px;line-height:1;padding:3px 5px;border-radius:6px; }
    .hd button:hover{ color:#F2F2F7; background:#2A2A38; }
    .body{ padding:13px; max-height:72vh; overflow:auto; }
    .body::-webkit-scrollbar{ width:8px; } .body::-webkit-scrollbar-thumb{ background:#2A2A38; border-radius:8px; }
    .tabs{ display:flex; gap:2px; padding:8px 9px 0; background:#15151C; }
    .tabs button{ flex:1;background:none;border:none;color:#8A8A9A;cursor:pointer;font-size:11.5px;font-weight:600;padding:7px 3px;border-radius:8px 8px 0 0; }
    .tabs button.on{ color:#fff; background:#1E1E28; }
    .sem{ display:flex; align-items:center; gap:12px; padding:14px; border-radius:11px; margin-bottom:12px; border:1px solid #2A2A38; background:#1E1E28; }
    .sem.green{ background:rgba(46,204,113,.1); border-color:rgba(46,204,113,.4);} .sem.amber{ background:rgba(245,166,35,.1);border-color:rgba(245,166,35,.45);} .sem.red{ background:rgba(255,77,77,.1);border-color:rgba(255,77,77,.5);}
    .beacon{ width:38px;height:38px;border-radius:50%;background:#5E5E6E;flex-shrink:0;position:relative; }
    .sem.green .beacon{background:#2ECC71;color:#2ECC71;} .sem.amber .beacon{background:#F5A623;color:#F5A623;} .sem.red .beacon{background:#FF4D4D;color:#FF4D4D;}
    .sem.green .beacon::after,.sem.amber .beacon::after,.sem.red .beacon::after{ content:"";position:absolute;inset:-5px;border-radius:50%;border:2px solid currentColor;opacity:.35;animation:rg 2s ease-out infinite; }
    @keyframes rg{ 0%{transform:scale(.85);opacity:.5} 100%{transform:scale(1.3);opacity:0} }
    .sem .st{ font-weight:700;font-size:18px;letter-spacing:-.01em; }
    .sem.green .st{color:#2ECC71;} .sem.amber .st{color:#F5A623;} .sem.red .st{color:#FF4D4D;} .sem .st.idle{color:#8A8A9A;}
    .sem .pc{ margin-left:auto;text-align:right; } .sem .pc b{ font-size:19px;font-variant-numeric:tabular-nums;letter-spacing:-.01em; } .sem .pc span{ display:block;font-size:10px;color:#8A8A9A;text-transform:uppercase;letter-spacing:.05em; }
    .reason{ font-size:12px;color:#8A8A9A;line-height:1.45;margin:-4px 0 12px;padding:0 2px; }
    .kg{ display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:9px; }
    .kp{ background:#1E1E28;border:1px solid #2A2A38;border-radius:9px;padding:9px 10px;position:relative; }
    .kp .kt{ display:flex;justify-content:space-between;align-items:center;margin-bottom:4px; }
    .kp .kn{ font-size:10px;font-weight:600;color:#8A8A9A;text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;gap:4px; }
    .kp .prov{ font-size:8px;color:#F5A623;background:rgba(245,166,35,.15);padding:1px 4px;border-radius:4px;letter-spacing:0;text-transform:none;font-weight:700; }
    .kp .kd{ width:7px;height:7px;border-radius:50%;background:#5E5E6E;flex-shrink:0; }
    .kp.good .kd{background:#2ECC71;} .kp.warn .kd{background:#F5A623;} .kp.bad .kd{background:#FF4D4D;}
    .kp .kv{ font-size:17px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.01em; }
    .kp .kc{ font-size:10.5px;color:#8A8A9A;margin-top:2px;line-height:1.3; }
    .kp.good .kc b{color:#2ECC71;} .kp.warn .kc b{color:#F5A623;} .kp.bad .kc b{color:#FF4D4D;}
    .derived{ display:flex;gap:8px;font-size:10.5px;color:#8A8A9A;background:#0B0B0F;border:1px solid #2A2A38;border-radius:8px;padding:7px 10px;margin-bottom:12px; }
    .derived b{ color:#F2F2F7;font-variant-numeric:tabular-nums; }
    .seclabel{ font-size:11px;font-weight:600;color:#8A8A9A;text-transform:uppercase;letter-spacing:.05em;margin:2px 0 8px; }
    .trg{ border:1px solid #2A2A38;border-radius:9px;padding:10px;margin-bottom:8px;background:#1E1E28; }
    .trg.warn{ background:rgba(245,166,35,.1);border-color:rgba(245,166,35,.4);} .trg.bad{ background:rgba(255,77,77,.1);border-color:rgba(255,77,77,.45);}
    .trg .tt{ font-weight:600;font-size:12.5px;margin-bottom:3px; } .trg.warn .tt{color:#F5A623;} .trg.bad .tt{color:#FF4D4D;}
    .trg .ta{ font-size:11.5px;color:#8A8A9A;line-height:1.4; }
    .trg .tb{ margin-top:7px;font-size:11px;font-weight:600;color:#7C5CFF;background:rgba(124,92,255,.12);border:1px solid rgba(124,92,255,.3);padding:5px 10px;border-radius:100px;cursor:pointer; }
    .trg .tb:hover{ background:#7C5CFF;color:#fff; }
    .fwbox{ margin-top:7px;background:#0B0B0F;border:1px solid #2A2A38;border-radius:8px;padding:9px;font-size:11.5px;line-height:1.5;display:none; } .fwbox.show{ display:block; }
    .fw{ border:1px solid #2A2A38;border-radius:9px;padding:11px;margin-bottom:8px;background:#1E1E28; }
    .fw h4{ font-size:13px;margin-bottom:7px;display:flex;gap:7px;align-items:center; }
    .fw .sc{ background:#0B0B0F;border:1px solid #2A2A38;border-radius:8px;padding:9px;font-size:11.5px;line-height:1.5;color:#F2F2F7;margin-bottom:8px; }
    .fw .use{ width:100%;font-size:11.5px;font-weight:600;color:#F2F2F7;background:#2A2A38;border:none;padding:8px;border-radius:8px;cursor:pointer; } .fw .use:hover{ background:#7C5CFF;color:#fff; }
    .em{ color:#5E5E6E;font-size:12px;text-align:center;padding:18px 10px;line-height:1.5; }
    .note{ font-size:11px;color:#5E5E6E;text-align:center;margin-top:6px; }
    .rowbtn{ display:flex;gap:7px;margin-bottom:10px; }
    .rowbtn button{ flex:1;font-size:11.5px;font-weight:600;padding:8px;border-radius:8px;cursor:pointer;border:1px solid #2A2A38;background:#1E1E28;color:#F2F2F7; } .rowbtn button:hover{ border-color:#7C5CFF; }
    .rowbtn button.pri{ background:#7C5CFF;border-color:#7C5CFF;color:#fff; } .rowbtn button.pri:hover{ background:#6a4aff; }
    /* calibração */
    .calibmap{ display:flex;flex-direction:column;gap:5px;margin-bottom:10px; }
    .cm{ display:flex;align-items:center;gap:8px;font-size:11.5px;padding:6px 9px;background:#1E1E28;border:1px solid #2A2A38;border-radius:8px; }
    .cm .d{ width:7px;height:7px;border-radius:50%;background:#5E5E6E;flex-shrink:0; } .cm.ok .d{ background:#2ECC71; }
    .cm .l{ flex:1;color:#8A8A9A;display:flex;align-items:center;gap:5px; } .cm.ok .l{ color:#F2F2F7; }
    .cm .tag{ font-size:8px;padding:1px 4px;border-radius:4px;font-weight:700; }
    .cm .tag.prov{ color:#F5A623;background:rgba(245,166,35,.15); } .cm .tag.opt{ color:#8A8A9A;background:#2A2A38; }
    .cm .v{ font-variant-numeric:tabular-nums;color:#8A8A9A; }
    /* sacola / cue sheet */
    .cue-hd{ display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;font-size:12px; }
    .cue-hd .cnt{ font-weight:700;font-variant-numeric:tabular-nums; } .cue-hd .cnt.over{ color:#FF4D4D; }
    .cue-warn{ font-size:11px;color:#F5A623;background:rgba(245,166,35,.1);border:1px solid rgba(245,166,35,.3);border-radius:8px;padding:8px 10px;margin-bottom:10px;line-height:1.4; }
    .cuec{ border:1px solid #2A2A38;border-radius:9px;padding:9px;margin-bottom:8px;background:#1E1E28; }
    .cuec.prime{ border-color:rgba(124,92,255,.45); }
    .cuec .crow{ display:flex;align-items:center;gap:6px;margin-bottom:6px; }
    .cuec .pos{ font-size:10px;font-weight:700;color:#8A8A9A;background:#0B0B0F;border:1px solid #2A2A38;border-radius:6px;padding:2px 6px;font-variant-numeric:tabular-nums;flex-shrink:0; }
    .cuec.prime .pos{ color:#7C5CFF;border-color:rgba(124,92,255,.4); }
    .cuec .vitrine{ font-size:8px;font-weight:700;color:#7C5CFF;background:rgba(124,92,255,.12);padding:1px 5px;border-radius:4px; }
    .cuec select{ flex:1;background:#0B0B0F;border:1px solid #2A2A38;border-radius:7px;color:#F2F2F7;font-size:11px;padding:5px 6px;cursor:pointer; }
    .cuec .del{ color:#5E5E6E;font-size:16px;cursor:pointer;padding:2px 6px;border-radius:6px;background:none;border:none; } .cuec .del:hover{ color:#FF4D4D;background:rgba(255,77,77,.1); }
    .cuec input{ width:100%;background:#0B0B0F;border:1px solid #2A2A38;border-radius:7px;color:#F2F2F7;font-size:11.5px;padding:6px 8px;margin-top:5px; } .cuec input:focus{ border-color:#7C5CFF;outline:none; }
    .cuec input.price{ font-variant-numeric:tabular-nums;max-width:110px; }
    .cue-add{ width:100%;font-size:11.5px;font-weight:600;color:#7C5CFF;background:rgba(124,92,255,.12);border:1px solid rgba(124,92,255,.3);padding:9px;border-radius:8px;cursor:pointer; } .cue-add:hover{ background:#7C5CFF;color:#fff; }
    /* compliance */
    .comp{ border:1px solid #2A2A38;border-radius:9px;padding:11px;margin-top:11px;background:#1E1E28; }
    .comp-hd{ display:flex;align-items:center;justify-content:space-between;font-size:11.5px;font-weight:600;color:#8A8A9A;text-transform:uppercase;letter-spacing:.04em;margin-bottom:9px; }
    .comp-hd .cc{ font-variant-numeric:tabular-nums;color:#FF4D4D; }
    .viol-btn{ width:100%;font-size:11.5px;font-weight:600;color:#FF4D4D;background:rgba(255,77,77,.1);border:1px solid rgba(255,77,77,.3);padding:8px;border-radius:8px;cursor:pointer; } .viol-btn:hover{ background:#FF4D4D;color:#fff; }
    .viol-form{ margin-top:8px; } .viol-form input{ width:100%;background:#0B0B0F;border:1px solid #2A2A38;border-radius:7px;color:#F2F2F7;font-size:11.5px;padding:7px 8px;margin-bottom:6px; } .viol-form input:focus{ border-color:#FF4D4D;outline:none; }
    .viol-item{ font-size:11px;color:#8A8A9A;padding:6px 0;border-top:1px solid #2A2A38;line-height:1.4; } .viol-item b{ color:#FF4D4D; }
    /* timeline */
    .tl-item{ display:flex;gap:9px;padding:8px 0;border-bottom:1px solid #2A2A38;font-size:11.5px; } .tl-item:last-child{ border-bottom:none; }
    .tl-time{ font-variant-numeric:tabular-nums;color:#8A8A9A;min-width:40px; }
    .tl-body{ flex:1;line-height:1.4; } .tl-body .k{ font-weight:600; }
    .tl-item.fw .k{ color:#7C5CFF; } .tl-item.viol .k{ color:#FF4D4D; }
    .reopen{ position:fixed;bottom:20px;right:20px;z-index:2147483647;background:#7C5CFF;color:#fff;border:none;border-radius:100px;padding:11px 16px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 8px 24px rgba(124,92,255,.4);font-family:'Inter',system-ui,-apple-system,sans-serif;display:flex;align-items:center;gap:8px; }
    .reopen .b{ width:8px;height:8px;border-radius:50%;background:#fff;animation:pl 1.4s ease-in-out infinite; }
    @keyframes pl{ 0%,100%{opacity:1} 50%{opacity:.4} }
    @media (prefers-reduced-motion:reduce){ *{ animation:none!important; } }
  `;

  function buildOverlay(){
    host = document.createElement("div"); host.id = "dashlive-host";
    (document.body||document.documentElement).appendChild(host);
    root = host.attachShadow({ mode:"open" });
    root.innerHTML = `
      <style>${STYLE}</style>
      <div class="panel" id="dl-panel">
        <div class="hd" id="dl-hd"><span class="b"></span><span class="ti">DashLive <small>· ao vivo</small></span><span class="sp"></span>
          <span class="tm" id="dl-timer"></span><button id="dl-min" title="Minimizar">–</button><button id="dl-close" title="Ocultar">×</button></div>
        <div class="tabs" id="dl-tabs">
          <button data-tab="monitor" class="on">Monitor</button>
          <button data-tab="sacola">Sacola</button>
          <button data-tab="frameworks">Frameworks</button>
          <button data-tab="calib">Dados</button>
        </div>
        <div class="body" id="dl-body"></div>
      </div>`;
    // Sem <link> de fonte remota: é recurso externo carregado em runtime (proibido no
    // brief) e ficaria refém da CSP do Seller Center. A stack do sistema resolve —
    // Inter entra se a máquina tiver, senão cai na fonte nativa da plataforma.

    const panel = root.getElementById("dl-panel"), ui = state.ui;
    // clamp: x/y vêm do storage e podem ter sido salvos noutra resolução/monitor.
    // Sem isso o painel "some" fora da viewport e parece que a extensão não abriu.
    const W = window.innerWidth, H = window.innerHeight;
    const x = Math.min(Math.max(ui.x!=null?ui.x:(W-364), 0), Math.max(0, W-120));
    const y = Math.min(Math.max(ui.y!=null?ui.y:80, 0), Math.max(0, H-80));
    panel.style.top = y+"px";
    panel.style.left = x+"px";

    const hd = root.getElementById("dl-hd"); let dragging=false, ox=0, oy=0;
    hd.addEventListener("pointerdown", e=>{ if(e.target.tagName==="BUTTON")return; dragging=true; hd.classList.add("drag");
      const r=panel.getBoundingClientRect(); ox=e.clientX-r.left; oy=e.clientY-r.top; hd.setPointerCapture(e.pointerId); });
    hd.addEventListener("pointermove", e=>{ if(!dragging)return;
      panel.style.left=Math.max(4,Math.min(window.innerWidth-60,e.clientX-ox))+"px";
      panel.style.top=Math.max(4,Math.min(window.innerHeight-40,e.clientY-oy))+"px"; });
    hd.addEventListener("pointerup", e=>{ if(!dragging)return; dragging=false; hd.classList.remove("drag");
      state.ui.x=parseInt(panel.style.left); state.ui.y=parseInt(panel.style.top); saveState(); });

    root.getElementById("dl-min").onclick=()=>{ state.ui.min=!state.ui.min; saveState(); render(); };
    root.getElementById("dl-close").onclick=()=>{ state.ui.hidden=true; saveState(); render(); };
    root.getElementById("dl-tabs").querySelectorAll("button").forEach(b=>b.onclick=()=>{ state.ui.tab=b.dataset.tab; saveState(); render(); });
  }

  /* ================= render ================= */
  function fmtBRL(n){ return "R$ "+Math.round(n).toLocaleString("pt-BR"); }
  function fmtNum(n){ return Math.round(n).toLocaleString("pt-BR"); }
  function pct1(n){ return n.toFixed(1).replace(".",","); }
  function pct2(n){ return n.toFixed(2).replace(".",","); }
  function hhmmss(ms){ const s=Math.max(0,Math.floor(ms/1000)),h=Math.floor(s/3600),m=Math.floor(s%3600/60),ss=s%60,p=x=>String(x).padStart(2,"0"); return `${p(h)}:${p(m)}:${p(ss)}`; }
  function clockAt(t){ const d=new Date(t); return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0"); }

  function render(){
    if(!root) return;
    if(orfao) return renderOrfao();
    let reopen = root.getElementById("dl-reopen"); const panel = root.getElementById("dl-panel");
    if(state.ui.hidden){ panel.style.display="none";
      if(!reopen){ reopen=document.createElement("button"); reopen.className="reopen"; reopen.id="dl-reopen"; reopen.innerHTML=`<span class="b"></span> DashLive`;
        reopen.onclick=()=>{ state.ui.hidden=false; saveState(); render(); }; root.appendChild(reopen); }
      reopen.style.display="flex"; return;
    } else { panel.style.display="block"; if(reopen) reopen.style.display="none"; }

    const tm=root.getElementById("dl-timer");
    if(state.startTime){ const end=state.endTime||Date.now(); tm.textContent=hhmmss(end-state.startTime); } else tm.textContent="";
    root.getElementById("dl-tabs").querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.tab===state.ui.tab));

    const body=root.getElementById("dl-body");
    if(state.ui.min){ body.innerHTML=miniView(); return; }
    const tab=state.ui.tab;
    if(tab==="frameworks"){ body.innerHTML=fwView(); bindFw(body); return; }
    if(tab==="calib"){ body.innerHTML=calibView(); bindCalib(body); return; }
    if(tab==="sacola"){ body.innerHTML=cueView(); bindCue(body); return; }
    body.innerHTML=monitorView(); bindMonitor(body);
  }

  function miniView(){
    const h=evaluateHealth(); const map={green:"No ritmo",amber:"Atenção",red:"Agir agora"}; const s=state.current;
    const pct=state.goal>0&&s.gmv!=null?Math.round(s.gmv/state.goal*100):null;
    return `<div class="sem ${h?h.overall:''}"><div class="beacon"></div><div class="st ${h?'':'idle'}">${h?map[h.overall]:'Sem dados'}</div>
      <div class="pc"><b>${pct!=null?pct+'%':'—'}</b><span>da meta</span></div></div>`;
  }

  function kpCard(cls,name,val,ctx,prov){
    return `<div class="kp ${cls}"><div class="kt"><span class="kn">${name}${prov?'<span class="prov">prov</span>':''}</span><span class="kd"></span></div><div class="kv">${val}</div><div class="kc">${ctx}</div></div>`;
  }
  function monitorView(){
    if(!state.startTime) return `<div class="em">Nenhuma live iniciada.<br>Abre o popup da extensão (ícone na barra) pra definir a meta e iniciar.</div>`;
    const calibrated=Object.keys(state.calib).length>0;
    const h=evaluateHealth(); const map={green:"No ritmo",amber:"Atenção",red:"Agir agora"}; const s=state.current;
    const pct=state.goal>0&&s.gmv!=null?Math.round(s.gmv/state.goal*100):null;
    const d=h?h.dims:{};

    let html=state.demo?`<div class="demo-flag">▶ MODO DEMO — números fabricados. Não grava no Supabase. Limpa na aba <b>Dados</b>.</div>`:"";
    html+=`<div class="sem ${h?h.overall:''}"><div class="beacon"></div><div><div class="st ${h?'':'idle'}">${h?map[h.overall]:'Aguardando leitura'}</div></div>
      <div class="pc"><b>${pct!=null?pct+'%':'—'}</b><span>da meta</span></div></div>`;
    html+=`<div class="reason">${h?heroReason(h):(calibrated?'Lendo a página… se ficar em branco, confira a aba <b>Dados</b>.':'Não reconheci as métricas nesta tela. Abre a aba <b>Dados</b> → <b>Mapear tela automaticamente</b>, ou aponta na mão.')}</div>`;

    // KPIs na ordem do funil: GMV/hora → ERR → CTR → CO → Ticket → Viewers
    const gmvHour = (s.gmv!=null && elapsedMin()>0) ? s.gmv/(elapsedMin()/60) : null;
    html+=`<div class="kg">`;
    html+=kpCard(d.gmvPace?d.gmvPace.grade:"", "GMV / hora", gmvHour!=null?fmtBRL(gmvHour):"—", d.gmvPace&&d.gmvPace.grade!=="na"?`ritmo <b>${Math.round(d.gmvPace.ratio*100)}%</b> da meta`:`—`);
    html+=kpCard(d.err?d.err.grade:"", "ERR entrada", s.err!=null?pct1(s.err)+"%":"—", d.err&&d.err.drop!==undefined&&s.err!=null?`tendência (sem bench)`:`—`, true);
    html+=kpCard(d.ctr?d.ctr.grade:"", "CTR live", s.ctr!=null?pct1(s.ctr)+"%":"—", `bench ${benchPct(BM&&BM.ctr)}${d.ctr&&d.ctr.ratio?` · <b>${Math.round(d.ctr.ratio*100)}%</b>`:""}`);
    html+=kpCard(d.co?d.co.grade:"", "CO pós-clique", d.co&&d.co.val!=null?pct1(d.co.val)+"%":"—", `${d.co&&d.co.deriv?"derivado · ":""}bench ${benchPct(BM&&BM.co)}${d.co&&d.co.ratio?` · <b>${Math.round(d.co.ratio*100)}%</b>`:""}`, d.co&&d.co.deriv);
    const ticket=(s.orders>0&&s.gmv!=null)?s.gmv/s.orders:0;
    html+=kpCard(d.aov?d.aov.grade:"", "Ticket / AOV", ticket>0?fmtBRL(ticket):"—", `bench ${benchBRL(BM&&BM.ticket)} · ${s.orders!=null?s.orders:0} ped.`);
    const aud=d.aud||{modo:"na"};
    html+=kpCard(aud.modo==="bench"?(d.viewersVol?d.viewersVol.grade:""):(d.viewersTrend?d.viewersTrend.grade:""),
      aud.modo==="trend"?"Espectadores":"Views",
      aud.val!=null?fmtNum(aud.val):"—",
      aud.modo==="bench" ? `esperado agora ${d.viewersVol&&d.viewersVol.benchAgora?fmtNum(d.viewersVol.benchAgora):"—"} · live inteira ${BM&&BM.views?fmtNum(BM.views):"—"}`
      : aud.modo==="trend" ? `ao vivo · tendência (sem bench)` : "—");
    html+=`</div>`;

    // derivados: conversão por visualização (CTR×CO) + GPM
    const cv=d.convView, gpm=d.gpm;
    html+=`<div class="derived"><span>Conv/visualização: <b>${cv?pct2(cv.val)+"%":"—"}</b> <span style="opacity:.6">(CTR×CO · bench ${BM&&BM.convView!=null?pct2(BM.convView)+"%":"—"})</span></span><span>GPM: <b>${gpm!=null?fmtBRL(gpm):"—"}</b><span style="opacity:.6">/1k</span></span></div>`;
    html+=`<div class="prov-src">${benchProvenance()}</div>`;

    // triggers
    const T=h?buildTriggers(h):[];
    html+=`<div class="seclabel">Gatilhos ${T.length?`(${T.length})`:""}</div>`;
    if(!T.length){ html+=`<div class="em" style="padding:12px">Tudo no ritmo. Nenhum gatilho.</div>`; }
    else T.forEach((t,i)=>{ html+=`<div class="trg ${t.sev}"><div class="tt">${t.icon} ${t.title}</div><div class="ta">${t.action}</div>
      <button class="tb" data-fw="${t.fw}" data-i="${i}">Ver script: ${FRAMEWORKS[t.fw].name.split(" (")[0]} →</button><div class="fwbox" id="dl-fwb-${i}">${FRAMEWORKS[t.fw].script}</div></div>`; });

    html+=`<div class="rowbtn" style="margin-top:11px"><button id="dl-snap" class="pri">Marcar snapshot (${state.snapshots.length})</button></div>`;
    html+=`<div class="note">Snapshot automático a cada 15min · leitura ao vivo a cada 8s.</div>`;

    // compliance
    html+=`<div class="comp"><div class="comp-hd"><span>Compliance</span><span class="cc">${state.violations.length||""}</span></div>
      <button class="viol-btn" id="dl-viol">⚠ Registrar violação</button>
      <div class="viol-form" id="dl-viol-form" style="display:none">
        <input id="dl-viol-motivo" placeholder="Motivo da violação"><input id="dl-viol-acao" placeholder="Ação/correção (opcional)">
        <div class="rowbtn"><button class="pri" id="dl-viol-save">Registrar</button><button id="dl-viol-cancel">Cancelar</button></div></div>
      ${state.violations.slice().reverse().slice(0,3).map(v=>`<div class="viol-item"><b>${clockAt(v.t)}</b> — ${escapeHtml(v.motivo)}${v.acao?` · ${escapeHtml(v.acao)}`:""}</div>`).join("")}</div>`;

    // timeline (curta)
    const items=[];
    state.snapshots.forEach(x=>items.push({t:x.t,kind:"snap",text:`<span class="k">Snapshot</span> ${x.gmv!=null?fmtBRL(x.gmv):""} · ${fmtNum(x.viewers||0)} view`}));
    state.events.forEach(e=>items.push({t:e.t,kind:"fw",text:`<span class="k">Framework</span> ${e.name.split(" (")[0]}`}));
    state.violations.forEach(v=>items.push({t:v.t,kind:"viol",text:`<span class="k">Violação</span> ${escapeHtml(v.motivo)}`}));
    items.sort((a,b)=>a.t-b.t);
    if(items.length){ html+=`<div class="seclabel" style="margin-top:12px">Linha do tempo</div>`;
      html+=items.slice(-8).map(i=>`<div class="tl-item ${i.kind}"><div class="tl-time">${clockAt(i.t)}</div><div class="tl-body">${i.text}</div></div>`).join(""); }
    return html;
  }
  // O operador precisa saber contra QUE régua a live está sendo medida — e quando
  // a régua ainda não foi decidida, precisa saber disso também.
  function benchProvenance(){
    if(!BM){
      const m = BM_DET.method;
      const txt = m==="ambiguo" ? "CTR lido não decide entre os dois padrões — calibra <b>Cliques em produto</b> pra resolver."
        : m==="sem-ctr" ? "aguardando leitura do CTR pra escolher a régua."
        : "sem benchmark aplicável.";
      return `⚖️ Bench indefinido — ${txt}`;
    }
    const nome = BM.profile==="views" ? "CTR ÷ views" : "CTR ÷ impressões de produto";
    const via  = BM_DET.method==="rotulo" ? "declarado pelo rótulo da página"
               : BM_DET.method==="identidade" ? "confirmado pelos cliques"
               : BM_DET.method==="magnitude"  ? "inferido pela ordem de grandeza — calibra <b>Cliques em produto</b> pra confirmar"
               : "perfil anterior mantido";
    const j = BM.janela ? `${BM.janela.de}→${BM.janela.ate} · ${BM.janela.lives} lives` : "janela ?";
    return `⚖️ Régua: <b>${nome}</b> (${via}) · base ${j}${BM.stale?" · <b>benchmarks.js ausente — fallback</b>":""}`;
  }

  function bindMonitor(body){
    body.querySelectorAll(".tb").forEach(b=>b.onclick=()=>{ const box=body.querySelector("#dl-fwb-"+b.dataset.i); if(box) box.classList.toggle("show"); });
    const snap=body.querySelector("#dl-snap"); if(snap) snap.onclick=commitSnapshot;
    const vb=body.querySelector("#dl-viol"), vf=body.querySelector("#dl-viol-form");
    if(vb) vb.onclick=()=>{ vf.style.display=vf.style.display==="none"?"block":"none"; };
    const vc=body.querySelector("#dl-viol-cancel"); if(vc) vc.onclick=()=>{ vf.style.display="none"; };
    const vs=body.querySelector("#dl-viol-save"); if(vs) vs.onclick=()=>{
      const motivo=(body.querySelector("#dl-viol-motivo").value||"").trim(); if(!motivo)return;
      const acao=(body.querySelector("#dl-viol-acao").value||"").trim();
      state.violations.push({t:Date.now(),motivo,acao}); saveState(); render();
    };
  }
  function escapeHtml(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

  function fwView(){ return Object.entries(FRAMEWORKS).map(([k,f])=>`<div class="fw"><h4>${f.icon} ${f.name}</h4><div class="sc">${f.script}</div><button class="use" data-use="${k}">Usei agora ✓</button></div>`).join(""); }
  function bindFw(body){ body.querySelectorAll(".use").forEach(b=>b.onclick=()=>{
    const k=b.dataset.use, now=Date.now(); state.events.push({t:now,key:k,name:FRAMEWORKS[k].name}); state.frameworksUsed.push({key:k,t:now}); saveState();
    b.textContent="Registrado ✓"; b.style.background="#2ECC71"; b.style.color="#fff"; setTimeout(()=>render(),900); }); }

  /* ---- Sacola (cue sheet com tipagem, ≤30, posições nobres) ---- */
  function cueView(){
    const list=state.cueSheet, n=list.length;
    const primeIdx=i=> i<5 || i>=n-5; // 5 primeiros e 5 últimos são os mais vistos
    const herosOutOfPrime=list.filter((c,i)=>c.tipo==="Herói"&&!primeIdx(i)).length;
    let html=`<div class="cue-hd"><span>Sacola da live</span><span class="cnt ${n>30?'over':''}">${n}/30 itens</span></div>`;
    if(n>30) html+=`<div class="cue-warn">Acima de 30 itens. O guia recomenda no máximo 30 — o excesso dilui impressão e CTR. Corta os mais fracos.</div>`;
    if(herosOutOfPrime>0) html+=`<div class="cue-warn">${herosOutOfPrime} herói(s) fora das posições nobres (1-5 e ${Math.max(1,n-4)}-${n}). Move os heróis pra lá — são as posições mais vistas.</div>`;
    html+=list.map((c,i)=>`<div class="cuec ${primeIdx(i)?'prime':''}">
      <div class="crow"><span class="pos">#${i+1}</span>${primeIdx(i)?'<span class="vitrine">vitrine</span>':''}
        <select data-i="${i}" data-f="tipo">${CUE_TYPES.map(t=>`<option ${t===c.tipo?'selected':''}>${t}</option>`).join("")}</select>
        <button class="del" data-del="${i}">×</button></div>
      <input data-i="${i}" data-f="nome" value="${escapeHtml(c.nome)}" placeholder="Produto">
      <input data-i="${i}" data-f="hook" value="${escapeHtml(c.hook)}" placeholder="Hook">
      <input class="price" data-i="${i}" data-f="preco" value="${escapeHtml(c.preco)}" placeholder="Preço"></div>`).join("");
    html+=`<button class="cue-add" id="dl-cue-add">+ Adicionar produto</button>`;
    html+=`<div class="note" style="text-align:left;margin-top:10px">Tipos: <b>Gerador de Tráfego</b> = isca de entrada (ativa GMV Max) · <b>Herói</b> = receita · <b>Valor Agregado</b> = sobe ticket (combos/beirada).</div>`;
    return html;
  }
  function bindCue(body){
    body.querySelectorAll("select,input").forEach(el=>el.oninput=()=>{ state.cueSheet[+el.dataset.i][el.dataset.f]=el.value; saveState();
      if(el.dataset.f==="tipo"){ render(); } });
    body.querySelectorAll(".del").forEach(b=>b.onclick=()=>{ state.cueSheet.splice(+b.dataset.del,1); saveState(); render(); });
    const add=body.querySelector("#dl-cue-add"); if(add) add.onclick=()=>{ state.cueSheet.push({nome:"Novo produto",tipo:"Herói",hook:"",preco:""}); saveState(); render(); };
  }

  /* ---- Dados (calibração) ---- */
  function calibView(){
    let html=`<div class="em" style="text-align:left;padding:4px 2px 12px;color:#8A8A9A">A extensão lê os números direto da tela do Seller Center. Clica em <b>Calibrar</b> e aponta cada métrica na página uma vez — ela memoriza e passa a ler sozinha.</div>`;
    html+=`<div class="calibmap">`;
    METRICS.forEach(m=>{ const c=state.calib[m.key]; const val=c?readMetric(m):null;
      const disp=val!=null?(m.type==='money'?fmtBRL(val):m.type==='pct'?pct1(val)+"%":fmtNum(val)):(c?'—':'—');
    // "R$ 2,8 mil" é lido certo (2800) mas vem arredondado da origem — avisa em vez de fingir precisão.
    const aprox = c && c.sample && LIB.ehAbreviado(c.sample) ? '<span class="tag prov">aprox.</span>' : '';
      const anc = c && c.label ? `<span class="anc">← "${escapeHtml(c.label)}"</span>` : '';
      html+=`<div class="cm ${c?'ok':''}"><span class="d"></span><span class="l">${m.label}${anc}${m.prov?'<span class="tag prov">provisório</span>':''}${m.opt?'<span class="tag opt">opcional</span>':''}${aprox}</span><span class="v">${disp}</span></div>`; });
    html+=`</div>`;
    const auto=Object.values(state.calib).filter(c=>c&&c.origem==="auto").length;
    const faltam=METRICS.filter(m=>!state.calib[m.key]);
    html+=`<div class="rowbtn"><button id="dl-auto" class="pri">🔎 Mapear tela automaticamente</button></div>`;
    html+=`<div class="rowbtn" style="margin-top:8px"><button id="dl-cal">Apontar na mão</button><button id="dl-cal-clear">Limpar</button></div>`;
    html+=`<div class="rowbtn" style="margin-top:8px"><button id="dl-diag">📋 Copiar diagnóstico</button></div>`;
    html+=`<textarea id="dl-diag-out" class="diag" style="display:none" readonly></textarea>`;
    if(auto) html+=`<div class="note" style="text-align:left">${auto} métrica(s) reconhecida(s) pelo rótulo da página. <b>Confere os valores acima</b> — se algum estiver errado, usa "Apontar na mão" pra corrigir só ele (o manual sempre vence o automático).</div>`;
    if(faltam.length) html+=`<div class="note" style="text-align:left">Não encontrei na tela: <b>${faltam.map(m=>m.label.split(" —")[0].split(" (")[0]).join(" · ")}</b>. Pode não existir nesta página — o painel roda sem, mostrando "—".</div>`;
    html+=`<div class="rowbtn" style="margin-top:8px"><button id="dl-demo">${state.demo?"Sair do modo demo":"Carregar dados demo"}</button></div>`;
    html+=`<div class="note" style="text-align:left">Demo preenche o painel com uma live fictícia pra você ver o semáforo, os gatilhos e a linha do tempo funcionando sem estar no ar. Enquanto estiver ligado, a leitura da página fica pausada e a gravação no Supabase, bloqueada.</div>`;
    html+=`<div class="note" style="text-align:left">Benchmarks vêm da tabela <b>lives</b> (mesma fonte do dash-live), não de constante no código — regera com <code>gerar_benchmarks_live.py</code>. <b>CO</b> é <b>medido</b> (coluna <code>ctor</code> = compra após clique); a <b>conv/visualização</b> é que é derivada (CTR×CO). Calibrar <b>Cliques em produto</b> é opcional mas recomendado: é o que confirma qual régua de CTR a tela usa. <b>ERR</b> segue por tendência (sem bench). Quebrou após atualização do TikTok? Recalibra.</div>`;
    return html;
  }
  // Texto colável: o que cada métrica ancorou, o que leu, e os rótulos que a página
  // tem mas o dicionário ainda não conhece. É o que permite corrigir o mapa sem
  // precisar adivinhar o DOM por print.
  function montarDiagnostico(){
    const L1=[]; L1.push("DASHLIVE — DIAGNÓSTICO DE LEITURA");
    L1.push("url: "+location.href.split("?")[0]);
    L1.push("perfil de CTR: "+(state.ctrProfile||"—")+" ("+(BM_DET&&BM_DET.method||"—")+")");
    L1.push("");
    L1.push("MÉTRICA | RÓTULO ANCORADO | AMOSTRA | VALOR LIDO");
    for (const m of METRICS){
      const c=state.calib[m.key];
      const v=c?readMetric(m):null;
      L1.push(`${m.key} | ${c&&c.label?c.label:"—"} | ${c&&c.sample?c.sample:"—"} | ${v==null?"—":v}`);
    }
    L1.push("");
    L1.push("RÓTULOS NA TELA QUE O DICIONÁRIO NÃO RECONHECE (com número ao lado):");
    const vistos=new Set(); let n=0;
    const cands=Array.from(document.querySelectorAll("body *"))
      .filter(el=>el.children.length<=1 && !elDoPainel(el) && visivel(el))
      .map(el=>{const r=el.getBoundingClientRect(); return {el,top:Math.round(r.top)};})
      .sort((a,b)=>a.top-b.top).map(x=>x.el);
    for (const el of cands){
      if (n>=40) break;
      const t=(el.textContent||"").trim();
      if (!t || t.length>50 || /^\d/.test(t) || vistos.has(t)) continue;
      if (LIB.metricaDoRotulo(t)) continue;             // já reconhecido
      const val=textoValorDe(el,"int"); if (!val || val.length>28) continue;
      vistos.add(t); n++;
      L1.push(`  "${t}" = ${val}`);
    }
    return L1.join("\n");
  }

  function bindCalib(body){
    const cal=body.querySelector("#dl-cal"); if(cal) cal.onclick=startCalibration;
    const clr=body.querySelector("#dl-cal-clear"); if(clr) clr.onclick=()=>{ state.calib={}; saveState(); render(); };
    const dm=body.querySelector("#dl-demo"); if(dm) dm.onclick=()=>{ state.demo?clearDemo():loadDemo(); };
    const dg=body.querySelector("#dl-diag");
    if(dg) dg.onclick=()=>{
      const ta=body.querySelector("#dl-diag-out");
      ta.value=montarDiagnostico(); ta.style.display="block"; ta.select();
      try { document.execCommand("copy"); dg.textContent="✓ Copiado"; }
      catch(e){ dg.textContent="Selecione e copie ↓"; }
      setTimeout(()=>{ dg.textContent="📋 Copiar diagnóstico"; }, 2500);
    };
    const am=body.querySelector("#dl-auto");
    if(am) am.onclick=()=>{ am.textContent="Procurando…"; const r=aplicarAutoMapa();
      am.textContent = r.total ? `✓ ${r.total} encontrada(s)` : "Nada reconhecido nesta tela";
      setTimeout(render, 1200); };
  }

  /* ================= calibration ================= */
  let calState=null;
  function startCalibration(){ calState={idx:0}; showCalHint(); document.addEventListener("mouseover",calHover,true); document.addEventListener("click",calClick,true); }
  function endCalibration(){ document.removeEventListener("mouseover",calHover,true); document.removeEventListener("click",calClick,true);
    if(calState&&calState.hl) calState.hl.style.outline=calState.prevOutline||""; const hint=document.getElementById("dl-calhint"); if(hint) hint.remove(); calState=null; saveState(); render(); }
  function showCalHint(){
    let hint=document.getElementById("dl-calhint");
    if(!hint){ hint=document.createElement("div"); hint.id="dl-calhint"; document.body.appendChild(hint); }
    const m=METRICS[calState.idx];
    hint.style.cssText="position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:2147483647;background:#7C5CFF;color:#fff;padding:10px 18px;border-radius:100px;font:600 13px Inter,system-ui,-apple-system,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.4);display:flex;gap:10px;align-items:center;";
    hint.innerHTML=`Clique no número de <b style="text-decoration:underline">${m.label}</b>${m.opt?' (ou pule)':''} &nbsp;<button id="dl-skip" style="background:rgba(255,255,255,.2);border:none;color:#fff;padding:4px 10px;border-radius:100px;font-size:12px;cursor:pointer">pular</button> <button id="dl-calcancel" style="background:rgba(255,255,255,.2);border:none;color:#fff;padding:4px 10px;border-radius:100px;font-size:12px;cursor:pointer">cancelar</button>`;
    hint.querySelector("#dl-skip").onclick=e=>{ e.stopPropagation(); advanceCalib(); };
    hint.querySelector("#dl-calcancel").onclick=e=>{ e.stopPropagation(); endCalibration(); };
  }
  function calHover(e){ if(!calState)return; if(host&&(e.target===host||host.contains(e.target)))return;
    if(calState.hl&&calState.hl!==e.target) calState.hl.style.outline=calState.prevOutline||"";
    calState.hl=e.target; calState.prevOutline=e.target.style.outline; e.target.style.outline="2px solid #7C5CFF"; }
  function calClick(e){
    if(!calState)return; if(host&&(e.target===host||host.contains(e.target)))return;
    const hint=document.getElementById("dl-calhint"); if(hint&&hint.contains(e.target))return;
    e.preventDefault(); e.stopPropagation();
    const el=e.target, m=METRICS[calState.idx], selector=cssPath(el);
    let label=null; const prev=el.previousElementSibling, par=el.parentElement;
    if(prev&&prev.textContent&&prev.textContent.trim().length<40) label=prev.textContent.trim();
    else if(par){ const t=Array.from(par.querySelectorAll("*")).find(x=>x!==el&&x.children.length===0&&x.textContent&&x.textContent.trim().length<40&&!/\d/.test(x.textContent)); if(t) label=t.textContent.trim(); }
    state.calib[m.key]={selector,label,sample:(el.textContent||"").trim().slice(0,40)};
    if(el.style) el.style.outline=calState.prevOutline||""; advanceCalib();
  }
  function advanceCalib(){ calState.idx++; if(calState.idx>=METRICS.length){ endCalibration(); return; } showCalHint(); }

  /* ================= modo demo =================
     Serve pro smoke test e pra treinar operador fora do ar. Os números são
     inventados de propósito num cenário que ACENDE o painel: funil entrando bem
     e afunilando no meio (CO e ticket fracos) com o GMV atrás do ritmo.
     `demo:true` viaja junto no state — o popup se recusa a gravar no Supabase
     enquanto estiver ligado, pra dado fabricado nunca virar histórico. */
  function loadDemo(){
    const agora=Date.now();
    if(!state.startTime){ state.startTime=agora-95*60000; state.endTime=null; }
    if(!state.goal) { state.goal=10000; state.plannedMin=240; }
    state.demo=true;
    // snapshot anterior: sem ele as métricas de TENDÊNCIA (ERR, viewers, engajamento)
    // não têm contra o que comparar e o painel fica só com as de nível.
    state.snapshots=[{ t:agora-20*60000, err:14.2, impressions:38000, clicks:1183, viewers:5400, liveViewers:180,
                       ctr:21.9, co:2.7, gmv:3100, orders:38, comments:280, ctrProfile:"views" }];
    // clicks = ctr × views de propósito (1310 ≈ 21,4% de 6120): fecha a identidade e o
    // painel resolve a régua pelos cliques, não pela ordem de grandeza.
    state.current={ err:11.1, impressions:54000, clicks:1310, viewers:6120, liveViewers:152,
                    ctr:21.4, co:1.6, gmv:4180, orders:62, comments:210, t:agora };
    state.lastSnapAt=agora;
    saveState(); render();
  }
  function clearDemo(){
    state.demo=false;
    state.current={ err:null,impressions:null,clicks:null,viewers:null,liveViewers:null,ctr:null,co:null,convView:null,gmv:null,orders:null,comments:null,t:null };
    state.snapshots=[]; state.events=[]; state.violations=[]; state.lastSnapAt=null;
    saveState(); render();
  }

  /* ================= live loop ================= */
  function commitSnapshot(){
    const s=state.current;
    if(s.gmv==null&&s.viewers==null&&s.liveViewers==null&&s.err==null) return;
    state.snapshots.push({ t:Date.now(), err:s.err, impressions:s.impressions, clicks:s.clicks, viewers:s.viewers||0, liveViewers:s.liveViewers, ctr:s.ctr, co:s.co, gmv:s.gmv||0, orders:s.orders||0, comments:s.comments, ctrProfile:state.ctrProfile });
    state.lastSnapAt=Date.now(); saveState(); render();
  }
  function readTick(){
    if(orfao) return;
    if(!contextoVivo()) return marcarOrfao();
    if(!state.startTime||state.endTime) return;
    if(state.demo) return;               // demo congelado: leitura real só depois de limpar
    if(Object.keys(state.calib).length===0) return;
    let changed=false;
    METRICS.forEach(m=>{ const v=readMetric(m); if(v!=null){ state.current[m.key]=v; changed=true; } });
    if(changed){ state.current.t=Date.now();
      if(!state.lastSnapAt||Date.now()-state.lastSnapAt>=15*60000){ commitSnapshot(); return; }
      saveState(); render(); }
  }
  function applyLiveLoop(){
    const running=state.startTime&&!state.endTime;
    if(running&&!readInt) readInt=setInterval(readTick,8000);
    if(!running&&readInt){ clearInterval(readInt); readInt=null; }
    if(!uiInt) uiInt=setInterval(()=>{
      if(orfao) return;
      if(!contextoVivo()) return marcarOrfao();   // detecta em até 1s, mesmo fora de live
      const tm=root&&root.getElementById("dl-timer"); if(tm&&state.startTime){ const end=state.endTime||Date.now(); tm.textContent=hhmmss(end-state.startTime); }
    },1000);
  }

  function init(){ loadState(()=>{
    buildOverlay();
    // Sem nenhuma calibração ainda: tenta reconhecer sozinho antes de mostrar a tela
    // vazia. Se achar, o painel já nasce com número; se não, cai no fluxo manual.
    if (Object.keys(state.calib).length===0) { try { aplicarAutoMapa(); } catch(e){ console.warn("[DashLive] auto-mapa falhou:", e); } }
    render(); applyLiveLoop(); readTick();
  }); }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",init); else init();
})();
