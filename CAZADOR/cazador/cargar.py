"""Carga de datos por símbolo y CANDADO DEL HOLDOUT.

El holdout (últimos ~2 meses) no se carga nunca por la vía normal: ``cargar_moneda`` recorta SIEMPRE en
``busqueda_fin``. Para abrirlo hay que llamar a ``abrir_holdout`` con las estrategias ya congeladas; la apertura
queda registrada en HOLDOUT_LOG.json (fecha, hash de las estrategias congeladas) y solo puede hacerse UNA vez.

Esto es un candado de procedimiento, no criptográfico: quien lo ejecuta (yo) podría saltárselo editando el código.
Por eso el hash del contenido del holdout y la fecha de bloqueo se guardan en git ANTES de la búsqueda, y cualquiera
puede comprobar en el historial que no se tocó antes de tiempo.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import datos as D
from .config import CFG
from .descarga import PERIODO, CACHE, RAIZ
from .motor import DatosMoneda, MS_MIN

HOLDOUT_LOG = RAIZ / "HOLDOUT_LOG.json"
HOLDOUT_HASH = RAIZ / "HOLDOUT_HASH.json"


def _ms(s: str, fin_dia: bool = False) -> int:
    t = pd.Timestamp(s)
    if fin_dia:
        t = t + pd.Timedelta(days=1)
    return int(t.timestamp() * 1000)


def _funding(sim: str) -> Optional[pd.DataFrame]:
    p = CACHE / "funding" / f"{sim}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def cargar_moneda(sim: str, tramo: str = "busqueda", intervalo: str = "1m", step: float = 0.0,
                  min_notional: float = 5.0, con_calentamiento: bool = True) -> Optional[DatosMoneda]:
    """tramo='busqueda' (por defecto; NUNCA incluye el holdout) | 'holdout' (solo vía ``abrir_holdout``).

    Con ``con_calentamiento`` se cargan además los meses previos (solo para calcular indicadores). El atributo
    ``idx_eval`` del resultado marca el primer índice de 1 m donde se puede operar (inicio del tramo).
    """
    if tramo not in ("busqueda", "holdout"):
        raise ValueError(tramo)
    from .periodo import NOMBRE
    if (tramo == "holdout" or NOMBRE == "ho") and not _holdout_abierto():
        raise PermissionError("El holdout está bloqueado: usa cazador.holdout (registra la apertura única con el hash de las estrategias)")
    p = CACHE / "klines" / intervalo / f"{sim}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if df.empty:
        return None
    ini_eval = _ms(PERIODO[f"{tramo}_ini"])
    ini = _ms(PERIODO["calentamiento_ini"]) if (con_calentamiento and tramo == "busqueda") else ini_eval
    if tramo == "holdout" and con_calentamiento:
        ini = _ms(PERIODO["busqueda_fin"], fin_dia=True) - 200 * 86_400_000       # 200 d previos para indicadores
    fin = _ms(PERIODO[f"{tramo}_fin"], fin_dia=True)
    df = df[(df["t"] >= ini) & (df["t"] < fin)]
    if df.empty or df["t"].max() < ini_eval:
        return None
    df = df.astype({"qv": "float64", "tb_qv": "float64", "v": "float64", "tb_v": "float64"})
    g, _ = D.a_rejilla_1m(df)
    f = _funding(sim)
    if f is not None and len(f):
        f = f[(f["t"] >= ini) & (f["t"] < fin)]
    d = D.a_datos_moneda(sim, g, f, step=step, min_notional=min_notional)
    d.idx_eval = int(max(0, np.ceil((ini_eval - d.t0_ms) / MS_MIN)))
    return d


# ----------------------------------------------------------------------------------------------
def hash_holdout(simbolos: List[str]) -> str:
    """SHA-256 del contenido del holdout (velas 1 m) de los símbolos dados, en orden alfabético."""
    h = hashlib.sha256()
    ini, fin = _ms(PERIODO["holdout_ini"]), _ms(PERIODO["holdout_fin"], True)
    for s in sorted(simbolos):
        p = CACHE / "klines" / "1m" / f"{s}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p, columns=["t", "o", "h", "l", "c", "qv"])
        df = df[(df["t"] >= ini) & (df["t"] < fin)]
        h.update(s.encode())
        h.update(np.ascontiguousarray(df[["t", "o", "h", "l", "c"]].to_numpy("float64")).tobytes())
    return h.hexdigest()


def bloquear_holdout(simbolos: List[str]) -> dict:
    """Se ejecuta UNA vez, antes de cualquier búsqueda, y se sube a git."""
    if HOLDOUT_HASH.exists():
        return json.loads(HOLDOUT_HASH.read_text())
    info = {"bloqueado_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "periodo_holdout":
            [PERIODO["holdout_ini"], PERIODO["holdout_fin"]], "n_simbolos": len(simbolos),
            "sha256_velas_1m": hash_holdout(simbolos)}
    HOLDOUT_HASH.write_text(json.dumps(info, indent=1))
    return info


def _holdout_abierto() -> bool:
    return HOLDOUT_LOG.exists()


def abrir_holdout(hash_estrategias_congeladas: str) -> dict:
    """Registra la apertura (única) del holdout. Falla si ya se abrió."""
    if HOLDOUT_LOG.exists():
        raise PermissionError("El holdout ya se abrió una vez: " + HOLDOUT_LOG.read_text())
    if not HOLDOUT_HASH.exists():
        raise PermissionError("El holdout nunca se bloqueó con hash antes de la búsqueda")
    info = {"abierto_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "hash_estrategias_congeladas": hash_estrategias_congeladas}
    HOLDOUT_LOG.write_text(json.dumps(info, indent=1))
    return info
