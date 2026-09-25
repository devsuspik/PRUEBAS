"""E13 · Foto de la lista de asistencia (27-VI-2025, Mariana, en el aula 6).
E14 · Epílogo: foto de Óscar del papelito en el mesabanco (11-VII-2025)."""
import sys, os
sys.path.insert(0, 'lib')
from photo import *
ROOT = os.path.abspath('../..')

def geom(img, W, H, ang, persp, out, fill):
    """Solo la geometría de la toma (para máscaras de edición digital)."""
    c = Image.new('RGB', (W, H), fill)
    c.paste(img.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=fill),
            (int(W / 2 - img.rotate(ang, expand=True).width / 2), int(H / 2 - img.rotate(ang, expand=True).height / 2)))
    c = perspective(c, *persp, fill=fill)
    mx, my = int(W * 0.05), int(H * 0.05)
    return c.crop((mx, my, W - mx, H - my)).resize(out, Image.LANCZOS)

def tapar(foto, mascara):
    """Rectángulos negros dibujados con el editor del teléfono sobre cada zona marcada."""
    m = np.asarray(mascara.convert('L')) < 128
    from PIL import ImageDraw
    d = ImageDraw.Draw(foto)
    vis = np.zeros_like(m)
    H, W = m.shape
    ys, xs = np.nonzero(m)
    # componentes por filas: agrupa por bandas horizontales
    rows = np.unique(ys)
    bandas, ini = [], rows[0]
    for a, b in zip(rows[:-1], rows[1:]):
        if b - a > 3: bandas.append((ini, a)); ini = b
    bandas.append((ini, rows[-1]))
    for y0, y1 in bandas:
        sel = (ys >= y0) & (ys <= y1)
        x0, x1 = xs[sel].min(), xs[sel].max()
        d.rectangle([x0 - 6, y0 - 5, x1 + 8, y1 + 5], fill=(8, 8, 8))
    return foto

def foto_mesa(render, dst, seed, ang, persp, folds=(), W=2700, H=3400, out=(1536, 2048), edge=0.1, obj_scale=1.0, mascara=None):
    obj = Image.open(f'_render/{render}.png').convert('RGBA')
    obj = paper_effects(obj, folds=folds, wrinkle=0.04, tint=(252, 250, 244), seed=seed, edge_dirt=edge, crease_strength=0.9)
    obj = rough_edges(obj, 0.8, seed + 1)
    bg = tex_laminate(H, W, seed=seed + 2, base=(214, 186, 144))
    c = place(bg, obj, W / 2, H / 2, ang, obj_scale, (14, 20, 22, 0.42))
    c = perspective(c, *persp, fill=(60, 50, 40))
    c = lighting(c, direction=(0.5, -0.9), strength=0.16, temp=(0.985, 1.0, 1.035), vignette=0.18, blob=(0.9, 1.0, 0.3, 0.18), seed=seed + 3)
    mx, my = int(W * 0.05), int(H * 0.05)
    c = c.crop((mx, my, W - mx, H - my))
    c = camera(c, blur=0.9, noise=3.2, out_size=out, seed=seed + 4)
    if mascara:
        mk = Image.open(f'_render/{mascara}.png').convert('RGB')
        c = tapar(c, geom(mk, W, H, ang, persp, out, (255, 255, 255)))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    jpeg(c, dst, q=84)

foto_mesa('asistencia', os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E13', 'img', 'IMG_20250627_140512.jpg'), 1310, -1.2,
          ((40, 60), (-80, 20), (0, 0), (40, 0)), W=2500, H=3100, mascara='asistencia_mascara')
foto_mesa('epilogo', os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E14', 'img', 'IMG_20250711_123844.jpg'), 1410, 3.5,
          ((30, 30), (-40, 20), (0, 0), (20, 0)), folds=[('h', .5), ('v', .5)], W=1900, H=2300, out=(1200, 1452), edge=0.2)
print('E13 y E14 listos')
