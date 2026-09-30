"""§5-F Transversal: long del top-k y short del bottom-k del universo, con rebalanceo periódico.

Las señales se calculan en el proceso principal (necesitan ver todas las monedas a la vez) y se reparten a los trabajadores
como ``senales_pre``. Causal: la clasificación en el rebalanceo t usa solo cierres de velas de 1 h ya cerradas en t.
Cada posición sale por tiempo en el siguiente rebalanceo (o por su stop de 3 ATR, el que llegue antes).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from . import cargar
from . import estrategias as E
from .descarga import PERIODO
from .motor import Senales

H_MS = 3_600_000


def preparar(simbolos: List[str], miembros: pd.DataFrame) -> dict:
    barras, atr14 = {}, {}
    for s in simbolos:
        d = cargar.cargar_moneda(s, "busqueda")
        if d is None:
            continue
        B = E.barras_tf(d, 60)
        barras[s] = B
        atr14[s] = E.atr(B, 14)
        del d
    h0 = int(min(B.ts_apertura[0] for B in barras.values()) // H_MS)
    h1 = int(max(B.ts_apertura[-1] for B in barras.values()) // H_MS)
    nh = h1 - h0 + 1
    syms = sorted(barras)
    C = np.full((nh, len(syms)), np.nan)
    A = np.full((nh, len(syms)), np.nan)
    IDX = np.full((nh, len(syms)), -1, np.int64)
    for j, s in enumerate(syms):
        B = barras[s]
        h = (B.ts_apertura // H_MS - h0).astype(int)
        C[h, j] = B.c
        A[h, j] = atr14[s]
        IDX[h, j] = B.idx_cierre
    fechas = pd.to_datetime((h0 + np.arange(nh)) * H_MS, unit="ms").normalize()
    M = np.zeros((nh, len(syms)), bool)
    for j, s in enumerate(syms):
        if s in miembros.columns:
            M[:, j] = miembros[s].reindex(fechas).fillna(False).to_numpy(bool)
    return dict(h0=h0, nh=nh, syms=syms, C=C, A=A, IDX=IDX, M=M)


def senales(mat: dict, L: int, R: int, k: int, modo: str = "momentum", k_atr: float = 3.0, min_monedas: int = 12) -> Dict[str, Senales]:
    """modo 'momentum': long de los que más suben en las últimas L horas, short de los que más bajan; 'reversion': al revés."""
    C, A, IDX, M, syms = mat["C"], mat["A"], mat["IDX"], mat["M"], mat["syms"]
    nh = mat["nh"]
    out = {s: ([], [], []) for s in syms}
    for t in range(L, nh, R):
        # la vela t (hora t..t+1) ya está cerrada al final de la hora t: usamos su cierre y el de t-L
        c1, c0 = C[t], C[t - L]
        ok = M[t] & np.isfinite(c1) & np.isfinite(c0) & np.isfinite(A[t]) & (IDX[t] >= 0)
        if ok.sum() < min_monedas:
            continue
        ret = np.where(ok, c1 / np.where(c0 > 0, c0, np.nan) - 1.0, np.nan)
        orden = np.argsort(np.where(np.isfinite(ret), ret, np.nan))
        orden = [j for j in orden if np.isfinite(ret[j])]
        top, bot = orden[-k:], orden[:k]
        largos, cortos = (top, bot) if modo == "momentum" else (bot, top)
        for lado, grupo in ((1, largos), (-1, cortos)):
            for j in grupo:
                i, l, d = out[syms[j]]
                i.append(IDX[t, j]); l.append(lado); d.append(k_atr * A[t, j])
    return {s: Senales(np.array(i, np.int64), np.array(l, np.int8), np.array(d, float)) for s, (i, l, d) in out.items() if i}
