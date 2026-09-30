"""Ronda 0: capacidades del entorno, acceso a datos y pruebas del motor. Escribe INFORME_RONDA0.md.

Uso:  python -m cazador.ronda0
No busca estrategias. Si no hay acceso a los datos lo dice y se detiene: nunca se sustituyen por datos inventados.
"""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
HOSTS = {
    "data.binance.vision (histórico)": "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2025-01.zip",
    "fapi.binance.com (API futuros)": "https://fapi.binance.com/fapi/v1/ping",
}
LIBS = ["numpy", "pandas", "pyarrow", "scipy", "sklearn", "lightgbm", "optuna", "numba", "statsmodels", "hmmlearn", "matplotlib"]


def comprobar_host(url: str) -> str:
    try:
        r = requests.head(url, timeout=20, allow_redirects=True)
        return f"OK ({r.status_code})" if r.status_code < 400 else f"ERROR HTTP {r.status_code}"
    except Exception as e:  # noqa: BLE001
        return f"SIN ACCESO ({type(e).__name__}: {str(e)[:90]})"


def main() -> int:
    l = [f"# Informe Ronda 0 – {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n"]
    l.append(f"- Python {platform.python_version()} · {os.cpu_count()} CPU · disco libre {shutil.disk_usage(RAIZ).free / 1e9:.0f} GB")
    faltan = []
    for m in LIBS:
        try:
            mod = importlib.import_module(m)
            l.append(f"- {m} {getattr(mod, '__version__', 'ok')}")
        except Exception:  # noqa: BLE001
            faltan.append(m)
    if faltan:
        l.append(f"- **Faltan librerías:** {', '.join(faltan)} (pip install -r requirements.txt)")
    l.append("\n## Acceso a datos\n")
    acceso = True
    for nombre, url in HOSTS.items():
        est = comprobar_host(url)
        acceso &= est.startswith("OK")
        l.append(f"- {nombre}: {est}")
    l.append("\n## Pruebas del motor (datos SINTÉTICOS, solo para validar el código)\n")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--no-header"], cwd=RAIZ, capture_output=True, text=True)
    l.append("```\n" + "\n".join(r.stdout.strip().splitlines()[-6:]) + "\n```")
    l.append("\n## Veredicto\n")
    if not acceso:
        l.append("**NO se puede empezar la búsqueda:** sin acceso a datos reales de mercado no hay nada que analizar. "
                 "No se sustituyen por datos inventados. Habilita la red a estos hosts (o ejecuta esto en tu máquina) y repite.")
    elif r.returncode != 0:
        l.append("**Datos accesibles pero el motor NO pasa sus pruebas:** hay que arreglarlo antes de buscar nada.")
    else:
        l.append("Datos accesibles y motor validado. Siguiente paso: descarga y Ronda 1.")
    (RAIZ / "INFORME_RONDA0.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))
    return 0 if acceso and r.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
