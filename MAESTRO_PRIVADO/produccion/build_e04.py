"""E04 · Correo impreso (PDF del navegador) y croquis adjunto: documentos digitales, sin foto."""
import os
from PIL import Image
ROOT = os.path.abspath('../..')
OUT = os.path.join(ROOT, 'JUGADOR_GRATIS', 'E04', 'img')
os.makedirs(OUT, exist_ok=True)
def png_q(src, dst, colors=128):
    im = Image.open(src).convert('RGB')
    im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(dst, optimize=True)
png_q('_render/correo.png', os.path.join(OUT, 'correo_direccion_30-06-2025.png'), 64)
png_q('_render/croquis.png', os.path.join(OUT, 'Croquis_PC_2024-2025.png'), 128)
print('E04 listo')
