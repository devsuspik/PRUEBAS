"""E12 · Fotos del hijo del profe Chava (6-VII-2025): libreta de listas e invitación (frente y vuelta),
sobre su escritorio, con lámpara."""
import sys, os
sys.path.insert(0, 'lib')
from photo import *
ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E12', 'img')
os.makedirs(OUT, exist_ok=True)

def foto(render, name, seed, ang, persp, W, H, glare=0.0, edge=0.3, out=(1440, 1100)):
    obj = Image.open(f'_render/{render}.png').convert('RGBA')
    obj = paper_effects(obj, wrinkle=0.03, tint=(250, 246, 236), seed=seed, edge_dirt=edge)
    obj = rough_edges(obj, 0.8, seed + 1)
    bg = tex_wood(H, W, seed=seed + 2, base=(70, 46, 32))
    c = place(bg, obj, W / 2, H / 2, ang, 1.0, (14, 18, 20, 0.55))
    c = perspective(c, *persp, fill=(30, 22, 16))
    c = lighting(c, direction=(-0.9, -0.3), strength=0.35, temp=(1.1, 1.0, 0.82), vignette=0.35, blob=(0.95, 0.9, 0.3, 0.2), seed=seed + 3)
    if glare:
        a = np.asarray(c, np.float32); h, w = a.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        g = np.exp(-(((xx - w * 0.38) / (w * 0.10)) ** 2 + ((yy - h * 0.3) / (h * 0.16)) ** 2))
        c = to_img(a + g[..., None] * glare)
    mx, my = int(W * 0.06), int(H * 0.06)
    c = c.crop((mx, my, W - mx, H - my))
    c = camera(c, blur=1.0, noise=4.0, out_size=out, seed=seed + 4)
    c = recompress(c, 78)
    jpeg(c, os.path.join(OUT, name), q=80)
    t = c.copy(); t.thumbnail((520, 520)); jpeg(t, os.path.join(OUT, 'mini_' + name), q=80)

foto('chava_libreta', 'IMG_20250706_210212.jpg', 1210, 1.2, ((20, 30), (-50, 10), (0, 0), (30, 0)), 2600, 2000, out=(1500, 1154))
foto('invit_frente', 'IMG_20250706_210331.jpg', 1220, -2.5, ((30, 50), (-60, 20), (0, 0), (40, 0)), 1900, 2500, glare=26, edge=0.15, out=(1152, 1500))
foto('invit_reverso', 'IMG_20250706_210340.jpg', 1230, 1.8, ((10, 30), (-40, 40), (0, 0), (30, 0)), 1900, 2500, glare=18, edge=0.15, out=(1152, 1500))
print('E12 fotos listas')
