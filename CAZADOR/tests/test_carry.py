import numpy as np
import pandas as pd
import pytest

from cazador import carry as CA
from cazador.config import Config
from cazador.motor import DatosMoneda, MS_MIN

CFG = Config()
T0 = int(pd.Timestamp("2025-01-01").timestamp() * 1000)
H = 3_600_000


def montar(dias=10, p_perp=None, p_spot=None, tasa=0.0005):
    n = dias * 1440
    perp = np.full(n, 100.0) if p_perp is None else p_perp(n)
    d = DatosMoneda("TEST", T0, perp.copy(), perp.copy(), perp.copy(), perp.copy(), np.full(n, 1e9))
    h = np.arange(0, dias * 24)
    spot_c = np.full(len(h), 100.0) if p_spot is None else p_spot(len(h))
    spot = pd.Series(spot_c, index=T0 + h * H)
    ft = np.arange(T0 + 15, T0 + dias * 86_400_000, 8 * H)           # marcas con 15 ms de retraso, como en Binance
    f = pd.DataFrame({"t": ft, "tasa": tasa, "horas": 8.0, "tasa8h": tasa})
    return d, spot, f


def miembro():
    from cazador import barrido as BR
    return np.ones(BR.ND, bool)


def test_carry_plano_cobra_funding_menos_costes():
    d, spot, f = montar()
    t = CA.simular_simbolo("TEST", d, spot, f, miembro(), m=1, th_in=0.0003, th_out=0.0, max_dias=3)
    assert len(t) >= 1
    x = t[0]
    # 3 días = 9 marcas x 0,05 % x 200 $ = 0,90 $ ; costes = (0,10 %+0,05 %) x 2 x 200 + 4 x 0,02 % x 200 = 0,76 $
    assert x["motivo"] == "max_dias"
    assert x["pnl"] == pytest.approx(0.90 - 0.76, abs=0.11)          # +-1 marca por el redondeo horario
    assert x["lado"] == -1


def test_carry_no_entra_si_el_funding_es_bajo():
    d, spot, f = montar(tasa=0.0001)
    assert CA.simular_simbolo("TEST", d, spot, f, miembro(), m=1, th_in=0.0003, th_out=0.0, max_dias=3) == []


def test_carry_sale_cuando_el_funding_cae():
    d, spot, f = montar()
    f.loc[f.index >= 6, ["tasa", "tasa8h"]] = 0.00005                # tras 6 marcas el funding se desploma
    t = CA.simular_simbolo("TEST", d, spot, f, miembro(), m=1, th_in=0.0003, th_out=0.0001, max_dias=10)
    assert t[0]["motivo"] == "funding_bajo"


def test_carry_liquidacion_del_corto_con_spot_que_sube_igual():
    def perp(n):
        p = np.full(n, 100.0)
        p[3 * 1440:] = 111.0                                          # +11 % > liquidación (9,5 %)
        return p

    def spot(n):
        p = np.full(n, 100.0)
        p[3 * 24:] = 111.0
        return p
    d, spot_s, f = montar(dias=10, p_perp=perp, p_spot=spot)
    t = CA.simular_simbolo("TEST", d, spot_s, f, miembro(), m=1, th_in=0.0003, th_out=0.0, max_dias=9)
    x = t[0]
    assert x["motivo"] == "liquidacion"
    # perdida del corto = margen (20 $); la pata spot gana 11 % de 200 $ = 22 $; neto ~ +2 $ menos costes y + funding
    assert -3.0 < x["pnl"] < 5.0
