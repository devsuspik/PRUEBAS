"""E05 · Fotos del cuaderno de planeación de la maestra Chayo (1-VII-2025, de noche, en su mesa)."""
import sys, os
sys.path.insert(0, 'lib')
from photo import *
ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E05', 'img')
os.makedirs(OUT, exist_ok=True)

def foto_chayo(pag, name, seed, ang, persp, blob):
    obj = Image.open(f'_render/chayo_{pag}.png').convert('RGBA')
    obj = paper_effects(obj, wrinkle=0.03, tint=(250, 246, 234), seed=seed, edge_dirt=0.15)
    bg = tex_cloth(3300, 2700, seed=seed + 1, base=(222, 208, 186))
    c = place(bg, obj, 1350, 1640, ang, 1.0, (10, 16, 18, 0.45))
    c = perspective(c, *persp, fill=(60, 50, 40))
    c = lighting(c, direction=(-0.2, -1.0), strength=0.33, temp=(1.10, 1.0, 0.80), vignette=0.33, blob=blob, seed=seed + 2)
    c = c.crop((200, 260, 2500, 3220))
    c = camera(c, blur=1.3, noise=5.0, out_size=(1200, 1544), seed=seed + 3, chroma_noise=2.0)
    c = recompress(c, 74, 2)
    jpeg(c, os.path.join(OUT, name), q=74)

foto_chayo('croquis', 'IMG-20250701-WA0004.jpg', 510, -1.5, ((40, 70), (-120, 100), (-20, 0), (50, -10)), (0.9, 0.8, 0.4, 0.25))
foto_chayo('diario_oct', 'IMG-20250701-WA0005.jpg', 520, 2.0, ((90, 30), (-60, 120), (0, 0), (40, 0)), (0.1, 0.9, 0.4, 0.2))
foto_chayo('diario_feb', 'IMG-20250701-WA0006.jpg', 530, -2.6, ((20, 90), (-100, 40), (-40, 0), (20, 0)), (0.95, 0.9, 0.35, 0.22))
foto_chayo('diario_mar', 'IMG-20250701-WA0007.jpg', 540, 1.2, ((60, 60), (-80, 110), (-30, 10), (30, -20)), (0.9, 0.95, 0.4, 0.28))
foto_chayo('diario_jun', 'IMG-20250701-WA0008.jpg', 550, -0.8, ((30, 40), (-140, 80), (0, 0), (60, 10)), (0.15, 0.95, 0.35, 0.2))
print('E05 listo')
