"""§7 Walk-forward sobre agregados diarios: optimizar en 6 meses -> probar el mes siguiente -> avanzar 1 mes.

Solo cuentan los meses de PRUEBA encadenados. La selección (qué combinación parámetros x salida x lado usar cada mes) se hace con
datos anteriores al mes de prueba; una combinación necesita >= ``min_ops_is`` operaciones en la ventana de entrenamiento.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import barrido as BR
from . import metricas as M

MES = BR.MES_DIA                 # mes (0..23) de cada día de búsqueda
NM = int(MES.max()) + 1


def _sharpe(x: np.ndarray) -> np.ndarray:
    """Sharpe diario por columna de una matriz días x combos."""
    sd = x.std(axis=0, ddof=1)
    return np.where(sd > 0, x.mean(axis=0) / np.where(sd > 0, sd, 1.0), -np.inf)


def walk_forward(pnl: np.ndarray, n: Optional[np.ndarray] = None, train: int = 6, min_ops_is: int = 30,
                 gw: Optional[np.ndarray] = None, gl: Optional[np.ndarray] = None, R: Optional[np.ndarray] = None) -> dict:
    """pnl: matriz días x combos ($ realizados por día). n/gw/gl/R: matrices del mismo tamaño (opcionales).

    Devuelve las series diarias OOS encadenadas (0 fuera de meses de prueba), las elecciones por mes y los meses de prueba.
    """
    T, N = pnl.shape
    oos = np.zeros(T)
    oos_n = np.zeros(T)
    oos_gw = np.zeros(T)
    oos_gl = np.zeros(T)
    oos_R = np.zeros(T)
    elegidas: List[int] = []
    meses_prueba: List[int] = []
    for m in range(train, NM):
        is_mask = (MES >= m - train) & (MES < m)
        te_mask = MES == m
        sc = _sharpe(pnl[is_mask])
        if n is not None:
            sc = np.where(n[is_mask].sum(axis=0) >= min_ops_is, sc, -np.inf)
        j = int(np.argmax(sc))
        if not np.isfinite(sc[j]) or sc[j] <= 0:        # sin ninguna combinación con Sharpe IS > 0: ese mes no se opera
            elegidas.append(-1)
            meses_prueba.append(m)
            continue
        oos[te_mask] = pnl[te_mask, j]
        if n is not None:
            oos_n[te_mask] = n[te_mask, j]
        if gw is not None:
            oos_gw[te_mask] = gw[te_mask, j]
            oos_gl[te_mask] = gl[te_mask, j]
            oos_R[te_mask] = R[te_mask, j]
        elegidas.append(j)
        meses_prueba.append(m)
    return dict(pnl=oos, n=oos_n, gw=oos_gw, gl=oos_gl, R=oos_R, elegidas=elegidas, meses=meses_prueba)


def resumen_oos(wf: dict) -> dict:
    """Métricas fuera de muestra sobre los meses de prueba encadenados."""
    meses = wf["meses"]
    mask = np.isin(MES, meses)
    d = wf["pnl"][mask]
    mens = np.array([wf["pnl"][MES == m].sum() for m in meses])
    operados = np.array([e >= 0 for e in wf["elegidas"]])
    n = wf["n"][mask].sum()
    sd = d.std(ddof=1)
    out = {
        "meses_prueba": len(meses), "meses_operados": int(operados.sum()), "beneficio_oos": float(d.sum()),
        "meses_pos": float((mens[operados] > 0).mean()) if operados.any() else np.nan,
        "sharpe_dia": float(d.mean() / sd) if sd > 0 else 0.0, "n": float(n),
        "cambios_de_eleccion": int(sum(1 for a, b in zip(wf["elegidas"], wf["elegidas"][1:]) if a != b)),
    }
    if n > 0:
        gw, gl = wf["gw"][mask].sum(), wf["gl"][mask].sum()
        out.update(exp_usd=float(d.sum() / n), exp_R=float(wf["R"][mask].sum() / n), pf=float(gw / gl) if gl > 0 else np.nan)
    sem = pd.Series(d).groupby(np.arange(len(d)) // 7).sum()
    out["sin_mejor_sem"] = float(d.sum() - sem.max())
    return out
