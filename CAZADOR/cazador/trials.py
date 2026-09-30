"""Registro de TODAS las pruebas realizadas (trials_log.csv). Es la base del Deflated Sharpe y del PBO:
si se prueba algo y no se anota, los estadísticos de significación mienten."""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Optional

RUTA = Path(__file__).resolve().parent.parent / "trials_log.csv"
COLS = ["ts", "ronda", "estrategia", "marco_min", "params", "salida", "segmento", "regimen", "lado",
        "n_ops", "exp_R", "beneficio_usd", "sharpe_periodo", "tramo"]


def registrar(fila: dict, ruta: Optional[Path] = None) -> None:
    ruta = ruta or RUTA
    nuevo = not ruta.exists()
    with ruta.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        fila = {"ts": int(time.time()), **fila}
        w.writerow(fila)


def total(ruta: Optional[Path] = None) -> int:
    ruta = ruta or RUTA
    if not ruta.exists():
        return 0
    with ruta.open() as f:
        return max(sum(1 for _ in f) - 1, 0)
