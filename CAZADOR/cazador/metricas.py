"""Métricas y estadística de validación (§7, §8, §9).

Todo lo que no se pueda calcular devuelve ``None`` (se imprime como "NO CALCULADO"), nunca un número inventado.
"""
from __future__ import annotations

import itertools
import math
from typing import Callable, Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

NO_CALC = None


# ----------------------------------------------------------------------------------------------
# Resumen de operaciones
# ----------------------------------------------------------------------------------------------
def curva_capital(trades: pd.DataFrame) -> pd.Series:
    """Capital acumulado ($) por operación cerrada, ordenado por hora de salida."""
    if trades.empty:
        return pd.Series(dtype=float)
    t = trades.sort_values("salida_ts")
    return t["pnl"].cumsum().reset_index(drop=True)


def max_drawdown(pnl: np.ndarray) -> float:
    """Drawdown máximo ($, positivo) de la secuencia de pnl por operación."""
    if len(pnl) == 0:
        return 0.0
    eq = np.concatenate([[0.0], np.cumsum(pnl)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


def peor_racha(pnl: np.ndarray) -> int:
    peor = cur = 0
    for x in pnl:
        cur = cur + 1 if x <= 0 else 0
        peor = max(peor, cur)
    return peor


def profit_factor(pnl: np.ndarray) -> Optional[float]:
    g = pnl[pnl > 0].sum()
    p = -pnl[pnl < 0].sum()
    if p <= 0:
        return None if g <= 0 else float("inf")
    return float(g / p)


def pnl_mensual(trades: pd.DataFrame) -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=float)
    mes = pd.to_datetime(trades["salida_ts"], unit="ms", utc=True).dt.tz_localize(None).dt.to_period("M")
    return trades.groupby(mes.values)["pnl"].sum()


def pnl_diario(trades: pd.DataFrame) -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=float)
    dia = pd.to_datetime(trades["salida_ts"], unit="ms", utc=True).dt.tz_localize(None).dt.floor("D")
    s = trades.groupby(dia.values)["pnl"].sum()
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"), fill_value=0.0)


def resumen(trades: pd.DataFrame, margen_usd: float = 20.0) -> Dict[str, Optional[float]]:
    """Resumen de una lista de operaciones (en $ con la posición configurada y en R)."""
    if trades.empty:
        return {"n": 0}
    pnl = trades["pnl"].to_numpy()
    R = trades["R"].to_numpy()
    gan, per = pnl[pnl > 0], pnl[pnl <= 0]
    mensual = pnl_mensual(trades)
    diario = pnl_diario(trades)
    sharpe = None
    if len(diario) > 30 and diario.std(ddof=1) > 0:
        sharpe = float(diario.mean() / diario.std(ddof=1) * math.sqrt(365))
    dias = max((trades["salida_ts"].max() - trades["entrada_ts"].min()) / 86_400_000, 1e-9)
    return {
        "n": int(len(trades)),
        "aciertos": float((pnl > 0).mean()),
        "ganancia_media": float(gan.mean()) if len(gan) else 0.0,
        "perdida_media": float(per.mean()) if len(per) else 0.0,
        "expectativa_usd": float(pnl.mean()),
        "expectativa_R": float(R.mean()),
        "beneficio_total": float(pnl.sum()),
        "profit_factor": profit_factor(pnl),
        "dd_max": max_drawdown(pnl),
        "peor_racha": peor_racha(pnl),
        "sharpe_anual": sharpe,
        "meses_positivos": float((mensual > 0).mean()) if len(mensual) else None,
        "n_meses": int(len(mensual)),
        "ops_por_dia": float(len(trades) / dias),
        "comisiones": float(trades["comisiones"].sum()),
        "funding": float(trades["funding"].sum()),
    }


def sin_mejores(trades: pd.DataFrame) -> Dict[str, float]:
    """Concentración: beneficio sin la mejor semana y sin las 5 mejores operaciones; peso de la mejor moneda."""
    if trades.empty:
        return {}
    sem = pd.to_datetime(trades["salida_ts"], unit="ms", utc=True).dt.tz_localize(None).dt.to_period("W")
    por_sem = trades.groupby(sem.values)["pnl"].sum()
    top5 = trades["pnl"].nlargest(5).sum()
    total = trades["pnl"].sum()
    por_moneda = trades.groupby("simbolo")["pnl"].sum()
    pos = por_moneda[por_moneda > 0].sum()
    return {
        "sin_mejor_semana": float(total - por_sem.max()),
        "sin_5_mejores_ops": float(total - top5),
        "peso_mejor_moneda": float(por_moneda.max() / pos) if pos > 0 else float("nan"),
    }


def estres_costes(pnl: np.ndarray, comisiones: np.ndarray, mult: float) -> np.ndarray:
    """Costes x mult aproximados a posteriori: pnl' = pnl - (mult-1) * comisiones (el deslizamiento se
    re-simula en el motor; esto es una cota rápida solo de comisiones). Usa ``estres_motor`` para el resto."""
    return pnl - (mult - 1.0) * comisiones


def coste_equilibrio(pnl: np.ndarray, costes_totales: np.ndarray) -> Optional[float]:
    """Multiplicador de costes al que la expectativa se hace 0: (beneficio bruto) / (costes)."""
    c = costes_totales.sum()
    if c <= 0:
        return None
    bruto = pnl.sum() + c
    return float(bruto / c)


def supervivencia(objetivo_R: float, coste_R: float, stop_R: float = 1.0) -> float:
    """% de aciertos mínimo para no perder = (stop + costes) / (objetivo + stop)."""
    return (stop_R + coste_R) / (objetivo_R + stop_R)


# ----------------------------------------------------------------------------------------------
# Significación: Deflated Sharpe Ratio (Bailey & López de Prado, 2014)
# ----------------------------------------------------------------------------------------------
def sharpe_periodo(r: np.ndarray) -> float:
    r = np.asarray(r, float)
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else 0.0


def sr_esperado_maximo(n_trials: int, var_sr: float) -> float:
    """SR0: Sharpe máximo esperado entre n_trials pruebas independientes sin ventaja."""
    if n_trials <= 1:
        return 0.0
    g = 0.5772156649015329
    return math.sqrt(max(var_sr, 0.0)) * ((1 - g) * stats.norm.ppf(1 - 1.0 / n_trials)
                                          + g * stats.norm.ppf(1 - 1.0 / (n_trials * math.e)))


def dsr(r: np.ndarray, n_trials: int, var_sr_pruebas: Optional[float] = None) -> Optional[float]:
    """Probabilidad de que el Sharpe verdadero sea > 0 tras corregir por el nº de pruebas y la no-normalidad.

    ``r`` = rendimientos por periodo (p. ej. $ diarios). ``var_sr_pruebas`` = varianza del Sharpe por periodo entre
    TODAS las pruebas registradas (trials_log.csv). Si no se conoce, devuelve None (NO CALCULADO).
    """
    r = np.asarray(r, float)
    T = len(r)
    if T < 30 or r.std(ddof=1) == 0:
        return NO_CALC
    sr = sharpe_periodo(r)
    if n_trials > 1 and var_sr_pruebas is None:
        return NO_CALC
    sr0 = sr_esperado_maximo(n_trials, var_sr_pruebas or 0.0)
    g3 = float(stats.skew(r))
    g4 = float(stats.kurtosis(r, fisher=False))
    den = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2
    if den <= 0:
        return NO_CALC
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(den)
    return float(stats.norm.cdf(z))


# ----------------------------------------------------------------------------------------------
# PBO con CSCV (Bailey, Borwein, López de Prado & Zhu, 2015)
# ----------------------------------------------------------------------------------------------
def pbo_cscv(M: np.ndarray, S: int = 16, max_comb: int = 4000, seed: int = 0) -> Optional[dict]:
    """M: matriz T x N (periodos x configuraciones probadas) de rendimientos.

    Devuelve la probabilidad de que la mejor configuración en muestra quede por debajo de la mediana fuera de muestra.
    """
    M = np.asarray(M, float)
    T, N = M.shape
    if N < 2 or T < S * 2:
        return NO_CALC
    S = S - (S % 2)
    bloques = np.array_split(np.arange(T), S)
    combos = list(itertools.combinations(range(S), S // 2))
    if len(combos) > max_comb:
        rng = np.random.default_rng(seed)
        combos = [combos[i] for i in rng.choice(len(combos), max_comb, replace=False)]
    logits = []
    for comb in combos:
        is_idx = np.concatenate([bloques[i] for i in comb])
        oos_idx = np.concatenate([bloques[i] for i in range(S) if i not in comb])
        a, b = M[is_idx], M[oos_idx]
        sr_is = a.mean(0) / np.where(a.std(0, ddof=1) > 0, a.std(0, ddof=1), np.inf)
        sr_oos = b.mean(0) / np.where(b.std(0, ddof=1) > 0, b.std(0, ddof=1), np.inf)
        best = int(np.argmax(sr_is))
        rank = (sr_oos < sr_oos[best]).sum() + 0.5 * ((sr_oos == sr_oos[best]).sum() - 1)
        w = (rank + 1) / (N + 1)
        logits.append(math.log(w / (1 - w)))
    logits = np.array(logits)
    return {"pbo": float((logits <= 0).mean()), "n_combinaciones": len(logits), "n_configs": N}


# ----------------------------------------------------------------------------------------------
# Monte Carlo por bloques y otras pruebas
# ----------------------------------------------------------------------------------------------
def monte_carlo_bloques(pnl: np.ndarray, n: int = 10_000, bloque: int = 10, seed: int = 0) -> Optional[dict]:
    """Remuestreo por bloques de la secuencia de operaciones: drawdown, peor racha y beneficio en p5/p50/p95."""
    pnl = np.asarray(pnl, float)
    L = len(pnl)
    if L < 30:
        return NO_CALC
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(L / bloque))
    starts = rng.integers(0, L - bloque + 1, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(bloque)[None, None, :]).reshape(n, -1)[:, :L]
    sim = pnl[idx]
    eq = np.cumsum(sim, axis=1)
    eq0 = np.concatenate([np.zeros((n, 1)), eq], axis=1)
    dd = (np.maximum.accumulate(eq0, axis=1) - eq0).max(axis=1)
    perd = sim <= 0
    racha = np.zeros(n, int)
    cur = np.zeros(n, int)
    for k in range(L):
        cur = np.where(perd[:, k], cur + 1, 0)
        racha = np.maximum(racha, cur)
    q = lambda x: {"p5": float(np.percentile(x, 5)), "p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95))}
    return {"dd": q(dd), "racha": q(racha), "beneficio": q(eq[:, -1])}


def test_permutacion_signo(pnl: np.ndarray, n: int = 1000, seed: int = 0) -> Optional[float]:
    """p-valor: ¿cuántas veces una secuencia con signos aleatorios iguala la expectativa observada?"""
    pnl = np.asarray(pnl, float)
    if len(pnl) < 30:
        return NO_CALC
    rng = np.random.default_rng(seed)
    obs = pnl.mean()
    m = np.abs(pnl)
    signos = rng.choice([-1.0, 1.0], size=(n, len(pnl)))
    return float(((signos * m).mean(1) >= obs).mean())


def meseta(evaluar: Callable[[dict], float], params: dict, rel: float = 0.2, enteros: Iterable[str] = ()) -> dict:
    """Mapa de vecinos ±rel de cada parámetro (uno a uno y combinaciones de esquinas).

    ``evaluar(params)`` devuelve la expectativa (R o $) fuera de muestra. Se exige que >=70 % de vecinos sean > 0.
    """
    enteros = set(enteros)
    claves = list(params)
    vecinos = []
    for k in claves:
        for f in (1 - rel, 1 + rel):
            p = dict(params)
            v = params[k] * f
            p[k] = int(round(v)) if k in enteros else v
            vecinos.append(p)
    if len(claves) <= 4:
        for signos in itertools.product((-1, 1), repeat=len(claves)):
            p = dict(params)
            for k, s in zip(claves, signos):
                v = params[k] * (1 + s * rel)
                p[k] = int(round(v)) if k in enteros else v
            vecinos.append(p)
    vals = [evaluar(p) for p in vecinos]
    vals = [v for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return {"frac_positivos": NO_CALC, "n_vecinos": 0}
    return {"frac_positivos": float(np.mean(np.array(vals) > 0)), "n_vecinos": len(vals),
            "min": float(np.min(vals)), "mediana": float(np.median(vals))}


# ----------------------------------------------------------------------------------------------
# Criterios §8
# ----------------------------------------------------------------------------------------------
UMBRALES = {
    "ops_min": 150, "ops_min_diario": 60, "pf_min": 1.25, "meses_pos_min": 0.60,
    "dsr_min": 0.90, "pbo_max": 0.35, "meseta_min": 0.70,
}


def clasificar(c: dict) -> tuple[str, list[str]]:
    """Aplica §8 sobre un dict con las métricas OOS. Falta un dato => ese criterio FALLA (no se asume)."""
    fallos, dudosos = [], []
    n_min = UMBRALES["ops_min_diario"] if c.get("marco_diario") else (1000 if c.get("segundos") else UMBRALES["ops_min"])

    def chk(nombre: str, cond: Optional[bool], cerca: bool = False):
        if cond is None:
            fallos.append(f"{nombre}: NO CALCULADO")
        elif not cond:
            (dudosos if cerca else fallos).append(nombre)

    g = c.get
    chk("operaciones", None if g("n") is None else g("n") >= n_min, cerca=(g("n") or 0) >= 0.8 * n_min)
    chk("expectativa_costes_x1.5", None if g("exp_x15") is None else g("exp_x15") > 0)
    pf = g("profit_factor")
    chk("profit_factor", None if pf is None else pf >= UMBRALES["pf_min"], cerca=(pf or 0) >= 1.15)
    mp = g("meses_positivos")
    chk("meses_positivos", None if mp is None else mp >= UMBRALES["meses_pos_min"], cerca=(mp or 0) >= 0.5)
    d = g("dsr")
    chk("DSR", None if d is None else d >= UMBRALES["dsr_min"], cerca=(d or 0) >= 0.8)
    p = g("pbo")
    chk("PBO", None if p is None else p <= UMBRALES["pbo_max"], cerca=(p is not None and p <= 0.45))
    me = g("meseta")
    chk("meseta", None if me is None else me >= UMBRALES["meseta_min"], cerca=(me or 0) >= 0.6)
    chk("sin_mejor_semana", None if g("sin_mejor_semana") is None else g("sin_mejor_semana") > 0)
    chk("sin_5_mejores_ops", None if g("sin_5_mejores_ops") is None else g("sin_5_mejores_ops") > 0)
    ho = g("holdout_exp")
    if ho is None and g("holdout_regimen_ausente"):
        pass
    else:
        chk("holdout", None if ho is None else ho > 0)
    duros = [f for f in fallos if "NO CALCULADO" not in f]
    faltan = [f for f in fallos if "NO CALCULADO" in f]
    if duros:
        return "RECHAZADA", duros + dudosos + faltan
    if faltan:
        # No se puede declarar APTA (ni RECHAZADA) con datos que faltan: pendiente de calcular.
        return "INCOMPLETA", faltan + dudosos
    if not dudosos:
        return "APTA", []
    if len(dudosos) <= 2:
        return "PROMETEDORA", dudosos
    return "RECHAZADA", dudosos


def score(mediana_cpcv_exp_R: float, n_oos: int, frac_meses_pos: float, pbo: float, dd_p95: float, benef_oos: float) -> float:
    """§9: mediana_CPCV(exp_R) * sqrt(n_OOS) * %meses_pos * (1-PBO) - 0.5 * DDmax_p95 / beneficio_OOS."""
    pen = 0.5 * dd_p95 / benef_oos if benef_oos > 0 else 10.0
    return float(mediana_cpcv_exp_R * math.sqrt(max(n_oos, 0)) * frac_meses_pos * (1 - pbo) - pen)
