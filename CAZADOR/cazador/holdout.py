"""APERTURA ÚNICA del holdout (2026-08-01..2026-09-29) para una lista CONGELADA de celdas.

Uso:  python -m cazador.holdout 3,4,22          (índices de CELDAS_CONGELADAS.json)

Pasos (todo queda en HOLDOUT_LOG.json y en el historial de git):
  1. comprueba que los datos del holdout siguen siendo EXACTAMENTE los fijados con hash antes de la búsqueda;
  2. calcula el hash de la lista de celdas congeladas + PREREGISTRO.md + índices pedidos;
  3. registra la apertura (falla si ya se abrió: solo UNA vez);
  4. ejecuta el mismo procedimiento de Ronda 2 (walk-forward de 6 meses) con periodo 'ho': entrena feb-jul 2026, prueba ago-sep 2026.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

from . import cargar
from .periodo import RAIZ

def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    idx = sys.argv[1]
    sel = json.loads((RAIZ / "UNIVERSO.json").read_text())["seleccion"]
    fijado = json.loads((RAIZ / "HOLDOUT_HASH.json").read_text())
    actual = cargar.hash_holdout(sel)
    if actual != fijado["sha256_velas_1m"]:
        print("ERROR: los datos del holdout NO coinciden con el hash fijado el", fijado["bloqueado_utc"])
        return 1
    print("hash del holdout verificado:", actual[:16], "(fijado", fijado["bloqueado_utc"], "UTC)")
    h = hashlib.sha256()
    for f in ("CELDAS_CONGELADAS.json", "PREREGISTRO.md", "CANDIDATAS_HOLDOUT.json"):
        h.update((RAIZ / f).read_bytes())
    h.update(idx.encode())
    reg = cargar.abrir_holdout(h.hexdigest())                          # falla si ya estaba abierto
    print("apertura registrada:", reg)
    shutil.copy(RAIZ / "UNIVERSO.json", RAIZ / "UNIVERSO_ho.json")      # misma selección de monedas (hecha antes del holdout)
    env = dict(os.environ, CAZADOR_PERIODO="ho")
    rc = subprocess.call([sys.executable, "-m", "cazador.ronda2", "--congeladas", "--solo", idx], env=env, cwd=RAIZ)
    rc2 = subprocess.call([sys.executable, "-m", "cazador.factores_1d"], env=env, cwd=RAIZ)
    return rc or rc2


if __name__ == "__main__":
    raise SystemExit(main())
