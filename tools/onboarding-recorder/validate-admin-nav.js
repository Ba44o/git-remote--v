const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const url = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 700 }, deviceScaleFactor: 2 });
  await page.addInitScript(() => { try { sessionStorage.setItem('rhode-admin-token','test-token'); } catch(e){} });
  // admin faz muitas queries no load; devolve vazio pra não travar — só queremos a topbar
  await page.route('**/api/get-hub', async (route) => {
    let b={}; try{ b=JSON.parse(route.request().postData()||'{}'); }catch{}
    if (b.action === 'admin_login') return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ token:'test-token' }) });
    if (b.action === 'admin_query') return route.fulfill({ status:200, contentType:'application/json', body: JSON.stringify({ ok:true, status:200, data:[] }) });
    return route.continue();
  });
  await page.goto(`${url}/admin.html`, { waitUntil:'domcontentloaded' });
  await page.waitForTimeout(2500);
  const out = path.resolve(__dirname, 'out', 'admin-nav.png');
  await page.screenshot({ path: out, clip: { x:0, y:0, width:1280, height:140 } });
  console.log('screenshot:', out);
  await browser.close();
})();
