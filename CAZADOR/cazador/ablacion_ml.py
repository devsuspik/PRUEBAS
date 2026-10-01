"""Ablación del ML: ¿de dónde sale la señal? Entrena con distintos conjuntos de variables y mide AUC y beneficio en el motor real."""
import json
import sys
import time

import numpy as np
import pandas as pd

from . import barrido as BR
from . import ml, ronda1, trials, universo
from .periodo import NOMBRE, RES, UNIV


def main() -> None:
    sel = json.loads(UNIV.read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, _ = ronda1.codigo_dia_busqueda()
    df = pd.read_parquet(RES / "ml_dataset.parquet")
    filas = []
    for nombre, feats in ml.CONJUNTOS.items():
        pred = ml.walk_forward_ml(df, feats=feats, log=lambda *a: None)
        pred.attrs.pop("importancias", None)
        ev = ml.evaluar_prediccion(pred)
        for th in (0.60,):
            jobs = []
            for i, solo in enumerate(("ambos", "long", "short")):
                sen = ml.senales_ml(pred, th, solo=solo)
                if sen:
                    jobs.append(dict(fam="ml_lgbm", tf=240, params={}, inv=False, id=60_000 + i, exits=["ml_1R_24h"], senales_pre=sen))
            agg = BR.barrido(jobs, sel, miembros, cod, nproc=4, tam_lote=3, log=lambda *a: None)
            for (jid, ex, lado), a in agg.items():
                if lado != "ambos":
                    continue
                m = BR.metricas(a)
                solo = ("ambos", "long", "short")[jid - 60_000]
                filas.append(dict(periodo=NOMBRE, conjunto=nombre, theta=th, solo=solo, auc_long=ev["auc_long"], auc_short=ev["auc_short"],
                                  n=m["n"], exp_usd=m["exp_usd"], pf=m["pf"], beneficio=m["beneficio"], meses_pos=m["meses_pos"], sharpe_dia=m["sharpe_dia"]))
                trials.registrar(dict(ronda=3, estrategia=f"ml_{nombre}", marco_min=240, params=f"theta={th},solo={solo}", salida=ex, segmento="reducido50",
                                      regimen="todos", lado="ambos", n_ops=m["n"], exp_R=round(m["exp_R"], 5), beneficio_usd=round(m["beneficio"], 2),
                                      sharpe_periodo=round(m["sharpe_dia"], 5), tramo="oos_walkforward"))
    out = pd.DataFrame(filas)
    out.to_csv(RES / "ablacion_ml.csv", index=False)
    pd.set_option("display.width", 220)
    print(out[out.solo == "ambos"].round(3).to_string(index=False))
    print(out[out.solo != "ambos"][["conjunto", "solo", "n", "exp_usd", "pf", "beneficio"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
