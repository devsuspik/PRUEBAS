"""Corto de listados con apalancamiento LIBRE: stops más anchos con el apalancamiento que permiten (liquidación = 1/apal - 0,5 %).
Salida en % del nocional (el nocional por operación es el único tope del usuario). Uso: CAZADOR_PERIODO=<p> python -m cazador.listados_libre"""
import dataclasses
import itertools
import json

import numpy as np
import pandas as pd

from . import listados as LI
from . import listados_1m as L1
from .config import CFG
from .periodo import NOMBRE, RES


def main():
    ev = LI.eventos()
    cache = {s: L1.cargar_evento(s, g) for s, g in ev}
    cache = {s: d for s, d in cache.items() if d is not None}
    L1.cargar_evento = lambda s, g, _c=cache: _c.get(s)
    ev = [(s, g) for s, g in ev if s in cache]
    filas = []
    for stop, obj, apal, dias in itertools.product((0.08, 0.12, 0.15, 0.20, 0.25), (0.30, 0.40, 0.50), (None,), (7, 10)):
        # apalancamiento más alto que mantiene la liquidación POR ENCIMA del stop con colchón: liq = 1/apal - mmr >= stop + 4 %
        ap = int(np.floor(1 / (stop + 0.04 + CFG.mantenimiento_margen_frac)))
        cfg = dataclasses.replace(CFG, apalancamiento=float(ap))
        t = L1.simular(ev, cfg=cfg, stop=stop, obj_R=obj / stop, dias=dias)
        if t.empty:
            continue
        p = t.pnl.to_numpy() / CFG.nocional_usd * 100          # % del nocional
        filas.append(dict(periodo=NOMBRE, stop=stop, obj=obj, dias=dias, apal=ap, n=len(p), neto_pct=p.mean(), t=p.mean() / (p.std(ddof=1) / np.sqrt(len(p))),
                          aciertos=(p > 0).mean(), pf=p[p > 0].sum() / -p[p <= 0].sum() if (p <= 0).any() else np.nan, liq=int((t.motivo == 6).sum()),
                          peor_pct=p.min()))
    pd.DataFrame(filas).to_csv(RES / "listados_libre.csv", index=False)
    print(NOMBRE, len(ev), "eventos;", len(filas), "variantes")


if __name__ == "__main__":
    main()
