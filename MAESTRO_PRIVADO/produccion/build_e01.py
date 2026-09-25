"""E01 · Carta sin sobre: fotos del celular de Mariana (anverso y reverso) en el aula 6.
También produce las piezas planas que reutiliza E06 (escaneo del reverso y la calca)."""
import sys, os
import numpy as np
from PIL import Image, ImageFilter, ImageOps
sys.path.insert(0, 'lib')
from photo import *

ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_GRATIS', 'E01', 'img')
PRIV = '_render'
os.makedirs(OUT, exist_ok=True)

S = 2  # dpr del render: 96 px/cm
W, H = 984 * S, 1296 * S
PANEL = 432 * S

# ---------------------------------------------------------------- calca verde
FUERZA = 1.0
def calca_oscar():
    """Tinta verde de la carta de Óscar transferida por humedad (en espejo) sobre el
    panel superior del reverso de la hoja de Itzel. Devuelve RGBA de W x PANEL."""
    t = Image.open(f'{PRIV}/c_oscar_texto.png').convert('RGBA')
    # zona de contacto: renglones 4-5 de la carta de Óscar (y 800..1232 css), x 30..1014
    box = (30 * S, 800 * S, 30 * S + W, 800 * S + PANEL)
    c = t.crop(box)
    c = ImageOps.mirror(c)
    a = np.asarray(c, np.float32)
    al = a[..., 3] / 255.0
    h, w = al.shape
    # transferencia irregular: mucha donde había agua (abajo y a la derecha del panel), poca arriba
    n = fnoise(h, w, 150, 4, 777)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grad = 0.35 + 0.65 * (yy / h) ** 0.8
    m = np.clip((n * 1.35 + grad * 0.45 - 0.86) * 2.6, 0, 1)
    speck = fnoise(h, w, 6, 2, 778)
    m *= np.clip(0.55 + speck, 0, 1)
    # la tinta se corre: difuminado y halo
    al_img = Image.fromarray((al * 255).astype(np.uint8))
    bleed = np.asarray(al_img.filter(ImageFilter.GaussianBlur(5.5)), np.float32) / 255
    core = np.asarray(al_img.filter(ImageFilter.GaussianBlur(1.7)), np.float32) / 255
    alpha = np.clip(core * 0.40 + bleed * 0.34, 0, 1) * m * FUERZA
    col = np.zeros((h, w, 4), np.float32)
    col[..., 0], col[..., 1], col[..., 2] = 84, 152, 124
    col[..., 3] = alpha * 255
    return Image.fromarray(col.astype(np.uint8), 'RGBA')

def hoja(cara):
    im = Image.open(f'{PRIV}/itzel_{cara}.png').convert('RGBA')
    if cara == 'reverso':
        g = calca_oscar()
        base = im.copy()
        base.alpha_composite(g, (0, 0))
        im = base
    # orilla arrancada del espiral: izquierda en el anverso, derecha en el reverso
    im = torn_left_edge(im, depth=26, seed=301, side='left' if cara == 'anverso' else 'right')
    im = rough_edges(im, 1.2, seed=302)
    stains = [dict(x=0.52 if cara == 'anverso' else 0.48, y=1.10, r=0.46, sx=2.3, sy=1.0, a=0.30, col=(168, 138, 88), rough=0.6),
              dict(x=0.90 if cara == 'anverso' else 0.10, y=0.98, r=0.10, a=0.18, col=(160, 130, 90))]
    im = paper_effects(im, folds=[('h', 1 / 3), ('h', 2 / 3)], stains=stains, wrinkle=0.05,
                       tint=(252, 248, 238), seed=303, edge_dirt=0.25, crease_strength=1.25)
    return im

def foto_mesabanco(obj, seed, ang, persp, name, blob):
    bg = tex_laminate(3300, 2560, seed=seed, base=(214, 186, 144))
    # la paleta del mesabanco termina: franja de metal/plástico gris al borde inferior
    bgc = place(bg, obj, 1270, 1620, ang, 1.0, (14, 20, 22, 0.42))
    bgc = perspective(bgc, *persp, fill=(60, 50, 40))
    bgc = lighting(bgc, direction=(0.5, -0.9), strength=0.16, temp=(0.985, 1.0, 1.035), vignette=0.18, blob=blob, seed=seed)
    bgc = bgc.crop((160, 180, 2400, 3160))
    bgc = camera(bgc, blur=0.9, noise=3.2, out_size=(1536, 2048), seed=seed)
    jpeg(bgc, os.path.join(OUT, name), q=84)

if __name__ == '__main__':
    an = hoja('anverso'); an.save(f'{PRIV}/itzel_anverso_obj.png')
    re_ = hoja('reverso'); re_.save(f'{PRIV}/itzel_reverso_obj.png')
    foto_mesabanco(an, 11, 1.6, ((40, 30), (-30, 10), (10, 0), (0, 0)), 'IMG_20250627_134112.jpg', (0.85, 1.02, 0.35, 0.22))
    foto_mesabanco(re_, 12, -2.1, ((0, 20), (-50, 40), (0, 0), (20, 0)), 'IMG_20250627_134127.jpg', (0.1, 1.05, 0.30, 0.20))
    print('E01 listo')
