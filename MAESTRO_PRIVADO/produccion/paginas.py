"""Genera las páginas públicas de evidencias y deducciones a partir de este archivo PRIVADO.
Contiene transcripciones y respuestas (como huellas). Ejecutar: python3 paginas.py
Salida: JUGADOR_GRATIS/E01..E04, D1 · JUGADOR_COMPLETO/E05..E14, D2, D3 · INTEGRACION/manifest.json"""
import os, json, hashlib, subprocess, re
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = os.path.abspath('../..')
G = os.path.join(ROOT, 'JUGADOR_GRATIS')
C = os.path.join(ROOT, 'JUGADOR_COMPLETO')
SAL = 'lc35'
CASO = 'La carta 35'

def H(did, qid, op):
    return hashlib.sha256(f'{SAL}|{did}|{qid}|{op}'.encode()).hexdigest()
def TOK(w):
    return hashlib.sha256(f'{SAL}|tok|{w}'.encode()).hexdigest()
def HORD(item, pos):
    return hashlib.sha256(f'{SAL}|ord|{item}|{pos}'.encode()).hexdigest()

def picos(mp3, n=96):
    raw = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-i', mp3, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], capture_output=True).stdout
    x = np.abs(np.frombuffer(raw, np.int16).astype(np.float32) / 32768)
    b = np.array_split(x, n)
    v = np.array([np.percentile(k, 95) if len(k) else 0 for k in b])
    v = v / (v.max() + 1e-6)
    return [round(float(t) ** 0.8, 3) for t in v]

def chat_txt(js, yo='Mariana', imgs=None):
    d = json.loads(subprocess.run(['node', 'chat2json.js', js], capture_output=True, text=True).stdout)
    out = [f"Chat: {d['titulo']}"]
    for m in d['m']:
        if 'day' in m: out.append(f"\n— {m['day']} —"); continue
        if 'sys' in m: out.append(f"[{m['sys']}]"); continue
        who = yo if m.get('out') else m['from']
        parts = []
        if m.get('fw'): parts.append('(Reenviado)')
        if m.get('img'):
            nm = os.path.basename(m['img'])
            parts.append(f"[Foto: {imgs.get(nm, nm) if imgs else nm}]")
        if m.get('audio'): parts.append(f"[Nota de voz, {m['audio']}]")
        if m.get('del'): parts.append(f"[{m['del']}]")
        if m.get('text'): parts.append(m['text'])
        out.append(f"{who} ({m['time']}): " + ' '.join(parts))
    return '\n'.join(out)

PAGINA = '''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{id} · {titulo} — {caso}</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="{rel}COMUN/visor.css">
</head><body>
<noscript><p style="padding:16px">Esta evidencia necesita JavaScript para el visor. Los archivos originales están en la carpeta <code>{carpeta}</code>.</p></noscript>
<script>window.EVIDENCIA = {data};</script>
<script src="{rel}COMUN/sha256.js"></script>
<script src="{rel}COMUN/visor.js"></script>
</body></html>
'''
DEDUC = '''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{id} · {titulo} — {caso}</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="{rel}COMUN/visor.css">
</head><body>
<script>window.DEDUCCION = {data};</script>
<script src="{rel}COMUN/sha256.js"></script>
<script src="{rel}COMUN/deduccion.js"></script>
</body></html>
'''

def escribir(base, carpeta, cfg, plantilla=PAGINA, var='EVIDENCIA'):
    d = os.path.join(base, carpeta)
    os.makedirs(d, exist_ok=True)
    cfg = dict(cfg); cfg.setdefault('caso', CASO)
    data = json.dumps(cfg, ensure_ascii=False, indent=1)
    html = plantilla.format(id=cfg['id'], titulo=cfg['titulo'], caso=CASO, rel='../../', carpeta=carpeta, data=data)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(html)

# ======================================================================= TEXTOS
T_CARTA = """9-VI-2000

Hola:
Si estás leyendo esto ya es el 2025 y ya estamos
viejos jaja. Yo voy a tener 37 años.

Ya se que la capsula es [tachado: nomas] de tu salón. Gracias
por dejarme. Te la doy a ti porque tu si sabes quien soy.

Cosas que quiero que se [borrón de goma] sepan en el 2025:
1. El pirul del patio tiene una rama que parece mano.
2. El vidrio de la ventana no lo rompio nadie de tu
   salón. Fue el balón del profe Chava.
3. La mejor hora del salón es cuando se esta llendo el
   sol y prenden las lámparas y pasa el tren de las seis
   y tiembla el vidrio.
4. Te gané 14 a 11. El ultimo cuenta aunque no
   contestaste.
5. Cuando sea grande quiero tener mi cuarto con
   ventana y un perro y que me digan como yo quiero.

Ojalá cuando abran la capsula yo este ahi. Y tu
también. Si no estoy no es porque se me olvido.

                              Itzel"""

T_REVERSO = """Para el de la mañana.
No la leas hasta el 2025."""

A_REVERSO = ("En el tercio de arriba del reverso hay manchas verdosas tenues. Con «Espejo» y «Realce» se leen como "
             "pedazos de otra carta escrita con tinta verde, con letra de niño y sobre renglones que no son los de esta hoja. "
             "Se alcanza a leer, con huecos: «…o en electrónica», «(o port…», «…z y que…», «un carro y una casa. Si alguien lee esto», "
             "«y no soy yo, no se burle.» y, más abajo, «…gato.». El resto no se distingue.")

def carta6b_txt(nombre, a):
    tit = ['1. Así soy yo:', '2. Lo que más me gusta:', '3. Mi familia:', '4. Lo que quiero ser de grande:', '5. Un mensaje para el futuro:']
    s = ['[Hoja fotocopiada] Esc. Prim. "Margarita Maza de Juárez" T.M. · Ciclo escolar 1999-2000',
         'MI CARTA PARA EL AÑO 2025 · Cápsula del tiempo · 6° "B"', f'Nombre: {nombre}    Fecha: 16 de junio del 2000', '']
    for t, r in zip(tit, a):
        s.append(t + ' ' + ' '.join(r))
    s.append('\n[Pie impreso] Esta carta se abrirá en el año 2025. ¡Escribe con tu mejor letra!')
    return '\n'.join(s)

ITZA = [['Tengo 11 años, soy morena, tengo el pelo largo', 'y soy muy platicadora (dice la maestra jaja).'], ['Cantar, Pikachu, mi perro Canelo y', 'las papitas con chile.'], ['Mi mamá, mi papá, mi hermana la Yesi', 'y mi abuelita que vive con nosotros.'], ['Veterinaria o cantante.'], ['Hola Itza del 2025!! Ojalá ya seas', 'veterinaria y tengas muchos perritos.', 'No te olvides de tus amigas del 6° B.', 'Te quiero mucho.   Itza ♥']]
BETO = [['Soy alto, flaco, me dicen Beto y soy', 'el mejor portero del salón.'], ['El fut, el Nintendo, las luchas y dormir.'], ['Mi papá trabaja en la Nissan, mi mamá vende', 'por catálogo y tengo dos hermanos.'], ['Futbolista o bombero.'], ['Beto del 2025: si ya eres futbolista cómprate', 'un carro rojo. Si no, ni modo.', 'Saludos a la raza del 6° B.']]
KARLA = [['Tengo 12 años, soy seria pero cuando agarro', 'confianza no me callo. Uso frenos.'], ['Leer, ver las novelas con mi mamá, dibujar', 'y el chocolate.'], ['Mi mamá es enfermera, mi papá es contador y', 'tengo un hermanito que se llama Pablo.'], ['Doctora (pediatra).'], ['Querida Karla: espero que hayas cumplido', 'tus sueños y que sigas siendo amiga de Mariana', 'y de Nayeli. Cuida a Pablo. No te enojes tanto.']]

LISTA = ['Ávila Romo José Luis','Castañeda Luévano Diana Laura','Chávez Medina Juan Carlos','De Luna Esparza Adriana','Delgado Ruiz Brenda Yesenia','Díaz de León Padilla Karla Patricia','Durón Salas Luis Fernando','Esparza Reyes Mariana','Flores Tiscareño Érick','García Velasco Ana Karen','González Campos Christian Alejandro','Guerrero López Nancy Guadalupe','Hernández Martínez Miguel Ángel','Ibarra Delgado Itzayana','Jiménez Serna Jorge Alberto','López Romo Fabiola','Macías Ávila Roberto','Martínez Durón Claudia Ivonne','Medina Castañeda Eduardo','Mendoza Luévano Óscar','Morales Esparza Gabriela','Muñoz Chávez Ricardo','Ortiz Lozano Daniel','Padilla Hernández Verónica','Ramírez Torres Francisco Javier','Reyes Macías Lizbeth','Romo Salas Alejandro','Ruvalcaba Ortiz Kevin Omar','Salas De Luna Mónica','Serna Guerrero Paola','Tiscareño Flores Jessica','Torres Medina Sandra Luz','Velasco Jiménez Arturo','Zamarripa Díaz Nayeli']
T_LISTA = ('6° "B"                Ciclo escolar 1999 - 2000\nRelación de alumnos                 [en rojo:] Carta 2025 · 16/jun\n\n' +
           '\n'.join(f'{i + 1}. {n}   [palomita roja]' for i, n in enumerate(LISTA)) +
           '\n\n34 alumnos: 18 niñas, 16 niños      [en rojo:] Total 34 cartas [palomita]')

import importlib.util
spec = importlib.util.spec_from_file_location('ba', 'build_audio.py'); ba = importlib.util.module_from_spec(spec); spec.loader.exec_module(ba)
T_CHAYO1 = ' '.join(t for t, _ in ba.CHAYO1)
T_CHAYO2 = ' '.join(t for t, _ in ba.CHAYO2)

T_CORREO = """[Impresión del correo desde el navegador · 30/6/25, 13:18]
Asunto: RE: Consulta sobre el salón de 6° B (generación 1994-2000)
De: Dirección Esc. Prim. Margarita Maza TM <dir.mmazatm.ags@gmail.com>
Para: Mariana Esparza <mariana.esparzareyes@hotmail.com>
Fecha: lun 30/06/2025 11:48 a. m.
Adjunto: Croquis PC 2024-2025.pdf (412 KB)

Estimada Sra. Mariana Esparza:

Reciba un cordial saludo. En atención a su correo del sábado, le informo lo siguiente:

1. De acuerdo con los registros de esta Dirección, el grupo de 6° "B" del ciclo escolar 1999-2000 ocupaba el aula 6 del edificio "B", la misma en la que se llevó a cabo la apertura.

2. Dicha aula se comparte con la Escuela Primaria "Profr. Rafael Ramírez", turno vespertino, que es una escuela distinta con su propia Dirección. Consulté con el Director de ese turno, Profr. Arturo Salas Guerrero, quien me informa que en el ciclo 1999-2000 el aula 6 correspondía al grupo de 6° "A" vespertino, a cargo del Profr. Salvador Olvera Díaz (†), y que en el registro de inscripción de ese grupo no aparece ninguna alumna con el nombre de Itzel.

3. Le comparto el croquis del Programa Interno de Protección Civil del plantel para que pueda ubicar el aula.

Por otra parte, le solicito de la manera más atenta retirar de Facebook la publicación con la fotografía de la carta. Desde el sábado varios padres de familia han llamado a la escuela preguntando por "la niña de la cápsula" y circulan versiones que no le ayudan a nadie. Le recuerdo que las cartas son documentos personales y que la escuela se comprometió a entregarlas únicamente a sus autores o a sus familiares.

Agradezco nuevamente a la Mtra. Rangel, titular del 6° "A" vespertino, que amablemente les facilitó el aula y se quedó a apoyarnos durante la apertura.

Sin más por el momento, quedo a sus órdenes.

Atentamente
Mtra. Silvia Reyes Castañeda
Directora
Esc. Prim. "Margarita Maza de Juárez" T.M.

---- Mensaje citado ----
El sáb, 28 jun 2025 a las 19:02, Mariana Esparza escribió:
Buenas tardes maestra Silvia, muchas gracias otra vez por todo el apoyo con la apertura.
Le quería preguntar dos cosas: ¿qué salón era el de 6° B en el 2000? ¿Era el mismo donde estuvimos? ¿Y en la tarde lo usaba algún grupo? Es por la carta de Itzel, la que salió sin sobre. En nuestro grupo no hay ninguna Itzel y queremos saber si podría ser de la escuela de la tarde.
Saludos,
Mariana Esparza (generación 1994-2000)"""

T_CROQUIS = """PROGRAMA INTERNO DE PROTECCIÓN CIVIL · CICLO ESCOLAR 2024-2025
Croquis de rutas de evacuación, zonas de menor riesgo y punto de reunión.
Esc. Prim. "Margarita Maza de Juárez" T.M. · Esc. Prim. "Profr. Rafael Ramírez" T.V. · Calle Maquinistas No. 214, Col. Talleres Poniente, Aguascalientes, Ags.

PLANO (norte hacia arriba; sin escala)
· Poniente (izquierda): barda y, del otro lado, VÍAS DEL FFCC. Entre la barda y el edificio B, el PATIO TRASERO con un PIRUL (a la altura del aula 6) y, en la esquina de abajo, la CASA CONSERJE / BODEGA junto al PORTÓN DE SERVICIO.
· EDIFICIO "B" (de norte a sur): AULA 8 (5° B T.M. / 4° A T.V.), AULA 7 (5° A T.M. / 5° A T.V.), AULA 6 (6° B T.M. / 6° A T.V.), AULA 5 (6° A T.M. / USAER-T.V.). Las ventanas de las aulas del edificio B están del lado poniente; las puertas dan al pasillo, del lado oriente.
· Centro: PATIO CÍVICO / CANCHA con ASTA BANDERA y PUNTO DE REUNIÓN.
· Norte: COOPERATIVA y BIBLIOTECA / AULA DE MEDIOS. Oriente: sanitarios y EDIFICIO "C" (aulas 9 a 12).
· Sur, sobre CALLE MAQUINISTAS: EDIFICIO "A" con DIRECCIÓN T.M., DIRECCIÓN T.V., ACCESO PRINCIPAL y AULAS 1 a 4.
· Flechas verdes: rutas de evacuación hacia el punto de reunión. Extintores, botiquín, alarma y tablero eléctrico señalados.

BRIGADAS (T.M. / T.V.)
Coordinación del inmueble: Mtra. Silvia Reyes Castañeda / Profr. Arturo Salas Guerrero
Evacuación edificio "A": Profra. Leticia Romo Díaz / Profr. Jesús Martínez Luna
Evacuación edificio "B": Profra. Nora Delgado Ávila / Profra. Ma. Guadalupe Rangel S.
Evacuación edificio "C": Profr. Víctor Esparza Muñoz / Profra. Karina López Serna
Primeros auxilios: Profra. Claudia Ibarra Luna / Profra. Rosa Elena Muñoz
Prevención y combate de incendios: Sr. Julián Ortega (intendente) / Profr. Jesús Martínez Luna
Comunicación: Profra. Ana Luisa Medina / Profra. Karina López Serna

EN CASO DE SISMO: NO CORRO · NO GRITO · NO EMPUJO. Emergencias: 911.
Elaboró: Comisión de Seguridad Escolar T.M. / T.V. · Actualización: septiembre de 2024 · Hoja 1 de 1"""

IMG_E02 = {'IMG-20250627-WA0012.jpg': 'pintarrón', 'IMG-20250627-WA0014.jpg': 'la carta de Itzel (E01)',
           'IMG-20250627-WA0016.jpg': 'carta de Itzayana', 'IMG-20250627-WA0021.jpg': 'carta de Beto',
           'IMG-20250627-WA0022.jpg': 'carta de Karla', 'IMG-20250627-WA0031.jpg': 'lista de la maestra Chayo'}

# ======================================================================= MUESTRA (gratis)
def muestra():
    e01 = dict(id='E01', titulo='Carta sin sobre', etapa='Muestra', orden=1,
        fuente='Dos fotos del celular de Mariana Esparza, tomadas en el aula 6 el viernes 27 de junio de 2025 (13:41 y 13:42), durante la apertura de la cápsula del tiempo del 6° B.',
        nota=dict(de='Mariana', texto='Esta es la hoja que salió hasta el fondo de la caja. No venía en ningún sobre. Le tomé foto de los dos lados antes de que alguien la agarrara.'),
        piezas=[dict(tipo='imagen', etiqueta='Anverso', src='img/IMG_20250627_134112.jpg',
                     alt='Hoja de cuaderno de raya escrita a lápiz, doblada en tres, con un cerco de agua en la parte de abajo, sobre un mesabanco.',
                     descripcion='Hoja arrancada de un cuaderno profesional de raya (la orilla del espiral quedó rota), escrita a lápiz. Se respeta la ortografía original.',
                     transcripcion=T_CARTA),
                dict(tipo='imagen', etiqueta='Reverso', src='img/IMG_20250627_134127.jpg',
                     alt='Reverso de la hoja: una leyenda a lápiz al centro y manchas verdosas tenues en el tercio superior.',
                     descripcion='Reverso de la misma hoja. Al centro, una leyenda a lápiz. En el tercio de arriba hay manchas verdosas tenues que no son del papel.',
                     transcripcion=T_REVERSO, accesible=A_REVERSO)],
        ayudas=[dict(tema='¿Qué son las manchas verdes del reverso?', niveles=[
                    'Amplía el tercio de arriba del reverso. Las manchas tienen forma: no son humedad nada más.',
                    'Prueba «Espejo» y luego «Realce». Con agua y presión, la tinta de una hoja puede calcarse en la hoja de junto.',
                    'Son pedazos de otra carta, escrita con tinta verde, que estuvo pegada a esta durante años. No es la letra de Itzel. Guarda el dato: más adelante vas a poder compararlo.']),
                dict(tema='¿A quién le escribe Itzel?', niveles=[
                    'Lee lo que dice por fuera, en el reverso.',
                    'Relaciónalo con la hora del día que describe la carta: el sol, las lámparas, el tren de las seis.',
                    'Itzel le escribe a alguien que ocupaba «su» salón en otro momento del día. Las siguientes evidencias te dirán cuándo estaba ella ahí.'])])
    escribir(G, 'E01', e01)

    capt = ['Screenshot_20250628-171204.jpg', 'Screenshot_20250628-171211.jpg', 'Screenshot_20250628-171219.jpg',
            'Screenshot_20250628-171302.jpg', 'Screenshot_20250628-171309.jpg', 'Screenshot_20250628-171316.jpg']
    txt_chat = chat_txt('fuentes_html/chat_grupo.js', 'Mariana', IMG_E02)
    piezas = [dict(tipo='imagen', etiqueta=f'Captura {i + 1}', src='img/' + c,
                   alt=f'Captura {i + 1} de 6 del grupo de WhatsApp de exalumnos.',
                   descripcion='Capturas de pantalla del teléfono de Mariana. La transcripción es de toda la conversación (las seis capturas).',
                   transcripcion=txt_chat) for i, c in enumerate(capt)]
    piezas += [
        dict(tipo='imagen', etiqueta='Foto: pintarrón', src='img/IMG-20250627-WA0012.jpg',
             alt='Pintarrón del aula 6 con un mensaje de bienvenida escrito con plumón azul y rojo.',
             descripcion='Foto que Mariana mandó al grupo (27 jun, 2:52 p. m.). Pintarrón del aula 6 antes de la apertura.',
             transcripcion='Arriba a la derecha (azul): «Viernes 27-VI-2025»\nAl centro (azul): «¡Bienvenidos, generación 1994-2000!»\nAbajo (rojo): «Esta sigue siendo su casa.»\nRestos borrados: «Tarea: Lección 12, pág. 118», «3/4 + 1/2 =», «5/8 - 1/4 =»\nCartel en la pared: «REGLAMENTO: 1. Levanto la mano. 2. Respeto a todos. 3. Cuido mi salón. 4. Tiro la basura en su lugar. 5. Traigo mi tarea. — 6° A T.V.»',
             accesible='En la esquina superior izquierda del pintarrón hay un gato (la cuadrícula #) dibujado con plumón azul, con una sola jugada: una O en la casilla del centro. El 7 de «27» está cruzado con una rayita.'),
        dict(tipo='imagen', etiqueta='Foto: carta de Itzayana', src='img/IMG-20250627-WA0016.jpg',
             alt='Carta en hoja fotocopiada, escrita con pluma de gel verde.', descripcion='Carta del sobre 14 (Itzayana Ibarra), escrita con gel verde en la hoja fotocopiada del grupo.',
             transcripcion=carta6b_txt('Itzayana Ibarra Delgado', ITZA)),
        dict(tipo='imagen', etiqueta='Foto: carta de Beto', src='img/IMG-20250627-WA0021.jpg',
             alt='Carta en hoja fotocopiada, escrita con pluma azul, con un cerco de agua abajo.', descripcion='Carta del sobre 17 (Roberto Macías), pluma azul.',
             transcripcion=carta6b_txt('Roberto Macías Ávila', BETO)),
        dict(tipo='imagen', etiqueta='Foto: carta de Karla', src='img/IMG-20250627-WA0022.jpg',
             alt='Carta en hoja fotocopiada, escrita con pluma de gel morada en letra cursiva.', descripcion='Carta del sobre 6 (Karla Díaz de León), gel morado.',
             transcripcion=carta6b_txt('Karla Patricia Díaz de León P.', KARLA)),
        dict(tipo='imagen', etiqueta='Foto: lista de la maestra', src='img/IMG-20250627-WA0031.jpg',
             alt='Página de cuaderno de cuadro chico con la lista del 6° B escrita en letra cursiva azul y palomitas rojas.',
             descripcion='Foto que la maestra Chayo le mandó a Mariana de su cuaderno de 1999-2000 (reenviada al grupo).',
             transcripcion=T_LISTA)]
    e02 = dict(id='E02', titulo='El grupo de exalumnos', etapa='Muestra', orden=2,
        fuente='Capturas del grupo de WhatsApp «6°B Gen 94-2000» (teléfono de Mariana, sábado 28 de junio de 2025) y las fotos que se compartieron ahí el 27 de junio.',
        nota=dict(de='Mariana', texto='Te paso lo que se habló en el grupo, perdón por el desorden. Las fotos te las mando aparte para que se vean mejor.'),
        piezas=piezas,
        comparar=[dict(etiqueta='E01 · Carta sin sobre (anverso)', src='../E01/img/IMG_20250627_134112.jpg', alt='Carta de Itzel, anverso'),
                  dict(etiqueta='E01 · Carta sin sobre (reverso)', src='../E01/img/IMG_20250627_134127.jpg', alt='Carta de Itzel, reverso')],
        ayudas=[dict(tema='¿Qué tiene de distinto la hoja de Itzel?', niveles=[
                    'Abre las fotos de las cartas de Itzayana, Beto y Karla. Fíjate en el papel, la fecha y la forma.',
                    'Usa «Comparar» para poner una de esas cartas junto a la de Itzel (E01).',
                    'Las cartas del 6° B se escribieron el mismo día, en la hoja fotocopiada que dio la maestra, con fecha «16 de junio del 2000». La de Itzel es una hoja de cuaderno, a lápiz, del «9-VI-2000». No la escribió en esa clase.']),
                dict(tema='¿Puede ser Itzayana?', niveles=[
                    'Compara su letra y su firma con las de la carta de Itzel.',
                    'Itzayana escribió con tinta verde. Mira qué dicen las manchas verdes del reverso de E01 y si coinciden con su carta.',
                    'Su carta está completa, firmada «Itza», con otra letra y otro texto. La calca verde de E01 no sale de su carta.'])])
    escribir(G, 'E02', e02)

    mp3 = os.path.join(G, 'E03', 'audio', 'PTT-20250628-WA0007.mp3')
    e03 = dict(id='E03', titulo='Nota de voz de la maestra Chayo', etapa='Muestra', orden=3,
        fuente='Nota de voz de la Profra. Ma. del Rosario Tiscareño («maestra Chayo»), maestra del 6° B en 1999-2000. Se la mandó a Mariana el sábado 28 de junio de 2025 (4:21 p. m.) y Mariana la reenvió al grupo.',
        nota=dict(de='Mariana', texto='La maestra ya tiene 72 años, pero se acuerda de todo. Bueno, casi.'),
        piezas=[dict(tipo='audio', etiqueta='Nota de voz · 1:28', src='audio/PTT-20250628-WA0007.mp3', duracion='1:28', picos=picos(mp3),
                     descripcion='Audio de 1:28. Voz de una mujer mayor en su casa; al fondo se oye un pájaro. Transcripción literal:',
                     transcripcion=T_CHAYO1)],
        ayudas=[dict(tema='¿Qué es seguro y qué es opinión?', niveles=[
                    'Separa lo que la maestra hizo con sus propias manos de lo que supone.',
                    'Ella contó los sobres y los guardó con llave. En 2025 la hoja de Itzel apareció sin sobre, junto a los sobres que se deshicieron (E02).',
                    'Si en 2000 no había hojas sueltas, la hoja de Itzel entró dentro del sobre de alguien del 6° B. Y lo de «Chava» no es un error de dedo: la maestra misma dice que a ella nunca le dijeron «profe».'])])
    escribir(G, 'E03', e03)

    e04 = dict(id='E04', titulo='Respuesta de la directora', etapa='Muestra', orden=4,
        fuente='Correo de la directora del turno matutino a Mariana (lunes 30 de junio de 2025), que Mariana guardó como PDF desde su navegador, y el croquis que venía adjunto.',
        nota=dict(de='Mariana', texto='Me contestó la directora. Me regañó por lo de Facebook, pero mandó el croquis de la escuela.'),
        piezas=[dict(tipo='imagen', etiqueta='Correo', src='img/correo_direccion_30-06-2025.png', alt='Impresión de un correo electrónico de la directora a Mariana.',
                     descripcion='Correo impreso a PDF desde el navegador.', transcripcion=T_CORREO),
                dict(tipo='imagen', etiqueta='Adjunto: croquis', src='img/Croquis_PC_2024-2025.png',
                     alt='Croquis de Protección Civil del plantel con edificios, rutas de evacuación en verde, simbología y tabla de brigadas.',
                     descripcion='Adjunto del correo: croquis del Programa Interno de Protección Civil (documento de Word exportado a PDF).', transcripcion=T_CROQUIS)],
        comparar=[dict(etiqueta='E01 · Carta sin sobre (anverso)', src='../E01/img/IMG_20250627_134112.jpg', alt='Carta de Itzel, anverso'),
                  dict(etiqueta='E02 · Foto del pintarrón', src='../E02/img/IMG-20250627-WA0012.jpg', alt='Pintarrón del aula 6')],
        ayudas=[dict(tema='¿Quién es el «profe Chava»?', niveles=[
                    'Busca en el correo quién daba clase en el aula 6 en 1999-2000, en cada turno.',
                    '«Chava» es un apodo muy común. ¿De qué nombre?',
                    'Chava es Salvador. El Profr. Salvador Olvera tenía el 6° A vespertino en la misma aula 6.']),
                dict(tema='¿Cuadra la carta con el croquis?', niveles=[
                    'Busca en el croquis lo que Itzel menciona: el pirul, el tren, las ventanas.',
                    'Fíjate hacia dónde dan las ventanas del aula 6 y qué hay de ese lado.',
                    'Las ventanas del aula 6 dan al poniente, al patio trasero con el pirul y a la vía del tren: por ahí se mete el sol en la tarde.'])])
    escribir(G, 'E04', e04)

    d1 = dict(id='D1', titulo='Primera deducción', etapa='Muestra', orden=5,
        intro='Con lo que tienes (E01 a E04) responde tres preguntas. Todavía no hace falta saber quién es Itzel.',
        preguntas=[
            dict(id='q1', tipo='unica', texto='¿Quién es el «profe Chava» que menciona la carta?', opciones=[
                dict(id='k2', t='La maestra Chayo (Ma. del Rosario Tiscareño): una niña pudo escribir mal el apodo.'),
                dict(id='m7', t='El Profr. Arturo Salas Guerrero, director del turno vespertino.'),
                dict(id='p4', t='El Profr. Salvador Olvera Díaz, maestro del 6° A vespertino en 1999-2000.'),
                dict(id='t9', t='Un maestro del 6° A del turno matutino.'),
                dict(id='z1', t='No hay manera de saberlo con estas pruebas.')],
                h=[H('D1', 'q1', 'p4')], ok='Chava es Salvador. Cuadra.'),
            dict(id='q2', tipo='unica', texto='¿En qué momento del día estaba Itzel en el aula 6?', opciones=[
                dict(id='a3', t='En la mañana: era alumna del 6° B y nadie la recuerda.'),
                dict(id='b8', t='En la tarde: en el turno vespertino, que usaba la misma aula.'),
                dict(id='c5', t='En el recreo: era del 6° A matutino y se metía al salón.'),
                dict(id='d6', t='Nunca estuvo ahí: escribió de oídas.')],
                h=[H('D1', 'q2', 'b8')]),
            dict(id='q3', tipo='multiple', texto='¿Qué lo sostiene? Marca todas las pruebas que apoyan tu respuesta anterior (al menos dos).', opciones=[
                dict(id='r1', t='Por fuera dice «Para el de la mañana»: ella no era de la mañana.'),
                dict(id='r2', t='Itzayana tiene un nombre parecido y también escribió con tinta verde.'),
                dict(id='r3', t='La carta habla del sol que se va, las lámparas prendidas y el tren de las seis.'),
                dict(id='r4', t='El correo: por la tarde, el aula 6 era del 6° A vespertino del Profr. Salvador Olvera.'),
                dict(id='r5', t='Beto se acuerda de que la carta se hizo en casa.'),
                dict(id='r6', t='La maestra Chayo: en la mañana no había ningún Chava.')],
                h=[H('D1', 'q3', x) for x in ['r1', 'r3', 'r4', 'r6']], min=2,
                no='Alguna de las marcadas no apoya esa conclusión, o falta marcar al menos dos.')],
        exito=dict(titulo='Itzel era de la tarde', mensajes=[
            dict(de='Mariana', texto='¡¿Chava de Salvador?! Obvio 🤦‍♀️ Entonces Itzel iba en la tarde, en nuestro mismo salón.'),
            dict(de='Mariana', texto='Pero la directora dice que en la lista de la tarde tampoco hay ninguna Itzel. ¿Cómo vas a clases sin estar en ninguna lista?'),
            dict(de='Mariana', texto='Y otra cosa: la maestra jura que no había hojas sueltas. O sea que alguien de nosotros metió esa hoja en su sobre. «Para el de la mañana»… ¿quién era el de la mañana?')],
            cierre='<b>Aquí termina la muestra gratuita.</b> En el caso completo, Mariana consigue el cuaderno de la maestra Chayo y las cartas mojadas del fondo de la caja, y alguien por fin contesta.'),
        ayudas=[dict(tema='Pregunta 1', niveles=['Lee otra vez el correo de la directora: ¿quién estaba en el aula 6 en la tarde?', '«Chava» es el apodo de un nombre que aparece en el correo.', 'Salvador → Chava. La maestra Chayo nunca fue «profe».']),
                dict(tema='Preguntas 2 y 3', niveles=['¿Cuándo prenden las lámparas en un salón y cuándo pasa «el tren de las seis»?', 'Compara con los horarios de los turnos: el 6° B salía antes del mediodía.', 'Ella estaba en el aula por la tarde. La leyenda «Para el de la mañana», el correo y lo que dice la maestra Chayo lo confirman.'])])
    escribir(G, 'D1', d1, DEDUC, 'DEDUCCION')
    return [e01, e02, e03, e04, d1]

if __name__ == '__main__':
    todo = muestra()
    print('Páginas de muestra:', [x['id'] for x in todo])
