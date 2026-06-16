// sdCompute — lógica de cálculo do painel Seeding & Ativação (live).
// Recebe sample_applications (SA) + affiliate_creator_product (CP) → linhas por creator,
// com números por JANELA (30/60/90/Tudo) e segmentos de ação. Mesma lógica do protótipo.
// Reutilizável: testado em node e embutido no admin.
function sdCompute(SA, CP, today){
  const DELIV=new Set(['COMPLETED','CONTENT_PENDING']), TRANS=new Set(['SHIPPED']),
        PEND=new Set(['PENDING','AWAITING_SHIPMENT']), SENT=new Set(['COMPLETED','CONTENT_PENDING','SHIPPED']);
  const CU=40,FR=25,MG=0.55;
  const cutDays=d=>{const c=new Date(today);c.setDate(c.getDate()-d);return c.toISOString().slice(0,10);};
  const WINS={'30':cutDays(30),'60':cutDays(60),'90':cutDays(90),'0':'0000-00-00'}, CUT14=cutDays(14);
  const cpByCk={};
  CP.forEach(r=>{const k=(r.creator||'').toLowerCase();(cpByCk[k]||(cpByCk[k]=[])).push(
    {pid:String(r.product_id),data:r.data||'',gmv:+r.gmv||0,com:+r.comissao||0,ped:+r.pedidos||0});});
  const byc={};
  SA.forEach(a=>{const k=(a.creator||'').toLowerCase();if(!k)return;(byc[k]||(byc[k]={creator:a.creator,nick:a.nickname||a.creator,apps:[]})).apps.push(a);});
  const PRIO=['aguardando','ativar','reativar','cancelada','caminho','vendeubem','ativa'];
  const rows=[];
  for(const k in byc){
    const o=byc[k];
    let deliv=0,transit=0,pend=0,canc=0; const sampled=new Set(), rates=[], dates=[], allp=new Set();
    o.apps.forEach(a=>{
      if(DELIV.has(a.status))deliv++; else if(TRANS.has(a.status))transit++; else if(PEND.has(a.status))pend++; else canc++;
      if(a.product_id)allp.add(String(a.product_id));
      if(SENT.has(a.status)&&a.product_id)sampled.add(String(a.product_id));
      if(a.commission_rate!==''&&a.commission_rate!=null)rates.push(+a.commission_rate);
      if(a.convite_data)dates.push(a.convite_data);
    });
    const env=deliv+transit, custo=env*CU+(env>0?FR:0);
    rates.sort((x,y)=>x-y); const med=rates.length?rates[Math.floor(rates.length/2)]:0;
    const sales=(cpByCk[k]||[]).filter(r=>sampled.has(r.pid));
    let gmvAll=0,last=''; sales.forEach(r=>{gmvAll+=r.gmv; if(r.gmv>0&&r.data>last)last=r.data;});
    const w={};
    for(const wk in WINS){const cut=WINS[wk];let g=0,cm=0,p=0;
      sales.forEach(r=>{if(r.data>=cut){g+=r.gmv;cm+=r.com;p+=r.ped;}});
      g=Math.round(g*100)/100;cm=Math.round(cm*100)/100;
      w[wk]={gmv:g,com:cm,pedidos:p,lucro:Math.round((g*MG-cm-custo)*100)/100,roas:custo?Math.round(g/custo*10)/10:0};}
    const roasAll=custo?gmvAll/custo:0;
    dates.sort(); const ci=dates[0]||'', cf=dates[dates.length-1]||'';
    const estagio=deliv>0?'Recebida':transit>0?'A caminho':pend>0?'Aguardando':canc>0?'Cancelada':'—';
    const flags=[];
    if(pend>0)flags.push('aguardando');
    if(transit>0)flags.push('caminho');
    if(canc>0&&deliv===0&&transit===0&&pend===0)flags.push('cancelada');
    if(deliv>0)flags.push(gmvAll===0?'ativar':(last&&last<CUT14)?'reativar':roasAll>=2?'vendeubem':'ativa');
    const seg=PRIO.find(s=>flags.includes(s))||'ativa';
    const ACAO={aguardando:'aprovar '+pend+' amostra(s) pendente(s)',ativar:'recebeu, nunca vendeu — ativar',
      reativar:'vendeu e esfriou — reativar',cancelada:'nada chegou — re-ofertar',
      caminho:transit+' a caminho — aguardar entrega',vendeubem:'top — próxima amostra / subir tier',
      ativa:'ativa, vende pouco — monitorar'};
    rows.push({creator:o.creator,nick:o.nick,estagio,mes:ci?ci.slice(0,7):'—',ci:ci||'—',cf:cf||'—',
      env,transit,pend,canc,skus:allp.size,faixa:med<0.115?8:12,custo,last:last||'—',flags,seg,acao:ACAO[seg],w});
  }
  rows.sort((a,b)=>(b.w['90'].gmv-a.w['90'].gmv)||a.creator.localeCompare(b.creator));
  rows.forEach((r,i)=>r.n=i+1);
  return rows;
}
if(typeof module!=='undefined')module.exports={sdCompute};
