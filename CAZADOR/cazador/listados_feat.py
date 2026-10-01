"""Variables condicionantes de cada operación del corto de listados (lista cerrada de PREREGISTRO.md, adenda 3). Solo información <= entrada."""
import numpy as np
import pandas as pd

from . import listados as LI
from . import listados_1m as L1
from . import ronda1
from .periodo import NOMBRE, RES

MS_MIN = 60_000


def main():
    t = pd.read_parquet(RES / "ficha_listados_trades_reg.parquet")
    ev = {s: g for s, g in LI.eventos()}
    btc = ronda1.btc_diario()
    c = btc["c"].astype(float)
    filas = []
    for r in t.itertuples():
        g = ev.get(r.simbolo)
        d = L1.cargar_evento(r.simbolo, g)
        if d is None:
            continue
        i = int((r.entrada_ts - d.t0_ms) // MS_MIN)               # índice de la vela de entrada
        if i < 60:
            continue
        primero = float(d.c[int(np.argmax(d.qv > 0))])
        vol24 = float(d.qv[max(0, i - 1440):i].sum())
        h_desde = (r.entrada_ts - d.t0_ms) / 3_600_000
        # funding conocido: última marca con t <= entrada
        fund = np.nan
        if len(d.f_ts_ms):
            k = np.searchsorted(d.f_ts_ms, r.entrada_ts, side="right") - 1
            if k >= 0:
                fund = float(d.f_rate[k])
        dia = pd.Timestamp(r.entrada_ts, unit="ms").floor("D")
        try:
            btc7 = float(c.loc[dia - pd.Timedelta(days=1)] / c.loc[dia - pd.Timedelta(days=8)] - 1)
        except KeyError:
            btc7 = np.nan
        filas.append(dict(simbolo=r.simbolo, entrada_ts=r.entrada_ts, pnl=r.pnl, R=r.R, reg=r.reg, runup=float(d.o[i]) / primero, funding=fund,
                          vol24h=vol24, horas=h_desde, btc7=btc7, periodo=NOMBRE))
    pd.DataFrame(filas).to_parquet(RES / "listados_feat.parquet")
    print(NOMBRE, len(filas), "operaciones con variables")


if __name__ == "__main__":
    main()
