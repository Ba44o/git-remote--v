// Launch video recorder — grava qualquer página do ecossistema Rhode em mp4
// pronto pra WhatsApp/redes sociais. Saída: 1080×1080 / 1080×1920 / 1920×1080.
//
// Uso típico:
//   node record.js --mode=tour --aspect=1x1 --duration=55
//   node record.js --page=dash-live --aspect=9x16 --duration=40
//   node record.js --url=https://exemplo.com/qq?demo=tour --aspect=1x1
//
// Veja README.md pro guia completo.

const { chromium } = require('playwright');
const ffmpegPath = require('ffmpeg-static');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = Object.fromEntries(process.argv.slice(2).map(a => {
  const [k, v] = a.replace(/^--/, '').split('=');
  return [k, v ?? true];
}));

const ASPECT = args.aspect || '1x1';
const STYLE = args.style || '';
const MODE = args.mode || 'tour'; // tour | onboarding | (qualquer ?demo=xxx custom)
const PAGE = args.page || 'hub';   // hub | dash-live | admin | flash | ... (qualquer /xxx.html)
const NAME = args.name || `${PAGE}-${MODE}-${ASPECT}`;
const HEADLESS = args.headless !== 'false';

const SIZES = {
  '9x16': { width: 1080, height: 1920 },
  '1x1':  { width: 1080, height: 1080 },
  '16x9': { width: 1920, height: 1080 },
};
const SIZE = SIZES[ASPECT] || SIZES['1x1'];

const BASE = args.base || 'https://creators.rhodejeans.com.br';
const URL = args.url || `${BASE}/${PAGE}.html?demo=${MODE}&aspect=${ASPECT}${STYLE ? '&style='+STYLE : ''}&_=${Date.now()}`;
const DURATION_MS = (parseFloat(args.duration || '55')) * 1000;

const OUT_DIR = path.resolve(__dirname, 'out');
const WEBM_DIR = path.resolve(OUT_DIR, 'raw');
fs.mkdirSync(WEBM_DIR, { recursive: true });

const STAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const FINAL_MP4 = path.join(OUT_DIR, `${NAME}-${STAMP}.mp4`);

(async () => {
  console.log(`[1/4] Browser headless · viewport ${SIZE.width}×${SIZE.height} (${ASPECT})`);
  console.log(`      URL: ${URL}`);

  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext({
    viewport: SIZE,
    deviceScaleFactor: 1,
    isMobile: false,
    hasTouch: false,
    recordVideo: { dir: WEBM_DIR, size: SIZE },
  });

  const page = await context.newPage();
  // esconde cursor real do SO + scrollbars (cursor fantasma é injetado pela página)
  await page.addInitScript(() => {
    const s = document.createElement('style');
    s.textContent = `*{cursor:none !important} html,body{overflow:hidden !important} ::-webkit-scrollbar{display:none}`;
    document.documentElement.appendChild(s);
  });
  page.on('pageerror', e => console.log(`  ⚠ pageerror: ${e.message.slice(0, 120)}`));

  console.log(`[2/4] Navegando + aguardando boot…`);
  await page.goto(URL, { waitUntil: 'networkidle' });
  // best-effort: aguarda algum sinal de pronto (modal onboarding OU body.tour-mode)
  await Promise.race([
    page.waitForSelector('.onb-overlay.on', { timeout: 5000 }).catch(() => {}),
    page.waitForFunction(() => document.body.classList.contains('tour-mode'), { timeout: 5000 }).catch(() => {}),
    page.waitForTimeout(2500),
  ]);

  console.log(`[3/4] Gravando ${DURATION_MS / 1000}s…`);
  await page.waitForTimeout(DURATION_MS);

  const videoPath = await page.video().path();
  await context.close();
  await browser.close();
  console.log(`      webm raw: ${path.basename(videoPath)}`);

  console.log(`[4/4] Convertendo webm → mp4 (h264 + AAC silencioso, faststart)…`);
  await new Promise((resolve, reject) => {
    const ff = spawn(ffmpegPath, [
      '-y',
      '-i', videoPath,
      '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
      '-vf', `scale=${SIZE.width}:${SIZE.height}:flags=lanczos,setsar=1`,
      '-r', '30',
      '-c:a', 'aac', '-b:a', '128k',
      '-shortest', '-movflags', '+faststart',
      FINAL_MP4,
    ]);
    let dots = 0;
    ff.stderr.on('data', () => { if (++dots % 4 === 0) process.stderr.write('.'); });
    ff.on('close', code => code === 0 ? resolve() : reject(new Error('ffmpeg exit ' + code)));
  });
  process.stderr.write('\n');

  const stat = fs.statSync(FINAL_MP4);
  console.log(`\n✓  pronto: ${FINAL_MP4}`);
  console.log(`   ${(stat.size / 1024 / 1024).toFixed(2)} MB · ${SIZE.width}×${SIZE.height} · ${DURATION_MS / 1000}s\n`);

  // Opcional: copia pro Desktop pra acesso fácil
  if (args.desktop !== 'false') {
    const desktopDest = path.join(process.env.HOME || '', 'Desktop', path.basename(FINAL_MP4));
    try { fs.copyFileSync(FINAL_MP4, desktopDest); console.log(`📁 também em: ${desktopDest}`); }
    catch (e) { /* silencioso */ }
  }
})().catch(err => { console.error(err); process.exit(1); });
