# Incidencias resueltas

| # | Dónde | Problema | Cómo se detectó | Solución |
|---|---|---|---|---|
| 1 | Plantilla 6° B | Renglones fuera de la hoja; sangría calculada a ojo | Render | Espaciado nuevo; se mide el ancho real de cada título |
| 2 | Motor de manuscrito | «¡» invisible y «¿» deforme en varias fuentes | Render del pintarrón | Se trazan como «!» y «?» girados 180° |
| 3 | Motor de manuscrito | Un cambio dejó `translateY` en em para todas las letras | Revisión del código | Unidades en px para letras normales |
| 4 | E01 | Orilla en peine, cerco de agua como humo gris, mesabanco con vetas de mármol | Mirar la foto | Nuevos algoritmos de orilla, cerco y laminado |
| 5 | E01 | Calca verde legible a simple vista | Mirar la foto | Transferencia parcial, difuminada y más tenue |
| 6 | E01/E06 | El realce borraba la calca (el contraste empujaba el papel al blanco) | Simulación de filtros en Python | Nuevos niveles: saturar, bajar el blanco y luego contrastar |
| 7 | E02 | Pintarrón con esquina vacía por la perspectiva y muro muy plano | Mirar la foto | Encuadre cerrado; marcado como provisional (P1) |
| 8 | E02 | Motas de fotocopia como pimienta; raya vertical muy marcada | Mirar la foto | Menos motas y más tenues |
| 9 | E02 | Mesa con vetas de mármol | Mirar la foto | Madera en tablones de veta recta |
| 10 | E02 | «Chucho Durón» (Chucho es de Jesús, no de Luis Fernando) | Revisión del canon | «Luisfer Durón» |
| 11 | E02/E03 | El chat decía 1:40 y el audio dura 1:28 | Duración real con ffmpeg | Chat, etiqueta y reproductor dicen 1:28 |
| 12 | E03/E11 | La voz sintética decía «Itself» por «Itzel» y deformaba «hoja» | Transcripción automática (whisper) | Reescritura fonética solo para el sintetizador; la transcripción conserva la ortografía |
| 13 | E04 | Norte encima del aula 9, extintor sobre un rótulo, acceso desalineado | Mirar el render | Reubicados |
| 14 | E05 | La flecha del «vidrio estrellado» señalaba el puesto 4 y no el de Óscar | Mirar el render | Ventanas reubicadas: la 3.ª a la altura del puesto 3 |
| 15 | E05 | El diario saltaba del 10 de marzo al 16 de junio en una página | Test de realismo | 4 páginas fechadas con entradas rutinarias |
| 16 | E06 | Fecha manuscrita encima del rótulo «Fecha» | Mirar el render | Movida a la línea |
| 17 | E06 | «Maestra Lupita (vesp.)» en la libreta de la etapa 1 adelantaba la identificación | Auditoría de siembras | «La maestra del vespertino…» |
| 18 | E08 | Texto fuera del papel; «¿» debajo del renglón; letra flotando entre renglones | Mirar el render | Tamaño menor, sin desplazamiento vertical y alineada a los renglones |
| 19 | E09 | Mayúsculas del padre encimadas y demasiado limpias | Mirar el render | Fuente torpe, renglón y medio por línea |
| 20 | E12 | Palomita de fuente de respaldo; iconos de estado como glifos | Mirar el render | Trazo SVG e iconos SVG |
| 21 | E13 | Tachado de teléfonos «impreso» en el papel | Test de procedencia | Máscara geométrica: rectángulos digitales después de la foto |
| 22 | E13 | Nora y Julián con la misma fuente que Chayo y Pedro | Canon tipográfico | Fuentes distintas |
| 23 | E14 | O copiadas por Óscar en el azul de ella | Mirar el render | Tinta negra |
| 24 | Visor | En móvil, la imagen tapaba la barra de herramientas y no se podía pulsar (prueba automática bloqueada) | Playwright | Altura propia del área del visor, calculada por JS |
| 25 | Visor | Miniaturas aplastadas en escritorio | Captura de escritorio | `flex:none` y altura dinámica |
| 26 | Visor | Selector con texto claro sobre fondo blanco | Captura | Estilo propio |
| 27 | Visor | El atributo `hidden` no ocultaba botones con `display:flex` | Captura | `[hidden]{display:none!important}` |
| 28 | Vista local | Mostraba «Lupe» (título de la etapa 2) antes de descubrirlo | Revisión de filtraciones | Etapas bloqueadas con nombres neutros |
| 29 | Paquete gratis | Copia de foto de WhatsApp sin uso en E02 | Revisión del paquete | Movida a los renders privados |
| 30 | Pruebas | El test interpretaba mal selectores con «=» | Error del test | Separación por el primer «=» |
