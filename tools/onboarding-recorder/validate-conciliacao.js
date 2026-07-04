const { chromium } = require('playwright');
const path = require('path');

// dados reais (1 linha/mês = agregado; a página soma por mês)
const FIN = [
  { data:'2026-03-15', revenue_amount:772590, fee_amount:-198361, shipping_cost:-17282, adjustment:4631, settlement:561577 },
  { data:'2026-04-15', revenue_amount:815215, fee_amount:-210351, shipping_cost:-17750, adjustment:5599, settlement:592713 },
  { data:'2026-05-15', revenue_amount:582984, fee_amount:-160045, shipping_cost:-13768, adjustment:3097, settlement:412268 },
  { data:'2026-06-08', revenue_amount:183616, fee_amount:-47024,  shipping_cost:-3477,  adjustment:1015, settlement:134131 },
];
// mock por produto (a página agrega por produto/mês pro ranking)
const PED = [
  { periodo:'2026-06', gmv:160000, qty:1950, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644', status:'DELIVERED' },
  { periodo:'2026-06', gmv: 62000, qty: 760, produto:'Calça Mom Jeans Feminina Cintura Alta', seller_sku:'REF55140', status:'COMPLETED' },
  { periodo:'2026-06', gmv: 38000, qty: 470, produto:'Calça Baggy Jeans Feminina Cintura Média', seller_sku:'REF58238', status:'DELIVERED' },
  { periodo:'2026-06', gmv: 26530, qty: 443, produto:'Shorts Mom Feminino Jeans Cintura Alta', seller_sku:'REF58742', status:'COMPLETED' },
  { periodo:'2026-06', gmv: 41000, qty: 510, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644', status:'CANCELLED' },
  { periodo:'2026-05', gmv:340000, qty:4277, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644', status:'DELIVERED' },
  { periodo:'2026-05', gmv: 95000, qty:1200, produto:'Calça Mom Jeans Feminina Cintura Alta', seller_sku:'REF55140', status:'CANCELLED' },
  { periodo:'2026-04', gmv:760000, qty:9100, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644', status:'DELIVERED' },
  { periodo:'2026-03', gmv:741000, qty:8900, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644', status:'DELIVERED' },
];

(async () => {
  const url = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1500 }, deviceScaleFactor: 2 });

  // injeta token de sessão antes de carregar (pula login)
  await page.addInitScript(() => { try { sessionStorage.setItem('rhode-admin-token','test-token'); } catch(e){} });

  // CPV mock (casa com os seller_sku do PED) pra renderizar a margem
  const CPV = [
    { ref:'REF51644', cpv:45 }, { ref:'REF55140', cpv:52 },
    { ref:'REF58238', cpv:45 }, { ref:'REF58742', cpv:38 },
  ];
  const ADS = [
    { periodo:'2026-06', campanha:'[GMV-MAX][MARMORIZADA-CARD-PRINCIPAL]', custo:23658, receita_bruta:163000, pedidos:1500 },
    { periodo:'2026-06', campanha:'[GMV-MAX][MOM-BAGGY]-07.05.26', custo:2075, receita_bruta:11000, pedidos:120 },
    { periodo:'2026-05', campanha:'[GMV-MAX][MARMORIZADA-CARD-PRINCIPAL]', custo:15159, receita_bruta:100000, pedidos:1000 },
  ];
  const STX = [
    { periodo:'2026-06', liquidados:3674, pendentes:261, devolvidos:500, pago_total:367220, settle_liq:262117, pago_liq:323614, a_receber:23778, devolucao:-8000, comissao_plataforma:20800, comissao_afiliada:12400, comissao_ads_afil:6200, frete:6500 },
    { periodo:'2026-05', liquidados:4621, pendentes:297, devolvidos:600, pago_total:523535, settle_liq:336633, pago_liq:439109, a_receber:28526, devolucao:-9000, comissao_plataforma:27200, comissao_afiliada:29000, comissao_ads_afil:3500, frete:8800 },
  ];
  const DIV = [
    { order_id:'581731099044840454', periodo:'2026-03', data:'2026-03-12', pago:348, status:'COMPLETED', produto:'Calça Jeans Wide Leg Marmorizada', classe:'repasse_faltante' },
    { order_id:'581898176810747069', periodo:'2026-03', data:'2026-03-08', pago:221, status:'COMPLETED', produto:'Calça Mom Jeans', classe:'repasse_faltante' },
    { order_id:'584154067080283289', periodo:'2026-06', data:'2026-06-20', pago:152, status:'IN_TRANSIT', produto:'Shorts Mom', classe:'pendente' },
    { order_id:'X1', periodo:'2026-03', data:'2026-03-15', pago:5000, status:'CANCELLED', produto:'Calça Wide Leg', classe:'cancelado' },
    { order_id:'X2', periodo:'2026-05', data:'2026-05-10', pago:3000, status:'CANCELLED', produto:'Calça Baggy', classe:'cancelado' },
  ];
  const PEDC = [
    { order_id:'584408285046146437', periodo:'2026-06', data:'2026-06-07', produto:'Calça Jeans Wide Leg Marmorizada', status:'COMPLETED', pago:99.90, settlement:73.50, taxa_pct:26.4, situacao:'liquidado' },
    { order_id:'584301122087654321', periodo:'2026-06', data:'2026-06-05', produto:'Calça Mom Jeans Cintura Alta', status:'COMPLETED', pago:89.90, settlement:66.10, taxa_pct:26.5, situacao:'liquidado' },
    { order_id:'584154067080283289', periodo:'2026-06', data:'2026-06-20', produto:'Shorts Mom Jeans', status:'IN_TRANSIT', pago:52.00, settlement:0, taxa_pct:null, situacao:'a_receber' },
    { order_id:'581731099044840454', periodo:'2026-06', data:'2026-06-12', produto:'Calça Baggy Marmorizada', status:'CANCELLED', pago:84.00, settlement:-20.00, taxa_pct:null, situacao:'devolvido' },
    { order_id:'584299881122334455', periodo:'2026-06', data:'2026-06-03', produto:'Body Básico Feminino Regata', status:'COMPLETED', pago:45.00, settlement:30.20, taxa_pct:32.9, situacao:'liquidado' },
  ];
  const OFI = [
    { periodo:'2026-06', pedidos_pagos:7151, gmv_oficial:628454, produto:611033, frete:9743, pago_cancelado:31148, produto_cancelado:30361, produto_valido:580672 },
    { periodo:'2026-05', pedidos_pagos:5574, gmv_oficial:523828, produto:505345, frete:13192, pago_cancelado:28696, produto_cancelado:27581, produto_valido:477726 },
    { periodo:'2026-04', pedidos_pagos:11061, gmv_oficial:917399, produto:877540, frete:32425, pago_cancelado:51312, produto_cancelado:49208, produto_valido:828332 },
    { periodo:'2026-03', pedidos_pagos:11141, gmv_oficial:932322, produto:893521, frete:32185, pago_cancelado:68876, produto_cancelado:66258, produto_valido:827263 },
  ];
  const CONCR = [
    { periodo:'2026-06', pedidos_total:7000, n_ok:6200, n_servico:300, n_comissao:20, n_devolucao:80, n_faltante:350, n_cancelado:50, receita:580000, repasse:430000, comissao_real:34800, comissao_esp:34800, servico_real:66000, servico_esp:62000, afiliada:38000, ads:5000, frete:6000, preco_tabela:1160000, desconto_vendedor:580000, div_servico_revisar:4000, custo_devolucao:2500, valor_faltante:12000, impacto_1507:12500 },
    { periodo:'2026-05', pedidos_total:5570, n_ok:4270, n_servico:209, n_comissao:15, n_devolucao:66, n_faltante:949, n_cancelado:61, receita:445000, repasse:336000, comissao_real:26700, comissao_esp:26700, servico_real:50300, servico_esp:47200, afiliada:28900, ads:3600, frete:4900, preco_tabela:890000, desconto_vendedor:445000, div_servico_revisar:3170, custo_devolucao:1800, valor_faltante:8000, impacto_1507:10500 },
  ];
  const CONCP = [
    { order_id:'584408285046146437', data:'2026-06-07', produto:'Calça Jeans Wide Leg Marmorizada', qty:1, preco_tabela:179.90, desconto_pct:44, receita_liq:99.90, comissao_real:5.99, comissao_esperada:5.99, servico_frete_real:9.99, servico_frete_esperado:10.59, afiliada_real:0, ads_real:7.99, settlement:74.73, taxa_efetiva_pct:24, conciliacao:'ok' },
    { order_id:'584232899716875843', data:'2026-06-05', produto:'Calça Baggy Jeans Feminina', qty:1, preco_tabela:179.90, desconto_pct:61, receita_liq:109.90, comissao_real:6.59, comissao_esperada:6.59, servico_frete_real:76.84, servico_frete_esperado:10.59, afiliada_real:0, ads_real:5.50, settlement:20.97, taxa_efetiva_pct:81, conciliacao:'servico_revisar' },
    { order_id:'584299881122334455', data:'2026-06-03', produto:'Body Básico Feminino Regata', qty:2, preco_tabela:90.00, desconto_pct:50, receita_liq:45.00, comissao_real:2.70, comissao_esperada:2.70, servico_frete_real:8.70, servico_frete_esperado:10.70, afiliada_real:4.50, ads_real:0, settlement:29.10, taxa_efetiva_pct:35, conciliacao:'com_devolucao' },
    { order_id:'584154067080283289', data:'2026-06-20', produto:'Shorts Mom Jeans', qty:1, preco_tabela:80.00, desconto_pct:35, receita_liq:52.00, comissao_real:3.12, comissao_esperada:3.12, servico_frete_real:7.12, servico_frete_esperado:7.12, afiliada_real:0, ads_real:0, settlement:0, taxa_efetiva_pct:0, conciliacao:'repasse_faltante' },
  ];
  const ADCUSTO = [
    { periodo:'2026-06', custo:78000, receita:581000, pedidos:1800, roi:7.45 },
    { periodo:'2026-05', custo:48003, receita:668265, pedidos:2600, roi:7.0 },
    { periodo:'2026-04', custo:52000, receita:700000, pedidos:2400, roi:7.2 },
    { periodo:'2026-03', custo:50000, receita:690000, pedidos:2300, roi:7.1 },
  ];
  const ADCAMP = [
    { data:'2026-06-07', periodo:'2026-06', campaign_id:'1837899752347697', campanha:'[GMV-MAX][MARMORIZADA-CARD-PRINCIPAL]', modelo:'tradicional', cost:23663.87, net_cost:23613.20, receita:163126.24, pedidos:1729 },
    { data:'2026-06-07', periodo:'2026-06', campaign_id:'1850046186207441', campanha:'LIVE-TESTE-GMV-MAX', modelo:'tradicional', cost:8812.97, net_cost:8748.91, receita:79363.02, pedidos:935 },
    { data:'2026-06-07', periodo:'2026-06', campaign_id:'1865736380155937', campanha:'[GMV]-[MIX_PRODUTOS][TESTE VENDAS LIQUIDAS]-20.05', modelo:'vendas_liquidas', cost:4752.78, net_cost:0, receita:24396.46, pedidos:240 },
    { data:'2026-06-07', periodo:'2026-06', campaign_id:'1866366311820657', campanha:'[GMV-MAX]-TESTE DE VENDAS LIQUIDAS-[MOM-BAGGY]-27.05.26', modelo:'vendas_liquidas', cost:4554.31, net_cost:0, receita:16836.86, pedidos:164 },
    { data:'2026-06-07', periodo:'2026-06', campaign_id:'1861190909809970', campanha:'[GMVMAX][AZM-BRANCA-STN-USED]-31.03.26', modelo:'tradicional', cost:979.06, net_cost:974.57, receita:6558.39, pedidos:65 },
    { data:'2026-05-07', periodo:'2026-05', campaign_id:'1837899752347697', campanha:'[GMV-MAX][MARMORIZADA-CARD-PRINCIPAL]', modelo:'tradicional', cost:15161.79, net_cost:15006.48, receita:100235.83, pedidos:997 },
  ];
  await page.route('**/api/get-hub', async (route) => {
    let b={}; try{ b=JSON.parse(route.request().postData()||'{}'); }catch{}
    if (b.action === 'admin_login') return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ token:'test-token' }) });
    if (b.action === 'admin_query') {
      const p = b.path || '';
      const data = p.includes('ads_campanha') ? ADCAMP : p.includes('ads_custo_resumo') ? ADCUSTO : p.includes('conciliacao_resumo') ? CONCR : p.includes('conciliacao_pedido') ? CONCP : p.includes('gmv_oficial_resumo') ? OFI : p.includes('pedido_conciliado') ? PEDC : p.includes('repasse_divergencias') ? DIV : p.includes('statement_tx_resumo') ? STX : p.includes('finance_statements') ? FIN : p.includes('pedidos_sku') ? PED : p.includes('custos_sku') ? CPV : p.includes('ads_gmvmax') ? ADS : [];
      return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ ok:true, status:200, data }) });
    }
    return route.continue();
  });

  await page.goto(`${url}/conciliacao.html`, { waitUntil:'networkidle' });
  await page.waitForTimeout(1800);
  const tabs = ['visao','conciliacao','repasse','receber','produtos','lucro','ads','pedidos'];
  for (const t of tabs) {
    if (t !== 'visao') { await page.click(`#tabnav button[data-t="${t}"]`).catch(()=>{}); await page.waitForTimeout(700); }
    const out = path.resolve(__dirname, 'out', `conc-${t}.png`);
    await page.screenshot({ path: out, fullPage: true });
    console.log('screenshot:', out);
  }
  // testa o export XLSX de verdade
  try {
    const [dl] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      page.click('#btn-export'),
    ]);
    const p2 = path.resolve(__dirname, 'out', dl.suggestedFilename());
    await dl.saveAs(p2);
    console.log('EXPORT OK:', dl.suggestedFilename());
  } catch (e) { console.log('EXPORT FAIL:', e.message); }
  await browser.close();
})();
