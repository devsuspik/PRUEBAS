// Motor de manuscrito: rompe la uniformidad tipográfica de las fuentes "de mano".
// Cada elemento .hw se procesa letra por letra con un PRNG con semilla (render reproducible).
// Atributos opcionales en .hw:
//   data-seed        semilla (entero)
//   data-jit         intensidad general (1 = normal)
//   data-cross7      "1" para cruzar los sietes
//   data-slope       deriva de renglón en grados (±)
//   data-press       variación de presión (0-1)
(function () {
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function proc(el, idx) {
    const seed = +(el.dataset.seed || (1000 + idx * 17));
    const R = mulberry32(seed);
    const g = () => (R() + R() + R() - 1.5) / 1.5; // ~gaussiana en [-1,1]
    const J = +(el.dataset.jit || 1);
    const cross7 = el.dataset.cross7 === '1';
    const press = +(el.dataset.press || 0.18);
    const slope = +(el.dataset.slope || 0.5);
    const lines = el.querySelectorAll('.ln');
    const targets = lines.length ? lines : [el];
    targets.forEach((ln) => {
      // deriva del renglón completo
      const rot = g() * slope * J;
      const dx = g() * 3 * J;
      const dy = g() * 1.2 * J;
      ln.style.transform = `translate(${dx}px,${dy}px) rotate(${rot}deg)`;
      ln.style.transformOrigin = '0 50%';
      const walker = document.createTreeWalker(ln, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach((tn) => {
        if (tn.parentElement.closest('.nohw')) return;
        const frag = document.createDocumentFragment();
        let wordShift = 0;
        for (const ch of tn.textContent) {
          if (ch === ' ') {
            const sp = document.createElement('span');
            sp.className = 'hsp';
            sp.textContent = ' ';
            sp.style.letterSpacing = (g() * 2.5 * J) + 'px';
            frag.appendChild(sp);
            wordShift = g() * 0.8 * J;
            continue;
          }
          const s = document.createElement('span');
          s.className = 'hc';
          // ¡ y ¿ se trazan como ! y ? girados (varias fuentes de mano los traen vacíos o deformes)
          const inv = (ch === '¡' || ch === '¿');
          s.textContent = ch === '¡' ? '!' : ch === '¿' ? '?' : ch;
          const r = g() * 3.2 * J;
          const by = g() * 0.9 * J + wordShift;
          const sc = 1 + g() * 0.045 * J;
          const sk = g() * 2 * J;
          s.style.transform = inv
            ? `translateY(calc(${by}px + .2em)) rotate(${r + 180}deg) scale(${sc})`
            : `translateY(${by}px) rotate(${r}deg) skewX(${sk}deg) scale(${sc})`;
          s.style.opacity = (1 - press / 2 + g() * press / 2).toFixed(3);
          s.style.marginRight = (g() * 0.6 * J) + 'px';
          if (cross7 && ch === '7') s.classList.add('c7');
          frag.appendChild(s);
        }
        tn.parentNode.replaceChild(frag, tn);
      });
    });
  }
  window.renderHand = function () {
    document.querySelectorAll('.hw').forEach(proc);
  };
  document.addEventListener('DOMContentLoaded', () => {
    document.fonts.ready.then(() => { window.renderHand(); document.body.dataset.ready = '1'; });
  });
})();
