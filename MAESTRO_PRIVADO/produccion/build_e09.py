"""E09 · Fotos con flash de la bitácora de la conserjería, en la bodega (4-VII-2025, Mariana)."""
import sys, os
sys.path.insert(0, 'lib')
from photo import *
ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E09', 'img')
os.makedirs(OUT, exist_ok=True)

def foto_flash(pag, name, seed, ang, persp):
    obj = Image.open(f'_render/bitacora_{pag}.png').convert('RGBA')
    if pag != 'portada':
        obj = paper_effects(obj, stains=[dict(x=0.95, y=0.05, r=0.22, a=0.2, rough=0.7, col=(165, 140, 95))], wrinkle=0.04,
                            tint=(246, 238, 218), seed=seed, edge_dirt=0.6)
    else:
        obj = paper_effects(obj, wrinkle=0.08, seed=seed, edge_dirt=0.2)
    obj = rough_edges(obj, 1.0, seed + 1)
    bg = tex_cardboard(2900, 2400, seed=seed + 2)
    # polvo sobre la caja
    a = np.asarray(bg, np.float32); n = fnoise(a.shape[0], a.shape[1], 12, 2, seed + 3)
    a = a * (1 + 0.1 * (n - 0.5))[..., None] + (n[..., None] > 0.72) * 18
    bg = to_img(a)
    c = place(bg, obj, 1200, 1450, ang, 1.0, (6, 8, 6, 0.55))
    c = perspective(c, *persp, fill=(90, 70, 50))
    # flash del celular: centro quemado, caída fuerte a las orillas, luz fría
    c = lighting(c, direction=(0, 0), strength=0.0, temp=(0.98, 1.0, 1.05), vignette=0.55, seed=seed + 4)
    a = np.asarray(c, np.float32); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hot = np.exp(-(((xx - w * 0.52) / (w * 0.22)) ** 2 + ((yy - h * 0.45) / (h * 0.2)) ** 2))
    a = a * (1 + 0.18 * hot[..., None]) + 22 * hot[..., None]
    c = to_img(a).crop((200, 230, 2200, 2700))
    c = camera(c, blur=0.9, noise=4.5, out_size=(1440, 1778), seed=seed + 5)
    jpeg(c, os.path.join(OUT, name), q=80)

foto_flash('portada', 'IMG_20250704_120418.jpg', 910, -4, ((30, 20), (-40, 60), (0, 0), (20, 0)))
foto_flash('p1', 'IMG_20250704_120502.jpg', 920, 1.5, ((20, 50), (-70, 20), (0, 0), (40, 0)))
foto_flash('p2', 'IMG_20250704_120531.jpg', 930, -1.0, ((50, 20), (-30, 70), (-20, 0), (10, 0)))
foto_flash('p3', 'IMG_20250704_120555.jpg', 940, 2.2, ((10, 40), (-60, 30), (0, 0), (50, 10)))
print('E09 listo')
