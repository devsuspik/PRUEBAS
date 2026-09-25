# Estado de los recursos y sustituciones

Estados: **Terminado** (listo para jugar, sin sustituto previsto) · **Provisional funcional** (se juega bien, pero conviene sustituirlo) · **Pendiente de sustitución visual** (ninguno bloquea el juego).

| Recurso | Evidencia | Estado | Cómo se hizo | Sustitución recomendada |
|---|---|---|---|---|
| Carta de Itzel, anverso y reverso (fotos) | E01 | Terminado | Texto con HTML y fuente manuscrita con variación por letra; papel, dobleces, agua, calca y cámara simulados en Python | Opcional: fondo de mesabanco real (P2). Ideal: utilería física, es decir, copiar el texto a lápiz en una hoja real, doblarla, mojarla y fotografiarla con la calca impresa en verde tenue. |
| Capturas del grupo de WhatsApp | E02 | Terminado | HTML que imita un cliente de mensajería de Android, sin logotipos | — |
| Foto del pintarrón | E02 | **Provisional funcional** | Escena HTML con fotografía simulada; el muro se ve algo sintético | **P1**: fondo fotográfico real o generado, sin texto, con las capas de texto compuestas por código |
| Cartas de Itzayana, Beto y Karla | E02 | Terminado | Plantilla fotocopiada (Comic Neue) con manuscrito | Opcional: mesa real (P5) |
| Lista de la maestra (foto) | E02 | Terminado | Cuaderno de cuadro y cursiva | Opcional: mantel real (P6) |
| Nota de voz 1 de la maestra Chayo | E03 | **Provisional funcional** | TTS neuronal local (piper, voz `es_MX-claude-high`), algo más grave y lenta, con acústica de celular. Transcripción disponible | **Locución humana**: mujer de 70-75 años de Aguascalientes, grabada con celular en una cocina. El guion literal está en `build_audio.py` (CHAYO1). Duración objetivo ±1:30; si cambia, actualizar «1:28» en `chat_grupo.js`, `paginas.py` y la etiqueta. |
| Correo impreso | E04 | Terminado | HTML de impresión del navegador | — |
| Croquis de Protección Civil | E04 | Terminado | SVG con estética de autoformas de Word | — |
| Cuaderno de Chayo (5 fotos) | E05 | Terminado | Cuadro chico, cursiva y espiral | Opcional: P6 |
| Libreta de apertura y escaneos | E06 | Terminado | Escaneos planos a la misma escala (necesaria para la superposición) | **No sustituir los escaneos** sin conservar escala y posición (x=60, y=984). |
| Chat privado de Óscar | E07 | Terminado | Motor de chat + álbum | — |
| Recaditos (8 fotos) | E08 | Terminado | Papelitos compuestos y hule simulado | Opcional: hule real (P3). Ideal: utilería física |
| Bitácora (4 fotos con flash) | E09 | Terminado | Libreta florete con tres manos distintas | Opcional: P4 |
| Publicación de Facebook | E10 | Terminado | HTML de vista de publicación; avatares con degradado | Opcional: P7 |
| Nota de voz 2 de la maestra Chayo | E11 | **Provisional funcional** | Igual que E03 (CHAYO2) | Locución humana (misma actriz que E03) |
| Chat de Messenger y 3 fotos | E12 | Terminado | HTML + libreta de listas + invitación de imprenta | Opcional: P5 y P7 |
| Lista de asistencia | E13 | Terminado | Tabla de Word y 26 manos; teléfonos tapados digitalmente después de la «foto» | Opcional: P2 |
| Papelito del epílogo | E14 | Terminado | Dos manos adultas y la partida de gato | Opcional: P2 |

## Qué no hay que delegar nunca a un generador de imágenes
Letras, fechas, cifras y firmas de: la carta de Itzel y su calca; las cartas del 6° B; la lista y el croquis de la maestra; los recaditos y su marcador; la bitácora; la libreta del profe; la invitación; la lista de asistencia; el pintarrón.

## Qué se pierde si se sustituye mal
- **E01/E06:** si cambia la escala o la posición del reverso, la herramienta «Superponer» deja de alinear.
- **E02:** si el pintarrón pierde el 7 cruzado, la fecha romana o la O al centro del gato, desaparece una siembra de la muestra.
- **E08:** si cambia el orden de llegada (`LLEGADA` en `build_e08.py`), hay que regenerar las huellas de orden con `paginas.py`.
