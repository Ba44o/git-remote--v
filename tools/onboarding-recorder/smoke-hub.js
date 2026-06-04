// Smoke test do Hub via proxy (/api/get-hub). Boota com o preview token e
// confere: app visível, sem erros de console, sem request /rest/v1 sensível
// vazando da página, e que o hero/perf renderizou.
const { chromium } = require('playwright');

const BASE = process.argv[2] || 'http://localhost:3010';
const TOKEN = 'TACI-PREVIEW-2026';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  const restCalls = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
  page.on('request', r => {
    const u = r.url();
    if (u.includes('/rest/v1/')) restCalls.push(u.replace(/\?.*/, '').split('/rest/v1/')[1]);
  });

  await page.goto(`${BASE}/hub.html?token=${TOKEN}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForTimeout(3000);

  const appVisible = await page.isVisible('#app').catch(() => false);
  const loadingHidden = !(await page.isVisible('#loading').catch(() => true));
  const heroText = (await page.textContent('#hero-section').catch(() => '') || '').trim().slice(0, 80);
  const bodyText = (await page.textContent('body').catch(() => '') || '');
  const hasGMV = /R\$/.test(bodyText);

  console.log('app visível:        ', appVisible);
  console.log('loading escondido:  ', loadingHidden);
  console.log('hero render:        ', heroText ? `"${heroText}…"` : '(vazio)');
  console.log('tem valor R$:       ', hasGMV);
  console.log('chamadas /rest/v1:  ', restCalls.length ? [...new Set(restCalls)] : '(nenhuma — tudo via proxy ✓)');
  console.log('erros de console:   ', consoleErrors.length ? consoleErrors.slice(0, 8) : '(nenhum ✓)');

  await page.screenshot({ path: '/tmp/hub-smoke.png', fullPage: false });
  console.log('screenshot:          /tmp/hub-smoke.png');

  const ok = appVisible && loadingHidden && consoleErrors.length === 0 &&
             restCalls.every(t => t === 'hub_eventos'); // só analytics pode ir direto
  console.log('\nRESULTADO:', ok ? '✅ PASS' : '❌ FALHA');
  await browser.close();
  process.exit(ok ? 0 : 1);
})();
