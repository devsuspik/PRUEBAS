"""Análisis a fondo de una variante de ML: operaciones, concentración, estrés de costes/latencia y cartera real (5 posiciones).
Uso: CAZADOR_PERIODO=reciente|val1 python -m cazador.analisis_ml [conjunto] [theta] [solo]"""
import dataclasses
import json
import sys

import numpy as np
import pandas as pd

from . import barrido as BR
from . import metricas as M
from . import ml, universo
from .config import CFG
from .motor import Salida, simular_moneda, filtro_cartera, MS_MIN
from .periodo import NOMBRE, RES, UNIV
from . import cargar


def trades_ml(pred, theta, solo, cfg=CFG, slip_mult=1.0, latencia=0):
    sen = ml.senales_ml(pred, theta, solo=solo)
    partes = []
    for s, sg in sen.items():
        d = cargar.cargar_moneda(s, "busqueda")
        if d is None:
            continue
        miem = None
        sg = BR.filtrar_senales(BR.Prep(d, _miembro(s), {}), sg)
        if len(sg):
            t = simular_moneda(d, sg, cfg, Salida(objetivo_R=1.0, max_velas_1m=1440), latencia, slip_mult=slip_mult)
            if len(t):
                t["prob"] = np.nan
                partes.append(t)
        del d
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


_MEM = None


def _miembro(sim):
    global _MEM
    if _MEM is None:
        _MEM = universo.miembros_por_fecha()
    fechas = pd.date_range(BR.PERIODO["busqueda_ini"], periods=BR.ND)
    return _MEM[sim].reindex(fechas).fillna(False).to_numpy(bool) if sim in _MEM.columns else np.zeros(BR.ND, bool)


def resumen(t, etiqueta):
    if t.empty:
        print(f"{etiqueta}: sin operaciones"); return
    pnl = t["pnl"].to_numpy()
    se = pnl.std(ddof=1) / np.sqrt(len(pnl))
    mc = M.monte_carlo_bloques(pnl, n=3000, bloque=10)
    print(f"{etiqueta}: n={len(t)} aciertos={np.mean(pnl>0):.3f} exp=${pnl.mean():+.3f} (EE {se:.3f}, t={pnl.mean()/se:+.1f}) PF={M.profit_factor(pnl):.2f} "
          f"total=${pnl.sum():+.0f} exp_R={t.R.mean():+.3f} ganancia_media={pnl[pnl>0].mean():.2f} pérdida_media={pnl[pnl<=0].mean():.2f}"
          + (f" | MC dd p95=${mc['dd']['p95']:.0f} racha p95={mc['racha']['p95']:.0f}" if mc else ""))


def main() -> None:
    conj = sys.argv[1] if len(sys.argv) > 1 else "solo_propias_moneda"
    theta = float(sys.argv[2]) if len(sys.argv) > 2 else 0.60
    solo = sys.argv[3] if len(sys.argv) > 3 else "long"
    df = pd.read_parquet(RES / "ml_dataset.parquet")
    pred = ml.walk_forward_ml(df, feats=ml.CONJUNTOS[conj], log=lambda *a: None)
    pred.attrs.pop("importancias", None)
    print(f"== {NOMBRE} | {conj} | theta={theta} | {solo}")
    t = trades_ml(pred, theta, solo)
    resumen(t, "base")
    if t.empty:
        return
    t["mes"] = pd.to_datetime(t.entrada_ts, unit="ms").dt.to_period("M")
    por_mes = t.groupby("mes")["pnl"].agg(["size", "sum"])
    print("por mes (n, $):", {str(k): (int(r["size"]), round(r["sum"])) for k, r in por_mes.iterrows()})
    por_m = t.groupby("simbolo")["pnl"].agg(["size", "sum"]).sort_values("sum", ascending=False)
    print("monedas: %d distintas | top5 por beneficio: %s | peso mejor moneda %.0f%%" % (len(por_m), [(k, int(r['size']), round(r['sum'])) for k, r in por_m.head(5).iterrows()], 100 * por_m['sum'].max() / por_m[por_m['sum'] > 0]['sum'].sum()))
    print("sin las 5 mejores operaciones: $%.0f | sin el mejor mes: $%.0f" % (t.pnl.sum() - t.pnl.nlargest(5).sum(), t.pnl.sum() - por_mes['sum'].max()))
    for mult in (1.5, 2.0):
        cfg = dataclasses.replace(CFG, comision_taker_pct=CFG.comision_taker_pct * mult, comision_maker_pct=CFG.comision_maker_pct * mult,
                                  deslizamiento_min_pct=CFG.deslizamiento_min_pct * mult)
        resumen(trades_ml(pred, theta, solo, cfg=cfg, slip_mult=mult), f"costes x{mult}")
    for lat in (1, 5, 15, 60):
        resumen(trades_ml(pred, theta, solo, latencia=lat), f"latencia +{lat} min")
    c, rech = filtro_cartera(t, CFG.max_posiciones_simultaneas)
    resumen(c, f"cartera máx. 5 pos. (rechazadas {rech})")


if __name__ == "__main__":
    main()
