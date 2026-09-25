// Renderiza fuentes HTML a PNG con Chromium (Playwright).
// Uso: NODE_PATH=/opt/node22/lib/node_modules node render.js trabajos.json
// trabajos.json: [{ "html": "fuentes_html/e01_carta.html", "out": "_render/e01_anverso.png",
//                   "width": 1000, "height": 1300, "dpr": 2, "selector": "#hoja",
//                   "transparent": true, "query": "?cara=anverso" }]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const only = process.argv[3];
  const browser = await chromium.launch();
  for (const j of jobs) {
    if (only && !j.out.includes(only)) continue;
    const ctx = await browser.newContext({
      viewport: { width: j.width || 1000, height: j.height || 1000 },
      deviceScaleFactor: j.dpr || 1,
    });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => console.error('ERR', j.html, e.message));
    await page.goto('file://' + path.resolve(j.html) + (j.query || ''));
    await page.evaluate(() => document.fonts.ready);
    try {
      await page.waitForFunction(() => document.body.dataset.ready === '1', null, { timeout: 5000 });
    } catch (e) { /* páginas sin hand.js */ }
    await page.waitForTimeout(150);
    if (j.scroll !== undefined) {
      await page.evaluate((sc) => {
        const box = document.querySelector('#scroller') || document.scrollingElement;
        if (typeof sc === 'number') box.scrollTop = sc;
        else { const el = document.querySelector(sc); box.scrollTop = el.offsetTop - 8; }
      }, j.scroll);
      await page.waitForTimeout(80);
    }
    fs.mkdirSync(path.dirname(j.out), { recursive: true });
    if (j.selector) {
      const el = await page.$(j.selector);
      await el.screenshot({ path: j.out, omitBackground: !!j.transparent });
    } else {
      await page.screenshot({ path: j.out, fullPage: !!j.fullPage, omitBackground: !!j.transparent });
    }
    console.log('ok', j.out);
    await ctx.close();
  }
  await browser.close();
})();
