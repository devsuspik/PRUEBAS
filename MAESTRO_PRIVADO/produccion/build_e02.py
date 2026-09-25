"""E02 · Fotos que circularon en el grupo de WhatsApp (27-28 jun 2025)."""
import sys, os
sys.path.insert(0, 'lib')
from photo import *
from PIL import Image, ImageOps

ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_GRATIS', 'E02', 'img')
os.makedirs(OUT, exist_ok=True)
PRIV = '_render'

def carta_6b(kid, seed, stains=(), wrinkle=0.05):
    im = Image.open(f'{PRIV}/c_{kid}.png').convert('RGBA')
    im = photocopy_marks(im, seed)
    im = rough_edges(im, 1.0, seed + 1)
    return paper_effects(im, folds=[('h', 1 / 3), ('h', 2 / 3)], stains=stains, wrinkle=wrinkle,
                         tint=(250, 247, 238), seed=seed + 2, edge_dirt=0.2, crease_strength=1.1)

def foto_mesa(obj, name, seed, ang, persp, temp=(1.03, 1.0, 0.94), blob=None, size=(1200, 1600), q=74):
    bg = tex_wood(3400, 2600, seed=seed, base=(96, 64, 44))
    c = place(bg, obj, 1300, 1700, ang, 1.0, (18, 26, 26, 0.5))
    c = perspective(c, *persp, fill=(40, 30, 22))
    c = lighting(c, direction=(-0.8, -0.5), strength=0.22, temp=temp, vignette=0.2, blob=blob, seed=seed)
    c = c.crop((120, 220, 2480, 3367))
    c = camera(c, blur=1.0, noise=3.5, out_size=size, seed=seed)
    c = recompress(c, 80)
    jpeg(c, os.path.join(OUT, name), q=q)
    return c

def pintarron():
    sc = Image.open(f'{PRIV}/pintarron.png').convert('RGB')
    w, h = sc.size
    a = np.asarray(sc, np.float32)
    n = fnoise(h, w, 24, 4, 91)
    n2 = fnoise(h, w, 300, 3, 94)
    a *= (1 + 0.05 * (n - 0.5) + 0.06 * (n2 - 0.5))[..., None]
    sc = to_img(a)
    sc = perspective(sc, (40, 90), (-10, 0), (-30, -10), (90, -120), fill=(200, 190, 170))
    sc = lighting(sc, direction=(0.4, -1.0), strength=0.22, temp=(0.97, 1.0, 1.04), vignette=0.30,
                  blob=(0.55, 0.95, 0.35, 0.08), seed=92)
    a = np.asarray(sc, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glare = np.exp(-(((xx - 0.44 * w) / (0.16 * w)) ** 2 + ((yy - 0.23 * h) / (0.07 * h)) ** 2))
    a = a + glare[..., None] * 36
    sc = to_img(a).crop((150, 150, 1960, 1030))
    sc = camera(sc, blur=1.2, noise=3.2, out_size=(1600, 765), seed=93)
    sc = recompress(sc, 78)
    jpeg(sc, os.path.join(OUT, 'IMG-20250627-WA0012.jpg'), q=76)

def lista_chayo():
    obj = Image.open(f'{PRIV}/chayo_lista.png').convert('RGBA')
    obj = paper_effects(obj, wrinkle=0.03, tint=(250, 246, 234), seed=120, edge_dirt=0.15)
    bg = tex_cloth(3300, 2700, seed=121, base=(222, 208, 186))
    c = place(bg, obj, 1350, 1640, -3.0, 1.0, (10, 16, 18, 0.45))
    c = perspective(c, (80, 60), (-160, 140), (-40, 0), (60, -20), fill=(60, 50, 40))
    c = lighting(c, direction=(-0.2, -1.0), strength=0.35, temp=(1.10, 1.0, 0.80), vignette=0.35,
                 blob=(0.95, 0.75, 0.4, 0.28), seed=122)
    c = c.crop((200, 260, 2500, 3220))
    c = camera(c, blur=1.6, noise=5.5, out_size=(1200, 1544), seed=123, chroma_noise=2.2)
    c = recompress(c, 72, 2)
    jpeg(c, os.path.join(OUT, 'IMG-20250627-WA0031.jpg'), q=72)

def itzel_wa():
    im = Image.open(os.path.join(ROOT, 'JUGADOR_GRATIS', 'E01', 'img', 'IMG_20250627_134112.jpg'))
    im = im.resize((1200, 1600), Image.LANCZOS)
    im = recompress(im, 78)
    jpeg(im, os.path.join('_render', 'IMG-20250627-WA0014.jpg'), q=76)  # solo para componer la captura

if __name__ == '__main__':
    pintarron()
    lista_chayo()
    itzel_wa()
    foto_mesa(carta_6b('itza', 140), 'IMG-20250627-WA0016.jpg', 141, 2.2, ((20, 40), (-60, 30), (0, 0), (40, 0)))
    foto_mesa(carta_6b('beto', 150, stains=[dict(x=0.2, y=1.12, r=0.30, sx=2.6, a=0.22, rough=0.55)]),
              'IMG-20250627-WA0021.jpg', 151, -1.4, ((60, 20), (0, 60), (-30, 0), (0, 0)))
    foto_mesa(carta_6b('karla', 160), 'IMG-20250627-WA0022.jpg', 161, 0.8, ((0, 30), (-40, 0), (0, 0), (30, 20)))
    print('E02 fotos listas')

def capturas():
    names = ['Screenshot_20250628-171204.jpg', 'Screenshot_20250628-171211.jpg', 'Screenshot_20250628-171219.jpg',
             'Screenshot_20250628-171302.jpg', 'Screenshot_20250628-171309.jpg', 'Screenshot_20250628-171316.jpg']
    for i, n in enumerate(names):
        im = Image.open(f'{PRIV}/wa_grupo_{i + 1}.png').convert('RGB').crop((1, 0, 1081, 2399))
        jpeg(im, os.path.join(OUT, n), q=88, subsampling=0)

if __name__ == '__main__':
    capturas()
