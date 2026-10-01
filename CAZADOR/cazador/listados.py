"""Exploración: corto/largo de listados nuevos con stop y objetivo, camino a camino con barras DIARIAS (alto/bajo).
Conservador: si stop y objetivo caen el mismo día cuenta el stop; si la apertura ya está más allá del stop se sale a la apertura.
Retorno por operación en % del nocional, neto de 0,14 % (ida y vuelta). Sin financiación (se declara). Uso: CAZADOR_PERIODO=<p> python -m cazador.listados"""
import itertools

import numpy as np
import pandas as pd
from scipy import stats

from . import universo
from .config import CFG
from .periodo import CACHE, NOMBRE, PERIODO, RES

COSTE = 2 * (CFG.fee_taker + CFG.slip_min)


def eventos():
    v = universo.volumen_busqueda()
    ex = universo.excluidos(v)
    malos = set(ex["ratio"]) | set(ex["manual"])
    ini = pd.Timestamp(PERIODO["previo_universo_ini"]) + pd.Timedelta(days=14)
    fin = pd.Timestamp(PERIODO["busqueda_fin"]) - pd.Timedelta(days=45)
    out = []
    for s in v.columns:
        if s in malos:
            continue
        g = pd.read_parquet(CACHE / "klines" / "1d" / f"{s}.parquet", columns=["t", "o", "h", "l", "c"])
        g.index = pd.to_datetime(g["t"], unit="ms").dt.floor("D")
        g = g[~g.index.duplicated()].loc[: PERIODO["busqueda_fin"]]
        if len(g) < 30 or not (ini <= g.index[0] <= fin):
            continue
        out.append((s, g))
    return out


def trade(g, k, lado, stop, obj, h):
    """Entra al cierre del día k (desde el listado). lado=-1 corto. stop/obj en fracción. Devuelve retorno bruto (fracción)."""
    c0 = g["c"].iloc[k]
    for j in range(k + 1, min(k + h, len(g) - 1) + 1):
        o, hi, lo, cl = g["o"].iloc[j], g["h"].iloc[j], g["l"].iloc[j], g["c"].iloc[j]
        if lado < 0:
            s_px, t_px = c0 * (1 + stop), c0 * (1 - obj)
            if o >= s_px: return -(o / c0 - 1)
            if hi >= s_px: return -stop
            if o <= t_px: return (c0 - o) / c0
            if lo <= t_px: return obj
        else:
            s_px, t_px = c0 * (1 - stop), c0 * (1 + obj)
            if o <= s_px: return o / c0 - 1
            if lo <= s_px: return -stop
            if o >= t_px: return o / c0 - 1
            if hi >= t_px: return obj
    j = min(k + h, len(g) - 1)
    return lado * (g["c"].iloc[j] / c0 - 1)


def main():
    ev = eventos()
    filas = []
    for k, lado, stop, obj, h in itertools.product((1, 3, 7), (-1, 1), (0.08, 0.15, 0.25), (0.10, 0.20, 0.40), (3, 7, 14)):
        r = np.array([trade(g, k, lado, stop, obj, h) for s, g in ev if len(g) > k + h + 1]) - COSTE
        if len(r) < 10:
            continue
        filas.append(dict(periodo=NOMBRE, k=k, lado="CORTO" if lado < 0 else "LARGO", stop=stop, obj=obj, h=h, n=len(r), neto_pct=r.mean() * 100,
                          t=r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), aciertos=(r > 0).mean(), pf=(r[r > 0].sum() / -r[r <= 0].sum()) if (r <= 0).any() else np.nan))
    RES.mkdir(exist_ok=True)
    d = pd.DataFrame(filas)
    d.to_csv(RES / "listados.csv", index=False)
    print(f"{NOMBRE}: {len(ev)} listados nuevos | combinaciones {len(d)} | netas>0: {(d.neto_pct > 0).mean():.0%} | mejor neto {d.neto_pct.max():.2f}% (t={d.loc[d.neto_pct.idxmax(), 't']:.2f})")


if __name__ == "__main__":
    main()
