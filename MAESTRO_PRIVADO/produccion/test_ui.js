// Prueba visual/funcional rápida de una página: node test_ui.js <ruta.html> <salida_prefijo> [acciones]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [,, page, out, acts] = process.argv;
  const b = await chromium.launch();
  const errs = [];
  for (const [nm, vp] of [['movil', { width: 390, height: 844, dpr: 3 }], ['escritorio', { width: 1280, height: 800, dpr: 1 }]]) {
    const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.dpr, hasTouch: nm === 'movil', isMobile: nm === 'movil' });
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errs.push(nm + ': ' + e.message));
    p.on('console', (m) => { if (m.type() === 'error') errs.push(nm + ' console: ' + m.text()); });
    p.on('requestfailed', (r) => { if (!/ERR_ABORTED/.test(r.failure().errorText)) errs.push(nm + ' fallo: ' + r.url()); });
    await p.goto('file://' + path.resolve(page));
    await p.waitForTimeout(900);
    await p.screenshot({ path: `${out}_${nm}.png` });
    if (acts) {
      for (const a of acts.split(';')) {
        const i = a.indexOf('='); const kind = a.slice(0, i), arg = a.slice(i + 1);
        if (kind === 'click') await p.click(arg);
        if (kind === 'wait') await p.waitForTimeout(+arg);
        if (kind === 'shot') await p.screenshot({ path: `${out}_${nm}_${arg}.png`, fullPage: false });
        if (kind === 'full') await p.screenshot({ path: `${out}_${nm}_${arg}.png`, fullPage: true });
        if (kind === 'key') await p.keyboard.press(arg);
        if (kind === 'focus') await p.focus(arg);
      }
    }
    await ctx.close();
  }
  console.log(errs.length ? 'ERRORES:\n' + errs.join('\n') : 'sin errores');
  await b.close();
})();
