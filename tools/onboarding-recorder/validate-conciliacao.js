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
  { periodo:'2026-06', gmv:160000, qty:1950, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644' },
  { periodo:'2026-06', gmv: 62000, qty: 760, produto:'Calça Mom Jeans Feminina Cintura Alta', seller_sku:'REF55140' },
  { periodo:'2026-06', gmv: 38000, qty: 470, produto:'Calça Baggy Jeans Feminina Cintura Média', seller_sku:'REF58238' },
  { periodo:'2026-06', gmv: 26530, qty: 443, produto:'Shorts Mom Feminino Jeans Cintura Alta', seller_sku:'REF58742' },
  { periodo:'2026-05', gmv:340000, qty:4277, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644' },
  { periodo:'2026-04', gmv:760000, qty:9100, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644' },
  { periodo:'2026-03', gmv:741000, qty:8900, produto:'Calça Jeans Feminina Wide Leg Cintura Alta', seller_sku:'REF51644' },
];

(async () => {
  const url = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1500 }, deviceScaleFactor: 2 });

  // injeta token de sessão antes de carregar (pula login)
  await page.addInitScript(() => { try { sessionStorage.setItem('rhode-admin-token','test-token'); } catch(e){} });

  await page.route('**/api/get-hub', async (route) => {
    let b={}; try{ b=JSON.parse(route.request().postData()||'{}'); }catch{}
    if (b.action === 'admin_login') return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ token:'test-token' }) });
    if (b.action === 'admin_query') {
      const p = b.path || '';
      const data = p.includes('finance_statements') ? FIN : p.includes('pedidos_sku') ? PED : [];
      return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ ok:true, status:200, data }) });
    }
    return route.continue();
  });

  await page.goto(`${url}/conciliacao.html`, { waitUntil:'networkidle' });
  await page.waitForTimeout(1500);
  const out = path.resolve(__dirname, 'out', 'conciliacao.png');
  await page.screenshot({ path: out, fullPage: true });
  console.log('screenshot:', out);
  await browser.close();
})();
