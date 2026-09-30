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
from .descarga import CACHE, PERIODO, RAIZ, ts, http_get

RES = RAIZ / "resultados"


# ----------------------------------------------------------------------------------------------
def btc_diario() -> pd.DataFrame:
    """BTCUSDT 1d desde 2022-01 (para tener SMA200 y percentiles desde el primer día de búsqueda). Solo hasta busqueda_fin."""
    p = CACHE / "klines" / "btc_1d_largo.parquet"
    if not p.exists():
        partes = []
        for m in D.meses_entre(pd.Timestamp("2022-01-01"), pd.Timestamp("2024-06-30")):
            r = http_get(f"{D.BASE}/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{m}.zip")
            if r is not None:
                partes.append(D.leer_klines_zip(r.content))
        partes.append(pd.read_parquet(CACHE / "klines" / "1d" / "BTCUSDT.parquet").astype({"qv": "float64", "v": "float64", "tb_v": "float64", "tb_qv": "float64", "n": "int64"}))
        g = pd.concat(partes, ignore_index=True).sort_values("t").drop_duplicates("t")
        g.to_parquet(p)
    g = pd.read_parquet(p)
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
def grid(rapido: bool = False) -> List[dict]:
    """Catálogo de Ronda 1: familias A, B, C con parámetros clásicos, sus inversas y todas las salidas de EXITS_R1."""
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


def main() -> int:
    rapido = "--rapido" in sys.argv
    RES.mkdir(exist_ok=True)
    t0 = time.time()
    sel = json.loads((RAIZ / "UNIVERSO.json").read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, etiquetas = codigo_dia_busqueda()
    print("régimen, días por etiqueta (búsqueda):",
          {(RG.ORDEN[i] if i < len(RG.ORDEN) else "sin_etiqueta"): int((cod == i).sum()) for i in np.unique(cod)}, flush=True)
    jobs = grid(rapido)
    print(f"jobs: {len(jobs)}  -> pruebas (x salidas x lados): {len(jobs) * len(BR.EXITS_R1) * 3}", flush=True)
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
    # DSR con el total real de pruebas (todas las combinaciones lanzadas, también las sin operaciones suficientes)
    n_trials = len(jobs) * len(BR.EXITS_R1) * 3
    var_sr = float(np.nanvar(df["sharpe_dia"].to_numpy(), ddof=1))
    df["dsr"] = [M.dsr(diarios[t].astype(float), n_trials, var_sr) if n >= 30 else np.nan for t, n in zip(df["trial"], df["n"])]
    df.to_parquet(RES / "ronda1.parquet")
    np.savez_compressed(RES / "ronda1_diario.npz", **{k.replace("|", "__"): v for k, v in diarios.items()})
    for r in df.itertuples():
        trials.registrar(dict(ronda=1, estrategia=r.fam, marco_min=r.tf, params=r.params, salida=r.salida, segmento="reducido50",
                              regimen="todos", lado=r.lado, n_ops=r.n, exp_R=round(r.exp_R, 5), beneficio_usd=round(r.beneficio, 2),
                              sharpe_periodo=round(r.sharpe_dia, 5), tramo="busqueda_24m"))
    print(f"terminado en {time.time() - t0:.0f}s; pruebas con operaciones: {len(df)} de {n_trials}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
