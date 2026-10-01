"""Aplica el criterio de PREREGISTRO.md a las 24 celdas congeladas: ¿beneficio OOS > 0 y PF > 1 SIN filtro de régimen en cada periodo?
Uso: python -m cazador.consistencia"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PERIODOS = {"reciente": RAIZ / "resultados", "val1": RAIZ / "resultados_val1", "val2": RAIZ / "resultados_val2"}


def cargar() -> pd.DataFrame:
    partes = []
    for p, d in PERIODOS.items():
        f = d / "ronda2_wf.parquet"
        if f.exists():
            x = pd.read_parquet(f)
            x = x[x.procedimiento == "sin_regimen"].copy()
            x["periodo"] = p
            partes.append(x)
    return pd.concat(partes, ignore_index=True)


def tabla() -> pd.DataFrame:
    df = cargar()
    # la celda se identifica por su posición en CELDAS_CONGELADAS (misma columna 'celda' en todos los periodos)
    pers = [p for p in PERIODOS if p in set(df.periodo)]
    filas = []
    for c, g in df.groupby("celda"):
        f = {"celda": c, "fam": g.fam.iloc[0], "tf": g.tf.iloc[0], "inv": g.inv.iloc[0]}
        ok = []
        for p in pers:
            r = g[g.periodo == p]
            if r.empty:
                f[f"{p}_$"] = np.nan; continue
            r = r.iloc[0]
            f[f"{p}_$"] = r.beneficio_oos
            f[f"{p}_n"] = r.n
            f[f"{p}_pf"] = r.pf
            f[f"{p}_mesespos"] = r.meses_pos
            f[f"{p}_sinmejorsem"] = r.sin_mejor_sem
            ok.append(bool(r.beneficio_oos > 0 and r.pf > 1))
        f["consistente"] = bool(ok) and all(ok) and len(ok) == len(pers)
        f["periodos_positivos"] = int(sum(ok))
        f["prometedora"] = f["consistente"] and all(f.get(f"{p}_n", 0) >= 60 for p in pers) and \
            sum(1 for p in pers if f.get(f"{p}_sinmejorsem", -1) > 0) >= 2
        filas.append(f)
    return pd.DataFrame(filas).sort_values(["periodos_positivos", "consistente"], ascending=False)


if __name__ == "__main__":
    t = tabla()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    cols = ["fam", "tf", "inv"] + [c for c in t.columns if c.endswith("_$") or c.endswith("_pf")] + ["periodos_positivos", "consistente", "prometedora"]
    print(t[cols].round(2).to_string(index=False))
    print("\nconsistentes (todos los periodos disponibles):", int(t.consistente.sum()), "de", len(t), "| prometedoras:", int(t.prometedora.sum()))
