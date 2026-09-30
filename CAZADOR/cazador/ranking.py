"""Ranking de Ronda 1: DSR con el total REAL de pruebas, PBO global, top y matriz estrategia × régimen.

Clasificación provisional de Ronda 1 (NO es la clasificación §8 definitiva, que exige walk-forward, meseta, estrés y holdout):
  PASA_R1   cumple los criterios baratos: n >= mínimo, exp > 0, PF >= 1,25, meses+ >= 60 %, sin mejor semana > 0,
            sin 5 mejores > 0, peso de la mejor moneda <= 25 %, DSR >= 0,90
  CERCA_R1  falla 1-2 de esos criterios
  resto     descartada en R1
Ninguna estrategia es APTA hasta pasar las Rondas 2+ (walk-forward, meseta, estrés x1,5, holdout).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

from . import barrido as BR
from . import metricas as M
from . import regimenes as RG
from .descarga import RAIZ

RES = RAIZ / "resultados"


def cargar(prefijos: Tuple[str, ...] = ("ronda1", "ronda1b")) -> tuple[pd.DataFrame, dict]:
    dfs, dia = [], {}
    for p in prefijos:
        f = RES / f"{p}.parquet"
        if f.exists():
            dfs.append(pd.read_parquet(f))
            z = np.load(RES / f"{p}_diario.npz")
            dia.update({k.replace("__", "|"): z[k] for k in z.files})
    return pd.concat(dfs, ignore_index=True), dia


def n_minimo(tf: int) -> int:
    return M.UMBRALES["ops_min_diario"] if tf >= 1440 else M.UMBRALES["ops_min"]


def evaluar(df: pd.DataFrame, dia: dict, n_trials: int) -> pd.DataFrame:
    df = df.copy()
    ok = df["n"] >= 30
    var_sr = float(np.nanvar(df.loc[ok, "sharpe_dia"].to_numpy(), ddof=1))
    df["dsr"] = np.nan
    for i in df.index[ok]:
        df.at[i, "dsr"] = M.dsr(dia[df.at[i, "trial"]].astype(float), n_trials, var_sr)
    df["n_min"] = df["tf"].map(n_minimo)
    crit = pd.DataFrame({
        "ops": df["n"] >= df["n_min"], "exp": df["exp_usd"] > 0, "pf": df["pf"] >= M.UMBRALES["pf_min"],
        "meses": df["meses_pos"] >= M.UMBRALES["meses_pos_min"], "sin_sem": df["sin_mejor_sem"] > 0,
        "sin_top5": df["sin_top5"] > 0, "moneda": df["peso_mejor_moneda"] <= 0.25, "dsr": df["dsr"] >= M.UMBRALES["dsr_min"],
    })
    fallos = (~crit).sum(axis=1)
    df["fallos_r1"] = fallos
    df["estado_r1"] = np.where(fallos == 0, "PASA_R1", np.where(fallos <= 2, "CERCA_R1", "DESCARTADA"))
    df["criterios_fallidos"] = crit.apply(lambda r: ",".join(c for c in crit.columns if not r[c]), axis=1)
    return df


def pbo_global(df: pd.DataFrame, dia: dict, min_n: int = 150, max_trials: int = 4000, seed: int = 0) -> dict:
    sel = df[(df["n"] >= min_n) & (df["lado"] == "ambos")]
    if len(sel) > max_trials:
        sel = sel.sample(max_trials, random_state=seed)
    M_ = np.column_stack([dia[t].astype(float) for t in sel["trial"]])
    r = M.pbo_cscv(M_, S=16, max_comb=800, seed=seed)
    return r or {}


def matriz_regimen(df: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    cols = {}
    nombres = RG.ORDEN + ["sin_etiqueta"]
    out = []
    for _, r in top.iterrows():
        fila = {"trial": r["trial"], "fam": r["fam"], "tf": r["tf"], "salida": r["salida"], "lado": r["lado"]}
        for i, nm in enumerate(nombres):
            n, p = r[f"reg{i}_n"], r[f"reg{i}_pnl"]
            fila[f"{RG.ICONOS.get(nm, '')}{nm}_$/op"] = (p / n) if n > 0 else np.nan
            fila[f"{nm}_n"] = n
        out.append(fila)
    return pd.DataFrame(out)


def main() -> None:
    df, dia = cargar()
    n_trials = int((df.attrs.get("n_trials", 0)) or 0)
    # total real de pruebas lanzadas (todas las combinaciones, con o sin operaciones)
    from . import ronda1
    n_trials = sum(len(j["exits"]) for j in ronda1.grid_a() + ronda1.grid_b()) * 3
    if not (RES / "ronda1b.parquet").exists():
        n_trials = sum(len(j["exits"]) for j in ronda1.grid_a()) * 3
    ev = evaluar(df, dia, n_trials)
    pb = pbo_global(ev, dia)
    ev.to_parquet(RES / "ranking_ronda1.parquet")
    print("pruebas totales lanzadas:", n_trials, "| con operaciones:", len(ev), "| PBO global:", pb)
    print(ev["estado_r1"].value_counts().to_string())
    cols = ["trial", "fam", "tf", "inv", "salida", "lado", "n", "aciertos", "exp_usd", "exp_R", "pf", "meses_pos", "sharpe_dia", "dsr",
            "peso_mejor_moneda", "estado_r1", "criterios_fallidos"]
    print("\nTOP 25 por Sharpe diario (n >= mínimo):")
    top = ev[ev["n"] >= ev["n_min"]].sort_values("sharpe_dia", ascending=False).head(25)
    print(top[cols].round(3).to_string())


if __name__ == "__main__":
    main()
