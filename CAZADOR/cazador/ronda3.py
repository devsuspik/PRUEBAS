"""Ronda 3 – ML con triple barrera (LightGBM), walk-forward con purga. Uso: python -m cazador.ronda3

Salidas: resultados/ml_dataset.parquet, ml_pred.parquet, ml_importancias.csv, ronda3.parquet (+ _diario.npz) y el log de pruebas.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import barrido as BR
from . import ml, ronda1, trials, universo
from .periodo import RES, UNIV

THETAS = (0.55, 0.60, 0.65)
EXITS_ML = ["ml_1R_24h"]


def main() -> int:
    t0 = time.time()
    RES.mkdir(exist_ok=True)
    sel = json.loads(UNIV.read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, _ = ronda1.codigo_dia_busqueda()
    df = ml.construir(sel, miembros, log=lambda *a: print(*a, flush=True))
    df.to_parquet(RES / "ml_dataset.parquet")
    print(f"dataset en {time.time() - t0:.0f}s", flush=True)
    pred = ml.walk_forward_ml(df, log=lambda *a: print(*a, flush=True))
    imp = pred.attrs.pop("importancias", None)
    pred.to_parquet(RES / "ml_pred.parquet")
    if imp is not None:
        imp.to_csv(RES / "ml_importancias.csv")
    ev = ml.evaluar_prediccion(pred)
    print("\nOOS: AUC long %.4f short %.4f | tasa base long %.3f short %.3f" % (ev["auc_long"], ev["auc_short"], ev["base_long"], ev["base_short"]), flush=True)
    for lado in ("long", "short"):
        print(f"  tasa de acierto por decil de probabilidad ({lado}):", [round(x, 3) for x in ev[f"tasa_por_decil_{lado}"]], flush=True)
    # ---- evaluación con el motor real (1 m, costes completos)
    jobs, i = [], 50_000
    for th in THETAS:
        for solo in ("ambos", "long", "short"):
            sen = ml.senales_ml(pred, th, solo=solo)
            if not sen:
                continue
            jobs.append(dict(fam="ml_lgbm", tf=240, params=dict(theta=th, solo=solo), inv=False, id=i, exits=EXITS_ML, senales_pre=sen))
            i += 1
    agg = BR.barrido(jobs, sel, miembros, cod, nproc=4, tam_lote=3, log=lambda *a: print(*a, flush=True))
    info = {j["id"]: j for j in jobs}
    filas, diarios = [], {}
    for (jid, ex, lado), a in agg.items():
        j = info[jid]
        m = BR.metricas(a)
        tid = f"{jid}|{ex}|{lado}"
        fila = {"trial": tid, "fam": "ml_lgbm", "tf": 240, "inv": False, "params": json.dumps(j["params"]), "salida": ex, "lado": lado, **m}
        for r in range(BR.NREG):
            fila[f"reg{r}_n"] = int(a["reg_n"][r])
            fila[f"reg{r}_pnl"] = float(a["reg_pnl"][r])
        filas.append(fila)
        diarios[tid] = a["d_pnl"].astype("float32")
    out = pd.DataFrame(filas)
    out.to_parquet(RES / "ronda3.parquet")
    np.savez_compressed(RES / "ronda3_diario.npz", **{k.replace("|", "__"): v for k, v in diarios.items()})
    for r in out.itertuples():
        trials.registrar(dict(ronda=3, estrategia="ml_lgbm", marco_min=240, params=r.params, salida=r.salida, segmento="reducido50",
                              regimen="todos", lado=r.lado, n_ops=r.n, exp_R=round(r.exp_R, 5), beneficio_usd=round(r.beneficio, 2),
                              sharpe_periodo=round(r.sharpe_dia, 5), tramo="oos_walkforward"))
    pd.set_option("display.width", 220)
    print(out[["params", "lado", "n", "aciertos", "exp_usd", "exp_R", "pf", "beneficio", "meses_pos", "sharpe_dia", "costes_por_op"]].round(3).to_string(), flush=True)
    print(f"terminado en {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
