const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch();
const ids=[['JUGADOR_GRATIS',['E01','E02','E03','E04','D1']],['JUGADOR_COMPLETO',['E05','E06','E07','E08','D2','E09','E10','E11','E12','E13','D3','E14']]];
const errs=[];
for (const [pk,list] of ids) for (const id of list) {
 for (const [nm,vp] of [['m',{width:390,height:844,dpr:2,mob:true}],['d',{width:1280,height:800,dpr:1,mob:false}]]) {
  const ctx=await b.newContext({viewport:{width:vp.width,height:vp.height},deviceScaleFactor:vp.dpr,isMobile:vp.mob,hasTouch:vp.mob});
  const p=await ctx.newPage(); p.on('pageerror',e=>errs.push(id+' '+e.message));
  p.on('requestfailed', r=>{ if(!/ERR_ABORTED/.test(r.failure().errorText)) errs.push(id+' fallo '+r.url()); });
  await p.goto('file://'+path.resolve(`../../${pk}/${id}/index.html`)); await p.waitForTimeout(700);
  // desplazar hasta el visor
  await p.evaluate(()=>{const m=document.querySelector('.ev-main'); if(m) window.scrollTo(0,m.offsetTop);});
  await p.waitForTimeout(250);
  await p.screenshot({path:`../../QA/capturas/pg_${id}_${nm}.png`});
  await ctx.close();
 }}
console.log(errs.length?errs.join('\n'):'sin errores'); await b.close();})();
