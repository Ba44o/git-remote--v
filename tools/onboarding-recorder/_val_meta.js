const { chromium } = require('playwright');
(async () => {
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1400,height:1700},deviceScaleFactor:1.5});
  await p.goto('https://dash.rhodejeans.com.br/dash-live.html',{waitUntil:'networkidle',timeout:45000});
  await p.waitForFunction(()=>{const o=document.getElementById('loading-overlay');return !o||o.style.display==='none';},{timeout:30000}).catch(()=>{});
  await p.evaluate(()=>showPage('meta')); await p.waitForTimeout(2500);
  await p.screenshot({path:'/Users/user/Documents/VS Claude Teste/tools/onboarding-recorder/out/meta10k.png'});
  const skus=await p.evaluate(()=>document.getElementById('meta-skus').children.length);
  const pie=await p.evaluate(()=>!!document.querySelector('#c-meta-pie'));
  console.log('cols top SKUs:',skus,'· pizza:',pie);
  await b.close();
})().catch(e=>{console.error('FAIL',e.message);process.exit(1);});
