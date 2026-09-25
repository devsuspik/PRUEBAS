/* Controles de deducción de «La carta 35». Lee window.DEDUCCION.
   Las respuestas se guardan como huellas SHA-256 para no dejarlas en texto plano.
   Esto NO protege el contenido: quien lea el código puede probar opciones. La validación real
   debe hacerla la plataforma (ver INTEGRACION/instrucciones.md).
   Al acertar, avisa a la ventana contenedora: postMessage({tipo:'lc35:deduccion', id, ok:true}). */
(function () {
  'use strict';
  const D = window.DEDUCCION;
  if (!D) return;
  const doc = document;
  const el = (tag, attrs, ...kids) => {
    const n = doc.createElement(tag);
    if (attrs) for (const k in attrs) { if (k === 'class') n.className = attrs[k]; else if (k === 'html') n.innerHTML = attrs[k]; else n.setAttribute(k, attrs[k]); }
    kids.flat().forEach((c) => c != null && n.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c));
    return n;
  };
  async function sha(s) {
    if (window.crypto && crypto.subtle && window.isSecureContext !== false) {
      try {
        const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
        return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
      } catch (e) { /* respaldo */ }
    }
    return window.sha256js(s);
  }
  const norm = (t) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9ñ ]+/g, ' ').split(/\s+/).filter(Boolean);

  const wrap = el('main', { class: 'dd' });
  wrap.appendChild(el('div', { class: 'ev-kicker', style: 'margin-bottom:6px' }, el('span', { class: 'ev-id' }, D.id), el('span', null, D.caso || 'La carta 35')));
  wrap.appendChild(el('h1', null, D.titulo));
  if (D.intro) wrap.appendChild(el('p', { class: 'intro', html: D.intro }));
  const form = el('form', { novalidate: 'true' });
  const cajas = [];
  D.preguntas.forEach((q, qi) => {
    const box = el('div', { class: 'q', id: 'q-' + q.id });
    const fs = el('fieldset');
    fs.appendChild(el('legend', null, `${qi + 1}. ${q.texto}`));
    if (q.nota) fs.appendChild(el('p', { class: 'trans-note', style: 'margin:0 0 6px' }, q.nota));
    if (q.tipo === 'texto') {
      fs.appendChild(el('input', { type: 'text', name: q.id, autocomplete: 'off', placeholder: q.placeholder || 'Escribe tu respuesta', 'aria-label': q.texto }));
    } else {
      q.opciones.forEach((o) => {
        const inp = el('input', { type: q.tipo === 'multiple' ? 'checkbox' : 'radio', name: q.id, value: o.id });
        fs.appendChild(el('label', { class: 'op' }, inp, el('span', null, o.t)));
      });
    }
    box.appendChild(fs);
    box.appendChild(el('div', { class: 'st', role: 'status' }));
    form.appendChild(box); cajas.push([q, box]);
  });
  const btn = el('button', { class: 'btn', type: 'submit' }, D.boton || 'Comprobar');
  form.appendChild(btn);
  wrap.appendChild(form);
  const out = el('div', { 'aria-live': 'polite' });
  wrap.appendChild(out);
  if (D.ayudas && D.ayudas.length) {
    const body = el('div', { class: 'pn-body' }, el('p', { class: 'trans-note' }, 'Cada pista se abre por separado: primero dónde mirar, luego qué comparar y, al final, qué concluir.'));
    D.ayudas.forEach((a) => {
      const box = el('div', { class: 'hint' }, el('h4', null, a.tema));
      let n = 0;
      const lvs = a.niveles.map((t, i) => { const d = el('div', { class: 'lv', html: `<b>Pista ${i + 1}</b>${t}` }); box.appendChild(d); return d; });
      const b = el('button', { class: 'tb', type: 'button' }, 'Ver pista 1');
      b.addEventListener('click', () => { lvs[n].classList.add('on'); n++; if (n >= lvs.length) b.remove(); else b.textContent = 'Ver pista ' + (n + 1); });
      box.appendChild(b); body.appendChild(box);
    });
    wrap.appendChild(el('details', { class: 'pn', style: 'margin-top:22px;border:1px solid var(--line);border-radius:10px;background:var(--panel)' }, el('summary', null, 'Ayuda opcional'), body));
  }
  doc.body.appendChild(wrap);

  async function evaluar(q) {
    const S = D.sal || 'lc35';
    if (q.tipo === 'unica') {
      const v = form.querySelector(`input[name="${q.id}"]:checked`);
      if (!v) return null;
      return q.h.includes(await sha(`${S}|${D.id}|${q.id}|${v.value}`));
    }
    if (q.tipo === 'multiple') {
      const vs = [...form.querySelectorAll(`input[name="${q.id}"]:checked`)].map((x) => x.value);
      if (!vs.length) return null;
      let ok = 0;
      for (const v of vs) if (q.h.includes(await sha(`${S}|${D.id}|${q.id}|${v}`))) ok++;
      return ok === vs.length && ok >= (q.min || 1);
    }
    if (q.tipo === 'texto') {
      const t = form.querySelector(`input[name="${q.id}"]`).value;
      const toks = norm(t);
      if (!toks.length) return null;
      const hs = await Promise.all(toks.map((k) => sha(`${S}|tok|${k}`)));
      return q.grupos.every((g) => hs.some((x) => g.includes(x)));
    }
    return false;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    let bien = 0, vacias = 0;
    for (const [q, box] of cajas) {
      const r = await evaluar(q);
      box.classList.remove('ok', 'no');
      const st = box.querySelector('.st');
      if (r === null) { vacias++; st.textContent = 'Falta responder.'; continue; }
      if (r) { bien++; box.classList.add('ok'); st.textContent = q.ok || 'Cuadra con las pruebas.'; }
      else { box.classList.add('no'); st.textContent = q.no || 'Esto todavía no cuadra con lo que muestran las pruebas.'; }
    }
    out.innerHTML = '';
    if (bien === cajas.length) {
      const box = el('div', { class: 'res-box ok' });
      if (D.exito.titulo) box.appendChild(el('h2', { style: 'margin:0 0 8px;font-size:19px' }, D.exito.titulo));
      (D.exito.mensajes || []).forEach((m) => box.appendChild(el('div', { class: 'msg-cli' }, el('div', { class: 'de' }, m.de), el('div', { html: m.texto }))));
      if (D.exito.cierre) box.appendChild(el('p', { html: D.exito.cierre }));
      out.appendChild(box);
      box.scrollIntoView({ behavior: 'smooth', block: 'start' });
      try { localStorage.setItem('lc35:' + D.id, 'ok'); } catch (err) { /* sin almacenamiento */ }
      try { window.parent && window.parent.postMessage({ tipo: 'lc35:deduccion', id: D.id, ok: true }, '*'); } catch (err) { /* sin ventana contenedora */ }
    } else {
      out.appendChild(el('div', { class: 'res-box' }, vacias ? `Te faltan ${vacias} respuesta(s).` : `${bien} de ${cajas.length} respuestas cuadran. Vuelve a las evidencias; la ayuda opcional está abajo.`));
    }
  });
})();
