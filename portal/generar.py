#!/usr/bin/env python3
"""Genera portal/datos.js para index.html (el portal del caso).

Reúne en un solo archivo: el manifest, las piezas de cada evidencia (con sus
descripciones y transcripciones), los documentos .md, el código de producción,
las capturas de QA y la lista completa de archivos del repositorio.

Uso (desde la raíz del repositorio):  python3 portal/generar.py
"""
import json
import os
import re
import subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAIZ)

DOCS = [
    ('Prompts', 'ASSETS_PENDIENTES/prompts_imagenes.md', 'Prompts de imagen', False),
    ('Prompts', 'ASSETS_PENDIENTES/sustituciones.md', 'Sustituciones pendientes', False),
    ('Solución', 'SOLUCION_PRIVADA/solucion.md', 'Solución', True),
    ('Solución', 'SOLUCION_PRIVADA/respuestas.md', 'Respuestas', True),
    ('Solución', 'SOLUCION_PRIVADA/justificacion_por_evidencias.md', 'Justificación por evidencias', True),
    ('Solución', 'SOLUCION_PRIVADA/respuestas.js', 'respuestas.js (modo pruebas)', True),
    ('Diseño', 'MAESTRO_PRIVADO/premisas.md', 'Premisas', False),
    ('Diseño', 'MAESTRO_PRIVADO/verdad.md', 'La verdad', True),
    ('Diseño', 'MAESTRO_PRIVADO/canon.md', 'Canon', True),
    ('Diseño', 'MAESTRO_PRIVADO/matriz_pistas.md', 'Matriz de pistas', True),
    ('Diseño', 'MAESTRO_PRIVADO/ritmo.md', 'Ritmo', False),
    ('Diseño', 'MAESTRO_PRIVADO/fichas_fuentes.md', 'Fichas de fuentes', False),
    ('Integración', 'README.md', 'README', False),
    ('Integración', 'INTEGRACION/instrucciones.md', 'Instrucciones de integración', False),
    ('Integración', 'INTEGRACION/manifest.json', 'manifest.json', False),
    ('QA', 'QA/pruebas_funcionales.md', 'Pruebas funcionales', False),
    ('QA', 'QA/auditoria_logica.md', 'Auditoría lógica', True),
    ('QA', 'QA/auditoria_visual.md', 'Auditoría visual', False),
    ('QA', 'QA/incidencias_resueltas.md', 'Incidencias resueltas', False),
]

TEXTO = ('.py', '.js', '.json', '.html', '.css', '.sh', '.md', '.txt')


def leer(ruta):
    with open(ruta, encoding='utf-8') as f:
        return f.read()


def evidencia(ruta_index):
    """Extrae window.EVIDENCIA de la página de una pieza."""
    html = leer(ruta_index)
    m = re.search(r'window\.EVIDENCIA = (\{.*?\n\});</script>', html, re.S)
    if not m:
        return None
    ev = json.loads(m.group(1))
    base = os.path.dirname(ruta_index)
    for p in ev.get('piezas', []):
        if p.get('src'):
            p['src'] = os.path.normpath(os.path.join(base, p['src']))
    return ev


def main():
    manifest = json.loads(leer('INTEGRACION/manifest.json'))
    piezas = []
    for p in manifest['piezas']:
        item = {k: p[k] for k in ('id', 'tipo', 'titulo', 'etapa', 'orden', 'paquete', 'ruta', 'miniatura', 'interaccion')}
        if p['tipo'] == 'evidencia':
            ev = evidencia(p['ruta'])
            if ev:
                item['fuente'] = ev.get('fuente', '')
                item['nota'] = ev.get('nota')
                item['archivos'] = [
                    {k: x.get(k) for k in ('tipo', 'etiqueta', 'src', 'alt', 'descripcion', 'transcripcion')}
                    for x in ev.get('piezas', []) if x.get('src')
                ]
        piezas.append(item)

    docs = [{'grupo': g, 'ruta': r, 'titulo': t, 'spoiler': s, 'texto': leer(r)} for g, r, t, s in DOCS]

    archivos = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout.split('\n')
    archivos = [a for a in archivos if a and os.path.exists(a)]
    lista = [{'ruta': a, 'bytes': os.path.getsize(a)} for a in archivos]

    codigo = [
        {'ruta': a, 'texto': leer(a)}
        for a in archivos
        if a.startswith('MAESTRO_PRIVADO/produccion/') and '/fuentes/' not in a and a.endswith(TEXTO)
    ]
    capturas = sorted(a for a in archivos if a.startswith('QA/capturas/'))

    datos = {
        'caso': manifest['caso'],
        'etapas': manifest['etapas'],
        'piezas': piezas,
        'docs': docs,
        'codigo': codigo,
        'capturas': capturas,
        'archivos': lista,
    }
    with open('portal/datos.js', 'w', encoding='utf-8') as f:
        f.write('window.PORTAL = ')
        json.dump(datos, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print('portal/datos.js:', len(piezas), 'piezas,', len(docs), 'documentos,',
          len(codigo), 'archivos de código,', len(capturas), 'capturas,', len(lista), 'archivos')


if __name__ == '__main__':
    main()
