// Smoke test do Admin via proxy. Loga com a senha, espera syncAll, e confere:
// painel visível, KPIs com valor, zero erros de console, e NENHUMA chamada
// /rest/v1 (tudo deve passar por /api/get-hub).
const { chromium } = require('playwright');
const BASE = process.argv[2] || 'http://localhost:3010';
const PASS = process.argv[3] || 'rhode2026';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [], restCalls = [], proxyCalls = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
  page.on('request', r => {
    const u = r.url();
    if (u.includes('/rest/v1/')) restCalls.push(u.split('/rest/v1/')[1].replace(/\?.*/, ''));
    if (u.includes('/api/get-hub')) proxyCalls.push(1);
  });

  await page.goto(`${BASE}/admin.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  // login
  await page.fill('#adm-pass', PASS);
  await page.click('button.btn-main');
  // espera o app aparecer + syncAll carregar (dá tempo das queries paginadas)
  await page.waitForSelector('#adm-app', { state: 'visible', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(9000);

  const appVisible = await page.isVisible('#adm-app').catch(() => false);
  const loginHidden = !(await page.isVisible('#adm-login').catch(() => true));
  const bodyText = (await page.textContent('body').catch(() => '') || '');
  const gmvMatches = (bodyText.match(/R\$[\s]?[\d.,]+[KM]?/g) || []).slice(0, 5);

  console.log('app visível:        ', appVisible);
  console.log('login escondido:    ', loginHidden);
  console.log('valores R$ na tela: ', gmvMatches.length ? gmvMatches : '(nenhum)');
  console.log('chamadas /api/get-hub:', proxyCalls.length);
  console.log('chamadas /rest/v1:  ', restCalls.length ? [...new Set(restCalls)] : '(nenhuma ✓)');
  console.log('erros de console:   ', consoleErrors.length ? consoleErrors.slice(0, 8) : '(nenhum ✓)');

  await page.screenshot({ path: '/tmp/admin-smoke.png', fullPage: false });
  console.log('screenshot:          /tmp/admin-smoke.png');

  const ok = appVisible && loginHidden && restCalls.length === 0 &&
             proxyCalls.length > 0 && gmvMatches.length > 0 && consoleErrors.length === 0;
  console.log('\nRESULTADO:', ok ? '✅ PASS' : '❌ FALHA');
  await browser.close();
  process.exit(ok ? 0 : 1);
})();
