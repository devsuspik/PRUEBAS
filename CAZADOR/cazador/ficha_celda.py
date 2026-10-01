"""Ficha de una celda congelada: walk-forward con costes x1 / x1,5 / x2 (mismas elecciones mensuales que con costes x1) y
efecto de la cartera de 5 posiciones. Uso: CAZADOR_PERIODO=<p> python -m cazador.ficha_celda <indice_celda>"""
import json
import sys

import numpy as np
import pandas as pd

from . import barrido as BR
from . import metricas as M
from . import ronda1, ronda2 as R2, universo, walkforward as WF
from .motor import filtro_cartera
from .periodo import NOMBRE, RAIZ, UNIV
from . import cargar


def correr(r, mult, sel, mem, cod):
    jobs, i = [], 200_000 + int(mult * 1000)
    for v in R2.variantes(r["fam"], r["base"]):
        jobs.append(dict(id=i, fam=r["fam"], tf=r["tf"], params=v, inv=bool(r["inv"]), exits=BR.EXITS_R1, detalle=True, cfg_mult=mult, celda=0))
        i += 1
    agg = BR.barrido(jobs, sel, mem, cod, nproc=4, tam_lote=4, log=lambda *a: None)
    mats, meta = R2.matrices(agg, jobs)
    return mats, meta


def serie(mats, elegidas, filtro="todos"):
    ix = R2.FILTROS[filtro]
    P = mats["dr_pnl"][ix].sum(0); N = mats["dr_n"][ix].sum(0); GW = mats["dr_gw"][ix].sum(0); GL = mats["dr_gl"][ix].sum(0)
    return P, N, GW, GL


def aplicar(mats, wf):
    P, N, GW, GL = serie(mats, wf["elegidas"])
    T = P.shape[0]
    out = dict(pnl=np.zeros(T), n=np.zeros(T), gw=np.zeros(T), gl=np.zeros(T), R=np.zeros(T), elegidas=wf["elegidas"], meses=wf["meses"])
    R = mats["dr_R"].sum(0)
    for m, j in zip(wf["meses"], wf["elegidas"]):
        if j < 0:
            continue
        k = WF.MES == m
        out["pnl"][k], out["n"][k], out["gw"][k], out["gl"][k], out["R"][k] = P[k, j], N[k, j], GW[k, j], GL[k, j], R[k, j]
    return out


def main() -> None:
    idx = int(sys.argv[1])
    cong = json.loads((RAIZ / "CELDAS_CONGELADAS.json").read_text())["celdas"][idx]
    sel = json.loads(UNIV.read_text())["seleccion"]
    mem = universo.miembros_por_fecha()
    cod, _ = ronda1.codigo_dia_busqueda()
    base = None
    res = {}
    for mult in (1.0, 1.5, 2.0):
        mats, meta = correr(cong, mult, sel, mem, cod)
        if base is None:
            P, N, GW, GL = serie(mats, None)
            R = mats["dr_R"].sum(0)
            wf = WF.walk_forward(P, n=N, gw=GW, gl=GL, R=R)
            base = wf
        wfm = aplicar(mats, base)
        s = WF.resumen_oos(wfm)
        res[mult] = s
        print(f"{NOMBRE} | costes x{mult}: OOS ${s['beneficio_oos']:+.0f} n={s['n']:.0f} exp=${s.get('exp_usd', float('nan')):+.3f} PF={s.get('pf', float('nan')):.2f} "
              f"meses+={s['meses_pos']:.2f} sin_mejor_sem=${s['sin_mejor_sem']:+.0f} Sharpe_dia={s['sharpe_dia']:+.3f}", flush=True)
        if mult == 1.0:
            d = wfm["pnl"][np.isin(WF.MES, wfm["meses"])]
            print(f"   días OOS={len(d)} | beneficio por mes ($): {[round(wfm['pnl'][WF.MES == m].sum()) for m in wfm['meses']]}", flush=True)
            elegidas = [meta[j] for j in wfm["elegidas"] if j >= 0]
            print(f"   combinaciones elegidas (variante, salida, lado) más frecuentes: {pd.Series([(a[1], a[2]) for a in elegidas]).value_counts().head(4).to_dict()}", flush=True)
    pd.Series({f"x{m}": v for m, v in res.items()}).to_json(RAIZ / f"resultados{('_' + NOMBRE) if NOMBRE != 'reciente' else ''}" / f"ficha_celda_{idx}.json")


if __name__ == "__main__":
    main()
