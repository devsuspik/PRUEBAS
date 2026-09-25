const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch();
for (const [nm,vp] of [['movil',{width:390,height:844,dpr:3,m:true}],['escritorio',{width:1280,height:800,dpr:1,m:false}]]) {
const ctx=await b.newContext({viewport:{width:vp.width,height:vp.height},deviceScaleFactor:vp.dpr,hasTouch:vp.m,isMobile:vp.m});
const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.goto('file://'+path.resolve('../../JUGADOR_COMPLETO/E06/index.html')); await p.waitForTimeout(700);
await p.click('button[title=Superponer]'); await p.waitForTimeout(700);
await p.selectOption('.ov-ctrl select','1'); await p.waitForTimeout(600);
await p.click('text=Calca en espejo'); await p.click('text=Mover calca');
// arrastrar la calca: de (150,820) a (60,984) en coordenadas de imagen
const s = await p.evaluate(()=>{const w=document.querySelector('.vw > div');const m=new DOMMatrix(getComputedStyle(w).transform);return m.a;});
const box = await p.locator('.vw').boundingBox();
const cx=box.x+box.width/2, cy=box.y+box.height/2;
await p.mouse.move(cx,cy); await p.mouse.down(); await p.mouse.move(cx+(60-150)*s, cy+(984-820)*s, {steps:12}); await p.mouse.up();
await p.waitForTimeout(300);
await p.evaluate(()=>document.querySelector('.vw').scrollIntoView());
await p.screenshot({path:`../../QA/capturas/E06_${nm}_superponer.png`});
// acercar a la zona
await p.click('text=Mover calca'); 
for (let i=0;i<3;i++) await p.click('button[title=Acercar]');
await p.screenshot({path:`../../QA/capturas/E06_${nm}_superponer_zoom.png`});
console.log(nm, 'escala', s.toFixed(3), errs.length?errs:'sin errores');
await ctx.close();}
await b.close();})();
