# Pruebas funcionales

## Ejecutadas de verdad
Todas con **Chromium (Playwright 1.56)**, que es el navegador disponible en el entorno. La batería se repite con:
```bash
bash MAESTRO_PRIVADO/produccion/qa_todo.sh
```

| # | Prueba | Cómo | Resultado |
|---|---|---|---|
| 1 | Carga de las 17 páginas en móvil (390×844, táctil, dpr 2) y escritorio (1280×800) | `qa_paginas.js`: errores JS, peticiones fallidas y capturas en `QA/capturas/pg_*` | **Sin errores** |
| 2 | Deducciones D1, D2 y D3 | `test_deduccion.js` con un juego incorrecto y uno correcto por control | Las incorrectas se marcan pregunta por pregunta («1 de 3…»). Las correctas muestran los mensajes de Mariana y envían `postMessage {tipo:'lc35:deduccion', ok:true}` |
| 3 | Texto libre tolerante (D3 q5) | Variantes probadas | Aceptadas: «la maestra lupita rangel», «GUADALUPE RANGEL», «Itzel Rangel», «Ma. Guadalupe Ytzel Rangel Soto». Rechazada: «rangel» sola |
| 4 | Texto libre (D2 q4) | «Le decían Lupita» | Aceptada |
| 5 | Mesa de ordenar (E08) | `qa_ordenar.js`: revisar sin mover, reordenar con los botones ↑ y abrir la ampliación | Al inicio, «0 de 8 en su lugar»; al final, mensaje de éxito; la ampliación abre |
| 6 | Superponer calca (E06) | `qa_superponer.js`: elegir la carta #20, activar espejo, arrastrar la capa hasta la posición correcta y acercar | Alinea letra por letra (capturas `QA/capturas/E06_*_superponer*.png`) en móvil y escritorio |
| 7 | Audio (E03) | `qa_audio.js`: metadatos, `canPlayType('audio/mpeg')` y reproducción | 87,7 s, «probably», avanza el tiempo |
| 8 | Espejo y realce (E01) | `test_ui.js`: reverso → espejo → realce ×2 → acercar ×2 | Funciona; la calca se lee (`QA/capturas/E01_movil_reverso_espejo.png`) |
| 9 | Comparar (E02) | `test_ui.js` | Pantalla dividida con selector en cada lado |
| 10 | Vista local de punta a punta | `test_vista.js`: muestra → D1 → simular compra → etapa 1 → D2 → etapa 2 → D3 → epílogo | Piezas abiertas: 5 → 5 (sin compra) → 10 → 16 → 17. Sin errores |
| 11 | Fronteras entre paquetes | grep | La muestra y `COMUN` no referencian `JUGADOR_COMPLETO`, `SOLUCION_PRIVADA` ni `MAESTRO_PRIVADO`. El completo no referencia lo privado |
| 12 | Recursos del manifest | Script Python | Existen todos |
| 13 | Metadatos de imagen | PIL (EXIF e info) | 0 archivos con metadatos |
| 14 | Inteligibilidad de las voces sintéticas | Transcripción automática local (faster-whisper «small») | Se entienden. Se corrigieron malas pronunciaciones («Itzel», «hoja») con reescritura fonética solo para el sintetizador |
| 15 | Funcionamiento sin red | Todas las pruebas corren desde `file://` | Sin peticiones externas |

## No ejecutadas (limitaciones honestas)
- **Safari iOS / WebKit y Firefox:** no disponibles en el entorno. Riesgos conocidos: `:has()` en los estilos de las opciones (Firefox reciente y Safari lo soportan); `crypto.subtle` en `file://` (hay respaldo `sha256.js`); MP3 (compatible en todos).
- **Lectores de pantalla reales** (VoiceOver, TalkBack, NVDA): solo se revisaron `alt`, `aria-label`, roles y el orden del DOM.
- **Duración con jugadores humanos:** **no se ha medido.** Los 60-75 min y los 9-12 min de la muestra son estimaciones de diseño (`MAESTRO_PRIVADO/ritmo.md`).

## Protocolo de prueba con personas (pendiente)
1. 5-8 jugadores adultos de México que no conozcan el caso, en móvil y en escritorio.
2. Cronometrar por pieza (la vista local registra qué piezas se abrieron). Anotar dónde piden ayuda y de qué nivel.
3. Tras la muestra, preguntar: ¿qué investigas?, ¿qué descubriste?, ¿comprarías el resto? (1-5).
4. Al terminar: ¿qué hipótesis tuviste?, ¿en qué momento sospechaste de la maestra?, ¿algo te pareció falso o «hecho para el jugador»?
5. Criterios de ajuste: si más del 30 % no resuelve D1 sin la ayuda 3, reforzar E04; si más del 50 % adivina la identidad final antes de E09, reducir la siembra en E02 y E04.
