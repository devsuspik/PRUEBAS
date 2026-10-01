"""Expediente §8 del corto de listados nuevos (regla pre-registrada), con los 4 periodos agrupados."""
import itertools
import json

import numpy as np
import pandas as pd

from . import listados as LI
from . import listados_1m as L1
from . import metricas as M
from .config import CFG
from .motor import filtro_cartera
from .periodo import NOMBRE, RES


def correr_periodo():
    ev = LI.eventos()
    cache = [(s, g, L1.cargar_evento(s, g)) for s, g in ev]
    cache = [(s, g, d) for s, g, d in cache if d is not None]

    def sim(stop=0.08, tgt=0.40, dias=7):
        L1.cargar_evento = lambda s, g, _c={s: d for s, g, d in cache}: _c.get(s)      # evita recargar parquet en cada vecino
        return L1.simular([(s, g) for s, g, d in cache], stop=stop, obj_R=tgt / stop, dias=dias)
    base = sim()
    vec = {}
    for stop, tgt, dias in itertools.product((0.064, 0.08, 0.096), (0.32, 0.40, 0.48), (6, 7, 8)):
        if (stop, tgt, dias) == (0.08, 0.40, 7):
            continue
        t = sim(stop, tgt, dias)
        vec[f"stop={stop:.3f},obj={tgt:.2f},dias={dias}"] = (len(t), float(t.pnl.mean()) if len(t) else np.nan, float(t.pnl.sum()) if len(t) else np.nan)
    base["periodo"] = NOMBRE
    base.to_parquet(RES / "ficha_listados_trades.parquet")
    json.dump(vec, open(RES / "ficha_listados_vecinos.json", "w"))


def agregar():
    from .periodo import RAIZ
    dirs = {"val0": RAIZ / "resultados_val0", "val1": RAIZ / "resultados_val1", "val2": RAIZ / "resultados_val2", "reciente": RAIZ / "resultados"}
    t = pd.concat([pd.read_parquet(d / "ficha_listados_trades.parquet") for d in dirs.values()], ignore_index=True)
    t["fecha"] = pd.to_datetime(t.entrada_ts, unit="ms")
    t = t.sort_values("fecha").reset_index(drop=True)
    pnl = t.pnl.to_numpy()
    print(f"OPERACIONES agrupadas: {len(t)} | aciertos {np.mean(pnl > 0):.2f} | exp ${pnl.mean():+.2f} | PF {M.profit_factor(pnl):.2f} | total ${pnl.sum():+.0f}")
    print("por periodo:", t.groupby("periodo").pnl.agg(["size", "mean", "sum"]).round(2).to_dict("index"))
    # meses positivos (por mes de entrada, solo meses con operaciones)
    mes = t.groupby(t.fecha.dt.to_period("M")).pnl.sum()
    print(f"meses con operaciones: {len(mes)} | positivos {np.mean(mes > 0):.0%} | mejor mes ${mes.max():+.0f} ({mes.idxmax()}) | sin el mejor mes ${pnl.sum() - mes.max():+.0f}")
    sem = t.groupby(t.fecha.dt.to_period("W")).pnl.sum()
    print(f"sin la mejor semana ${pnl.sum() - sem.max():+.0f} | sin las 5 mejores operaciones ${pnl.sum() - np.sort(pnl)[-5:].sum():+.0f} | sin las 10 mejores ${pnl.sum() - np.sort(pnl)[-10:].sum():+.0f}")
    by = t.groupby("simbolo").pnl.sum(); pos = by[by > 0].sum()
    print(f"monedas distintas {t.simbolo.nunique()} | peso de la mejor moneda {by.max() / pos:.1%}")
    # por periodo: sin 5 mejores
    for p, g in t.groupby("periodo"):
        x = g.pnl.to_numpy(); print(f"  {p}: n={len(x)} total ${x.sum():+.0f} sin 5 mejores ${x.sum() - np.sort(x)[-5:].sum():+.0f} PF {M.profit_factor(x):.2f}")
    # MC por bloques sobre las operaciones en orden cronológico
    mc = M.monte_carlo_bloques(pnl, n=10000, bloque=10)
    print("Monte Carlo (10.000 bloques): drawdown p5/p50/p95 = %.0f/%.0f/%.0f $ | peor racha de pérdidas p95 = %.0f ops | beneficio p5/p50/p95 = %.0f/%.0f/%.0f $" % (
        mc["dd"]["p5"], mc["dd"]["p50"], mc["dd"]["p95"], mc["racha"]["p95"], mc["beneficio"]["p5"], mc["beneficio"]["p50"], mc["beneficio"]["p95"]))
    # DSR / PBO sobre los retornos por evento de la familia de 81 combos de cortos (daily-bar), pooled
    return t


def matriz_periodo():
    """Retornos netos por evento (barras diarias) de las 81 combinaciones CORTAS del grid, ordenados por fecha de listado."""
    ev = LI.eventos()
    combos = list(itertools.product((1, 3, 7), (0.08, 0.15, 0.25), (0.10, 0.20, 0.40), (3, 7, 14)))
    filas, fechas = [], []
    for s, g in ev:
        if len(g) < 7 + 14 + 2:
            continue
        filas.append([LI.trade(g, k, -1, st, ob, h) - LI.COSTE for k, st, ob, h in combos])
        fechas.append(g.index[0])
    np.savez(RES / "ficha_listados_matriz.npz", fechas=np.array([f.value for f in fechas]), M=np.array(filas), periodo=NOMBRE)


def pruebas_finales():
    from scipy import stats
    from .periodo import RAIZ
    mats = [np.load(d / "ficha_listados_matriz.npz") for d in (RAIZ / "resultados_val0", RAIZ / "resultados_val1", RAIZ / "resultados_val2", RAIZ / "resultados")]
    f = np.concatenate([m["fechas"] for m in mats]); X = np.vstack([m["M"] for m in mats])
    o = np.argsort(f); X = X[o]
    combos = list(itertools.product((1, 3, 7), (0.08, 0.15, 0.25), (0.10, 0.20, 0.40), (3, 7, 14)))
    pb = M.pbo_cscv(X, S=16, max_comb=4000)
    print(f"PBO (CSCV, 81 combinaciones cortas, {X.shape[0]} eventos agrupados): {pb['pbo']:.3f}")
    # DSR de la regla principal con N = 162 pruebas exploratorias (81 cortas + 81 largas) y varianza del Sharpe por evento entre combinaciones
    j = combos.index((1, 0.08, 0.40, 7))
    r = X[:, j]
    srs = X.mean(0) / X.std(0, ddof=1)
    for N in (1, 24, 162, 23466):
        d = M.dsr(r, N, float(np.var(srs, ddof=1))) if N > 1 else M.dsr(r, 1)
        print(f"DSR regla principal (retornos por evento, T={len(r)}), N pruebas={N}: {d:.3f}" if d is not None else f"DSR N={N}: NO CALCULADO")
    print(f"Sharpe por evento de la regla principal: {r.mean() / r.std(ddof=1):.3f} (mejor combinación del grid: {srs.max():.3f}, mediana {np.median(srs):.3f})")
    # meseta: vecinos a 1 m (guardados por periodo)
    pool = {}
    for d in (RAIZ / "resultados_val0", RAIZ / "resultados_val1", RAIZ / "resultados_val2", RAIZ / "resultados"):
        for k, (n, m, tot) in json.load(open(d / "ficha_listados_vecinos.json")).items():
            a = pool.setdefault(k, [0, 0.0]); a[0] += n; a[1] += (tot if tot == tot else 0.0)
    ex = {k: v[1] / v[0] for k, v in pool.items() if v[0] > 0}
    print(f"MESETA (vecinos ±20 % a 1 m, 4 periodos agrupados): {sum(1 for v in ex.values() if v > 0)}/{len(ex)} con expectativa > 0 | mín ${min(ex.values()):+.2f} mediana ${np.median(list(ex.values())):+.2f}")
    print("  vecinos no positivos:", {k: round(v, 2) for k, v in ex.items() if v <= 0})


if __name__ == "__main__":
    import sys
    if "--matriz" in sys.argv:
        matriz_periodo()
    elif "--finales" in sys.argv:
        pruebas_finales()
    elif "--agregar" in sys.argv:
        agregar()
    else:
        correr_periodo()
