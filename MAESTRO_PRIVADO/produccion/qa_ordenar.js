const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch(); const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true});
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.goto('file://'+path.resolve('../../JUGADOR_COMPLETO/E08/index.html')); await p.waitForTimeout(700);
await p.screenshot({path:'../../QA/capturas/E08_movil_mesa.png'});
await p.click('text=Revisar el orden'); await p.waitForTimeout(400);
console.log('inicial:', await p.textContent('.ord .res[role=status]'));
// ordenar: llegada D,H,A,F,C,G,B,E -> objetivo A..H usando botones subir
const target=['Foto 3','Foto 7','Foto 5','Foto 1','Foto 8','Foto 4','Foto 6','Foto 2'];
for (let i=0;i<target.length;i++){
  while(true){
    const labels=await p.$$eval('.ord li .tx b',bs=>bs.map(x=>x.textContent));
    const k=labels.indexOf(target[i]); if(k<=i) break;
    await p.click(`.ord li:nth-child(${k+1}) .mv button:first-child`);
  }
}
await p.click('text=Revisar el orden'); await p.waitForTimeout(400);
console.log('final:', await p.textContent('.ord .res[role=status]'));
await p.click('.ord li:nth-child(1) img'); await p.waitForTimeout(600);
await p.screenshot({path:'../../QA/capturas/E08_movil_lightbox.png'});
console.log(errs.length?errs:'sin errores'); await b.close();})();
