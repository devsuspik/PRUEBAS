"""Notas de voz (provisionales funcionales) con TTS neuronal local (piper, es_MX)
y tratamiento de nota de voz de celular. Sustituir por locución humana (ver ASSETS_PENDIENTES).
Uso: python3 build_audio.py chayo1|chayo2"""
import sys, os, subprocess, wave, json
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

FF = get_ffmpeg_exe()
VOCES = '/tmp/voices'
TMP = '_render/audio'
os.makedirs(TMP, exist_ok=True)
ROOT = os.path.abspath('../..')
SR = 22050

# Reescrituras fonéticas solo para el sintetizador (la transcripción conserva la ortografía)
FONETICA = {'Itzel': 'Ítsel', 'Hoja': 'Oja', 'hoja': 'oja'}

def tts(text, voice, out, length=1.12, noise=0.72, noise_w=0.9):
    for a, b in FONETICA.items():
        text = text.replace(a, b)
    cfg = dict(length_scale=length, noise_scale=noise, noise_w=noise_w)
    p = subprocess.run([sys.executable, '-m', 'piper', '-m', f'{VOCES}/{voice}.onnx', '-f', out,
                        '--length-scale', str(length), '--noise-scale', str(noise), '--noise-w-scale', str(noise_w)],
                       input=text.encode('utf-8'), capture_output=True)
    if p.returncode != 0:
        # versiones de piper sin --noise-w-scale
        p = subprocess.run([sys.executable, '-m', 'piper', '-m', f'{VOCES}/{voice}.onnx', '-f', out,
                            '--length-scale', str(length), '--noise-scale', str(noise)],
                           input=text.encode('utf-8'), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[-500:])

def leer(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x, w.getframerate()

def canario(dur, sr, seed):
    """Trino lejano de canario (síntesis FM), muy bajo."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(dur * sr), np.float32)
    t0 = 0
    while t0 < len(out) - sr // 2:
        n = rng.integers(4, 9)
        for k in range(n):
            L = int(sr * rng.uniform(0.035, 0.07))
            t = np.arange(L) / sr
            f0 = rng.uniform(2600, 4200); sw = rng.uniform(-900, 900)
            ph = 2 * np.pi * (f0 * t + sw * t * t / (2 * t[-1] + 1e-6))
            env = np.sin(np.pi * np.arange(L) / L) ** 2
            s = np.sin(ph + 0.8 * np.sin(2 * np.pi * 38 * t)) * env
            a = t0 + k * int(sr * 0.085)
            if a + L < len(out):
                out[a:a + L] += s * 0.5
        t0 += int(sr * rng.uniform(3.5, 9.0))
    return out

def armar(partes, voice, nombre, sal, pitch=0.965, bird=True, length=1.12, seed=1):
    """partes: lista de (texto, silencio_despues_s)."""
    rng = np.random.default_rng(seed)
    pcs = []
    for i, (t, sil) in enumerate(partes):
        f = f'{TMP}/{nombre}_{i:02d}.wav'
        tts(t, voice, f, length=length * rng.uniform(0.97, 1.04))
        x, sr = leer(f)
        # recorta silencios de los extremos que agrega el TTS
        nz = np.where(np.abs(x) > 0.01)[0]
        if len(nz): x = x[max(0, nz[0] - 400): nz[-1] + 1200]
        pcs.append(x)
        pcs.append(np.zeros(int(sr * sil), np.float32))
    y = np.concatenate([np.zeros(int(SR * 0.35), np.float32)] + pcs + [np.zeros(int(SR * 0.25), np.float32)])
    # ruido de habitación y canario lejano
    room = np.random.default_rng(seed + 1).normal(0, 1, len(y)).astype(np.float32)
    room = np.convolve(room, np.ones(40) / 40, 'same') * 0.012
    y = y + room
    if bird:
        y = y + canario(len(y) / SR, SR, seed + 2) * 0.012
    raw = f'{TMP}/{nombre}_raw.wav'
    w = wave.open(raw, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    # cadena de nota de voz: tono un poco más grave, micro de celular, cuarto pequeño, compresión
    af = (f'asetrate={int(SR * pitch)},aresample=44100,'
          'highpass=f=140,lowpass=f=7200,equalizer=f=2600:t=q:w=1.2:g=3,'
          'aecho=0.8:0.5:18|31:0.18|0.10,'
          'acompressor=threshold=-20dB:ratio=3.5:attack=8:release=160:makeup=4,'
          'alimiter=limit=0.9')
    os.makedirs(os.path.dirname(sal), exist_ok=True)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', raw, '-af', af, '-ac', '1', '-ar', '44100',
                    '-c:a', 'libmp3lame', '-b:a', '64k', sal], check=True)
    d = subprocess.run([FF, '-i', sal], capture_output=True).stderr.decode()
    dur = [l for l in d.splitlines() if 'Duration' in l]
    print(sal, dur[0].strip() if dur else '')

CHAYO1 = [
    ('Mariana, mija, buenas tardes.', 0.45),
    ('Oye, fíjate que ya vi la foto que me mandaste de la cartita.', 0.55),
    ('No, mija. Yo no tuve ninguna Itzel.', 0.3),
    ('Ni en ese grupo, ni en ningún otro. Y mira que yo me acuerdo de todos mis alumnos, eh. Con nombre y apellido.', 0.65),
    ('Las cartas las hicieron en el salón, un viernes, a mediados de junio. La hoja se las di yo, fotocopiada.', 0.35),
    ('Y cada quien metió la suya en su sobre, con su nombre, y lo cerró ahí, delante de mí.', 0.5),
    ('Yo los conté. Treinta y cuatro sobres, uno por alumno. Y los guardé en el archivero, con llave, hasta el día que los enterramos.', 0.45),
    ('Hoja suelta no había ninguna. Eso te lo firmo.', 0.75),
    ('Y lo del profe Chava...', 0.5),
    ('pues no, mija. En la mañana no había ningún Chava. ¿No habrá querido poner Chayo, la criatura?', 0.35),
    ('Aunque a mí nunca me dijeron profe, ¿eh?', 0.65),
    ('En la tarde el edificio era de la otra escuela, de la vespertina. Pero esos eran otra cosa. Otra dirección, otros maestros. Ni nos hablábamos.', 0.3),
    ('Nomás nos dejaban el salón hecho un cochinero.', 0.7),
    ('Bueno, mija, te dejo, que ya llegó mi nieto. Salúdame a todos, y felicidades por la reunión. Qué bonito que se acordaron.', 0.2),
]

CHAYO2 = [
    ('Mija, ya me acordé.', 0.6),
    ('Me quedé pensando toda la noche con lo que me contaste de los recaditos. Era la niña de Don Cuco. El conserje.', 0.5),
    ('Vivían ahí atrás del edificio B, en los cuartitos. Don Cuco casi no sabía escribir. La niña le hacía todo, los recados, la libreta, todo.', 0.55),
    ('Yo nunca supe que se llamara Itzel, eh. A mí me dijeron Lupita. La niña de Don Cuco.', 0.6),
    ('Y sí, fui yo la que le avisó a la directora. La maestra Hortensia.', 0.4),
    ('Porque esa niña no estaba inscrita en ningún lado, mija. No tenía papeles. Se metía a la clase del profe Salvador, de la tarde, y el profe la dejaba.', 0.5),
    ('Y yo dije, pues no. Una niña que no está inscrita no puede estar en un salón. Si le pasa algo, ¿quién responde?', 0.55),
    ('La directora habló con Don Cuco, y con los de la tarde, y ya no la dejaron entrar.', 0.5),
    ('El profe Salvador se enojó muchísimo conmigo. Ya nunca me volvió a hablar. Nunca.', 0.6),
    ('Después supe que él mismo la llevó al Registro Civil a sacarle su acta. Y a Don Cuco lo cambiaron a una secundaria, en junio, antes de que enterráramos la caja.', 0.65),
    ('Yo hice lo que se tenía que hacer. ¿Verdad?', 0.5),
    ('Pero sí me quedé con eso, mija. Sí me quedé con eso.', 0.4),
    ('Bueno. Ahí me dices qué averiguas.', 0.2),
]

if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else 'chayo1'
    if q == 'chayo1':
        armar(CHAYO1, 'es_MX-claude-high', 'chayo1',
              os.path.join(ROOT, 'JUGADOR_GRATIS', 'E03', 'audio', 'PTT-20250628-WA0007.mp3'), seed=5)
    elif q == 'chayo2':
        armar(CHAYO2, 'es_MX-claude-high', 'chayo2',
              os.path.join(ROOT, 'JUGADOR_COMPLETO', 'E11', 'audio', 'PTT-20250705-WA0019.mp3'), seed=9, bird=False)
