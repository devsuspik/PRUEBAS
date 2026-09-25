# Prompts de imagen para sustituciones (fondos y escenas, nunca texto)

**Regla general:** ninguna imagen generada debe contener texto, cifras, fechas, firmas ni logotipos. Los textos que son pista (cartas, recaditos, bitácora, pintarrón, listas) se componen siempre con código (`MAESTRO_PRIVADO/produccion/fuentes_html/*.html`) y se integran encima con `lib/photo.py`. El generador solo aporta **superficie, luz, objeto o entorno**. Si una imagen generada trae letras, se descarta o se retoca.

Proceso de revisión común a todos los recursos:
1. Buscar texto accidental: letras, números, carteles o etiquetas. Si aparece, se rechaza la imagen.
2. Buscar anacronismos: nada posterior a la fecha de la toma; en 2000 no hay pantallas planas, pintarrones ni celulares a la vista.
3. Buscar pistas accidentales, como nombres, uniformes con escudo reconocible o placas de escuela real.
4. Integrar con el script del recurso, volver a renderizar y comparar lado a lado con la versión actual: la pista debe seguir legible con zoom en móvil.
5. Anotar el cambio en `QA/incidencias_resueltas.md`.

---
## P1 · Pintarrón del aula 6 (el más importante)
- **Evidencia:** E02 (foto del grupo de WhatsApp). **Archivo a sustituir:** `JUGADOR_GRATIS/E02/img/IMG-20250627-WA0012.jpg`. La miniatura aparece también dentro de `Screenshot_20250628-171204.jpg` (volver a renderizar la captura).
- **Función narrativa:** es la bienvenida escrita por la maestra del vespertino el día de la apertura. Tiene que conservar: «Viernes 27-VI-2025» (con el 7 cruzado), «¡Bienvenidos, generación 1994-2000!», «Esta sigue siendo su casa.» en rojo y el **gato con una O al centro** en la esquina superior izquierda. Esos cuatro elementos son pistas y se componen con código.
- **Descripción visual:** muro de salón de primaria pública mexicana, pintado en dos tonos (arriba crema, abajo verde institucional), con un pintarrón blanco de marco de aluminio y charola con plumones. Un cartel de cartulina amarilla pegado con cinta a la derecha. Luz de lámparas fluorescentes con reflejo en el pintarrón. Toma de celular desde un mesabanco, ligeramente de lado y desde abajo.
- **Composición:** el pintarrón ocupa el 85 % del ancho; se ven 5-10 cm de muro arriba y a los lados. Horizontal, aproximadamente 16:9.
- **Debe estar:** el pintarrón **limpio o con restos borrados tenues**, el marco, la charola y la luz fría.
- **No debe aparecer:** letras ni números en ninguna parte (tampoco en el cartel), personas, logotipos de marcas, banderas, escudos, relojes con hora legible, proyector o pantalla.
- **Realismo:** foto de celular de gama media, ligero ruido y compresión de WhatsApp.
- **Resolución:** 2048×1152 o mayor.
- **Prompt sugerido (GPT Image u otro):**
  > Realistic smartphone photo of a Mexican public primary school classroom wall in 2025, two-tone institutional paint (cream above, pale green below), a large blank white dry-erase whiteboard with aluminum frame and a marker tray holding blue, red and black markers, faint grey ghosting of erased marker, fluorescent ceiling light glare on the board, a yellow poster board taped at the right edge with no writing, taken slightly from below and from the left, natural phone camera noise, no text, no letters, no numbers, no people, no logos.
- **Integración:** en `fuentes_html/pintarron.html`, cambiar `#escena` por la foto de fondo (`background:url(...)`) y ajustar la posición de `.pint` al rectángulo del pintarrón. Deben quedar visibles **solo** las capas de texto y el gato. Luego correr `render.js jobs_e02.json pintarron` y `build_e02.py` y volver a renderizar las capturas (`jobs_wa_grupo.json`). Para respetar la perspectiva, aplicar la del fondo a la capa de texto con `photo.perspective`.
- **Revisión específica:** comprobar con zoom que el 7 cruzado y la O al centro se distinguen y que no queda otra O en el gato.

## P2 · Cubierta de mesabanco
- **Evidencias:** E01 (anverso y reverso), E13 (lista de asistencia) y E14 (epílogo). **Se sustituye:** el fondo procedural `tex_laminate` de `lib/photo.py`.
- **Función:** situar las fotos en el aula 6. No es pista.
- **Prompt:**
  > Top-down realistic photo of the worn laminate top of a Mexican school desk ("mesabanco"), light wood-grain melamine with small scratches, faint old pen marks and chipped edges, flat even classroom fluorescent light, no objects, no text, no letters, no logos, 4:3.
- **No debe aparecer:** grafitis con nombres, fechas o corazones con iniciales (podrían leerse como pistas).
- **Integración:** guardar como `MAESTRO_PRIVADO/produccion/texturas/mesabanco.jpg` y reemplazar `tex_laminate(...)` por `Image.open(...).resize((W, H))` en `build_e01.py` y `build_e13_e14.py`.

## P3 · Mantel de hule de cocina
- **Evidencia:** E08 (ocho fotos de recaditos) y la miniatura del álbum en E07. **Se sustituye:** `_render/hule.png` (patrón SVG).
- **Prompt:**
  > Top-down realistic photo of a Mexican kitchen table covered with a glossy plastic oilcloth ("mantel de hule") printed with lemons, cherries and leaves on a cream background, slightly wrinkled, warm tungsten kitchen light, a few crumbs, no objects, no text, no logos.
- **Integración:** sustituir la carga de `hule.png` en `build_e08.py`.

## P4 · Caja de cartón con polvo (bodega)
- **Evidencia:** E09. **Se sustituye:** `tex_cardboard` en `build_e09.py`.
- **Prompt:**
  > Close top-down photo of the dusty flat top of an old cardboard archive box in a storage room, visible dust and a coffee-ring stain, harsh phone flash in the center, dark falloff to the edges, no labels, no text, no tape with writing.

## P5 · Mesa de comedor y escritorio de madera
- **Evidencias:** E02 (cartas de Itzayana, Beto y Karla), E06 (libreta de Mariana) y E12 (fotos del hijo). **Se sustituye:** `tex_wood`.
- **Prompt:**
  > Top-down photo of a dark varnished wooden dining table made of planks, soft window daylight from the left, subtle reflections, no objects, no text.
  > (variante E12) Same, but a single warm desk lamp from the right, darker ambience.

## P6 · Mantel de tela de la maestra Chayo
- **Evidencias:** E02 (lista) y E05. **Se sustituye:** `tex_cloth`.
- **Prompt:**
  > Top-down photo of a beige woven cotton tablecloth with a subtle embroidered border, warm yellow evening lamp light, slight vignette, no objects, no text.

## P7 · Fotos de perfil (Facebook y Messenger)
- **Evidencias:** E10 y E12. **Se sustituyen:** los degradados de `AV` en `facebook.html` y `messenger.html`.
- **Prompt (uno por persona, cuadrado 256×256):** fotos genéricas sin caras reconocibles: flores de jacaranda, un perro de espaldas, un atardecer en carretera, un pastel de cumpleaños sin velas con números, el mar. **Nunca rostros**, para no inventar personas reales identificables.
- **Revisión:** que ninguna imagen tenga texto ni recuerde a una persona real.
