const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
p.on('requestfailed', r=>console.log('failed', r.url().slice(-30), r.failure().errorText));
await p.goto('file://'+path.resolve('../../JUGADOR_GRATIS/E03/index.html'));await p.waitForTimeout(800);
const r=await p.evaluate(async()=>{const a=new Audio('audio/PTT-20250628-WA0007.mp3'); await new Promise(res=>{a.onloadedmetadata=res;a.onerror=res;setTimeout(res,3000)}); return [a.duration, a.error&&a.error.code, a.canPlayType('audio/mpeg')];});
console.log(r); await p.click('.play'); await p.waitForTimeout(1500); console.log(await p.evaluate(()=>document.querySelector('.au .t').textContent));
await p.screenshot({path:'../../QA/capturas/E03_movil_play.png'}); await b.close();})();
