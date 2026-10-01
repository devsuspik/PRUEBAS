"""Ronda 2 – optimización robusta con walk-forward y filtros de régimen.

Para cada CELDA candidata (familia, marco, inversa) elegida en Ronda 1:
  1. variantes de parámetros alrededor del valor clásico (<= 5 parámetros libres: stop k_atr, hasta 2 parámetros de señal,
     salida, lado y filtro de régimen);
  2. se simula TODO con curvas diarias por régimen (el régimen es el de la ENTRADA, que solo usa información previa);
  3. walk-forward: cada mes se elige la combinación (variante x salida x lado x filtro) con mejor Sharpe en los 6 meses previos
     y se aplica al mes siguiente; solo cuentan los meses de prueba encadenados.
Se evalúan dos procedimientos por celda: SIN filtro de régimen (línea base) y CON filtros, para medir si el régimen aporta algo.

Uso: python -m cazador.ronda2 [--celdas N]
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from . import barrido as BR
from . import estrategias as E
from . import metricas as M
from . import regimenes as RG
from . import ranking as RK
from . import ronda1, trials, universo, walkforward as WF
from .config import CFG
from .descarga import RAIZ

from .periodo import RES, UNIV
IDX = {nm: i for i, nm in enumerate(RG.ORDEN)}
TODOS = list(range(BR.NREG))
FILTROS: Dict[str, List[int]] = {
    "todos": TODOS,
    "alcista+euforia": [IDX[RG.ALCISTA], IDX[RG.EUFORIA]],
    "bajista+capit": [IDX[RG.BAJISTA], IDX[RG.CAPIT]],
    "lateral": [IDX[RG.LAT_TRANQ], IDX[RG.LAT_VOL]],
    "no_bajista": [IDX[RG.ALCISTA], IDX[RG.EUFORIA], IDX[RG.LAT_TRANQ], IDX[RG.LAT_VOL]],
    "no_alcista": [IDX[RG.BAJISTA], IDX[RG.CAPIT], IDX[RG.LAT_TRANQ], IDX[RG.LAT_VOL]],
}


# ----------------------------------------------------------------------------------------------
def variantes(fam: str, base: dict) -> List[dict]:
    reg = E.REGISTRO[fam]
    p = {**reg["params"], **base}
    rangos, enteros = reg["rangos"], set(reg["enteros"])
    ejes: Dict[str, list] = {}
    if "k_atr" in p:
        ejes["k_atr"] = [round(p["k_atr"] * f, 3) for f in (0.75, 1.0, 1.5)]
    otros = [k for k in p if k != "k_atr" and k in rangos and isinstance(p[k], (int, float)) and not isinstance(p[k], bool)][:2]
    for k in otros:
        lo, hi = rangos[k]
        vals = []
        for f in (0.8, 1.0, 1.25):
            v = float(np.clip(p[k] * f, lo, hi))
            vals.append(int(round(v)) if k in enteros else round(v, 4))
        ejes[k] = sorted(set(vals))
    if "tendencia" in p:
        ejes["tendencia"] = [False, True]
    claves = list(ejes)
    out = []
    for combo in itertools.product(*[ejes[k] for k in claves]):
        out.append({**p, **dict(zip(claves, combo))})
    return out


def elegir_celdas(ev: pd.DataFrame, k: int) -> pd.DataFrame:
    """Celdas (fam, tf, inv) con mayor percentil 90 de Sharpe diario entre sus pruebas válidas (n >= mínimo)."""
    v = ev[(ev["n"] >= ev["n_min"]) & ev["fam"].isin(E.REGISTRO.keys())]
    g = v.groupby(["fam", "tf", "inv"]).agg(pruebas=("n", "size"), p90=("sharpe_dia", lambda x: x.quantile(0.9)),
                                             mejor=("sharpe_dia", "max")).reset_index()
    g = g.sort_values("p90", ascending=False).head(k)
    # parámetros base de la celda: los de su mejor prueba
    bases = []
    for r in g.itertuples():
        mejor = v[(v.fam == r.fam) & (v.tf == r.tf) & (v.inv == r.inv)].sort_values("sharpe_dia", ascending=False).iloc[0]
        bases.append(json.loads(mejor["params"]))
    g["base"] = bases
    return g


def matrices(aggs: dict, jobs: List[dict]) -> Tuple[dict, list]:
    """Arrays (NREG, ND, C) por (variante x salida x lado) de una celda."""
    meta, cols = [], {k: [] for k in ("dr_pnl", "dr_n", "dr_gw", "dr_gl", "dr_R")}
    for j in jobs:
        for ex in j["exits"]:
            for lado in BR.LADOS:
                a = aggs.get((j["id"], ex, lado))
                if a is None:
                    continue
                meta.append((j["id"], ex, lado))
                for k in cols:
                    cols[k].append(a[k])
    return {k: np.stack(v, axis=-1) for k, v in cols.items()}, meta


def wf_celda(mats: dict, meta: list, filtros: List[str]) -> Tuple[dict, list]:
    """Walk-forward sobre todas las combinaciones (variante, salida, lado) x filtros de régimen indicados."""
    C = mats["dr_pnl"].shape[-1]
    mp, mn, mg, ml, mr = [], [], [], [], []
    etiquetas = []
    for f in filtros:
        ix = FILTROS[f]
        mp.append(mats["dr_pnl"][ix].sum(0)); mn.append(mats["dr_n"][ix].sum(0)); mg.append(mats["dr_gw"][ix].sum(0))
        ml.append(mats["dr_gl"][ix].sum(0)); mr.append(mats["dr_R"][ix].sum(0))
        etiquetas += [(f,) + m for m in meta]
    P, N, GW, GL, R = (np.concatenate(x, axis=1) for x in (mp, mn, mg, ml, mr))
    wf = WF.walk_forward(P, n=N, gw=GW, gl=GL, R=R)
    wf["matriz"] = P
    return wf, etiquetas


def main() -> int:
    k = int(sys.argv[sys.argv.index("--celdas") + 1]) if "--celdas" in sys.argv else 24
    t0 = time.time()
    RES.mkdir(exist_ok=True)
    congeladas = "--congeladas" in sys.argv
    if congeladas:
        # VALIDACIÓN: las celdas vienen del fichero congelado ANTES de mirar este periodo; no se reeligen ni se tocan
        cong = json.loads((RAIZ / "CELDAS_CONGELADAS.json").read_text())
        celdas = pd.DataFrame([{"fam": c["fam"], "tf": c["tf"], "inv": c["inv"], "base": c["base"], "pruebas": 0, "p90": np.nan, "mejor": np.nan}
                               for c in cong["celdas"]])
        ev = pd.read_parquet(RAIZ / "resultados" / "ranking_ronda1.parquet")          # solo para la varianza de Sharpe entre pruebas
    else:
        ev = pd.read_parquet(RES / "ranking_ronda1.parquet")
        celdas = elegir_celdas(ev, k)
    celdas = celdas.reset_index(drop=True)
    if "--solo" in sys.argv:                                             # p. ej. --solo 3,4,22 (índices de CELDAS_CONGELADAS)
        idx = [int(x) for x in sys.argv[sys.argv.index("--solo") + 1].split(",")]
        celdas = celdas.loc[idx]
    print("celdas candidatas:\n", celdas[["fam", "tf", "inv", "pruebas", "p90", "mejor"]].round(3).to_string(), flush=True)

    sel = json.loads(UNIV.read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, _ = ronda1.codigo_dia_busqueda()

    jobs, celda_de, i = [], {}, 100_000
    for r in celdas.itertuples():
        ci = r.Index
        for v in variantes(r.fam, r.base):
            jobs.append(dict(id=i, fam=r.fam, tf=r.tf, params=v, inv=bool(r.inv), exits=BR.EXITS_R1, detalle=True, celda=ci))
            celda_de[i] = ci
            i += 1
    n_sims = sum(len(j["exits"]) for j in jobs)
    print(f"variantes totales: {len(jobs)} | simulaciones (x50 monedas): {n_sims} | combos (x3 lados x{len(FILTROS)} filtros): {n_sims * 3 * len(FILTROS)}", flush=True)
    aggs = BR.barrido(jobs, sel, miembros, cod, nproc=4, tam_lote=4, log=lambda *a: print(*a, flush=True))
    print(f"simulado en {time.time() - t0:.0f}s", flush=True)

    var_sr = float(np.nanvar(ev.loc[ev['n'] >= 30, 'sharpe_dia'].to_numpy(), ddof=1))
    filas, detalle = [], {}
    n_total = RK.total_pruebas_lanzadas() + n_sims * 3
    n_total_con_filtros = RK.total_pruebas_lanzadas() + n_sims * 3 * len(FILTROS)
    for r in celdas.itertuples():
        ci = r.Index
        js = [j for j in jobs if j["celda"] == ci]
        mats, meta = matrices(aggs, js)
        res = {}
        for nombre, fl in (("sin_regimen", ["todos"]), ("con_regimen", list(FILTROS))):
            wf, etiq = wf_celda(mats, meta, fl)
            s = WF.resumen_oos(wf)
            d_oos = wf["pnl"][np.isin(WF.MES, wf["meses"])]
            dsr_t = M.dsr(d_oos, n_total, var_sr) if s["beneficio_oos"] != 0 else None
            res[nombre] = (wf, etiq, s)
            filas.append({"celda": ci, "fam": r.fam, "tf": r.tf, "inv": r.inv, "procedimiento": nombre,
                          "combos": wf["matriz"].shape[1], **s, "dsr_ntotal": dsr_t})
        detalle[ci] = {k: (v[0]["elegidas"], [v[1][e] if e >= 0 else None for e in v[0]["elegidas"]]) for k, v in res.items()}
    out = pd.DataFrame(filas)
    out.to_parquet(RES / "ronda2_wf.parquet")
    celdas.drop(columns=["base"]).to_parquet(RES / "ronda2_celdas.parquet")
    json.dump({str(k): v for k, v in detalle.items()}, open(RES / "ronda2_elecciones.json", "w"), default=str)
    np.savez_compressed(RES / "ronda2_agg_keys.npz", keys=np.array([f"{a}|{b}|{c}" for a, b, c in aggs], dtype=object))
    pd.set_option("display.width", 250)
    cols = ["fam", "tf", "inv", "procedimiento", "combos", "meses_operados", "n", "beneficio_oos", "exp_usd", "pf", "meses_pos", "sharpe_dia", "sin_mejor_sem"]
    print(out[cols].round(3).to_string(), flush=True)
    print(f"\ncon beneficio OOS > 0: sin régimen {int(((out.procedimiento=='sin_regimen')&(out.beneficio_oos>0)).sum())}/{len(celdas)}"
          f" | con régimen {int(((out.procedimiento=='con_regimen')&(out.beneficio_oos>0)).sum())}/{len(celdas)}", flush=True)
    print(f"total de pruebas (para DSR): {n_total} (sin contar filtros) / {n_total_con_filtros} (con filtros)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
