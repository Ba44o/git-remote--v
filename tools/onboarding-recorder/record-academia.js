// Recorder dedicado da Rhode Academy (/academia?demo=tour) → mp4 9:16 pronto p/ WhatsApp/Reels.
// Renderiza a página MOBILE a 540px CSS (dsf 2) e grava em 1080×1920 — cara de celular,
// coluna única, sem margens vazias. Usa o Chrome do sistema (channel:'chrome') e a mesma
// conversão do record.js (h264 + AAC silencioso + faststart).
//
// Uso:  node record-academia.js [--url=...] [--duration=35] [--width=540]
const { chromium } = require('playwright');
const ffmpegPath = require('ffmpeg-static');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, v] = a.replace(/^--/, '').split('='); return [k, v ?? true]; }));
const CSS_W = parseInt(args.width || '540', 10);
const CSS_H = Math.round(CSS_W * 16 / 9);
const OUT_W = 1080, OUT_H = 1920;
const DURATION_MS = (parseFloat(args.duration || '35')) * 1000;
const TRIM_HEAD = parseFloat(args.trimhead || '1.6');   // corta o boot em branco do começo
const URL = (args.url || 'http://localhost:8799/academia.html?demo=tour') + (args.url && args.url.includes('?') ? '' : '') + `&_=${Date.now()}`;

const OUT_DIR = path.resolve(__dirname, 'out');
const RAW_DIR = path.resolve(OUT_DIR, 'raw');
fs.mkdirSync(RAW_DIR, { recursive: true });
const STAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const FINAL_MP4 = path.join(OUT_DIR, `academia-tour-${STAMP}.mp4`);

(async () => {
  console.log(`[1/4] Chrome do sistema · render ${CSS_W}×${CSS_H} CSS · vídeo ${OUT_W}×${OUT_H}`);
  console.log(`      URL: ${URL}`);
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const context = await browser.newContext({
    viewport: { width: CSS_W, height: CSS_H },
    deviceScaleFactor: 2,
    recordVideo: { dir: RAW_DIR, size: { width: CSS_W, height: CSS_H } },
  });
  const page = await context.newPage();
  await page.addInitScript(() => {
    const inject = () => {
      const root = document.documentElement || document.head || document.body;
      if (!root) return;
      const s = document.createElement('style');
      s.textContent = `*{cursor:none !important} html,body{overflow:hidden !important} ::-webkit-scrollbar{display:none}`;
      root.appendChild(s);
    };
    if (document.documentElement) inject();
    else document.addEventListener('DOMContentLoaded', inject);
  });
  page.on('pageerror', e => console.log(`  ⚠ pageerror: ${e.message.slice(0, 120)}`));

  console.log(`[2/4] Navegando + aguardando tour-mode…`);
  await page.goto(URL, { waitUntil: 'networkidle' });
  await Promise.race([
    page.waitForFunction(() => document.body.classList.contains('tour-mode'), { timeout: 5000 }).catch(() => {}),
    page.waitForTimeout(2000),
  ]);

  console.log(`[3/4] Gravando ${DURATION_MS / 1000}s…`);
  await page.waitForTimeout(DURATION_MS);
  const videoPath = await page.video().path();
  await context.close();
  await browser.close();

  console.log(`[4/4] webm → mp4 (h264 + AAC silencioso, faststart)…`);
  await new Promise((resolve, reject) => {
    const ff = spawn(ffmpegPath, [
      '-y', '-ss', String(TRIM_HEAD), '-i', videoPath,
      '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
      '-vf', `scale=${OUT_W}:${OUT_H}:flags=lanczos,setsar=1`, '-r', '30',
      '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', FINAL_MP4,
    ]);
    let d = 0; ff.stderr.on('data', () => { if (++d % 4 === 0) process.stderr.write('.'); });
    ff.on('close', c => c === 0 ? resolve() : reject(new Error('ffmpeg exit ' + c)));
  });
  process.stderr.write('\n');
  const mb = (fs.statSync(FINAL_MP4).size / 1024 / 1024).toFixed(2);
  console.log(`\n✓ pronto: ${FINAL_MP4}  (${mb} MB · ${OUT_W}×${OUT_H})`);
  try { const d = path.join(process.env.HOME || '', 'Desktop', path.basename(FINAL_MP4)); fs.copyFileSync(FINAL_MP4, d); console.log(`📁 também em: ${d}`); } catch (e) {}
})().catch(e => { console.error(e); process.exit(1); });
