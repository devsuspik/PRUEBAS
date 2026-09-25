// node test_deduccion.js <pagina> '<json respuestas correctas>' '<json incorrectas>'
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const [,, pg, okj, badj] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', (e) => errs.push(e.message));
  let msg = null; await p.exposeFunction('__m', (d) => { msg = d; });
  await p.addInitScript(() => { window.addEventListener('message', (e) => window.__m && window.__m(e.data)); });
  async function llenar(ans) {
    await p.goto('file://' + path.resolve(pg)); await p.waitForTimeout(300);
    for (const [q, v] of Object.entries(ans)) {
      if (Array.isArray(v)) for (const x of v) await p.check(`input[name="${q}"][value="${x}"]`);
      else if (v.startsWith('txt:')) await p.fill(`input[name="${q}"]`, v.slice(4));
      else await p.check(`input[name="${q}"][value="${v}"]`);
    }
    await p.click('button[type=submit]'); await p.waitForTimeout(500);
    return p.evaluate(() => ({ ok: document.querySelectorAll('.q.ok').length, no: document.querySelectorAll('.q.no').length, res: (document.querySelector('.res-box') || {}).innerText }));
  }
  console.log('INCORRECTAS:', JSON.stringify(await llenar(JSON.parse(badj))));
  console.log('CORRECTAS:', JSON.stringify(await llenar(JSON.parse(okj))));
  console.log('postMessage:', JSON.stringify(msg), errs.length ? 'ERR ' + errs : '');
  await p.screenshot({ path: '../../QA/capturas/' + path.basename(path.dirname(pg)) + '_exito.png', fullPage: true });
  await b.close();
})();
