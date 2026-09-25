# E07: capturas del chat privado Mariana ↔ Óscar (render de whatsapp.html?chat=oscar).
# Requiere: node render.js jobs_wa_oscar.json
import os
from PIL import Image
import sys; sys.path.insert(0, 'lib')
from photo import jpeg

OUT = os.path.join('..', '..', 'JUGADOR_COMPLETO', 'E07', 'img')
NOMBRES = ['Screenshot_20250703-092412.jpg', 'Screenshot_20250703-092419.jpg',
           'Screenshot_20250703-092503.jpg', 'Screenshot_20250703-092511.jpg']

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for i, n in enumerate(NOMBRES):
        im = Image.open(f'_render/wa_oscar_{i + 1}.png').convert('RGB').crop((1, 0, 1081, 2399))
        jpeg(im, os.path.join(OUT, n), q=88, subsampling=0)
    print('E07 listo')
