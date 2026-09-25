/* Visor de evidencias de «La carta 35».
   Lee window.EVIDENCIA (definido en cada index.html de evidencia) y construye la página.
   Sin dependencias. Funciona desde file:// y en cualquier servidor estático.
   Teclado en el visor: + / - acercar/alejar · 0 ajustar · flechas mover · R girar · E espejo · C realce. */
(function () {
  'use strict';
  const E = window.EVIDENCIA;
  if (!E) return;
  const doc = document;
  const el = (tag, attrs, ...kids) => {
    const n = doc.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class') n.className = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== undefined && attrs[k] !== null) n.setAttribute(k, attrs[k]);
    }
    kids.flat().forEach((c) => c != null && n.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c));
    return n;
  };
  const ICON = {
    fit: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    zin: '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5 21 21M10.5 7.5v6M7.5 10.5h6" stroke="currentColor" stroke-width="2"/></svg>',
    zout: '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5 21 21M7.5 10.5h6" stroke="currentColor" stroke-width="2"/></svg>',
    rot: '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.4-5.7M20 4v5h-5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    mir: '<svg viewBox="0 0 24 24"><path d="M12 3v18M9 7 4 17h5zM15 7l5 10h-5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
    fx: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/></svg>',
    cmp: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="8" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="2"/><rect x="13" y="4" width="8" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    ov: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="12" height="12" rx="1" fill="none" stroke="currentColor" stroke-width="2"/><rect x="9" y="9" width="12" height="12" rx="1" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 2"/></svg>',
    play: '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z" fill="currentColor"/></svg>',
    pause: '<svg viewBox="0 0 24 24"><path d="M6 4h4v16H6zM14 4h4v16h-4z" fill="currentColor"/></svg>',
  };
  // Realce pensado para marcas tenues sobre papel claro: primero baja el blanco y luego estira el contraste.
  const REALCE = ['none', 'saturate(1.8) contrast(1.35)', 'saturate(4) brightness(0.66) contrast(3.2)', 'grayscale(1) brightness(0.62) contrast(4)'];

  /* ------------------------------------------------------------ Visor de imagen */
  class Visor {
    constructor(host, etiqueta) {
      this.host = host;
      host.classList.add('vw');
      host.tabIndex = 0;
      host.setAttribute('role', 'img');
      this.wrap = el('div', { style: 'position:absolute;left:0;top:0;transform-origin:0 0' });
      this.img = el('img', { draggable: 'false', alt: '' });
      this.img.style.position = 'static';
      this.wrap.appendChild(this.img);
      host.appendChild(this.wrap);
      if (etiqueta) { this.lbl = el('span', { class: 'lbl' }, etiqueta); host.appendChild(this.lbl); }
      this.s = 1; this.cx = 0; this.cy = 0; this.rot = 0; this.mir = false; this.fx = 0;
      this.w = 1; this.h = 1; this.ptrs = new Map(); this.overlay = null; this.moveOverlay = false;
      this.bind();
      new ResizeObserver(() => { if (!this.touched) this.fit(); else this.apply(); }).observe(host);
    }
    load(src, alt) {
      return new Promise((res) => {
        this.img.onload = () => { this.w = this.img.naturalWidth; this.h = this.img.naturalHeight; this.touched = false; this.rot = 0; this.mir = false; this.fit(); res(); };
        this.img.onerror = () => { this.host.setAttribute('aria-label', 'No se pudo cargar la imagen'); res(); };
        this.img.src = src;
        this.img.alt = alt || '';
        this.host.setAttribute('aria-label', alt || 'Imagen de la evidencia');
      });
    }
    fit() {
      const W = this.host.clientWidth, H = this.host.clientHeight;
      if (!W || !H) return;
      const r90 = Math.abs(this.rot % 180) === 90;
      const bw = r90 ? this.h : this.w, bh = r90 ? this.w : this.h;
      this.s = Math.min(W / bw, H / bh) * 0.96;
      this.cx = W / 2; this.cy = H / 2;
      this.apply();
    }
    apply() {
      this.wrap.style.transform = `translate(${this.cx}px,${this.cy}px) scale(${this.s}) rotate(${this.rot}deg) scaleX(${this.mir ? -1 : 1}) translate(${-this.w / 2}px,${-this.h / 2}px)`;
      this.wrap.style.width = this.w + 'px';
      this.wrap.style.height = this.h + 'px';
      this.img.style.filter = REALCE[this.fx];
      if (this.overlay) this.overlay.apply();
    }
    zoomAt(k, px, py) {
      const ns = Math.max(0.05, Math.min(this.s * k, 12));
      k = ns / this.s;
      this.cx = px - (px - this.cx) * k; this.cy = py - (py - this.cy) * k; this.s = ns;
      this.touched = true; this.apply();
    }
    zoom(k) { this.zoomAt(k, this.host.clientWidth / 2, this.host.clientHeight / 2); }
    rotate() { this.rot = (this.rot + 90) % 360; this.fit(); this.touched = true; }
    mirror() { this.mir = !this.mir; this.apply(); return this.mir; }
    realce() { this.fx = (this.fx + 1) % REALCE.length; this.apply(); return this.fx; }
    // pantalla -> coordenadas de la imagen (sin giro ni espejo, suficiente para la calca)
    toImg(dx, dy) { return [dx / this.s, dy / this.s]; }
    bind() {
      const H = this.host;
      let last = null, pinch = null, tapT = 0;
      H.addEventListener('pointerdown', (e) => {
        H.setPointerCapture(e.pointerId);
        this.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
        H.classList.add('drag');
        if (this.ptrs.size === 2) {
          const [a, b] = [...this.ptrs.values()];
          pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
        }
        const now = Date.now();
        if (now - tapT < 300 && this.ptrs.size === 1) {
          const r = H.getBoundingClientRect();
          if (this.s > this.fitScale() * 1.5) this.fit(); else this.zoomAt(2.5, e.clientX - r.left, e.clientY - r.top);
        }
        tapT = now;
        last = { x: e.clientX, y: e.clientY };
      });
      H.addEventListener('pointermove', (e) => {
        if (!this.ptrs.has(e.pointerId)) return;
        this.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (this.ptrs.size === 2 && pinch) {
          const [a, b] = [...this.ptrs.values()];
          const d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          const r = H.getBoundingClientRect();
          this.cx += mx - pinch.mx; this.cy += my - pinch.my;
          this.zoomAt(d / pinch.d, mx - r.left, my - r.top);
          pinch = { d, mx, my };
          return;
        }
        if (last) {
          const dx = e.clientX - last.x, dy = e.clientY - last.y;
          if (this.overlay && this.moveOverlay) this.overlay.nudgeScreen(dx, dy);
          else { this.cx += dx; this.cy += dy; this.touched = true; this.apply(); }
          last = { x: e.clientX, y: e.clientY };
        }
      });
      const up = (e) => { this.ptrs.delete(e.pointerId); if (this.ptrs.size < 2) pinch = null; if (!this.ptrs.size) { last = null; H.classList.remove('drag'); } else { const v = [...this.ptrs.values()][0]; last = { x: v.x, y: v.y }; } };
      H.addEventListener('pointerup', up); H.addEventListener('pointercancel', up);
      H.addEventListener('wheel', (e) => { e.preventDefault(); const r = H.getBoundingClientRect(); this.zoomAt(Math.exp(-e.deltaY * 0.0016), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
      H.addEventListener('keydown', (e) => {
        const k = e.key;
        if (k === '+' || k === '=') this.zoom(1.25);
        else if (k === '-') this.zoom(0.8);
        else if (k === '0') this.fit();
        else if (k.startsWith('Arrow')) {
          const st = e.shiftKey ? 8 : 40;
          const dx = k === 'ArrowLeft' ? st : k === 'ArrowRight' ? -st : 0, dy = k === 'ArrowUp' ? st : k === 'ArrowDown' ? -st : 0;
          if (this.overlay && this.moveOverlay) this.overlay.nudgeScreen(-dx / 8, -dy / 8);
          else { this.cx += dx; this.cy += dy; this.apply(); }
        } else if (k === 'r' || k === 'R') this.rotate();
        else if (k === 'e' || k === 'E') this.mirror();
        else if (k === 'c' || k === 'C') this.realce();
        else return;
        e.preventDefault();
      });
    }
    fitScale() {
      const W = this.host.clientWidth, H = this.host.clientHeight;
      const r90 = Math.abs(this.rot % 180) === 90;
      return Math.min(W / (r90 ? this.h : this.w), H / (r90 ? this.w : this.h)) * 0.96;
    }
  }

  /* ------------------------------------------------------------ Audio */
  function reproductor(p) {
    const a = new Audio(p.src);
    a.preload = 'metadata';
    const cv = el('canvas', { 'aria-label': 'Posición en la grabación', role: 'slider', tabindex: '0' });
    const bt = el('button', { class: 'play', 'aria-label': 'Reproducir', html: ICON.play });
    const tt = el('span', { class: 't' }, '0:00 / ' + (p.duracion || '--:--'));
    const fmt = (s) => { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
    const peaks = p.picos || [];
    function draw() {
      const r = cv.getBoundingClientRect(), d = window.devicePixelRatio || 1;
      cv.width = r.width * d; cv.height = r.height * d;
      const g = cv.getContext('2d'); g.scale(d, d);
      const n = peaks.length || 80, bw = r.width / n, pr = a.duration ? a.currentTime / a.duration : 0;
      for (let i = 0; i < n; i++) {
        const v = peaks.length ? peaks[i] : 0.3;
        const hh = Math.max(3, v * (r.height - 6));
        g.fillStyle = i / n < pr ? '#e3b04b' : '#5b6167';
        g.fillRect(i * bw + 1, (r.height - hh) / 2, Math.max(1, bw - 2), hh);
      }
    }
    a.addEventListener('timeupdate', () => { tt.textContent = fmt(a.currentTime) + ' / ' + (p.duracion || fmt(a.duration)); draw(); });
    a.addEventListener('ended', () => { bt.innerHTML = ICON.play; bt.setAttribute('aria-label', 'Reproducir'); });
    bt.addEventListener('click', () => { if (a.paused) { a.play(); bt.innerHTML = ICON.pause; bt.setAttribute('aria-label', 'Pausa'); } else { a.pause(); bt.innerHTML = ICON.play; bt.setAttribute('aria-label', 'Reproducir'); } });
    const seek = (e) => { const r = cv.getBoundingClientRect(); if (a.duration) a.currentTime = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * a.duration; draw(); };
    cv.addEventListener('pointerdown', (e) => { seek(e); cv.setPointerCapture(e.pointerId); cv.onpointermove = seek; });
    cv.addEventListener('pointerup', () => { cv.onpointermove = null; });
    cv.addEventListener('keydown', (e) => { if (e.key === 'ArrowRight') a.currentTime += 5; else if (e.key === 'ArrowLeft') a.currentTime -= 5; else return; e.preventDefault(); });
    const sp = el('div', { class: 'sp' });
    [1, 1.5, 2].forEach((v) => {
      const b = el('button', { class: 'tb', 'aria-pressed': v === 1 ? 'true' : 'false' }, v + '×');
      b.addEventListener('click', () => { a.playbackRate = v; sp.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', 'false')); b.setAttribute('aria-pressed', 'true'); });
      sp.appendChild(b);
    });
    const box = el('div', { class: 'au' },
      el('div', { class: 'meta' }, p.etiqueta || 'Nota de voz'),
      el('div', { class: 'row' }, bt, cv, tt), sp);
    new ResizeObserver(draw).observe(cv);
    box._stop = () => a.pause();
    return box;
  }

  /* ------------------------------------------------------------ Página */
  const piezas = E.piezas || [];
  const comparables = [...piezas.filter((p) => p.tipo === 'imagen'), ...(E.comparar || [])];
  let actual = 0, modo = 'uno', vA = null, vB = null, audioBox = null;

  const head = el('header', { class: 'ev-head' },
    el('div', { class: 'ev-kicker' }, el('span', { class: 'ev-id' }, E.id), el('span', null, E.caso || 'La carta 35'), E.etapa ? el('span', null, '· ' + E.etapa) : null),
    el('h1', { class: 'ev-title' }, E.titulo),
    E.encargo ? el('div', { class: 'ev-encargo', html: E.encargo }) : null,
    el('p', { class: 'ev-src' }, E.fuente || ''),
    E.nota ? el('p', { class: 'ev-nota', html: `<b>${E.nota.de}:</b> ${E.nota.texto}` }) : null);
  doc.body.appendChild(head);

  const tabs = el('div', { class: 'ev-tabs', role: 'tablist', 'aria-label': 'Piezas de esta evidencia' });
  if (piezas.length > 1) doc.body.appendChild(tabs);
  piezas.forEach((p, i) => {
    const t = el('button', { class: 'ev-tab', role: 'tab', 'aria-selected': i === 0 ? 'true' : 'false', title: p.etiqueta },
      p.tipo === 'audio' ? el('span', { class: 'aud', html: ICON.play }) : p.tipo === 'ordenar' ? el('span', { class: 'aud', html: '<svg viewBox="0 0 24 24" width="30" height="30"><path d="M4 6h16M4 12h16M4 18h16" stroke="#e3b04b" stroke-width="2"/></svg>' }) : el('img', { src: p.mini || p.src, alt: '', loading: 'lazy' }),
      el('span', null, p.etiqueta));
    t.addEventListener('click', () => mostrar(i));
    tabs.appendChild(t);
  });

  const main = el('main', { class: 'ev-main' });
  const stage = el('div', { class: 'ev-stage' });
  main.appendChild(stage);
  doc.body.appendChild(main);

  const tools = el('div', { class: 'ev-tools', role: 'toolbar', 'aria-label': 'Herramientas' });
  const B = {};
  function tb(key, label, icon, fn, toggle) {
    const b = el('button', { class: 'tb', type: 'button', title: label, html: (icon ? ICON[icon] : '') + `<span>${label}</span>` });
    if (toggle) b.setAttribute('aria-pressed', 'false');
    b.addEventListener('click', fn);
    B[key] = b; tools.appendChild(b); return b;
  }
  const act = () => vA;
  tb('fit', 'Ajustar', 'fit', () => { act() && act().fit(); vB && vB.fit(); });
  tb('zin', 'Acercar', 'zin', () => act() && act().zoom(1.3));
  tb('zout', 'Alejar', 'zout', () => act() && act().zoom(1 / 1.3));
  tb('rot', 'Girar', 'rot', () => act() && act().rotate());
  tb('mir', 'Espejo', 'mir', () => { if (act()) B.mir.setAttribute('aria-pressed', String(act().mirror())); }, true);
  tb('fx', 'Realce', 'fx', () => { if (act()) { const v = act().realce(); B.fx.setAttribute('aria-pressed', String(v > 0)); B.fx.querySelector('span').textContent = v ? 'Realce ' + v : 'Realce'; } }, true);
  if (comparables.length > 1) tb('cmp', 'Comparar', 'cmp', () => setModo(modo === 'cmp' ? 'uno' : 'cmp'), true);
  if (E.superponer) tb('ov', 'Superponer', 'ov', () => setModo(modo === 'ov' ? 'uno' : 'ov'), true);
  doc.body.appendChild(tools);
  // El visor y la barra llenan la pantalla cuando la cabecera sale de vista.
  let compacto = false;
  function alto() { main.style.height = compacto ? '340px' : Math.max(380, window.innerHeight - (tools.hidden ? 0 : tools.offsetHeight) - 6) + 'px'; }
  window.addEventListener('resize', alto);
  new ResizeObserver(alto).observe(tools);
  alto();

  const panels = el('section', { class: 'ev-panels' });
  const pTrans = el('details', { class: 'pn' }, el('summary', null, 'Transcripción y descripción'), el('div', { class: 'pn-body' }));
  panels.appendChild(pTrans);
  if (E.ayudas && E.ayudas.length) {
    const body = el('div', { class: 'pn-body' }, el('p', { class: 'trans-note' }, 'Solo si te atoras. Cada pista se abre por separado, de menos a más.'));
    E.ayudas.forEach((a) => {
      const box = el('div', { class: 'hint' }, el('h4', null, a.tema));
      let n = 0;
      const lvs = a.niveles.map((t, i) => { const d = el('div', { class: 'lv', html: `<b>Pista ${i + 1}</b>${t}` }); box.appendChild(d); return d; });
      const btn = el('button', { class: 'tb', type: 'button' }, 'Ver pista 1');
      btn.addEventListener('click', () => { lvs[n].classList.add('on'); n++; if (n >= lvs.length) btn.remove(); else btn.textContent = 'Ver pista ' + (n + 1); });
      box.appendChild(btn); body.appendChild(box);
    });
    panels.appendChild(el('details', { class: 'pn' }, el('summary', null, 'Ayuda opcional'), body));
  }
  doc.body.appendChild(panels);

  function transcripcion(p) {
    const b = pTrans.querySelector('.pn-body');
    b.innerHTML = '';
    if (p.descripcion) b.appendChild(el('p', { class: 'trans-note' }, p.descripcion));
    if (p.transcripcion) b.appendChild(el('div', { class: 'trans' }, p.transcripcion));
    if (p.accesible) {
      const d = el('details', { style: 'margin-top:10px' }, el('summary', { style: 'cursor:pointer;color:var(--acc)' }, 'Descripción accesible de detalles visuales (revela lo que se ve con las herramientas)'),
        el('div', { class: 'trans', style: 'margin-top:8px' }, p.accesible));
      b.appendChild(d);
    }
    if (!p.descripcion && !p.transcripcion) b.appendChild(el('p', { class: 'trans-note' }, 'Sin texto.'));
  }

  function limpiar() {
    if (audioBox && audioBox._stop) audioBox._stop();
    stage.innerHTML = ''; stage.className = 'ev-stage'; vA = vB = null; audioBox = null;
    const oc = doc.querySelector('.ov-ctrl'); if (oc) oc.remove();
  }
  function herramientas(on) {
    ['fit', 'zin', 'zout', 'rot', 'mir', 'fx', 'cmp', 'ov'].forEach((k) => { if (B[k]) B[k].hidden = !on; });
    tools.hidden = !on;
    if (B.mir) B.mir.setAttribute('aria-pressed', 'false');
    if (B.fx) { B.fx.setAttribute('aria-pressed', 'false'); B.fx.querySelector('span').textContent = 'Realce'; }
  }
  function mostrar(i) {
    actual = i;
    tabs.querySelectorAll('.ev-tab').forEach((t, k) => t.setAttribute('aria-selected', String(k === i)));
    if (modo !== 'uno') { modo = 'uno'; if (B.cmp) B.cmp.setAttribute('aria-pressed', 'false'); if (B.ov) B.ov.setAttribute('aria-pressed', 'false'); }
    limpiar();
    const p = piezas[i];
    transcripcion(p);
    compacto = p.tipo === 'audio';
    if (p.tipo === 'audio') {
      audioBox = reproductor(p); stage.appendChild(audioBox); herramientas(false);
    } else if (p.tipo === 'ordenar') {
      stage.appendChild(ordenar(p)); herramientas(false);
    } else {
      const h = el('div'); stage.appendChild(h);
      vA = new Visor(h); vA.load(p.src, p.alt); herramientas(true);
    }
    alto();
  }

  function selector(v, idx) {
    const s = el('select', { 'aria-label': 'Elegir imagen' });
    comparables.forEach((c, k) => s.appendChild(el('option', { value: k }, c.etiqueta)));
    s.value = idx;
    s.addEventListener('change', () => v.load(comparables[+s.value].src, comparables[+s.value].alt));
    s.addEventListener('pointerdown', (e) => e.stopPropagation());
    return s;
  }
  function setModo(m) {
    const p = piezas[actual];
    if (p.tipo !== 'imagen') return;
    modo = m;
    if (B.cmp) B.cmp.setAttribute('aria-pressed', String(m === 'cmp'));
    if (B.ov) B.ov.setAttribute('aria-pressed', String(m === 'ov'));
    limpiar(); herramientas(true);
    if (m === 'uno') { mostrar(actual); return; }
    if (m === 'cmp') {
      stage.classList.add('split');
      const h1 = el('div'), h2 = el('div'); stage.append(h1, h2);
      vA = new Visor(h1); vB = new Visor(h2);
      const i1 = comparables.indexOf(p) >= 0 ? comparables.indexOf(p) : 0;
      const i2 = (i1 + 1) % comparables.length;
      h1.appendChild(selector(vA, i1)); h2.appendChild(selector(vB, i2));
      vA.load(comparables[i1].src, comparables[i1].alt); vB.load(comparables[i2].src, comparables[i2].alt);
      [h1, h2].forEach((h, k) => h.addEventListener('pointerdown', () => { vA = k ? vB : vA; }));
      // la herramienta activa es la del último visor tocado
      let activo = vA; const oA = vA, oB = vB;
      h1.addEventListener('pointerdown', () => { activo = oA; }); h2.addEventListener('pointerdown', () => { activo = oB; });
      vA = new Proxy({}, { get: (_, k) => (typeof activo[k] === 'function' ? activo[k].bind(activo) : activo[k]) });
      vB = oB;
    }
    if (m === 'ov') superponer();
  }

  /* ------------------------------------------------------------ Superposición (calca) */
  function superponer() {
    const S = E.superponer;
    const h = el('div'); stage.appendChild(h);
    const v = new Visor(h); vA = v;
    let base = 0;
    const top = el('img', { class: 'ov-top', alt: S.capa.alt || '', draggable: 'false' });
    v.wrap.appendChild(top);
    const st = { ox: S.capa.x0 || 0, oy: S.capa.y0 || 0, mir: false, op: 0.6, sc: S.capa.escala || 1 };
    v.overlay = {
      apply() {
        top.style.transform = `translate(${st.ox}px,${st.oy}px) scale(${st.sc}) ${st.mir ? `translateX(${top.naturalWidth}px) scaleX(-1)` : ''}`;
        top.style.opacity = st.op;
      },
      nudgeScreen(dx, dy) { st.ox += dx / v.s; st.oy += dy / v.s; this.apply(); },
    };
    top.onload = () => v.overlay.apply();
    top.src = S.capa.src;
    v.load(S.bases[0].src, S.bases[0].alt);
    const sel = el('select', { 'aria-label': 'Carta de abajo' });
    S.bases.forEach((b, k) => sel.appendChild(el('option', { value: k }, b.etiqueta)));
    sel.addEventListener('change', () => { base = +sel.value; v.load(S.bases[base].src, S.bases[base].alt).then(() => v.overlay.apply()); });
    const op = el('input', { type: 'range', min: '0', max: '100', value: '60', 'aria-label': 'Opacidad de la calca' });
    op.addEventListener('input', () => { st.op = op.value / 100; v.overlay.apply(); });
    const mir = el('button', { class: 'tb', type: 'button', 'aria-pressed': 'false' }, 'Calca en espejo');
    mir.addEventListener('click', () => { st.mir = !st.mir; mir.setAttribute('aria-pressed', String(st.mir)); v.overlay.apply(); });
    const mov = el('button', { class: 'tb', type: 'button', 'aria-pressed': 'false' }, 'Mover calca');
    mov.addEventListener('click', () => { v.moveOverlay = !v.moveOverlay; mov.setAttribute('aria-pressed', String(v.moveOverlay)); h.classList.toggle('ovl', v.moveOverlay); });
    const ctrl = el('div', { class: 'ov-ctrl' },
      el('label', null, 'Abajo: ', sel),
      el('label', null, 'Arriba: ' + S.capa.etiqueta),
      el('label', null, 'Opacidad ', op), mir, mov,
      el('span', { class: 'trans-note', style: 'margin:0' }, S.nota || 'Con «Mover calca» activo, arrastra la hoja de arriba (o usa las flechas del teclado).'));
    tools.after(ctrl);
  }

  /* ------------------------------------------------------------ Ordenar (mesa de piezas) */
  function ordenar(p) {
    const wrap = el('div', { class: 'ord' });
    const ol = el('ol');
    let items = p.items.slice();
    let sel = null;
    const res = el('p', { class: 'res', role: 'status' });
    function lightbox(it) {
      const ov = el('div', { style: 'position:fixed;inset:0;z-index:50;background:rgba(0,0,0,.92);display:flex;flex-direction:column' });
      const hv = el('div', { style: 'flex:1;position:relative' });
      const close = el('button', { class: 'tb', type: 'button', style: 'margin:10px auto' }, 'Cerrar');
      ov.append(hv, close); doc.body.appendChild(ov);
      const v = new Visor(hv); v.load(it.src, it.alt); hv.focus();
      const bar = el('div', { class: 'ev-tools', style: 'background:transparent;border:0' });
      [['Acercar', () => v.zoom(1.3)], ['Alejar', () => v.zoom(1 / 1.3)], ['Girar', () => v.rotate()], ['Realce', () => v.realce()]].forEach(([t, f]) => { const b = el('button', { class: 'tb', type: 'button' }, t); b.onclick = f; bar.appendChild(b); });
      ov.insertBefore(bar, close);
      const cerrar = () => ov.remove();
      close.onclick = cerrar; ov.addEventListener('keydown', (e) => { if (e.key === 'Escape') cerrar(); });
    }
    function pintar() {
      ol.innerHTML = '';
      items.forEach((it, i) => {
        const up = el('button', { class: 'tb', type: 'button', 'aria-label': `Subir ${it.etiqueta}` }, '↑');
        const dn = el('button', { class: 'tb', type: 'button', 'aria-label': `Bajar ${it.etiqueta}` }, '↓');
        up.disabled = i === 0; dn.disabled = i === items.length - 1;
        up.onclick = () => { [items[i - 1], items[i]] = [items[i], items[i - 1]]; pintar(); ol.children[i - 1].querySelector('button').focus(); };
        dn.onclick = () => { [items[i + 1], items[i]] = [items[i], items[i + 1]]; pintar(); ol.children[i + 1].querySelectorAll('button')[1].focus(); };
        const im = el('img', { src: it.mini || it.src, alt: it.alt || it.etiqueta });
        im.onclick = () => lightbox(it);
        const li = el('li', { class: sel === i ? 'sel' : '' }, el('span', { class: 'n' }, String(i + 1)), im,
          el('span', { class: 'tx' }, el('b', null, it.etiqueta), el('br'), it.resumen || 'Toca la imagen para ampliarla.'),
          el('span', { class: 'mv' }, up, dn));
        ol.appendChild(li);
      });
    }
    pintar();
    const chk = el('button', { class: 'btn sec', type: 'button', style: 'display:block;margin:14px auto 0' }, 'Revisar el orden');
    chk.onclick = async () => {
      let bien = 0;
      for (let i = 0; i < items.length; i++) if (p.h.includes(await sha256(`lc35|ord|${items[i].id}|${i}`))) bien++;
      res.textContent = bien === items.length ? p.exito : (p.parcial || '{n} de {t} en su lugar.').replace('{n}', bien).replace('{t}', items.length);
    };
    wrap.append(el('p', { class: 'res', style: 'margin-top:0' }, p.instruccion || ''), ol, chk, res);
    return wrap;
  }

  /* ------------------------------------------------------------ SHA-256 (solo para no dejar respuestas en texto plano) */
  async function sha256(s) {
    if (window.crypto && crypto.subtle) {
      const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
      return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
    }
    return window.sha256js(s);
  }
  window.lc35sha = sha256;

  mostrar(0);
})();
