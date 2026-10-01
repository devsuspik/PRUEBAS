"""¿Qué estrategia del catálogo funciona en qué régimen, de forma CONSISTENTE entre periodos?
Cruza los barridos de Ronda 1 (A, B, C) de los 4 periodos (reciente, VAL2, VAL1, VAL0) usando los agregados por régimen.
Criterio (estricto, fijado antes de mirar): en el régimen r, la prueba (misma estrategia, parámetros, salida y lado en cada periodo)
tiene expectativa > 0 en TODOS los periodos donde hay >= 25 operaciones en ese régimen, hay >= 3 periodos así, >= 150 operaciones en
total y la expectativa agrupada >= 0,5 $/operación (costes ya incluidos). Es una exploración con muchas hipótesis: los candidatos se
verifican aparte (significación y permutación) y se informan como 'consistentes', no como 'probados'."""
import numpy as np
import pandas as pd

from . import regimenes as RG
from .periodo import RAIZ

DIRS = {"reciente": RAIZ / "resultados", "val2": RAIZ / "resultados_val2", "val1": RAIZ / "resultados_val1", "val0": RAIZ / "resultados_val0"}
NOM = RG.ORDEN + ["sin"]


def cargar():
    partes = []
    for p, d in DIRS.items():
        for suf in ("ronda1", "ronda1b", "ronda1c"):
            f = d / f"{suf}.parquet"
            if f.exists():
                x = pd.read_parquet(f)
                x["per"] = p
                partes.append(x)
    return pd.concat(partes, ignore_index=True)


def escanear(df, min_n_per=25, min_per=3, min_n_tot=150, min_exp=0.5):
    out = []
    pers = sorted(df.per.unique())
    base = df.set_index(["trial", "per"])
    trials = df.trial.unique()
    for r in range(len(NOM) - 1):                              # sin 'sin etiqueta'
        n_c, p_c = f"reg{r}_n", f"reg{r}_pnl"
        sub = df[df[n_c] > 0][["trial", "per", n_c, p_c, "fam", "tf", "inv", "salida", "lado", "params"]]
        g = sub.groupby("trial")
        for trial, x in g:
            val = x[x[n_c] >= min_n_per]
            if len(val) < min_per or x[n_c].sum() < min_n_tot:
                continue
            medias = (val[p_c] / val[n_c]).to_numpy()
            pooled = x[p_c].sum() / x[n_c].sum()
            if (medias > 0).all() and pooled >= min_exp:
                out.append(dict(trial=trial, regimen=NOM[r], fam=x.fam.iloc[0], tf=x.tf.iloc[0], inv=x.inv.iloc[0], salida=x.salida.iloc[0], lado=x.lado.iloc[0],
                                n_tot=int(x[n_c].sum()), exp_agrupada=pooled, periodos=len(val), min_periodo=medias.min(),
                                por_periodo={p: (int(n), round(m, 2)) for p, n, m in zip(val.per, val[n_c], medias)}))
    return pd.DataFrame(out)


if __name__ == "__main__":
    df = cargar()
    print("periodos:", sorted(df.per.unique()), "| filas", len(df))
    res = escanear(df)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
    print("candidatos consistentes:", len(res), "de", df.trial.nunique(), "pruebas x 5 regímenes")
    if len(res):
        print(res.sort_values("min_periodo", ascending=False).drop(columns=["trial"]).head(40).round(2).to_string(index=False))
        res.to_csv(RAIZ / "resultados_final" / "playbook_candidatos.csv", index=False)
