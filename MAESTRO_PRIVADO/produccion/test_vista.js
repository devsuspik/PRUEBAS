// Recorrido completo de la vista local (móvil): muestra → D1 → compra → E05..D2 → E09..D3 → E14
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', (e) => errs.push('page: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  p.on('requestfailed', (r) => { if (!/ERR_ABORTED/.test(r.failure().errorText)) errs.push('fallo: ' + r.url()); });
  await p.goto('file://' + path.resolve('../../VISTA_LOCAL/index.html')); await p.waitForTimeout(500);
  const cuenta = async () => p.$$eval('.card', (cs) => ({ total: cs.length, abiertas: cs.filter((c) => !c.disabled).length }));
  console.log('inicio', await cuenta());
  await p.screenshot({ path: '../../QA/capturas/VL_movil_inicio.png', fullPage: true });
  const fr = () => p.frame({ url: /index\.html$/ }) || p.frames()[1];
  async function abrir(id) { await p.click(`.card:has(.id:text-is("${id}"))`); await p.waitForTimeout(700); }
  async function deducir(id, ans) {
    await abrir(id); const f = p.frames().find((x) => x.url().includes('/' + id + '/'));
    for (const [q, v] of Object.entries(ans)) {
      if (Array.isArray(v)) for (const x of v) await f.check(`input[name="${q}"][value="${x}"]`);
      else if (v.startsWith('txt:')) await f.fill(`input[name="${q}"]`, v.slice(4));
      else await f.check(`input[name="${q}"][value="${v}"]`);
    }
    await f.click('button[type=submit]'); await p.waitForTimeout(600);
    await p.click('#cerrar'); await p.waitForTimeout(300);
  }
  for (const id of ['E01', 'E02', 'E03', 'E04']) { await abrir(id); await p.click('#cerrar'); }
  await deducir('D1', { q1: 'p4', q2: 'b8', q3: ['r1', 'r4'] });
  console.log('tras D1 sin compra', await cuenta());
  await p.check('#compra'); await p.waitForTimeout(200);
  console.log('tras compra', await cuenta());
  for (const id of ['E05', 'E06', 'E07', 'E08']) { await abrir(id); await p.click('#cerrar'); }
  await deducir('D2', { q1: 'f5', q2: 'u9', q3: 'm6', q4: 'txt:Lupe' });
  console.log('tras D2', await cuenta());
  for (const id of ['E09', 'E10', 'E11', 'E12', 'E13']) { await abrir(id); await p.click('#cerrar'); }
  await deducir('D3', { q1: 'd9', q2: 'h3', q3: 'k2', q4: ['p1', 'p3', 'p7'], q5: 'txt:Guadalupe Rangel' });
  console.log('tras D3', await cuenta());
  await abrir('E14'); await p.screenshot({ path: '../../QA/capturas/VL_movil_E14.png' }); await p.click('#cerrar');
  await p.screenshot({ path: '../../QA/capturas/VL_movil_final.png', fullPage: true });
  console.log(errs.length ? 'ERRORES:\n' + errs.join('\n') : 'sin errores');
  await b.close();
})();
