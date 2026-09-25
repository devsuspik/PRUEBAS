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


# ======================================================================= ETAPA 1 (pago)
T_CROQ_CHAYO = """Acomodo del grupo 6° "B"            sept. 1999
[Arriba: Pizarrón; a la derecha: escritorio y Puerta. A la izquierda, a lo largo de la hoja: "Ventanas", cuatro dibujadas.]
Fila de las ventanas (de adelante hacia atrás): Adriana · Miguel Á. · [tachado: Óscar M.] Kevin R. · Lizbeth · Arturo V. · Érick
2a. fila: Diana · José Luis · Nancy · Ricardo · Sandra · Daniel
3a. fila: Mariana · Juan Carlos · Fabiola · Christian · Mónica · Fco. Javier
4a. fila: Karla · Luis Fdo. · Itzayana · Jorge A. · [tachado: Kevin R.] Óscar M. · Alejandro
5a. fila: Brenda · Eduardo · Ana Karen · Roberto · Verónica · Paola
6a. fila (junto a la puerta): Claudia · Gabriela · Jessica · Nayeli · (vacío) · (vacío)
[En rojo, con flecha hacia la 3a. ventana:] vidrio estrellado 13/oct
[Abajo, en tinta negra:] cambio 9/mar"""

def diario_txt(pag):
    import re as _re
    src = open('fuentes_html/chayo_cuaderno.html', encoding='utf-8').read()
    a = src.index(f"    {pag}: [")
    b = src.index("    ],", a)
    out = []
    for f, ls in _re.findall(r"\['([^']+)', \[([^\]]*)\]\]", src[a:b]):
        out.append(f)
        out += ['  ' + x for x in _re.findall(r"'([^']*)'", ls)]
        out.append('')
    return '\n'.join(out).strip()

T_LIBRETA = """[Libreta de Mariana]                         Fecha: 27/jun/25
APERTURA CÁPSULA 6°B
12:50 Julián (intendente) sacó la caja.
Tapa estrellada en una esquina (la del lado del pirul).
Agua en el fondo, como 3 dedos :(

Sobres: 34 (según la lista de la maestra)
Enteros: 30 → ok (algunos húmedos)
#18 Claudia · sobre roto, carta bien
#19 Eduardo · sobre deshecho, carta mojada (sí se lee)
#20 Óscar · sobre deshecho, carta muy mojada, tinta corrida
#21 Gaby · sobre despegado, carta mojada
[En un recuadro:] HOJA SIN SOBRE, hasta el fondo, entre los pedazos de los sobres 19-20-21 → firma "Itzel" ??

Entregadas hoy: 22
Me llevo 12 (¡secarlas!): Diana, Juan Carlos, Érick, Christian, Nancy, Eduardo, Óscar (Mty), Gaby, Jorge A., Daniel, Verónica, Mónica
La maestra del vespertino nos prestó el salón → darle las gracias
Mandar fotos al grupo · preguntar a la maestra Chayo"""

OSCAR = [['Tengo 12 años, soy moreno, uso lentes', 'desde 4° y soy de las Chivas!!'], ['el fut, dibujar carros, el Nintendo de mi', 'primo y los tacos de mi tía Cuca.'], ['mi mamá Rosa, mi papá Toño que es', 'chofer y mi hermano el Chuy que es mas chico.'], ['Ingeniero en electrónica', '(o portero de las Chivas).'], ['En el 2025 voy a tener 37 años. Ojalá las Chivas', 'ya sean campeones otra vez y que yo tenga', 'un carro y una casa. Si alguien lee esto', 'y no soy yo, no se burle.', 'P.D. Lo que mas me gustó de 6° fue el gato.']]
EDUARDO = [['Me llamo Eduardo, tengo 11 años, soy', 'chaparro y me gusta mucho la ciencia.'], ['Los experimentos, armar cosas, las caricaturas', 'y el pozole de mi abuela.'], ['Mi mamá, mi abuela y yo.'], ['Científico o maestro de ciencias.'], ['Eduardo: ojalá ya existan los carros que vuelan.', 'Si no, invéntalos tú. Y no te pelees', 'con mi mamá.']]
GABY = [['Me llamo Gaby, tengo 11 años y soy la más', 'chiquita de mi casa.'], ['Bailar, cantar con mis primas, mi tamagochi', '(ya se murió) y el elote con mayonesa.'], ['Somos 6: mi papá, mi mamá, mis 3', 'hermanas y yo.'], ['Maestra de kínder.'], ['Gaby del futuro: no se te olvide tu cumpleaños', 'y hazte una fiesta grande. Y acuérdate de', 'la maestra Chayo que fue muy buena.']]

RECADOS = {
 'A': ('Recadito del sacapuntas', """[Papelito de cuaderno de cuadro, a lápiz y pluma azul]
(lápiz) ¿De quién es esta banca en la mañana? Se te olvidó tu sacapuntas de las Chivas. Te lo guardé en la canastilla. —I.   22-XI-99
(pluma azul) Es mío!! gracias. Soy Óscar de 6°B. ¿Tú quién eres?
(lápiz) Itzel. Voy en la tarde con el profe Chava. ¿Juegas gato? Empiezo yo.   24-XI-99
[Un gato terminado en empate. A un lado, a lápiz: "empate"]"""),
 'B': ('Hoja de partidas', """[Hoja blanca con cuatro partidas de gato. Las O a lápiz, las X en azul.]
(pluma azul) revancha!!   ·   esa no se vale
(lápiz) Van: Itzel 3, Óscar 1 jaja
(lápiz) Mañana otra. 30-XI-99"""),
 'C': ('Recadito del fantasma', """[Papelito de cuaderno de raya]
(pluma azul) ¿Es cierto que en la noche espantan en este salón? El Beto dice que se ve una niña en la ventana.
(lápiz) Jajaja no espantan. Soy yo. Hago la tarea aquí en la noche porque en el cuarto no hay luz buena. Mi papá tiene las llaves. No le digas a nadie.   7-XII-99"""),
 'D': ('Recadito del chocolate', """[Papelito de cuaderno de cuadro con una mancha de chocolate]
(pluma azul) Te dejé un chocolate por lo de navidad. ¿Cuándo es tu cumpleaños? El mío es el 14 de febrero jaja
(lápiz) Gracias!! Te dejé colación de la posada de aquí. Mi papá dice que nací en mayo pero no sé bien porque no tengo acta. Por eso no salgo en la lista del profe. Soy oyente.   11-I-2000"""),
 'E': ('Recadito de «oyente»', """[Papelito de cuaderno de raya]
(pluma azul) ¿Qué es oyente? Mi mamá dice que si no tienes acta no existes jaja
(lápiz) Oyente es que vengo pero no cuento. Pero sí existo, te gano en gato. En mi casa me dicen Lupe pero tú dime Itzel.   18-I-2000"""),
 'F': ('Segunda hoja de partidas', """[Papelito de cuaderno de cuadro con tres partidas de gato]
(pluma azul) ya te voy alcanzando!!
(lápiz) Nomás porque te dejé. Van: Itzel 11, Óscar 9.   15-II-2000"""),
 'G': ('Recadito de la cápsula', """[Tira de cuaderno de raya]
(pluma azul) Vamos a hacer una cápsula del tiempo, cada quien mete una carta para abrirla en el 2025. Qué flojera escribir jaja
(lápiz) ¿Puedo meter una carta en tu cápsula? Yo no soy de tu salón pero el salón también es mío tantito.   28-II-2000
(pluma azul) Sí. Me la das y la meto con la mía. Pero no le digas a nadie.
(lápiz) Trato. 2-III-2000"""),
 'H': ('Último recadito', """[Papelito de cuaderno de raya, solo a lápiz]
¿Ya no me vas a contestar? Si es por lo que dijeron los de tu salón no importa. Me dijeron que ya no puedo venir con el profe. Sigo aquí atrás.
Te dejé tu tiro. Si no contestas gano yo. Vamos 13 a 11.
[Un gato empezado: O al centro, X en una esquina, O en otra esquina.]
13-III-2000"""),
}
ORDEN_OK = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

def etapa1():
    e05 = dict(id='E05', titulo='El cuaderno de la maestra Chayo', etapa='Etapa 1 · El de la mañana', orden=6,
        fuente='Cinco fotos que la maestra Chayo tomó de su cuaderno de planeación de 1999-2000 y le mandó a Mariana el martes 1 de julio de 2025, de noche.',
        nota=dict(de='Mariana', texto='La maestra encontró su cuaderno de ese año (¡lo tenía guardado!). Me mandó las páginas donde hay algo de las cartas.'),
        piezas=[dict(tipo='imagen', etiqueta='Acomodo del grupo', src='img/IMG-20250701-WA0004.jpg', alt='Página de cuaderno de cuadro con el acomodo de los mesabancos del 6° B, nombres en cursiva y dos nombres tachados.', descripcion='Croquis de lugares hecho por la maestra en su cuaderno (septiembre de 1999), con correcciones posteriores.', transcripcion=T_CROQ_CHAYO),
                dict(tipo='imagen', etiqueta='Diario · octubre 1999', src='img/IMG-20250701-WA0005.jpg', alt='Página del diario de clase de octubre de 1999.', transcripcion=diario_txt('diario_oct')),
                dict(tipo='imagen', etiqueta='Diario · febrero 2000', src='img/IMG-20250701-WA0006.jpg', alt='Página del diario de clase de febrero de 2000.', transcripcion=diario_txt('diario_feb')),
                dict(tipo='imagen', etiqueta='Diario · marzo 2000', src='img/IMG-20250701-WA0007.jpg', alt='Página del diario de clase de marzo de 2000.', transcripcion=diario_txt('diario_mar')),
                dict(tipo='imagen', etiqueta='Diario · junio 2000', src='img/IMG-20250701-WA0008.jpg', alt='Página del diario de clase de junio de 2000.', transcripcion=diario_txt('diario_jun'))],
        comparar=[dict(etiqueta='E01 · Carta sin sobre (anverso)', src='../../JUGADOR_GRATIS/E01/img/IMG_20250627_134112.jpg', alt='Carta de Itzel'),
                  dict(etiqueta='E04 · Croquis de Protección Civil', src='../../JUGADOR_GRATIS/E04/img/Croquis_PC_2024-2025.png', alt='Croquis del plantel')],
        ayudas=[dict(tema='¿Quién ocupaba el lugar de Itzel en la mañana?', niveles=[
                    'La carta de Itzel dice algo sobre la ventana de «su» lugar. Búscalo.',
                    'Busca la anotación en rojo en el acomodo del grupo y fíjate a qué mesabanco apunta.',
                    'El vidrio estrellado era el de la 3a. ventana, junto al tercer mesabanco de la fila de las ventanas. Ahí se sentaba Óscar M. hasta el 9 de marzo; después, Kevin R.']),
                dict(tema='¿Qué pasó el 9 de marzo de 2000?', niveles=[
                    'Lee la entrada de ese día y la del día siguiente.',
                    '¿De qué turno era la niña de los recaditos? ¿En qué fila estaban? ¿Con quién habló la directora?',
                    'Encontraron recaditos de una niña de la tarde en un mesabanco de la fila de las ventanas. Cambiaron a Óscar de lugar y la directora habló con el conserje y con la Dirección de la tarde.'])])
    escribir(C, 'E05', e05)

    bases = [dict(etiqueta='Carta #19 (Eduardo)', src='img/Escaneo_0031.jpg', alt='Escaneo de la carta de Eduardo'),
             dict(etiqueta='Carta #20 (Óscar)', src='img/Escaneo_0032.jpg', alt='Escaneo de la carta de Óscar'),
             dict(etiqueta='Carta #21 (Gaby)', src='img/Escaneo_0033.jpg', alt='Escaneo de la carta de Gaby')]
    e06 = dict(id='E06', titulo='Las cartas del fondo de la caja', etapa='Etapa 1 · El de la mañana', orden=7,
        fuente='Foto de la libreta donde Mariana anotó el estado de los sobres durante la apertura, y los escaneos que hizo en su casa el miércoles 2 de julio de 2025.',
        nota=dict(de='Mariana', texto='Óscar todavía no me da permiso de enseñar la suya, pero te la paso nomás para esto. Escaneé también la de Itzel: por atrás se ve mejor la mancha.'),
        piezas=[dict(tipo='imagen', etiqueta='Libreta: relación de apertura', src='img/IMG_20250702_203015.jpg', alt='Página de libreta con notas a mano sobre el estado de los sobres.', transcripcion=T_LIBRETA),
                dict(tipo='imagen', etiqueta='Escaneo: carta #19', src='img/Escaneo_0031.jpg', alt='Carta de Eduardo, mojada, pluma azul.', transcripcion=carta6b_txt('Eduardo Medina Castañeda', EDUARDO)),
                dict(tipo='imagen', etiqueta='Escaneo: carta #20', src='img/Escaneo_0032.jpg', alt='Carta de Óscar, muy mojada, tinta verde corrida en la parte de abajo.', transcripcion=carta6b_txt('Óscar Mendoza Luévano', OSCAR)),
                dict(tipo='imagen', etiqueta='Escaneo: carta #21', src='img/Escaneo_0033.jpg', alt='Carta de Gaby, mojada, a lápiz.', transcripcion=carta6b_txt('Gabriela Morales Esparza', GABY)),
                dict(tipo='imagen', etiqueta='Escaneo: hoja de Itzel (reverso)', src='img/Escaneo_0034.jpg', alt='Reverso de la hoja de Itzel escaneado; la mancha verde se ve con más claridad.', transcripcion=T_REVERSO, accesible=A_REVERSO),
                dict(tipo='imagen', etiqueta='Escaneo: hoja de Itzel (anverso)', src='img/Escaneo_0035.jpg', alt='Anverso de la hoja de Itzel escaneado.', transcripcion=T_CARTA)],
        comparar=[dict(etiqueta='E02 · Carta de Itzayana (tinta verde)', src='../../JUGADOR_GRATIS/E02/img/IMG-20250627-WA0016.jpg', alt='Carta de Itzayana')],
        superponer=dict(bases=bases, capa=dict(etiqueta='tercio de arriba del reverso de Itzel', src='img/capa_reverso_tercio_superior.jpg', alt='Tercio superior del reverso de la hoja de Itzel', x0=150, y0=820),
                        nota='Activa «Calca en espejo» y «Mover calca»; arrastra la hoja de arriba hasta que los renglones coincidan. Prueba con cada carta.'),
        ayudas=[dict(tema='¿De quién es la calca verde?', niveles=[
                    'Usa «Superponer» y pon el tercio de arriba del reverso de Itzel sobre cada una de las cartas del fondo.',
                    'La calca está al revés: activa «Calca en espejo» y usa «Mover calca» para empalmar los renglones. Baja la opacidad si hace falta.',
                    'Solo en una carta los trazos verdes caen justo encima de las letras: la #20, de Óscar Mendoza. La hoja de Itzel pasó 25 años dentro de su sobre.'])])
    escribir(C, 'E06', e06)

    capt = ['Screenshot_20250703-092412.jpg', 'Screenshot_20250703-092419.jpg', 'Screenshot_20250703-092503.jpg', 'Screenshot_20250703-092511.jpg']
    t7 = chat_txt('fuentes_html/chat_oscar.js', 'Mariana').replace('\no (', '\nÓscar (').replace('\no ', '\nÓscar ')
    t7 = re.sub(r'^o \(', 'Óscar (', t7, flags=re.M)
    e07 = dict(id='E07', titulo='Óscar contesta', etapa='Etapa 1 · El de la mañana', orden=8,
        fuente='Capturas de la conversación privada de WhatsApp entre Mariana y Óscar Mendoza (miércoles 2 y jueves 3 de julio de 2025).',
        nota=dict(de='Mariana', texto='Óscar me pidió que no lo pusiera en el grupo. Te lo paso a ti porque me estás ayudando; por favor no lo compartas.'),
        piezas=[dict(tipo='imagen', etiqueta=f'Captura {i + 1}', src='img/' + c, alt=f'Captura {i + 1} de 4 del chat entre Mariana y Óscar.', transcripcion=t7) for i, c in enumerate(capt)],
        ayudas=[dict(tema='¿Qué sabe Óscar y qué no?', niveles=[
                    'Separa lo que Óscar vivió de lo que supone.',
                    'Óscar cree que Itzel era hija del profe de la tarde. ¿Qué dicen los recaditos (E08) sobre quién tenía las llaves y dónde vivía?',
                    'Óscar nunca supo su nombre completo ni dónde vivía. Lo del profe es una suposición de niño; los recaditos apuntan a otra persona.'])])
    escribir(C, 'E07', e07)

    import json as _j
    llegada = _j.load(open('_render/recados_llegada.json'))
    inv = {v: k for k, v in llegada.items()}
    items, fotos = [], []
    ids = {r: f'n{(ord(r) * 7919) % 997:03d}' for r in ORDEN_OK}
    for k, (nm, r) in enumerate(llegada.items()):
        items.append(dict(id=ids[r], etiqueta=f'Foto {k + 1}', src='img/' + nm, mini='img/mini_' + nm, alt=f'Foto {k + 1}: recadito'))
        fotos.append(dict(tipo='imagen', etiqueta=f'Foto {k + 1}', src='img/' + nm, alt=f'Recadito fotografiado sobre un mantel de hule (foto {k + 1}).', descripcion=RECADOS[r][0], transcripcion=RECADOS[r][1]))
    hs = [HORD(ids[r], i) for i, r in enumerate(ORDEN_OK)]
    e08 = dict(id='E08', titulo='Los recaditos', etapa='Etapa 1 · El de la mañana', orden=9,
        fuente='Ocho fotos que la mamá de Óscar tomó de los recaditos que él guardaba en una lata de galletas. Óscar se las reenvió a Mariana el jueves 3 de julio de 2025. Llegaron revueltas.',
        nota=dict(de='Mariana', texto='Óscar dice que se los mandaron revueltos. ¿Me ayudas a ponerlos en orden? Yo ya lloré dos veces.'),
        piezas=[dict(tipo='ordenar', etiqueta='Mesa: ordenar', instruccion='Pon los recaditos en el orden en que se escribieron (el primero arriba). Toca una foto para ampliarla y usa las flechas para moverla.',
                     items=items, h=hs, exito='Así quedan en orden: del 22 de noviembre de 1999 al 13 de marzo de 2000. El marcador del gato va subiendo hasta 13 a 11, y el último recadito se quedó sin respuesta.',
                     descripcion='Mesa para ordenar los recaditos. Cada foto tiene su transcripción en su pestaña.', transcripcion='Abre cada foto en su pestaña para leer su transcripción.')] + fotos,
        ayudas=[dict(tema='¿Cómo se ordenan?', niveles=[
                    'Casi todos tienen una fecha con la letra de Itzel. El mes está en números romanos.',
                    'XI es noviembre, XII diciembre, I enero, II febrero y III marzo. Lo de 1999 va antes que lo de 2000. El marcador del gato también ayuda.',
                    'Orden: sacapuntas (22-XI-99) · hoja de partidas «3 a 1» (30-XI-99) · «no espantan» (7-XII-99) · chocolate (11-I-2000) · «oyente» (18-I-2000) · «11 a 9» (15-II-2000) · la cápsula (28-II/2-III-2000) · el último (13-III-2000).']),
                dict(tema='¿Qué cuentan de Itzel?', niveles=[
                    'Fíjate dónde hace la tarea, quién tiene las llaves y por qué no está en la lista.',
                    'Compara con el croquis de Protección Civil (E04): ¿qué hay «aquí atrás» del edificio B?',
                    'Itzel vivía dentro de la escuela, en la casa del conserje, detrás del aula 6. No tenía acta, así que no podía inscribirse: iba de oyente. En su casa le decían Lupe.'])])
    escribir(C, 'E08', e08)

    d2 = dict(id='D2', titulo='Segunda deducción', etapa='Etapa 1 · El de la mañana', orden=10,
        intro='Con lo que sabes hasta E08, responde. Todavía falta saber quién es Itzel hoy.',
        preguntas=[
            dict(id='q1', tipo='unica', texto='¿A quién iba dirigida la carta y cómo llegó a la cápsula?', opciones=[
                dict(id='w3', t='A Kevin Ruvalcaba, que en junio ocupaba ese mesabanco; Itzel la dejó en su canastilla.'),
                dict(id='h8', t='A Itzayana, por el parecido del nombre; se la dio en el recreo.'),
                dict(id='f5', t='A Óscar Mendoza, que ocupaba su mismo mesabanco en la mañana; él la metió en su propio sobre.'),
                dict(id='j1', t='A la maestra Chayo, que la guardó en el archivero con los sobres.'),
                dict(id='v6', t='A nadie en particular; alguien la metió en la caja la noche antes de enterrarla.')],
                h=[H('D2', 'q1', 'f5')]),
            dict(id='q2', tipo='unica', texto='¿Por qué Itzel no aparece en ninguna lista, ni de la mañana ni de la tarde?', opciones=[
                dict(id='c2', t='Porque estaba inscrita con otro nombre en el turno vespertino.'),
                dict(id='u9', t='Porque no tenía acta de nacimiento: no podía inscribirse y entraba de oyente a la clase del profe Chava.'),
                dict(id='g4', t='Porque se dio de baja antes de fin de año y la borraron de las listas.'),
                dict(id='s7', t='Porque era de otra escuela y solo venía de visita.')],
                h=[H('D2', 'q2', 'u9')]),
            dict(id='q3', tipo='unica', texto='¿Dónde vivía Itzel en 1999-2000?', opciones=[
                dict(id='k8', t='Con el profe Salvador (Chava), porque era su hija.'),
                dict(id='p1', t='Enfrente de la escuela, del otro lado de la calle Maquinistas.'),
                dict(id='m6', t='En la escuela misma: en la casa del conserje, detrás del edificio B. Su papá era el conserje.'),
                dict(id='x2', t='No se puede saber con estas pruebas.')],
                h=[H('D2', 'q3', 'm6')]),
            dict(id='q4', tipo='texto', texto='¿Cómo le decían en su casa?', placeholder='Un nombre', grupos=[[TOK(x) for x in ['lupe', 'lupita', 'guadalupe', 'lupis']]])],
        exito=dict(titulo='Itzel vivía en la escuela', mensajes=[
            dict(de='Mariana', texto='Vivía en la escuela… detrás de nuestro salón. Y nosotros diciendo que espantaban 😔'),
            dict(de='Mariana', texto='Lupe. Itzel. Sin acta, de oyente. Y en marzo le prohibieron entrar por nuestra culpa, o por la de la maestra, ya no sé.'),
            dict(de='Mariana', texto='Ahora sí necesito saber quién es y dónde está. El viernes voy a la escuela a dejar las cartas que faltan; la bodega de atrás era la casa del conserje. A ver qué encuentro.')],
            cierre='<b>Etapa 2 · Lupe.</b> Se desbloquean E09 a E13.'),
        ayudas=[dict(tema='Pregunta 1', niveles=['Recuerda la calca verde y el croquis de lugares.', 'La calca coincide con una sola carta (E06) y el vidrio estrellado señala un mesabanco (E05).', 'Óscar: su carta tocó la de Itzel y él lo confirma en E07.']),
                dict(tema='Preguntas 2 a 4', niveles=['Lee el recadito del chocolate y el de «oyente» (E08).', 'Junta «mi papá tiene las llaves», «el cuarto», «la posada de aquí» y «sigo aquí atrás» con el croquis de Protección Civil (E04).', 'No tenía acta; iba de oyente; vivía en la casa del conserje; en su casa le decían Lupe.'])])
    escribir(C, 'D2', d2, DEDUC, 'DEDUCCION')
    return [e05, e06, e07, e08, d2]


# ======================================================================= ETAPA 2 (pago)
T_BIT = {
 'portada': '[Libreta de pasta dura negra con lomo rojo. Etiqueta blanca escrita con plumón:] BITÁCORA / CONSERJERÍA / 1998 - 2001',
 'p1': """11-X-99   Se destapó el baño de los niños. Se barrió el patio de atrás.
13-X-99   Amaneció estrellado el vidrio de la 3a ventana del aula 6. Fue un balonazo del 6° A de la tarde. Se le puso cinta. Se le avisó a la directora de la mañana.
14-X-99   Se lavaron los tinacos.
17-XI-99  Se arregló la llave del bebedero.
22-XI-99  Se cambió el foco de en medio del aula 6 (se fundió). Se recogieron 2 chamarras olvidadas y se dejaron en la dirección.
26-XI-99  Vinieron a fumigar. Se abrieron todas las aulas.
29-XI-99  Se cambió el vidrio del baño de niñas.
3-XII-99  Se pusieron los adornos de navidad en la dirección.
[Firma, con otra letra, pesada:] J. Refugio Rangel M.
[Las notas están en pluma azul, con letra redonda y fechas con el mes en números romanos.]""",
 'p2': """6-III-2000   Se pintó la guarnición del patio cívico.
10-III-2000  Vino la directora de la mañana a revisar las llaves de las aulas. Se le dio copia de la del aula 6.
[A lápiz, en mayúsculas grandes y temblorosas, con otra letra:]
15 MARZO 2000
ME DIJO LA DIRECTORA DE LA MAÑANA QUE MI HIJA NO ENTRE A LOS SALONES NI A LA CLASE DEL PROFE. ESTA BIEN.
R. RANGEL
21-III-2000  Día festivo, no hubo clases. Se regaron las plantas.
24-III-2000  Se cambió la chapa del baño de maestras.
28-III-2000  Se arregló la reja del portón de servicio.
31-III-2000  Se barrió la azotea del edificio B. Había 3 balones.
[Firma:] J. Refugio Rangel M.""",
 'p3': """9-VI-2000   Se cortó el pasto del patio de atrás. Se podó el pirul (menos la rama de la mano).
14-VI-2000  Se entregaron las llaves de la bodega a la dirección para el inventario.
16-VI-2000  Entrego la casa y 27 llaves por mi cambio a la secundaria técnica del oriente. La casa queda limpia. Gracias.
[Firma:] J. Refugio Rangel M.
[Con otra letra, alta y angosta, en pluma negra y fechas con diagonales:]
19/06/2000  Recibí la casa y las llaves (25, faltan 2 de la bodega). Pedro Luévano G.
20/06/2000  Se revisó la instalación de luz del edificio B.
23/06/2000  Hoyo para la cápsula del 6° B junto al pirul (60 cm). Se tapó después de la ceremonia. P.L.
26/06/2000  Se sacó basura de la casa de conserje (cajas).
28/06/2000  Fumigación. Todo en orden. P.L.""",
}

T_FB = """[Publicación de Mariana Esparza · 28 de junio a las 10:14 · Pública]
¿Alguien conoce a ITZEL? 💌
Ayer abrimos la cápsula del tiempo que enterramos en junio del 2000 en la Primaria Margarita Maza de Juárez (6° B, generación 94-2000) y salió una carta de una niña que firma Itzel. NADIE del grupo la conoce 😮
Si sabes quién es o estudiaste en esa escuela, compártelo 🙏
#CápsulaDelTiempo #Aguascalientes
EDIT: quité la foto de la carta por respeto 🙏 Gracias a todos
[212 reacciones · 64 comentarios · 41 veces compartido]

Comentarios (más relevantes):
Itzayana Ibarra (6 d): YA NO ME ETIQUETEN, NO SOY YO 😂🙄  [45]
Salvador Olvera Lozano (3 h): Mi papá fue maestro de la tarde en esa escuela muchos años (el profe Salvador Olvera, q.e.p.d.). Siempre contaba de una niña que se metía a su salón sin estar inscrita y que era la más aplicada de todos. Te mando mensaje.  [38]
   ↳ Mariana Esparza, autora (2 h): Muchas gracias!! Ya le contesté 🙏
Chuy Romo (6 d): Yo iba en la tarde en esa escuela (Rafael Ramírez) y decían que en la noche se veía una niña en la ventana del edificio B 😱😱 a lo mejor era ella  [21]
   ↳ Rocío Luévano (6 d): No inventes Chuy 😂
Mary Tiscareño (6 d): Mi mamá fue la maestra de ese grupo 🥰 le dio mucho gusto que se acordaran de ella  [17]
Lupita Rangel (6 d): Con todo respeto, Mariana: si esa niña no se ha presentado, a lo mejor tiene sus razones. Esa carta tiene destinatario, y no es Facebook.  [12]
   ↳ Mariana Esparza, autora (6 d): Tiene razón, maestra 🙏 ya quité la foto.
Kevin Ruvalcaba (5 d): Yo me acuerdo de unos recaditos que encontramos en un mesabanco… éramos bien pesados de chiquitos 😔  [9]
Rosy Medina (6 d): Seguro era hija de algún maestro de la tarde, esos se quedaban hasta noche  [3]
Yesenia Macías (7 d): Qué bonito 😢 ojalá la encuentren  [4]
[Ver 51 comentarios más]"""

T_MSG = """[Chat de Messenger con Salvador Olvera Lozano]
— SÁB 18:36 —
Mariana: ¡Hola! Muchas gracias por escribir. Todo lo que se acuerde nos ayuda muchísimo 🙏
— DOM 21:05 —
Salvador: Buenas noches Mariana, soy Salvador Olvera, el hijo del profe Salvador (el de la tarde). Vi tu publicación.
Salvador: Mi papá murió en 2019. Guardaba muchas cosas de sus grupos, estuve buscando en sus cajas.
Salvador: Siempre contaba de una niña que "se le metía al salón". Decía que aprendió a leer casi sola con lo que dejaban escrito en el pizarrón los de la mañana y que era la más aplicada. Que no tenía papeles y que él la llevó al Registro Civil para que le hicieran su acta.
Salvador: Nunca nos dijo cómo se llamaba, o yo no me acuerdo. Encontré esto en su libreta de ese año y una invitación que tenía guardada en la misma caja. Te mando fotos.
Salvador: [3 fotos]
Salvador: Por cierto, vi que alguien comentó que a lo mejor era hija de un maestro de la tarde. Mi papá tuvo puros hombres, somos tres 😅
Salvador: Ojalá la encuentres. A mi papá le hubiera dado mucho gusto.
— LUN 9:58 —
Mariana: Muchísimas gracias, Salvador. No sabe cuánto nos ayuda 🙏"""

T_LIBRETA_CHAVA = """6° A  T.V.   1999-2000          Marzo          Salvador Olvera D.
[Columnas de asistencia: días 1, 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17. Punto = asistió; rayita roja = faltó.]
1. Alvarado Díaz Juan M. · 2. Barrón López Cristina · 3. Calvillo Ruiz Ernesto · 4. Campos Medina Leticia · 5. Cruz Ramírez José A. · 6. Delgado Sandoval Mayra · 7. Espinoza Luna Héctor · 8. Galván Torres Rosa Ma. · 9. Gómez Reyes Luis A. · 10. Hernández Vela Brenda · 11. Jaramillo Cruz Marco A. · 12. Lara Martínez Yadira · 13. Macías Durón Erika · 14. Martínez Salas Armando · 15. Muñoz Ortega Claudia · 16. Nava Serrano Rigoberto · 17. Ortiz Pedroza Nancy · 18. Pérez Aguilar Sergio · 19. Quezada Rincón Lorena · 20. Ramos Luévano Víctor · 21. Reyes Castillo Jazmín · 22. Romo Díaz Jesús · 23. Ruiz Esquivel Omar · 24. Sánchez Vargas Liliana · 25. Tapia Macías Iván · 26. Torres Anaya Rocío · 27. Valdivia Luna Eduardo · 28. Zúñiga Ríos Karina
[Renglón sin número, a lápiz:] Lupita (oyente) — hija de D. Refugio   [puntos del 1 al 14; el 15, una raya]
[A lápiz:] 15-III ya no puede entrar (orden Dir. T.M.)
[En pluma azul, añadido después:] acta: Reg. Civ. 5-V-2000 ✓"""

T_INVIT_F = """[Invitación impresa en cartulina perlada, letras doradas, con un birrete arriba]
Escuela Normal «Profra. Eduviges Parga»
Licenciatura en Educación Primaria
Generación 2008 · 2012
Con la bendición de Dios y el apoyo de quienes creyeron en mí, tengo el honor de invitarle a mi
CEREMONIA DE GRADUACIÓN
María Guadalupe Ytzel Rangel Soto
Misa de Acción de Gracias: Viernes 13 de julio de 2012 · 12:00 hrs. · Templo de San José
Ceremonia: Viernes 13 de julio de 2012 · 18:00 hrs. · Auditorio de la Escuela Normal
Mis padres: J. Refugio Rangel Muñoz · Ma. Guadalupe Soto Ibarra (†)
Aguascalientes, Ags."""

T_INVIT_R = """[Vuelta de la invitación, a mano, pluma azul]
Profe Chava:
su oyente ya es maestra.
Gracias por dejarme estar.
Lupita
(la de Don Cuco)
6-VII-2012"""

def asistencia_txt():
    import re as _re
    src = open('fuentes_html/asistencia.html', encoding='utf-8').read()
    rows = _re.findall(r"\['([^']+)', '([^']+)', '[^']+', '[^']+', '([^']+)', '[^']+'\]", src)
    s = ['ESC. PRIM. "MARGARITA MAZA DE JUÁREZ" T.M. · REGISTRO DE ASISTENCIA', 'Apertura de la Cápsula del Tiempo · Generación 1994-2000 · Viernes 27 de junio de 2025', '', 'No. | Nombre completo | Generación / Cargo | Teléfono | Firma']
    for i, (n, g, f) in enumerate(rows):
        s.append(f'{i + 1}. {n} | {g} | [tapado] | [firma: «{f}»]')
    s.append('27-30: vacíos')
    return '\n'.join(s)

T_EPI = """[Hoja de libreta de raya. Arriba, en pluma negra, letra de adulto:]
10/jul/2025
Itzel:
Perdón por no contestarte en marzo.
Ya me contaron todo.
¿Me dejas seguir?  Te toca.
— Óscar (el de la mañana)
[Un gato: X en la esquina de arriba a la izquierda y abajo a la izquierda; O al centro, arriba a la derecha y, en azul, una O nueva en el centro de la izquierda.]
[Abajo, en pluma azul:]
11-VII-2025
Te dejo seguir. Pero vamos 14 a 11. Mañana te toca.
— I."""

def etapa2():
    E01A = dict(etiqueta='E01 · Carta sin sobre (anverso)', src='../../JUGADOR_GRATIS/E01/img/IMG_20250627_134112.jpg', alt='Carta de Itzel')
    E06A = dict(etiqueta='E06 · Escaneo de la hoja de Itzel (anverso)', src='../E06/img/Escaneo_0035.jpg', alt='Escaneo de la carta de Itzel')
    E08C = dict(etiqueta='E08 · Recadito «no espantan»', src='../E08/img/IMG-20250703-WA0025.jpg', alt='Recadito')
    E08E = dict(etiqueta='E08 · Recadito «oyente»', src='../E08/img/IMG-20250703-WA0028.jpg', alt='Recadito')
    E02P = dict(etiqueta='E02 · Foto del pintarrón', src='../../JUGADOR_GRATIS/E02/img/IMG-20250627-WA0012.jpg', alt='Pintarrón del aula 6')
    E04C = dict(etiqueta='E04 · Croquis de Protección Civil', src='../../JUGADOR_GRATIS/E04/img/Croquis_PC_2024-2025.png', alt='Croquis')
    E09P1 = dict(etiqueta='E09 · Bitácora (oct.-dic. 1999)', src='../E09/img/IMG_20250704_120502.jpg', alt='Bitácora')
    E12F = dict(etiqueta='E12 · Invitación (frente)', src='../E12/img/IMG_20250706_210331.jpg', alt='Invitación')
    E12R = dict(etiqueta='E12 · Invitación (vuelta)', src='../E12/img/IMG_20250706_210340.jpg', alt='Dedicatoria')
    E13L = dict(etiqueta='E13 · Lista de asistencia', src='../E13/img/IMG_20250627_140512.jpg', alt='Lista de asistencia')

    e09 = dict(id='E09', titulo='La bitácora de la conserjería', etapa='Etapa 2 · Lupe', orden=11,
        fuente='Cuatro fotos con flash que Mariana tomó el viernes 4 de julio de 2025 en la bodega del edificio B, que antes era la casa del conserje, de una libreta guardada en una caja de «archivo muerto».',
        nota=dict(de='Mariana', texto='Fui a dejar las cartas que faltaban. Julián, el intendente, me dejó ver la bodega… era la casa del conserje. Había cajas con libretas viejas y les tomé fotos. La directora no sabe 🙈'),
        piezas=[dict(tipo='imagen', etiqueta='Portada', src='img/IMG_20250704_120418.jpg', alt='Libreta de pasta dura negra con una etiqueta escrita a mano.', transcripcion=T_BIT['portada']),
                dict(tipo='imagen', etiqueta='Oct.-dic. 1999', src='img/IMG_20250704_120502.jpg', alt='Página de la bitácora con notas de octubre a diciembre de 1999.', transcripcion=T_BIT['p1']),
                dict(tipo='imagen', etiqueta='Marzo 2000', src='img/IMG_20250704_120531.jpg', alt='Página de la bitácora de marzo de 2000 con una nota en mayúsculas.', transcripcion=T_BIT['p2']),
                dict(tipo='imagen', etiqueta='Junio 2000', src='img/IMG_20250704_120555.jpg', alt='Página de la bitácora de junio de 2000 con dos letras distintas.', transcripcion=T_BIT['p3'])],
        comparar=[E06A, E01A, E08C, E08E],
        ayudas=[dict(tema='¿Quién escribió la bitácora?', niveles=[
                    'Compara la letra de las notas diarias con la firma de abajo y con la nota en mayúsculas del 15 de marzo.',
                    'Con «Comparar», pon una página junto a la carta de Itzel (escaneo de E06) o junto a un recadito (E08). Fíjate en las fechas con números romanos, el 7 cruzado y la forma de las letras.',
                    'Casi todas las notas las escribió la niña por su papá, el conserje J. Refugio Rangel M. Él solo firmaba y escribió la nota del 15 de marzo. Es la misma letra de la carta.']),
                dict(tema='¿Qué pasó en marzo y en junio de 2000?', niveles=[
                    'Lee la nota en mayúsculas y compárala con el diario de la maestra Chayo (E05).',
                    'Fíjate en el 16 de junio y en quién escribe después, y cómo.',
                    'El 15 de marzo le prohibieron a su hija entrar a los salones y a la clase del profe. El 16 de junio la familia entregó la casa por un cambio de trabajo y llegó otro conserje (otra letra, fechas con diagonales).'])])
    escribir(C, 'E09', e09)

    e10 = dict(id='E10', titulo='La publicación', etapa='Etapa 2 · Lupe', orden=12,
        fuente='Capturas de la publicación que Mariana hizo en Facebook el 28 de junio de 2025, con sus comentarios, tomadas el sábado 5 de julio.',
        nota=dict(de='Mariana', texto='Ya quité la foto de la carta, pero la publicación sigue. Lee los comentarios.'),
        piezas=[dict(tipo='imagen', etiqueta=f'Captura {i + 1}', src='img/' + n, alt=f'Captura {i + 1} de 2 de la publicación y sus comentarios.', transcripcion=T_FB)
                for i, n in enumerate(['Screenshot_20250705-204112.jpg', 'Screenshot_20250705-204120.jpg'])],
        ayudas=[dict(tema='¿Hay algo útil entre tanto comentario?', niveles=[
                    'Separa rumores de datos. ¿Quién habla de algo que vivió?',
                    'Fíjate en los nombres de quienes comentan y en cómo les contesta Mariana. ¿Alguno ya salió en otra evidencia?',
                    'El hijo del profe Chava ofrece información. «Lupita Rangel» defiende a la autora de la carta y Mariana le dice «maestra». El apellido Rangel ya salió en la bitácora (E09) y en el croquis de Protección Civil (E04).'])])
    escribir(C, 'E10', e10)

    mp3 = os.path.join(C, 'E11', 'audio', 'PTT-20250705-WA0019.mp3')
    e11 = dict(id='E11', titulo='La maestra Chayo se acuerda', etapa='Etapa 2 · Lupe', orden=13,
        fuente='Segunda nota de voz de la maestra Chayo a Mariana, sábado 5 de julio de 2025, después de que Mariana le contó lo de los recaditos.',
        nota=dict(de='Mariana', texto='Le conté a la maestra lo de los recaditos y me mandó esto. Se oye triste.'),
        piezas=[dict(tipo='audio', etiqueta='Nota de voz · 1:32', src='audio/PTT-20250705-WA0019.mp3', duracion='1:32', picos=picos(mp3),
                     descripcion='Audio de 1:32. La misma voz de E03, más despacio. Transcripción literal:', transcripcion=T_CHAYO2)],
        ayudas=[dict(tema='¿Qué cambia con este audio?', niveles=[
                    'Compáralo con su primer audio (E03). ¿Qué no sabía o no relacionaba entonces?',
                    '¿Qué nombre usa para la niña? ¿Quién era Don Cuco?',
                    'La maestra nunca supo el nombre «Itzel»: para ella era Lupita, la hija de Don Cuco (Refugio), el conserje. Ella dio el aviso que terminó en la prohibición.'])])
    escribir(C, 'E11', e11)

    e12 = dict(id='E12', titulo='Lo que guardaba el profe Salvador', etapa='Etapa 2 · Lupe', orden=14,
        fuente='Capturas del chat de Messenger entre Mariana y Salvador Olvera Lozano, hijo del profe Salvador «Chava» (5 a 7 de julio de 2025), y las tres fotos que él mandó el domingo 6.',
        nota=dict(de='Mariana', texto='El hijo del profe me escribió. Mira lo que encontró en las cajas de su papá.'),
        piezas=[dict(tipo='imagen', etiqueta=f'Captura {i + 1}', src='img/' + n, alt=f'Captura {i + 1} de 3 del chat con el hijo del profe Salvador.', transcripcion=T_MSG)
                for i, n in enumerate(['Screenshot_20250707-100211.jpg', 'Screenshot_20250707-100219.jpg', 'Screenshot_20250707-100304.jpg'])] + [
                dict(tipo='imagen', etiqueta='Libreta del profe', src='img/IMG_20250706_210212.jpg', alt='Página de una libreta de listas de asistencia con un renglón a lápiz al final.', transcripcion=T_LIBRETA_CHAVA),
                dict(tipo='imagen', etiqueta='Invitación (frente)', src='img/IMG_20250706_210331.jpg', alt='Invitación de graduación de una Escuela Normal, con letras doradas.', transcripcion=T_INVIT_F),
                dict(tipo='imagen', etiqueta='Invitación (vuelta)', src='img/IMG_20250706_210340.jpg', alt='Vuelta de la invitación con una dedicatoria a mano.', transcripcion=T_INVIT_R)],
        comparar=[E09P1, E06A, E02P, E13L],
        ayudas=[dict(tema='¿Qué dice la libreta del profe?', niveles=[
                    'Busca el renglón que no tiene número.',
                    'Compara sus fechas con la bitácora (E09) y con el último recadito (E08).',
                    'Lupita era oyente e hija de D. Refugio. Dejó de ir el 15 de marzo por orden de la Dirección de la mañana. El profe anotó que su acta salió el 5 de mayo de 2000.']),
                dict(tema='¿Quién es la graduada de la invitación?', niveles=[
                    'Lee el frente y la vuelta.',
                    'Compara el nombre y a los padres con la bitácora (E09). ¿Qué quiere decir «su oyente ya es maestra»?',
                    'María Guadalupe Ytzel Rangel Soto, hija de J. Refugio Rangel Muñoz: Lupita, la oyente. En 2012 se graduó de maestra de primaria. «Ytzel» es la Itzel de la carta, escrita con Y en el acta.'])])
    escribir(C, 'E12', e12)

    e13 = dict(id='E13', titulo='La lista de asistencia de la apertura', etapa='Etapa 2 · Lupe', orden=15,
        fuente='Foto que Mariana tomó en el aula 6 el viernes 27 de junio de 2025 de la hoja de registro de asistentes a la apertura. Tapó los teléfonos con el editor de su celular antes de mandarla.',
        nota=dict(de='Mariana', texto='La lista de los que firmaron el día de la apertura; la usé para mandarles las fotos a todos. Tapé los teléfonos.'),
        piezas=[dict(tipo='imagen', etiqueta='Registro de asistencia', src='img/IMG_20250627_140512.jpg', alt='Hoja impresa de registro de asistencia llenada a mano por 26 personas, con los teléfonos tapados.', transcripcion=asistencia_txt())],
        comparar=[E04C, E12F, E12R, E02P],
        ayudas=[dict(tema='¿Quién más estaba en el salón?', niveles=[
                    'Lee también a quienes no son exalumnos.',
                    'Compara esos nombres con el croquis de Protección Civil (E04) y con la invitación (E12).',
                    'La Mtra. Ma. Guadalupe Y. Rangel S., titular del 6° A vespertino, firmó la lista: estuvo en la apertura. Su firma empieza con Y.'])])
    escribir(C, 'E13', e13)

    d3 = dict(id='D3', titulo='Reconstrucción final', etapa='Etapa 2 · Lupe', orden=16,
        intro='Reconstruye lo que pasó. Puedes volver a cualquier evidencia antes de contestar. Al terminar, Mariana decidirá qué hacer con la carta.',
        preguntas=[
            dict(id='q1', tipo='unica', texto='¿Quién escribió la carta firmada «Itzel»?', opciones=[
                dict(id='a1', t='Itzayana Ibarra Delgado, alumna del 6° B.'),
                dict(id='b7', t='Óscar Mendoza, que la escribió él mismo.'),
                dict(id='c3', t='Una hija del profe Salvador Olvera que se quedaba en su clase.'),
                dict(id='e2', t='La hija del conserje, de quien nadie volvió a saber nada.'),
                dict(id='d9', t='María Guadalupe Ytzel Rangel Soto, «Lupita», la hija del conserje, que hoy es la maestra del 6° A vespertino de la misma escuela.'),
                dict(id='f4', t='Una alumna del 6° A matutino que se cambió de escuela.'),
                dict(id='g6', t='Nancy Guadalupe Guerrero, alumna del 6° B.')],
                h=[H('D3', 'q1', 'd9')]),
            dict(id='q2', tipo='unica', texto='¿Por qué dejó de ir a la clase del profe Chava en marzo de 2000?', opciones=[
                dict(id='h1', t='Porque su familia se mudó ese mes.'),
                dict(id='h2', t='Porque el profe Chava la corrió por pelearse con Óscar.'),
                dict(id='h3', t='Porque al encontrarse los recaditos, la maestra Chayo avisó a la Dirección y, como no estaba inscrita, le prohibieron entrar a los salones.'),
                dict(id='h4', t='Porque se enfermó y ya no pudo regresar.')],
                h=[H('D3', 'q2', 'h3')]),
            dict(id='q3', tipo='unica', texto='El día de la apertura, ¿dónde estaba ella?', opciones=[
                dict(id='k1', t='En otra ciudad: nunca supo de la apertura.'),
                dict(id='k2', t='En el salón: prestó el aula, escribió la bienvenida en el pintarrón y firmó la lista de asistencia.'),
                dict(id='k3', t='En su casa: se enteró días después por Facebook.'),
                dict(id='k4', t='Afuera de la escuela: mandó a alguien por la carta.')],
                h=[H('D3', 'q3', 'k2')]),
            dict(id='q4', tipo='multiple', texto='¿Qué pruebas la identifican? Marca todas las que sirven (al menos tres).', opciones=[
                dict(id='p1', t='La invitación de la Normal: «María Guadalupe Ytzel Rangel Soto», hija de J. Refugio Rangel, dedicada al profe Chava por «su oyente».'),
                dict(id='p2', t='Itzayana escribió con tinta verde.'),
                dict(id='p3', t='La lista de asistencia: «Ma. Guadalupe Y. Rangel S., docente 6° A T.V.».'),
                dict(id='p4', t='El croquis y el correo de la directora: la Mtra. Rangel, del 6° A vespertino, les prestó el aula.'),
                dict(id='p5', t='Beto recuerda que la carta se hizo en casa.'),
                dict(id='p6', t='El pintarrón: la fecha con el mes en números romanos y un gato con una O al centro, como en sus partidas.'),
                dict(id='p7', t='La bitácora: la misma letra de la carta, firmada por J. Refugio Rangel M.')],
                h=[H('D3', 'q4', x) for x in ['p1', 'p3', 'p4', 'p6', 'p7']], min=3,
                no='Alguna de las marcadas no la identifica, o faltan pruebas (al menos tres).'),
            dict(id='q5', tipo='texto', texto='¿Cómo se llama hoy, tal como aparece en sus papeles?', placeholder='Nombre y apellido', nota='Basta con nombre y apellido paterno.',
                 grupos=[[TOK('rangel')], [TOK(x) for x in ['guadalupe', 'lupita', 'lupe', 'ytzel', 'itzel', 'maria']]])],
        exito=dict(titulo='Itzel estuvo ahí todo el tiempo', mensajes=[
            dict(de='Mariana', texto='La maestra Lupita… Nos prestó SU salón. Nos escribió «Esta sigue siendo su casa». Y yo leyendo su carta en voz alta delante de todos 😔'),
            dict(de='Mariana', texto='Ya borré la publicación. En el grupo no voy a decir nada. Le voy a llevar a Óscar su carta… y el nombre. Lo demás le toca a ellos.'),
            dict(de='Mariana', texto='(Una semana después) Óscar vino a Ags. La directora nos dejó entrar al salón a las 12:30. Hoy me mandó esto.')],
            cierre='<a class="btn" style="display:inline-block;text-decoration:none;margin-top:6px" href="../E14/index.html">Ver el epílogo</a>'),
        ayudas=[dict(tema='Pregunta 1', niveles=['Junta la bitácora (E09), la libreta del profe y la invitación (E12).', 'Busca ese mismo nombre en el croquis (E04) y en la lista de asistencia (E13).', 'Es Ma. Guadalupe Ytzel Rangel Soto, Lupita, hija del conserje: la maestra del 6° A vespertino que les prestó el aula.']),
                dict(tema='Preguntas 2 y 3', niveles=['Diario de la maestra (E05), bitácora (E09) y segunda nota de voz (E11).', '¿Quién escribió en el pintarrón (E02) y quién firmó la lista (E13)?', 'Dejó de ir por la prohibición tras el aviso de la maestra Chayo; el día de la apertura estuvo en el aula.']),
                dict(tema='Preguntas 4 y 5', niveles=['Solo sirven las pruebas que dicen algo de ella, no de otras personas.', 'Nombre completo en la invitación; «Y.» en la lista; «Rangel» en el croquis y la bitácora.', 'María Guadalupe Ytzel Rangel Soto.'])])
    escribir(C, 'D3', d3, DEDUC, 'DEDUCCION')

    e14 = dict(id='E14', titulo='Epílogo: la canastilla', etapa='Epílogo', orden=17,
        fuente='Foto que Óscar le mandó a Mariana el viernes 11 de julio de 2025 a las 12:38, desde el aula 6.',
        nota=dict(de='Mariana', texto='Óscar dejó un papelito ayer en la canastilla del mesabanco junto a la ventana. Hoy regresó a ver.'),
        piezas=[dict(tipo='imagen', etiqueta='El papelito', src='img/IMG_20250711_123844.jpg', alt='Hoja de libreta doblada en cuatro sobre un mesabanco, con dos letras distintas y un juego de gato.', transcripcion=T_EPI)])
    escribir(C, 'E14', e14)
    return [e09, e10, e11, e12, e13, d3, e14]

if __name__ == '__main__':
    todo = muestra() + etapa1() + etapa2()
    print('Páginas:', [x['id'] for x in todo])

# ======================================================================= MANIFEST
DUR = {'E01': [2, 3], 'E02': [3, 4], 'E03': [2, 2], 'E04': [1, 2], 'D1': [1, 1], 'E05': [5, 6], 'E06': [5, 6], 'E07': [3, 4], 'E08': [6, 8], 'D2': [2, 2],
       'E09': [5, 6], 'E10': [3, 4], 'E11': [2, 3], 'E12': [4, 5], 'E13': [2, 3], 'D3': [5, 8], 'E14': [1, 2]}
INTER = {'E01': ['zoom', 'anverso-reverso', 'espejo', 'realce', 'comparar'], 'E02': ['capturas', 'zoom', 'comparar', 'realce'], 'E03': ['audio', 'velocidad', 'transcripcion'],
         'E04': ['zoom', 'comparar'], 'D1': ['deduccion'], 'E05': ['zoom', 'comparar', 'realce'], 'E06': ['superponer-calca', 'espejo', 'zoom', 'comparar'],
         'E07': ['capturas', 'zoom'], 'E08': ['ordenar', 'zoom', 'comparar'], 'D2': ['deduccion', 'texto-libre'], 'E09': ['zoom', 'comparar-letra', 'realce'],
         'E10': ['capturas', 'zoom'], 'E11': ['audio', 'velocidad', 'transcripcion'], 'E12': ['capturas', 'zoom', 'comparar'], 'E13': ['zoom', 'comparar'],
         'D3': ['deduccion', 'texto-libre'], 'E14': ['zoom']}
ETAPA = {'Muestra': 'muestra', 'Etapa 1 · El de la mañana': 'etapa1', 'Etapa 2 · Lupe': 'etapa2', 'Epílogo': 'epilogo'}

def manifest(todo):
    piezas = []
    for cfg in todo:
        paquete = 'gratis' if cfg['id'] in ('E01', 'E02', 'E03', 'E04', 'D1') else 'completo'
        base = 'JUGADOR_GRATIS' if paquete == 'gratis' else 'JUGADOR_COMPLETO'
        rec, ext = [], []
        for p in cfg.get('piezas', []):
            for k in ('src', 'mini'):
                if p.get(k): rec.append(f"{base}/{cfg['id']}/{p[k]}")
            for it in p.get('items', []):
                rec += [f"{base}/{cfg['id']}/{it['src']}", f"{base}/{cfg['id']}/{it['mini']}"]
        if cfg.get('superponer'):
            rec += [f"{base}/{cfg['id']}/{b['src']}" for b in cfg['superponer']['bases']] + [f"{base}/{cfg['id']}/{cfg['superponer']['capa']['src']}"]
        for c_ in cfg.get('comparar', []):
            path = os.path.normpath(os.path.join(base, cfg['id'], c_['src'])).replace(os.sep, '/')
            ext.append(path)
        deps = sorted({x.split('/')[1] for x in ext})
        prim = next((p for p in cfg.get('piezas', []) if p.get('tipo') == 'imagen'), None)
        mini_ = f"{base}/{cfg['id']}/{prim['src']}" if prim else None
        piezas.append(dict(id=cfg['id'], tipo='deduccion' if cfg['id'].startswith('D') else 'evidencia', titulo=cfg['titulo'],
                           etapa=ETAPA[cfg['etapa']], orden=cfg['orden'], paquete=paquete, ruta=f"{base}/{cfg['id']}/index.html",
                           miniatura=mini_, recursos=sorted(set(rec)), recursos_de_otras_piezas=sorted(set(ext)), dependencias=deps,
                           interaccion=INTER[cfg['id']], duracion_estimada_min=DUR[cfg['id']]))
    m = dict(caso=dict(id='la-carta-35', titulo='La carta 35', idioma='es-MX', version='1.0.0',
                       pregunta='¿Quién es Itzel?', duracion_estimada_min=[60, 75], muestra_estimada_min=[9, 12],
                       sinopsis='Junio de 2025, Aguascalientes. Los exalumnos del 6° B abren la cápsula del tiempo que enterraron en 2000. Eran 34 alumnos y hay 34 sobres, pero al fondo de la caja aparece una hoja más, sin sobre, firmada por «Itzel». Nadie la recuerda.',
                       advertencia='Caso de ficción. Personas, escuelas, colonia y documentos son inventados; Aguascalientes es real.'),
             runtime=dict(css='COMUN/visor.css', js_evidencia=['COMUN/sha256.js', 'COMUN/visor.js'], js_deduccion=['COMUN/sha256.js', 'COMUN/deduccion.js'],
                          evento_deduccion={'origen': 'window.parent.postMessage', 'datos': {'tipo': 'lc35:deduccion', 'id': 'D1|D2|D3', 'ok': True}},
                          nota='Las evidencias leen su configuración de window.EVIDENCIA dentro de su index.html. No requieren servidor ni red.'),
             etapas=[dict(id='muestra', titulo='Muestra gratuita', acceso='gratis', requiere=[], piezas=['E01', 'E02', 'E03', 'E04', 'D1']),
                     dict(id='etapa1', titulo='El de la mañana', acceso='pago', requiere=['compra', 'D1'], piezas=['E05', 'E06', 'E07', 'E08', 'D2']),
                     dict(id='etapa2', titulo='Lupe', acceso='pago', requiere=['compra', 'D2'], piezas=['E09', 'E10', 'E11', 'E12', 'E13', 'D3']),
                     dict(id='epilogo', titulo='Epílogo', acceso='pago', requiere=['compra', 'D3'], piezas=['E14'])],
             piezas=piezas)
    os.makedirs(os.path.join(ROOT, 'INTEGRACION'), exist_ok=True)
    json.dump(m, open(os.path.join(ROOT, 'INTEGRACION', 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # copia para la vista local (funciona con file://, sin fetch)
    open(os.path.join(ROOT, 'VISTA_LOCAL', 'manifest_local.js'), 'w', encoding='utf-8').write('window.MANIFEST = ' + json.dumps(m, ensure_ascii=False) + ';\n')
    return m

if __name__ == '__main__':
    mm = manifest(todo)
    print('manifest:', len(mm['piezas']), 'piezas')
