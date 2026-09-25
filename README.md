# La carta 35

Caso digital de investigación **no criminal** para adultos de México, en español mexicano. Duración estimada: 60-75 min, con una muestra gratuita de 9-12 min. Son estimaciones de diseño y **no se han medido con jugadores**.

> Junio de 2025, Aguascalientes. Los exalumnos del 6° B de una primaria pública abren la cápsula del tiempo que enterraron en el año 2000. Eran 34 alumnos y hay 34 sobres. Pero al fondo de la caja aparece una hoja más, sin sobre, firmada por «Itzel». Nadie se llama así. Nadie la recuerda.
> **¿Quién es Itzel?**

## Abrir la vista local
Abre **`VISTA_LOCAL/index.html`** en el navegador (funciona con doble clic, desde `file://`). También se puede servir:
```bash
python3 -m http.server 8000     # desde esta carpeta
# y visitar http://localhost:8000/VISTA_LOCAL/
```
- Al inicio solo está abierta la **muestra gratuita** (E01-E04 + D1).
- Marca «Simular compra del caso completo» para probar el resto. Cada etapa se desbloquea al resolver la deducción anterior.
- `VISTA_LOCAL/pruebas.html` es un **modo privado de pruebas**: desbloquea todo y muestra las respuestas. Está separado del juego y no se entrega.

## Estructura
| Carpeta | Contenido | ¿Pública? |
|---|---|---|
| `JUGADOR_GRATIS/` | Muestra: E01-E04 y D1, con todos sus recursos | Sí |
| `JUGADOR_COMPLETO/` | Resto del caso: E05-E14, D2 y D3 (usa imágenes de la muestra para comparar) | Solo para compradores |
| `COMUN/` | Visor, deducciones y SHA-256 (sin contenido del caso) | Sí |
| `INTEGRACION/` | `manifest.json` e `instrucciones.md` | Equipo técnico |
| `VISTA_LOCAL/` | Recorrido de prueba sin plataforma comercial | Equipo |
| `SOLUCION_PRIVADA/` | `solucion.md`, `respuestas.md`, `justificacion_por_evidencias.md` y `respuestas.js` (modo pruebas) | **No** |
| `MAESTRO_PRIVADO/` | Premisas, verdad, canon, matriz de pistas, ritmo y fichas de fuente; `produccion/` con las fuentes HTML, los scripts de render y postproceso, las tipografías OFL y las pruebas | **No** |
| `ASSETS_PENDIENTES/` | `prompts_imagenes.md` y `sustituciones.md` | **No** |
| `QA/` | Pruebas funcionales, auditorías lógica y visual, incidencias y capturas | **No** |

## Las piezas
| Etapa | ID | Evidencia | Interacción principal |
|---|---|---|---|
| Muestra | E01 | Carta sin sobre (anverso y reverso) | Zoom, espejo y realce sobre una calca de tinta |
| | E02 | El grupo de exalumnos (6 capturas + 5 fotos) | Leer el chat y comparar cartas |
| | E03 | Nota de voz de la maestra Chayo | Audio con velocidad y transcripción |
| | E04 | Respuesta de la directora + croquis de Protección Civil | Zoom y comparar |
| | D1 | Primera deducción | Opción única y selección de pruebas |
| Etapa 1 | E05 | El cuaderno de la maestra Chayo (5 fotos) | Croquis de lugares y diario |
| | E06 | Las cartas del fondo de la caja (libreta + 5 escaneos) | **Superponer la calca en espejo** sobre cada carta |
| | E07 | Óscar contesta (4 capturas) | Leer y contrastar |
| | E08 | Los recaditos (8 fotos) | **Ordenar** por fecha romana y marcador del gato |
| | D2 | Segunda deducción | Opciones y texto libre |
| Etapa 2 | E09 | La bitácora de la conserjería (4 fotos) | Comparar letras entre evidencias |
| | E10 | La publicación (2 capturas) | Leer comentarios |
| | E11 | La maestra Chayo se acuerda | Audio |
| | E12 | Lo que guardaba el profe Salvador (3 capturas + 3 fotos) | Libreta de asistencia e invitación de graduación |
| | E13 | Lista de asistencia de la apertura | Zoom y comparar |
| | D3 | Reconstrucción final | Opciones, pruebas y nombre en texto libre |
| Epílogo | E14 | La canastilla | — |

**Total:** 14 evidencias (13 de investigación + epílogo), 3 deducciones y 54 archivos de evidencia (imágenes y audio), más 12 miniaturas y capas auxiliares. **Interacciones funcionales:** zoom y arrastre (ratón, rueda, pellizco, teclado), giro, espejo, realce en 3 niveles, comparación en pantalla dividida, superposición con opacidad y arrastre, ordenación con verificación, reproductor de audio con velocidad, transcripciones, descripciones accesibles, ayuda opcional en 3 niveles y 3 deducciones con validación tolerante.

## Cómo se hizo
- Todo el **texto que es pista** (cartas, recaditos, bitácora, listas, pintarrón) se compone con código en HTML, con 13 manos manuscritas distintas y variación por letra. Después se «fotografía» o «escanea» con Python: papel, dobleces, agua, luz, perspectiva, ruido y compresión de WhatsApp.
- Las capturas imitan un Android real, sin logotipos.
- Las voces son **TTS neuronal local** (piper `es_MX`) con tratamiento de nota de voz: son **provisionales**.
- Tipografías libres (SIL OFL) incluidas con sus licencias en `MAESTRO_PRIVADO/produccion/fuentes/`.
- Regenerar: ver `INTEGRACION/instrucciones.md` («Regenerar el contenido»). Orden: `render.js` con los `jobs_*.json` → `build_e01.py` … `build_e13_e14.py` → `build_audio.py` → `paginas.py`.

## Estado
- **Terminado:** las 14 evidencias, las 3 deducciones, el visor, la vista local, el manifest, la solución y la documentación.
- **Provisional funcional (se juega bien, conviene sustituir):** las 2 notas de voz (TTS → locución humana) y la foto del pintarrón (fondo sintético → foto real con el texto compuesto por código). Los fondos procedurales (mesabanco, hule, cartón) se pueden mejorar con fotos reales. Detalle en `ASSETS_PENDIENTES/`.

## Decisiones importantes
- **Premisa:** de tres evaluadas (`MAESTRO_PRIVADO/premisas.md`) se eligió la cápsula del tiempo. La pregunta se entiende de inmediato y la solución se apoya en algo cotidiano de la escuela pública mexicana: dos turnos, dos escuelas y una sola aula.
- **Sin culpables:** cada persona calla o se equivoca por razones comprensibles (vergüenza, reglamento, protección de una compañera, entusiasmo).
- **La respuesta está sembrada desde la muestra** (pintarrón, croquis, correo) sin que se pueda deducir ahí.
- **Ciudad real y todo lo demás ficticio:** escuelas, colonia, Normal y personas. Sin CCT, sin logotipos oficiales y sin números de teléfono visibles.

## Limitaciones honestas
- La duración no se ha validado con personas (hay un protocolo en `QA/pruebas_funcionales.md`).
- Probado solo en Chromium (móvil emulado y escritorio). Falta Safari iOS, Firefox y lectores de pantalla reales.
- Validar las respuestas con huellas en el navegador **no protege nada**: la plataforma debe validar y servir el contenido de pago desde su servidor.
- Las voces sintéticas, aun corregidas, no igualan a una actriz.
