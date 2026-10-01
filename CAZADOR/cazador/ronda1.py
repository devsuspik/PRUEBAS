"""Ronda 1 – barrido del catálogo con parámetros clásicos, en varios marcos y con costes reales.

Uso:  python -m cazador.ronda1 [--rapido]        (--rapido: 1/5 del grid, para comprobar la tubería)
Escribe: resultados/ronda1.parquet, resultados/ronda1_diario.npz, trials_log.csv y INFORME_RONDA1.md
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from . import barrido as BR
from . import datos as D
from . import metricas as M
from . import regimenes as RG
from . import trials, universo
from .config import CFG
from .descarga import CACHE, PERIODO, RAIZ, ts
from .datos import http_get

from .periodo import RES, UNIV


# ----------------------------------------------------------------------------------------------
def btc_diario() -> pd.DataFrame:
    """BTCUSDT 1d con 20 meses de historia previa al inicio de búsqueda (SMA200 y percentiles desde el primer día). Solo hasta busqueda_fin."""
    p = CACHE / "klines" / "btc_1d_largo.parquet"
    if not p.exists():
        ini = pd.Timestamp(PERIODO["busqueda_ini"]) - pd.DateOffset(months=20)
        fin = pd.Timestamp(PERIODO["busqueda_fin"])
        partes = []
        for m in D.meses_entre(ini, fin):
            if pd.Period(m, "M").end_time.normalize() > fin:
                break
            r = http_get(f"{D.BASE}/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{m}.zip")
            if r is not None:
                partes.append(D.leer_klines_zip(r.content))
        g = pd.concat(partes, ignore_index=True).sort_values("t").drop_duplicates("t")
        p.parent.mkdir(parents=True, exist_ok=True)
        g.to_parquet(p)
    g = pd.read_parquet(p)
    fin_ms = int((pd.Timestamp(PERIODO["busqueda_fin"]) + pd.Timedelta(days=1)).timestamp() * 1000)
    if g["t"].max() < fin_ms - 2 * 86_400_000:                       # la caché larga acaba antes: se completa con el 1d reciente
        r = pd.read_parquet(CACHE / "klines" / "1d" / "BTCUSDT.parquet").astype(
            {"qv": "float64", "v": "float64", "tb_v": "float64", "tb_qv": "float64", "n": "int64"})
        g = pd.concat([g, r], ignore_index=True).sort_values("t").drop_duplicates("t")
    g.index = pd.to_datetime(g["t"], unit="ms").dt.floor("D")
    return g.loc[: PERIODO["busqueda_fin"]]


def codigo_dia_busqueda() -> tuple[np.ndarray, pd.DataFrame]:
    """Código de régimen (índice en ORDEN; NREG-1 = sin etiqueta) que rige cada día de búsqueda = etiqueta del día ANTERIOR."""
    btc = btc_diario()
    e = RG.etiquetas_macro(btc)
    cod = e["regimen"].map({k: i for i, k in enumerate(RG.ORDEN)})
    ayer = cod.shift(1)
    dias = pd.date_range(PERIODO["busqueda_ini"], periods=BR.ND)
    out = ayer.reindex(dias).fillna(BR.NREG - 1).astype(int).to_numpy()
    return out, e


# ----------------------------------------------------------------------------------------------
def grid_a(rapido: bool = False) -> List[dict]:
    """Catálogo de Ronda 1 (A): familias A, B, C originales con parámetros clásicos, sus inversas y todas las salidas de EXITS_R1."""
    base: List[dict] = []
    for tf in (15, 60, 240, 1440):
        for r, l in ((9, 21), (20, 50), (50, 200)):
            base.append(dict(fam="ema_cross", tf=tf, params=dict(rapida=r, lenta=l, k_atr=2.0)))
        for n in (20, 55):
            base.append(dict(fam="donchian", tf=tf, params=dict(n=n, k_atr=2.0)))
        for th in (5, 10):
            base.append(dict(fam="rsi2", tf=tf, params=dict(umbral=float(th), sma_filtro=200, k_atr=2.0)))
    for tf, ns in ((240, (42, 84, 180)), (1440, (7, 14, 30, 60))):
        for n in ns:
            base.append(dict(fam="tsmom", tf=tf, params=dict(n=n, k_atr=3.0)))
    for tf in (5, 15, 60, 240):
        for ks in (2.0, 2.5, 3.0):
            base.append(dict(fam="bollinger_rev", tf=tf, params=dict(n=20, k_sigma=ks, k_atr=2.0)))
    for tf in (5, 15, 30):
        for h in (0.0, 7.0, 13.5):
            for k in (1.0, 1.5):
                base.append(dict(fam="orb_sesion", tf=tf, params=dict(hora_inicio_utc=h, minutos_rango=60, k_atr=k)))
    jobs, i = [], 0
    for b in base:
        for inv in (False, True):
            jobs.append({**b, "inv": inv, "id": i, "exits": BR.EXITS_R1})
            i += 1
    if rapido:
        jobs = jobs[::5]
    return jobs


def grid_b() -> List[dict]:
    """Catálogo de Ronda 1 (B): derivados, flujo, estacionalidad, velas, reversión y rupturas adicionales."""
    T4 = (15, 60, 240, 1440)
    b: List[dict] = []
    f = lambda fam, tf, **p: b.append(dict(fam=fam, tf=tf, params=p))
    for tf in (60, 240):
        for pct in (0.90, 0.95, 0.98):
            for k in (2.0, 3.0):
                f("funding_extremo", tf, pct=pct, k_atr=k)
    for tf in (5, 15, 60):
        for n in (6, 12):
            for um in (0.56, 0.60):
                f("flujo_taker", tf, n=n, umbral=um, k_atr=2.0)
    for tf in T4:
        for t in (False, True):
            f("engulfing", tf, tendencia=t, k_atr=2.0)
            f("inside_bar", tf, tendencia=t, k_atr=2.0)
            for r in (2.0, 3.0):
                f("pin_bar", tf, ratio=r, tendencia=t, k_atr=2.0)
    for tf in (5, 15, 60):
        for k in (1.5, 2.5):
            f("vwap_dev", tf, k=k, k_atr=2.0)
    for tf in (15, 60, 240):
        for n in (20, 50):
            f("barrida_liquidez", tf, n=n, k_atr=1.5)
        for k in (2.5, 3.0):
            f("zscore_rev", tf, n=50, k=k, k_atr=2.0)
        f("squeeze_bk", tf, n=20, pct_ancho=0.2, k_atr=2.0)
    for um in (0.10, 0.15, 0.25):
        f("sobreextension", 60, horas=24, umbral=um, k_atr=3.0)
    for um in (0.20, 0.30):
        f("sobreextension", 60, horas=72, umbral=um, k_atr=3.0)
    for tf in (60, 240, 1440):
        f("nr7", tf, k_atr=2.0)
    for tf in (15, 60):
        f("max_min_ayer", tf, k_atr=1.5)
    for tf in (60, 240, 1440):
        for m in (2.0, 3.0):
            f("supertrend", tf, periodo=10, mult=m, k_atr=2.0)
    for tf in (60, 240):
        f("adx_retroceso", tf, adx_min=25.0, ema_n=20, k_atr=2.0)
    for tf in (240, 1440):
        for dias in (60, 180):
            f("max_n_dias", tf, dias=dias, k_atr=3.0)
    jobs, i = [], 10_000
    for x in b:
        for inv in (False, True):
            jobs.append({**x, "inv": inv, "id": i, "exits": BR.EXITS_R1})
            i += 1
    # estacionalidad: salidas solo por tiempo
    for h in range(24):
        for inv in (False, True):
            jobs.append(dict(fam="hora_dia", tf=60, params=dict(hora=float(h), k_atr=3.0), inv=inv, id=i, exits=BR.EXITS_TIEMPO_G))
            i += 1
    for d in range(7):
        for inv in (False, True):
            jobs.append(dict(fam="dia_semana", tf=60, params=dict(dow=d, hora=0.0, k_atr=3.0), inv=inv, id=i, exits=["t12h", "t24h", "t48h", "t72h"]))
            i += 1
    return jobs


def grid_c(mat: dict) -> List[dict]:
    """Ronda 1 (C): transversales (F). Señales precalculadas en el proceso principal."""
    from . import transversal as TR
    jobs, i = [], 20_000
    for L in (24, 72, 168, 720):
        for R in (4, 24, 168):
            for k in (3, 5):
                for modo in ("momentum", "reversion"):
                    sen = TR.senales(mat, L, R, k, modo)
                    jobs.append(dict(fam=f"transv_{modo}", tf=60, params=dict(L=L, R=R, k=k), inv=(modo == "reversion"), id=i,
                                     exits=[f"t{R}h"], senales_pre=sen))
                    i += 1
    return jobs


def grid_e() -> List[dict]:
    """Ronda 1 (E): familias de tendencia con 'mantener hasta la señal contraria' (baja rotación) y stop de catástrofe ancho."""
    b: List[dict] = []
    f = lambda fam, tf, **p: b.append(dict(fam=fam, tf=tf, params=p))
    for tf in (60, 240, 1440):
        for k in (3.0, 4.0):
            for r, l in ((9, 21), (20, 50), (50, 200)):
                f("ema_cross", tf, rapida=r, lenta=l, k_atr=k)
            for n in (20, 55, 100):
                f("donchian", tf, n=n, k_atr=k)
            for m in (2.0, 3.0):
                f("supertrend", tf, periodo=10, mult=m, k_atr=k)
    for tf, ns in ((240, (42, 84, 180)), (1440, (7, 14, 30, 60))):
        for n in ns:
            for k in (3.0, 4.0):
                f("tsmom", tf, n=n, k_atr=k)
    jobs, i = [], 40_000
    for x in b:
        for inv in (False, True):
            jobs.append({**x, "inv": inv, "id": i, "exits": ["hold", "hold_trail4R"], "contraria": True})
            i += 1
    return jobs


def grid(rapido: bool = False, cual: str = "a", mat: dict | None = None) -> List[dict]:
    if cual == "b":
        return grid_b()
    if cual == "c":
        return grid_c(mat)
    if cual == "e":
        return grid_e()
    return grid_a(rapido)


def main() -> int:
    rapido = "--rapido" in sys.argv
    cual = "b" if "--grid-b" in sys.argv else ("c" if "--grid-c" in sys.argv else ("e" if "--grid-e" in sys.argv else "a"))
    pref = {"a": "ronda1", "b": "ronda1b", "c": "ronda1c", "e": "ronda1e"}[cual]
    RES.mkdir(exist_ok=True)
    t0 = time.time()
    sel = json.loads(UNIV.read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, etiquetas = codigo_dia_busqueda()
    print("régimen, días por etiqueta (búsqueda):",
          {(RG.ORDEN[i] if i < len(RG.ORDEN) else "sin_etiqueta"): int((cod == i).sum()) for i in np.unique(cod)}, flush=True)
    mat = None
    if cual == "c":
        from . import transversal as TR
        mat = TR.preparar(sel, miembros)
        print(f"matriz transversal: {mat['nh']} horas x {len(mat['syms'])} monedas", flush=True)
    jobs = grid(rapido, cual, mat)
    n_trials = sum(len(j['exits']) for j in jobs) * 3
    print(f"jobs: {len(jobs)}  -> pruebas (x salidas x lados): {n_trials}", flush=True)
    agg = BR.barrido(jobs, sel, miembros, cod, nproc=4, tam_lote=6, log=lambda *a: print(*a, flush=True))

    # ---- métricas y registro de pruebas
    info = {j["id"]: j for j in jobs}
    filas, diarios = [], {}
    for (jid, ex, lado), a in agg.items():
        j = info[jid]
        m = BR.metricas(a)
        tid = f"{jid}|{ex}|{lado}"
        fila = {"trial": tid, "fam": j["fam"], "tf": j["tf"], "inv": j["inv"], "params": json.dumps(j["params"], sort_keys=True),
                "salida": ex, "lado": lado, **m}
        for r in range(BR.NREG):
            fila[f"reg{r}_n"] = int(a["reg_n"][r])
            fila[f"reg{r}_pnl"] = float(a["reg_pnl"][r])
        filas.append(fila)
        diarios[tid] = a["d_pnl"].astype("float32")
    df = pd.DataFrame(filas)
    # el DSR se calcula en ranking.py con el total REAL de pruebas de todos los barridos
    df.to_parquet(RES / f"{pref}.parquet")
    np.savez_compressed(RES / f"{pref}_diario.npz", **{k.replace("|", "__"): v for k, v in diarios.items()})
    for r in df.itertuples():
        trials.registrar(dict(ronda=1, estrategia=r.fam, marco_min=r.tf, params=r.params, salida=r.salida, segmento="reducido50",
                              regimen="todos", lado=r.lado, n_ops=r.n, exp_R=round(r.exp_R, 5), beneficio_usd=round(r.beneficio, 2),
                              sharpe_periodo=round(r.sharpe_dia, 5), tramo="busqueda_24m"))
    print(f"terminado en {time.time() - t0:.0f}s; pruebas con operaciones: {len(df)} de {n_trials}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
