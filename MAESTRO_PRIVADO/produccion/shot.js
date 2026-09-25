// Uso: node shot.js <html> <png> [ancho] [dpr] [selector]
const { chromium } = require('playwright');
(async () => {
  const [,, src, out, w='1200', dpr='1', sel] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: 800 }, deviceScaleFactor: +dpr });
  await p.goto('file://' + require('path').resolve(src));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  if (sel) await (await p.$(sel)).screenshot({ path: out, omitBackground: true });
  else await p.screenshot({ path: out, fullPage: true });
  await b.close();
})();
