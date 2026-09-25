"""Postproceso fotográfico: convierte renders planos en fotos de celular, escaneos o capturas.

El texto exacto se compone antes con HTML (render.js). Aquí solo se simula
el soporte físico y la cámara: papel, dobleces, humedad, superficie, perspectiva,
luz, ruido y compresión. Todo es determinista (semillas fijas).
"""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
import io, math

# ---------------------------------------------------------------- ruido base
def fnoise(h, w, cell=64, octaves=4, seed=0, persistence=0.5):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    c = cell
    for _ in range(octaves):
        gh, gw = max(2, h // max(1, c) + 2), max(2, w // max(1, c) + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(im, np.float32) / 255.0)
        tot += amp
        amp *= persistence
        c = max(1, c // 2)
    return out / tot

def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------- superficies
def tex_laminate(h, w, seed=1, base=(206, 176, 134), grain=0.10):
    """Cubierta de mesabanco: laminado imitación madera de veta recta, gastado."""
    rng = np.random.default_rng(seed)
    # veta: ruido muy alargado en horizontal
    small = fnoise(max(8, h // 3), max(8, w // 60), 6, 4, seed)
    streak = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    fine = fnoise(max(8, h // 1), max(8, w // 25), 3, 2, seed + 3)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    blot = fnoise(h, w, 400, 3, seed + 1)
    v = 0.90 + grain * 1.2 * (streak - 0.5) + 0.05 * (fine - 0.5) + 0.07 * (blot - 0.5)
    img = np.stack([v * base[0], v * base[1] * 0.995, v * base[2] * 0.985], -1)
    im = to_img(img)
    d = ImageDraw.Draw(im, 'RGBA')
    for _ in range(int(w * h / 70000)):
        x0, y0 = rng.integers(0, w), rng.integers(0, h)
        L = rng.integers(20, 180); a = rng.uniform(-0.5, 0.5)
        d.line([(x0, y0), (x0 + L * math.cos(a), y0 + L * math.sin(a))], fill=(255, 248, 232, int(rng.integers(12, 34))), width=1)
    for _ in range(int(w * h / 500000)):
        x0, y0 = rng.integers(0, w), rng.integers(0, h)
        L = rng.integers(30, 140); a = rng.uniform(-1, 1)
        col = [(40, 60, 140, 34), (60, 60, 60, 30), (150, 40, 40, 26)][rng.integers(0, 3)]
        pts = [(x0 + k * L / 6 * math.cos(a), y0 + k * L / 6 * math.sin(a) + rng.normal(0, 1.5)) for k in range(7)]
        d.line(pts, fill=col, width=2)
    return im.filter(ImageFilter.GaussianBlur(0.7))

def tex_wood(h, w, seed=2, base=(92, 60, 40)):
    """Mesa de comedor de madera barnizada: veta recta, tablones."""
    rng = np.random.default_rng(seed)
    small = fnoise(max(8, h // 50), max(8, w // 2), 5, 4, seed)
    streak = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    fine = fnoise(max(8, h // 20), max(8, w), 3, 2, seed + 3)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    blot = fnoise(h, w, 500, 3, seed + 1)
    v = 0.86 + 0.22 * (streak - 0.5) + 0.08 * (fine - 0.5) + 0.10 * (blot - 0.5)
    # juntas entre tablones (vertical en la imagen: la veta corre en vertical)
    xs = np.arange(w)
    for x0 in range(int(rng.integers(300, 700)), w, int(rng.integers(700, 900))):
        v[:, max(0, x0 - 2):x0 + 2] *= 0.6
    img = np.stack([v * base[0], v * base[1], v * base[2]], -1)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.8))

def tex_cloth(h, w, seed=3, base=(226, 218, 200), weave=3):
    """Mantel de tela lisa (trama visible de cerca)."""
    n = fnoise(h, w, 260, 3, seed)
    yy, xx = np.mgrid[0:h, 0:w]
    tr = (np.sin(xx * math.pi / weave) * np.sin(yy * math.pi / weave)) * 0.5 + 0.5
    v = 0.92 + 0.05 * (tr - 0.5) + 0.10 * (n - 0.5)
    img = np.stack([v * base[0], v * base[1], v * base[2]], -1)
    return to_img(img)

def tex_cardboard(h, w, seed=4, base=(176, 138, 92)):
    n = fnoise(h, w, 120, 5, seed)
    f = fnoise(h, w, 6, 2, seed + 5)
    v = 0.9 + 0.12 * (n - 0.5) + 0.06 * (f - 0.5)
    img = np.stack([v * base[0], v * base[1], v * base[2]], -1)
    return to_img(img).filter(ImageFilter.GaussianBlur(0.5))

def tex_flat(h, w, color, seed=5, amount=0.04):
    n = fnoise(h, w, 200, 3, seed)
    v = 1 + amount * (n - 0.5)
    return to_img(np.stack([v * color[0], v * color[1], v * color[2]], -1))

# ---------------------------------------------------------------- papel
def paper_effects(im, folds=(), stains=(), wrinkle=0.035, tint=None, seed=10,
                  edge_dirt=0.0, crease_strength=1.0):
    """im: RGBA del objeto plano. folds: lista de ('h'|'v', fracción).
    stains: lista de dicts {x,y,r (fracciones), a (intensidad), col}."""
    im = im.convert('RGBA')
    w, h = im.size
    a = np.asarray(im, np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    # ondulación suave del papel (no queda plano)
    n = fnoise(h, w, max(w, h) // 3, 3, seed)
    shade = 1 + wrinkle * (n - 0.5) * 2
    # dobleces: cada panel recibe una luz distinta y la arista un filo claro/oscuro
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for i, (ax, pos) in enumerate(folds):
        p = pos * (h if ax == 'h' else w)
        dist = (yy - p) if ax == 'h' else (xx - p)
        rng = np.random.default_rng(seed + 31 * i)
        wob = fnoise(h, w, 90, 2, seed + i) - 0.5
        dist = dist + wob * 6
        side = np.tanh(dist / 18.0)
        shade *= 1 + 0.018 * crease_strength * side * (1 if i % 2 == 0 else -1)
        line = np.exp(-(dist / 1.6) ** 2)
        hl = np.exp(-((dist - 3) / 2.2) ** 2)
        shade *= (1 - 0.16 * crease_strength * line) * (1 + 0.05 * crease_strength * hl)
    rgb = rgb * shade[..., None]
    # manchas de agua: fondo apenas más oscuro y ondulado; cerco fino color té
    for k, s_ in enumerate(stains):
        cx, cy, r = s_['x'] * w, s_['y'] * h, s_['r'] * min(w, h)
        nn = fnoise(h, w, int(r / 3) + 8, 4, seed + 100 + k)
        d = np.sqrt(((xx - cx) / (s_.get('sx', 1))) ** 2 + ((yy - cy) / s_.get('sy', 1)) ** 2) / r + (nn - 0.5) * s_.get('rough', 0.5)
        inside = np.clip((1 - d) * 25, 0, 1)
        ring = np.exp(-((d - 1) / 0.006) ** 2) * 0.9 + np.exp(-((d - 0.985) / 0.02) ** 2) * 0.35
        col = np.array(s_.get('col', (176, 146, 96)), np.float32)
        amt = s_.get('a', 0.22)
        cockle = 1 + 0.035 * (fnoise(h, w, 40, 2, seed + 200 + k) - 0.5) * inside
        rgb = rgb * cockle[..., None]
        mix_in = amt * 0.28 * inside[..., None]
        rgb = rgb * (1 - mix_in) + (rgb * col / 255.0) * mix_in
        mix_r = amt * 1.2 * ring[..., None]
        rgb = rgb * (1 - np.clip(mix_r, 0, 1)) + (rgb * (col * 0.78) / 255.0) * np.clip(mix_r, 0, 1)
    if tint is not None:
        t = np.array(tint, np.float32) / 255.0
        rgb = rgb * t
    if edge_dirt > 0:
        m = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
        e = np.exp(-m / 25.0) * edge_dirt * (0.6 + 0.8 * fnoise(h, w, 30, 2, seed + 7))
        rgb = rgb * (1 - e[..., None] * 0.35)
    out = np.concatenate([np.clip(rgb, 0, 255), al], -1).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def torn_left_edge(im, depth=14, seed=20, side='left'):
    """Orilla arrancada de cuaderno de espiral: perforaciones rotas de forma irregular."""
    im = im.convert('RGBA')
    w, h = im.size
    rng = np.random.default_rng(seed)
    al = np.asarray(im.split()[-1], np.float32)
    prof = np.zeros(h, np.float32)
    period = depth * 1.35  # paso aproximado de la perforación
    y = 0.0
    while y < h:
        p = period * rng.uniform(0.8, 1.25)
        kind = rng.random()
        y0, y1 = int(y), int(min(h, y + p))
        t = np.linspace(0, 1, max(1, y1 - y0))
        if kind < 0.55:   # pestaña que quedó: sobresale
            base = depth * rng.uniform(0.05, 0.35)
            bump = -np.sin(t * np.pi) ** 1.5 * depth * rng.uniform(0.2, 0.6)
        elif kind < 0.85:  # desgarro hacia dentro
            base = depth * rng.uniform(0.35, 0.8)
            bump = np.sin(t * np.pi) * depth * rng.uniform(0.1, 0.4)
        else:              # tramo recto
            base = depth * rng.uniform(0.2, 0.5)
            bump = np.zeros_like(t)
        prof[y0:y1] = base + bump + rng.normal(0, depth * 0.06, y1 - y0)
        y += p
    prof = np.convolve(prof, np.ones(5) / 5, 'same')
    lf = fnoise(h, 8, 60, 2, seed)[:, 0]
    prof = np.clip(prof + (lf - 0.5) * depth * 0.6, 0, depth * 1.6)
    xx = np.arange(w)[None, :]
    if side == 'left':
        mask = xx >= prof[:, None]
    else:
        mask = xx <= (w - 1 - prof[:, None])
    al = al * mask
    out = np.asarray(im).copy()
    out[..., 3] = al.astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def rough_edges(im, amount=1.5, seed=21):
    """Orillas ligeramente irregulares (papel cortado a mano o gastado)."""
    im = im.convert('RGBA')
    w, h = im.size
    al = np.asarray(im.split()[-1], np.float32) / 255
    n = fnoise(h, w, 8, 2, seed)
    al2 = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(amount))
    al2 = np.asarray(al2, np.float32) / 255
    al3 = np.clip((al2 - 0.5 + (n - 0.5) * 0.35) * 6 + 0.5, 0, 1)
    out = np.asarray(im).copy()
    out[..., 3] = (np.minimum(al, al3) * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

# ---------------------------------------------------------------- composición
def place(bg, obj, cx, cy, angle=0.0, scale=1.0, shadow=(10, 14, 18, 0.45)):
    """Coloca obj (RGBA) sobre bg (RGB) centrado en (cx, cy) con sombra suave."""
    bg = bg.convert('RGB').copy()
    if scale != 1.0:
        obj = obj.resize((int(obj.width * scale), int(obj.height * scale)), Image.LANCZOS)
    rot = obj.rotate(angle, resample=Image.BICUBIC, expand=True)
    x, y = int(cx - rot.width / 2), int(cy - rot.height / 2)
    if shadow:
        dx, dy, blur, op = shadow
        sh = Image.new('L', rot.size, 0)
        sh.paste(rot.split()[-1])
        pad = int(blur * 3)
        shc = Image.new('L', (rot.width + pad * 2, rot.height + pad * 2), 0)
        shc.paste(sh, (pad, pad))
        shc = shc.filter(ImageFilter.GaussianBlur(blur))
        shc = shc.point(lambda v: int(v * op))
        dark = Image.new('RGB', shc.size, (20, 16, 12))
        bg.paste(dark, (x - pad + dx, y - pad + dy), shc)
    bg.paste(rot, (x, y), rot)
    return bg

def _coeffs(src, dst):
    m = []
    for (xs, ys), (xd, yd) in zip(src, dst):
        m.append([xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd])
        m.append([0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd])
    A = np.array(m, np.float64)
    B = np.array(src, np.float64).reshape(8)
    return np.linalg.solve(A, B).tolist()

def perspective(im, tl=(0, 0), tr=(0, 0), br=(0, 0), bl=(0, 0), fill=(0, 0, 0)):
    """Desplaza las esquinas (en px) para simular un celular no paralelo."""
    w, h = im.size
    dst = [(tl[0], tl[1]), (w + tr[0], tr[1]), (w + br[0], h + br[1]), (bl[0], h + bl[1])]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    c = _coeffs(src, dst)
    return im.transform((w, h), Image.PERSPECTIVE, c, Image.BICUBIC, fillcolor=fill)

def lighting(im, direction=(-0.6, -0.8), strength=0.18, falloff=None, temp=(1.0, 1.0, 1.0),
             vignette=0.12, blob=None, seed=40):
    """Luz ambiente: gradiente direccional, viñeta, temperatura de color y
    opcionalmente una sombra difusa (mano/celular) blob=(x,y,r,intensidad)."""
    a = np.asarray(im.convert('RGB'), np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xx / w - 0.5), (yy / h - 0.5)
    g = 1 + strength * (-(nx * direction[0] + ny * direction[1]))
    r = np.sqrt(nx ** 2 + ny ** 2) / 0.7071
    g *= 1 - vignette * r ** 2
    n = fnoise(h, w, max(w, h) // 2, 2, seed)
    g *= 1 + 0.04 * (n - 0.5)
    if blob:
        bx, by, br, bi = blob
        d = np.sqrt((xx / w - bx) ** 2 + (yy / h - by) ** 2) / br
        g *= 1 - bi * np.exp(-d ** 2)
    a = a * g[..., None] * np.array(temp, np.float32)[None, None, :]
    return to_img(a)

def camera(im, blur=0.7, noise=3.0, sharpen=True, out_size=None, seed=50, chroma_noise=1.2):
    im = im.convert('RGB')
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if out_size:
        im = im.resize(out_size, Image.LANCZOS)
    a = np.asarray(im, np.float32)
    rng = np.random.default_rng(seed)
    lum = a.mean(-1, keepdims=True) / 255
    nz = rng.normal(0, noise, a.shape[:2])[..., None] * (1.4 - lum)
    cn = rng.normal(0, chroma_noise, a.shape) * (1.3 - lum)
    a = a + nz + cn
    im = to_img(a)
    if sharpen:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=55, threshold=2))
    return im

def jpeg(im, path, q=82, subsampling=2):
    im.convert('RGB').save(path, 'JPEG', quality=q, optimize=True, progressive=True, subsampling=subsampling)

def recompress(im, q=70, times=1):
    """Simula el paso por WhatsApp (recompresión)."""
    for _ in range(times):
        b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=q); b.seek(0)
        im = Image.open(b).convert('RGB')
    return im

# ---------------------------------------------------------------- escáner
def scan(obj_rgba, pad=40, bg=(246, 246, 244), skew=0.35, seed=60, dust=40, dpi_blur=0.45,
         lid_shadow=0.0):
    """Hoja sobre cama de escáner: fondo casi blanco, sin perspectiva, leve sesgo."""
    w, h = obj_rgba.size
    canvas = tex_flat(h + pad * 2, w + pad * 2, bg, seed, 0.01)
    canvas = place(canvas, obj_rgba, canvas.width / 2, canvas.height / 2, skew, 1.0, (0, 2, 4, 0.25))
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(canvas)
    for _ in range(dust):
        x, y = rng.integers(0, canvas.width), rng.integers(0, canvas.height)
        r = rng.uniform(0.4, 1.6)
        c = int(rng.uniform(90, 170))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, c))
    if lid_shadow:
        canvas = lighting(canvas, (1, 0), lid_shadow, vignette=0.0, temp=(1, 1, 1))
    canvas = canvas.filter(ImageFilter.GaussianBlur(dpi_blur))
    return canvas

def photocopy_marks(im, seed=70, specks=140, streak=True):
    """Marcas de fotocopiadora sobre la hoja (motas de tóner, raya tenue)."""
    im = im.convert('RGBA')
    w, h = im.size
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(im, 'RGBA')
    for _ in range(specks):
        x, y = rng.integers(0, w), rng.integers(0, h)
        r = abs(rng.normal(0.5, 0.4)) + 0.3
        a = int(rng.uniform(40, 150))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(30, 30, 30, a))
    if streak:
        x0 = int(w * rng.uniform(0.75, 0.95))
        for k in range(2):
            d.line([(x0 + k, 0), (x0 + k + rng.integers(-3, 3), h)], fill=(90, 90, 90, 6))
    # velo gris de la copia en los bordes
    a = np.asarray(im, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy))
    veil = np.exp(-m / 40.0) * 18
    a[..., :3] -= veil[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
