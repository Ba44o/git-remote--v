const { chromium } = require('playwright');
const path = require('path');

// Simula uma creator SEM venda no mês corrente (último período = maio/2026)
const NO_JUNE = [
  { periodo:'2026-05', gmv_bruto:6800, gmv_liquido:5200, reembolso:900, pedidos:48, videos:9, lives:2, comissao:1040, tier:'bronze', refund_pct:13 },
  { periodo:'2026-04', gmv_bruto:7400, gmv_liquido:5900, reembolso:760, pedidos:55, videos:11, lives:1, comissao:1180, tier:'bronze', refund_pct:10 },
  { periodo:'2026-03', gmv_bruto:5100, gmv_liquido:4200, reembolso:540, pedidos:39, videos:7, lives:0, comissao:840, tier:'bronze', refund_pct:11 },
];

(async () => {
  const url = process.argv[2];
  if (!url) { console.error('uso: node validate-empty-month.js <BASE_URL>'); process.exit(1); }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 430, height: 1500 }, deviceScaleFactor: 2 });

  await page.route('**/api/get-hub', async (route) => {
    const req = route.request();
    let body = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch {}
    if (body.action === 'perf') {
      return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify(NO_JUNE) });
    }
    return route.continue(); // bootstrap, profile, etc. seguem reais
  });

  await page.goto(`${url}/hub.html?token=TACI-PREVIEW-2026`, { waitUntil:'networkidle' });
  await page.waitForTimeout(3500);
  const out = path.resolve(__dirname, 'out', 'empty-month-state.png');
  await page.screenshot({ path: out, fullPage: true });
  console.log('screenshot:', out);
  await browser.close();
})();
