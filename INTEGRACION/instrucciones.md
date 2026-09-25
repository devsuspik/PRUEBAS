# Integración en la plataforma

## Qué se integra
- **`JUGADOR_GRATIS/`** · muestra pública: E01-E04 y D1. Se puede servir sin compra.
- **`JUGADOR_COMPLETO/`** · contenido de pago: E05-E14, D2 y D3. Solo debe servirse a compradores. **Depende** de `JUGADOR_GRATIS` (compara con imágenes de E01, E02 y E04).
- **`COMUN/`** · código del visor y de las deducciones (`visor.css`, `visor.js`, `deduccion.js`, `sha256.js`). No contiene nada del caso; es público.
- **`INTEGRACION/manifest.json`** · catálogo de piezas.
- **Nunca se publican:** `MAESTRO_PRIVADO/`, `SOLUCION_PRIVADA/`, `QA/`, `ASSETS_PENDIENTES/` ni `VISTA_LOCAL/pruebas.html`.

Estructura de rutas: cada pieza es `PAQUETE/ID/index.html` más sus recursos en `img/` o `audio/`. Las referencias son relativas (`../../COMUN/…`, `../../JUGADOR_GRATIS/E01/img/…`), así que conviene conservar este árbol en el servidor. Si la plataforma reorganiza rutas, basta con reescribir `recursos_de_otras_piezas` y las rutas `../../COMUN/` en los `index.html`.

## El manifest
`caso` (título, pregunta, duración, sinopsis), `runtime` (qué CSS y JS usan las piezas, evento de deducción), `etapas` (acceso y requisitos) y `piezas`. Cada pieza incluye:

| Campo | Significado |
|---|---|
| `id` | Identificador estable (E01…E14, D1…D3). No cambiar. |
| `tipo` | `evidencia` o `deduccion` |
| `titulo` / `titulo_bloqueado` | Título real y rótulo neutro («Evidencia 7», «Deducción 2») para mostrar mientras la pieza esté bloqueada |
| `etapa` / `orden` | `muestra`, `etapa1`, `etapa2` o `epilogo`; el orden recomendado es 1-17 |
| `paquete` | `gratis` o `completo` |
| `ruta` | Página de la pieza |
| `miniatura` | Imagen para la tarjeta de la pieza |
| `recursos` | Archivos propios |
| `recursos_de_otras_piezas` / `dependencias` | Imágenes de otras piezas que usa la herramienta «Comparar» (deben estar accesibles) |
| `interaccion` | Tipos de interacción (zoom, espejo, realce, comparar, superponer-calca, ordenar, audio, deducción, texto libre…) |
| `duracion_estimada_min` | Rango en minutos (estimación de diseño; no validada con jugadores) |

## Etapas y desbloqueo sugerido
1. **Muestra** (gratis): E01 → E04 y luego D1.
2. **Etapa 1** (compra + D1 resuelta): E05 → E08 y luego D2.
3. **Etapa 2** (D2 resuelta): E09 → E13 y luego D3.
4. **Epílogo** (D3 resuelta): E14.

Mientras una etapa esté bloqueada, **no se deben mostrar sus títulos ni los de sus piezas**: algunos adelantan hallazgos (la etapa 2 se llama «Lupe»; E07 es «Óscar contesta»; E12, «Lo que guardaba el profe Salvador»). Etapas y piezas traen `titulo_bloqueado` con un rótulo neutro para ese caso. Tampoco conviene mostrar miniaturas de piezas bloqueadas.

## Evento de deducción
Al acertar, cada página de deducción ejecuta:
```js
window.parent.postMessage({ tipo: 'lc35:deduccion', id: 'D1' | 'D2' | 'D3', ok: true }, '*')
```
Si la pieza se carga en un `<iframe>`, la plataforma puede escuchar ese mensaje para desbloquear la etapa siguiente. También se guarda `localStorage['lc35:D1'] = 'ok'` (solo como comodidad).

## Seguridad: qué NO hacen estos archivos
- Las respuestas de las deducciones están como **huellas SHA-256** para que no se lean a simple vista. **No es una protección**: hay pocas opciones y se pueden probar por fuerza bruta. Si la plataforma necesita validar de verdad, debe:
  1. Quitar `DEDUCCION.preguntas[*].h` y `grupos` del HTML.
  2. Enviar las respuestas del jugador a su servidor, que valida contra `SOLUCION_PRIVADA/respuestas.md`.
  3. Servir el contenido de pago solo a sesiones autorizadas (control de acceso en el servidor, no en JavaScript).
- Ningún archivo de la muestra hace referencia a `JUGADOR_COMPLETO`, `SOLUCION_PRIVADA` ni `MAESTRO_PRIVADO` (comprobado con grep; ver QA/pruebas_funcionales.md).
- Las imágenes no tienen metadatos EXIF (comprobado).

## Requisitos técnicos
- Sin dependencias externas ni red: fuentes, imágenes y audio son locales. Las evidencias son imágenes, así que no cargan fuentes web.
- Funciona desde `file://` y desde cualquier servidor estático.
- Navegadores: probado en Chromium (Playwright 1.56) con emulación móvil (390×844, táctil) y escritorio (1280×800). **Falta probar en Safari iOS y Firefox** (ver QA).
- Audio: MP3 mono de 64 kbps.
- Pesos: muestra ≈ 5 MB; caso completo ≈ 12 MB adicionales.

## Accesibilidad
- Cada imagen tiene `alt`, descripción y transcripción literal. En E01 y E02, los hallazgos que dependen de herramientas visuales (espejo, realce, detalles del pintarrón) están en un bloque aparte, «Descripción accesible de detalles visuales», que avisa de que revela lo que se ve con las herramientas.
- Audios con transcripción completa y velocidades de 1×, 1,5× y 2×.
- Visor manejable con teclado: + / - / 0, flechas, R (girar), E (espejo), C (realce). La mesa de ordenar tiene botones ↑ ↓.
- Las ayudas son opcionales, por niveles y separadas del material.

## Regenerar el contenido (equipo de producción)
Todo sale de `MAESTRO_PRIVADO/produccion/`:
```bash
cd MAESTRO_PRIVADO/produccion
pip install pillow numpy piper-tts imageio-ffmpeg        # una vez
export NODE_PATH=/ruta/a/node_modules                     # donde esté playwright
node render.js jobs_cartas.json && node render.js jobs_e02.json   # etc. (jobs_*.json)
python3 build_e01.py && python3 build_e02.py && python3 build_e04.py && python3 build_e05.py
python3 build_e06.py && python3 build_e07.py && python3 build_e08.py && python3 build_e09.py && python3 build_e12.py && python3 build_e13_e14.py
python3 build_audio.py chayo1 && python3 build_audio.py chayo2   # requiere voces piper en /tmp/voices
python3 paginas.py      # regenera las páginas, el manifest y VISTA_LOCAL/manifest_local.js
```
El orden de render recomendado está en el README.
