const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 2 });
  const file = 'file://' + path.resolve(__dirname, 'story-central-comissoes.html');
  await page.goto(file, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200); // garante fontes do Google carregadas
  const out = path.resolve(__dirname, 'out', 'story-central-comissoes.png');
  await page.screenshot({ path: out });
  console.log('PNG salvo em:', out);
  await browser.close();
})();
