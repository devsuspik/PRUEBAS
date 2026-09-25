"""E06 · Relación de apertura (foto) y escaneos de Mariana (2-VII-2025): cartas #19, #20, #21
y la hoja de Itzel por ambos lados. Todos los escaneos comparten escala para poder superponerlos."""
import sys, os, json
sys.path.insert(0, 'lib')
from photo import *
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np

ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E06', 'img')
os.makedirs(OUT, exist_ok=True)
PRIV = '_render'
S = 2
PAD = 40
ESC = 0.6  # escala final de todos los escaneos
W_IT, PANEL = 984 * S, 432 * S

def mojar_tinta(ink, seed, fuerza=1.0, zona=0.35):
    """Tinta de gel corrida por el agua en la parte baja de la hoja (zona = fracción desde arriba donde empieza)."""
    a = np.asarray(ink, np.float32)
    h, w = a.shape[:2]
    al = a[..., 3] / 255
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    n = fnoise(h, w, 160, 3, seed)
    wet = np.clip(((yy / h - zona) * 3 + (n - 0.5) * 0.9) * fuerza, 0, 1)
    img = Image.fromarray((al * 255).astype(np.uint8))
    b1 = np.asarray(img.filter(ImageFilter.GaussianBlur(3.6)), np.float32) / 255
    b2 = np.asarray(img.filter(ImageFilter.GaussianBlur(11)), np.float32) / 255
    al2 = al * (1 - 0.62 * wet) + b1 * 0.75 * wet + b2 * 0.45 * wet
    out = a.copy()
    out[..., 3] = np.clip(al2, 0, 1) * 255
    # la tinta lavada se aclara
    out[..., :3] = out[..., :3] * (1 - 0.25 * wet[..., None]) + np.array([120, 190, 160]) * 0.25 * wet[..., None]
    return Image.fromarray(out.astype(np.uint8), 'RGBA')

def hoja_oscar():
    base = Image.open(f'{PRIV}/c_oscar_plantilla.png').convert('RGBA')
    base = photocopy_marks(base, 610)
    ink = mojar_tinta(Image.open(f'{PRIV}/c_oscar_texto.png').convert('RGBA'), 611, 1.0, 0.42)
    base.alpha_composite(ink)
    base = rough_edges(base, 1.0, 612)
    st = [dict(x=0.5, y=1.18, r=0.55, sx=2.2, a=0.34, rough=0.6, col=(160, 150, 100)),
          dict(x=0.35, y=0.98, r=0.36, sx=2.5, a=0.26, rough=0.7, col=(150, 140, 95))]
    return paper_effects(base, folds=[('h', 1 / 3), ('h', 2 / 3)], stains=st, wrinkle=0.06, tint=(248, 246, 236), seed=613, edge_dirt=0.3, crease_strength=1.3)

def hoja_6b(kid, seed, st):
    im = Image.open(f'{PRIV}/c_{kid}.png').convert('RGBA')
    im = photocopy_marks(im, seed)
    im = rough_edges(im, 1.0, seed + 1)
    return paper_effects(im, folds=[('h', 1 / 3), ('h', 2 / 3)], stains=st, wrinkle=0.05, tint=(249, 246, 237), seed=seed + 2, edge_dirt=0.25, crease_strength=1.2)

def escanear(obj, nombre, seed):
    sc = scan(obj, pad=PAD, bg=(244, 244, 241), skew=0.0, seed=seed, dust=60, dpi_blur=0.5)
    sc = ImageEnhance.Contrast(sc).enhance(1.08)
    sc = sc.resize((int(sc.width * ESC), int(sc.height * ESC)), Image.LANCZOS)
    jpeg(sc, os.path.join(OUT, nombre), q=86)
    return sc

def libreta():
    obj = Image.open(f'{PRIV}/mariana_libreta.png').convert('RGBA')
    obj = paper_effects(obj, wrinkle=0.03, seed=620, edge_dirt=0.1)
    bg = tex_wood(3300, 2600, seed=621, base=(96, 64, 44))
    c = place(bg, obj, 1300, 1650, 1.8, 1.0, (16, 22, 24, 0.5))
    c = perspective(c, (30, 60), (-90, 20), (0, 0), (50, 0), fill=(40, 30, 22))
    c = lighting(c, direction=(0.6, -0.7), strength=0.2, temp=(1.05, 1.0, 0.9), vignette=0.25, blob=(0.9, 0.2, 0.3, 0.15), seed=622)
    c = c.crop((160, 200, 2440, 3240))
    c = camera(c, blur=0.9, noise=3.4, out_size=(1536, 2048), seed=623)
    jpeg(c, os.path.join(OUT, 'IMG_20250702_203015.jpg'), q=82)

if __name__ == '__main__':
    libreta()
    escanear(hoja_6b('eduardo', 630, [dict(x=0.6, y=1.15, r=0.45, sx=2.4, a=0.28, rough=0.6)]), 'Escaneo_0031.jpg', 631)
    escanear(hoja_oscar(), 'Escaneo_0032.jpg', 632)
    escanear(hoja_6b('gaby', 640, [dict(x=0.4, y=1.2, r=0.5, sx=2.2, a=0.26, rough=0.6)]), 'Escaneo_0033.jpg', 641)
    rev = Image.open(f'{PRIV}/itzel_reverso_obj.png').convert('RGBA')
    ana = Image.open(f'{PRIV}/itzel_anverso_obj.png').convert('RGBA')
    sc_rev = escanear(rev, 'Escaneo_0034.jpg', 650)
    escanear(ana, 'Escaneo_0035.jpg', 651)
    # capa para la herramienta de superposición: tercio superior del reverso escaneado (misma escala)
    x0, y0 = int(PAD * ESC), int(PAD * ESC)
    capa = sc_rev.crop((x0, y0, x0 + int(W_IT * ESC), y0 + int(PANEL * ESC)))
    jpeg(capa, os.path.join(OUT, 'capa_reverso_tercio_superior.jpg'), q=88)
    # posición correcta (privada) de la capa en espejo sobre el escaneo de Óscar
    pos = [round((PAD + 30 * S) * ESC), round((PAD + 800 * S) * ESC)]
    json.dump({'capa_en_espejo_sobre_Escaneo_0032': pos}, open(f'{PRIV}/calca_pos.json', 'w'))
    print('E06 listo; posición correcta', pos)
