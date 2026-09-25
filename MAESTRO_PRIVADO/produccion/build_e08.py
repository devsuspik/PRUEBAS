"""E08 · Recaditos fotografiados por la mamá de Óscar sobre el hule de la cocina (3-VII-2025).
Llegan revueltos: el orden de los archivos NO es el cronológico."""
import sys, os, json
sys.path.insert(0, 'lib')
from photo import *
ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E08', 'img')
os.makedirs(OUT, exist_ok=True)
# orden en que llegaron (WA0021..WA0028) -> recado
LLEGADA = ['D', 'H', 'A', 'F', 'C', 'G', 'B', 'E']
FOLDS = {'A': [('h', .5), ('v', .5)], 'B': [('h', .5), ('v', 1 / 3), ('v', 2 / 3)], 'C': [('h', .5), ('v', .5), ('v', .25)],
         'D': [('h', .5), ('v', .5)], 'E': [('h', .5), ('v', .5), ('v', .75)], 'F': [('h', .5), ('v', .5)],
         'G': [('h', .5), ('v', .5), ('v', .25)], 'H': [('h', 1 / 3), ('h', 2 / 3), ('v', .5)]}
TORN = {'A': 'left', 'B': None, 'C': 'left', 'D': 'right', 'E': 'left', 'F': 'right', 'G': 'left', 'H': 'left'}

def recado(r, seed):
    im = Image.open(f'_render/recado_{r}.png').convert('RGBA')
    if TORN[r]:
        im = torn_left_edge(im, depth=22, seed=seed, side=TORN[r])
    im = rough_edges(im, 1.6, seed + 1)
    st = [dict(x=0.8, y=0.15, r=0.25, a=0.10, rough=0.7)] if r == 'D' else []
    return paper_effects(im, folds=FOLDS[r], stains=st, wrinkle=0.08, tint=(248, 243, 228), seed=seed + 2, edge_dirt=0.35, crease_strength=1.5)

hule = Image.open('_render/hule.png').convert('RGB')
res = {}
for i, r in enumerate(LLEGADA):
    seed = 800 + i * 10
    obj = recado(r, seed)
    bg = hule.copy().resize((2600, 2000))
    a = np.asarray(bg, np.float32)
    n = fnoise(a.shape[0], a.shape[1], 300, 3, seed)
    a *= (1 + 0.06 * (n - 0.5))[..., None]
    bg = to_img(a)
    ang = [-6, 4, -2.5, 7, -3.5, 2, -8, 5][i]
    c = place(bg, obj, 1300 + (i % 3 - 1) * 60, 1000 + (i % 2) * 40, ang, 1.0, (10, 14, 16, 0.5))
    c = perspective(c, (40 + i * 5, 30), (-60, 50 - i * 4), (-10, 0), (30, -10), fill=(200, 190, 170))
    c = lighting(c, direction=(-0.5, -0.8), strength=0.3, temp=(1.12, 1.0, 0.78), vignette=0.35, blob=(0.2 + (i % 3) * 0.3, 1.0, 0.35, 0.25), seed=seed + 5)
    c = c.crop((520, 330, 2080, 1640))
    c = camera(c, blur=1.5, noise=5.5, out_size=(1280, 1075), seed=seed + 6, chroma_noise=2.4)
    c = recompress(c, 72, 2)
    nm = f'IMG-20250703-WA00{21 + i}.jpg'
    jpeg(c, os.path.join(OUT, nm), q=72)
    # miniatura para la mesa de ordenar
    t = c.copy(); t.thumbnail((360, 360)); jpeg(t, os.path.join(OUT, 'mini_' + nm), q=78)
    res[nm] = r
json.dump(res, open('_render/recados_llegada.json', 'w'))
print('E08 listo', res)
