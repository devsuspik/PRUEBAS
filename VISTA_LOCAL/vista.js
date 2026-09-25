/* Vista local: lista de piezas desde manifest_local.js, simulación de compra y desbloqueo por deducciones.
   El progreso se guarda en localStorage (comodidad local; la plataforma real guardará el suyo). */
(function () {
  'use strict';
  const M = window.MANIFEST;
  const $ = (s) => document.querySelector(s);
  const K = 'lc35:vl:';
  const get = (k) => { try { return localStorage.getItem(K + k); } catch (e) { return null; } };
  const set = (k, v) => { try { localStorage.setItem(K + k, v); } catch (e) { /* sin almacenamiento */ } };
  const del = (k) => { try { localStorage.removeItem(K + k); } catch (e) { /* nada */ } };
  const piezas = M.piezas.slice().sort((a, b) => a.orden - b.orden);
  let abiertas = [];

  function resuelta(id) { return get(id) === 'ok'; }
  function etapaAbierta(et) {
    if (et.acceso === 'gratis') return true;
    if (!$('#compra').checked) return false;
    return et.requiere.filter((r) => r !== 'compra').every(resuelta);
  }
  function mini(p) {
    const r = p.miniatura || p.recursos.find((x) => /\.(jpg|png)$/i.test(x) && !/mini_|capa_/.test(x));
    return r ? '../' + r : '';
  }
  function pintar() {
    const box = $('#etapas');
    box.innerHTML = '';
    abiertas = [];
    M.etapas.forEach((et) => {
      const abierta = etapaAbierta(et);
      const sec = document.createElement('section');
      sec.className = 'et';
      const min = et.piezas.reduce((s, id) => s + piezas.find((p) => p.id === id).duracion_estimada_min[0], 0);
      const max = et.piezas.reduce((s, id) => s + piezas.find((p) => p.id === id).duracion_estimada_min[1], 0);
      const nombre = abierta ? et.titulo : (et.titulo_bloqueado || 'Etapa');
      sec.innerHTML = `<h2>${nombre} <small>${et.acceso === 'gratis' ? 'gratis' : 'caso completo'} · ${min}–${max} min estimados</small></h2>`;
      const req = document.createElement('p');
      req.className = 'req';
      if (!abierta) {
        const falta = et.requiere.map((r) => (r === 'compra' ? 'la compra del caso completo' : 'resolver ' + r)).join(' y ');
        req.textContent = 'Bloqueada: requiere ' + falta + '.';
      }
      sec.appendChild(req);
      const grid = document.createElement('div');
      grid.className = 'grid';
      et.piezas.forEach((id) => {
        const p = piezas.find((x) => x.id === id);
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'card' + (p.tipo === 'deduccion' ? ' ded' : '') + (resuelta(p.id) ? ' ok' : get('v:' + p.id) ? ' visto' : '');
        const esAudio = p.interaccion.includes('audio');
        const th = p.tipo === 'deduccion' ? '<div class="th">?</div>' : `<div class="th" style="background-image:url('${abierta ? mini(p) : ''}')">${esAudio ? '<span class="aud">▶</span>' : ''}</div>`;
        // En etapas bloqueadas no se muestran títulos (evita adelantar contenido)
        const titulo = abierta ? p.titulo : (p.titulo_bloqueado || (p.tipo === 'deduccion' ? 'Deducción' : 'Evidencia'));
        b.innerHTML = `${th}<div class="bd"><span class="id">${p.id}</span><span class="ti">${titulo}</span><span class="du">${p.duracion_estimada_min[0]}–${p.duracion_estimada_min[1]} min</span></div>`;
        if (!abierta) b.disabled = true;
        else { abiertas.push(p); b.addEventListener('click', () => abrir(p)); }
        grid.appendChild(b);
      });
      sec.appendChild(grid);
      box.appendChild(sec);
    });
  }
  let actual = null;
  function abrir(p) {
    actual = p;
    set('v:' + p.id, '1');
    $('#mtit').textContent = `${p.id} · ${p.titulo}`;
    $('#ifr').src = '../' + p.ruta;
    $('#marco').hidden = false;
    document.body.style.overflow = 'hidden';
    const i = abiertas.indexOf(p);
    $('#ant').disabled = i <= 0;
    $('#sig').disabled = i < 0 || i >= abiertas.length - 1;
  }
  function cerrar() { $('#marco').hidden = true; $('#ifr').src = 'about:blank'; document.body.style.overflow = ''; pintar(); }
  $('#cerrar').addEventListener('click', cerrar);
  $('#ant').addEventListener('click', () => { const i = abiertas.indexOf(actual); if (i > 0) abrir(abiertas[i - 1]); });
  $('#sig').addEventListener('click', () => { const i = abiertas.indexOf(actual); if (i < abiertas.length - 1) abrir(abiertas[i + 1]); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#marco').hidden) cerrar(); });
  window.addEventListener('message', (e) => {
    const d = e.data || {};
    if (d.tipo === 'lc35:deduccion' && d.ok) {
      set(d.id, 'ok');
      // recalcula qué hay abierto sin cerrar el marco (el jugador lee el mensaje de éxito)
      const cur = actual; pintar(); actual = cur;
      const i = abiertas.indexOf(cur);
      $('#sig').disabled = i < 0 || i >= abiertas.length - 1;
    }
  });
  $('#compra').checked = get('compra') === '1';
  $('#compra').addEventListener('change', () => { set('compra', $('#compra').checked ? '1' : '0'); pintar(); });
  $('#reiniciar').addEventListener('click', () => {
    if (!confirm('¿Borrar el progreso local (deducciones y evidencias vistas)?')) return;
    piezas.forEach((p) => { del(p.id); del('v:' + p.id); });
    del('compra'); $('#compra').checked = false; pintar();
  });
  pintar();
})();
