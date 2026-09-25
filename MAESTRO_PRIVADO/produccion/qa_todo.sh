#!/usr/bin/env bash
# Batería de pruebas reproducible (Chromium vía Playwright). Uso: bash qa_todo.sh
set -u
cd "$(dirname "$0")"
export NODE_PATH=${NODE_PATH:-/opt/node22/lib/node_modules}
echo "== 1. Todas las páginas (móvil y escritorio): errores JS y recursos faltantes"; node qa_paginas.js
echo "== 2. Deducciones"
node test_deduccion.js ../../JUGADOR_GRATIS/D1/index.html '{"q1":"p4","q2":"b8","q3":["r1","r3","r4"]}' '{"q1":"k2","q2":"b8","q3":["r1","r2"]}' | sed 's/^/   /'
node test_deduccion.js ../../JUGADOR_COMPLETO/D2/index.html '{"q1":"f5","q2":"u9","q3":"m6","q4":"txt:Le decían Lupita"}' '{"q1":"w3","q2":"u9","q3":"k8","q4":"txt:Itzel"}' | sed 's/^/   /'
node test_deduccion.js ../../JUGADOR_COMPLETO/D3/index.html '{"q1":"d9","q2":"h3","q3":"k2","q4":["p1","p3","p6"],"q5":"txt:Ma. Guadalupe Ytzel Rangel Soto"}' '{"q1":"e2","q2":"h3","q3":"k1","q4":["p1","p2","p3"],"q5":"txt:Lupita"}' | sed 's/^/   /'
echo "== 3. Mesa de ordenar (E08)"; node qa_ordenar.js | sed 's/^/   /'
echo "== 4. Superponer calca (E06)"; node qa_superponer.js | sed 's/^/   /'
echo "== 5. Audio (E03)"; node qa_audio.js | sed 's/^/   /'
echo "== 6. Recorrido de la vista local con desbloqueos"; node test_vista.js | sed 's/^/   /'
echo "== 7. Fronteras entre paquetes"
cd ../..
grep -r -l -E "JUGADOR_COMPLETO|SOLUCION_PRIVADA|MAESTRO_PRIVADO" JUGADOR_GRATIS COMUN && echo "   FALLA: la muestra referencia material de pago/privado" || echo "   ok: la muestra no referencia pago/privado"
grep -r -l -E "SOLUCION_PRIVADA|MAESTRO_PRIVADO" JUGADOR_COMPLETO && echo "   FALLA" || echo "   ok: el completo no referencia privado"
echo "== 8. Recursos declarados en el manifest que no existen"
python3 - <<'PY'
import json, os
m = json.load(open('INTEGRACION/manifest.json'))
falta = [r for p in m['piezas'] for r in p['recursos'] + p['recursos_de_otras_piezas'] + [p['ruta']] if not os.path.exists(r)]
print('   faltan:', falta if falta else 'ninguno')
PY
