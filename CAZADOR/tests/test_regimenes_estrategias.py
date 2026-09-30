import numpy as np
import pandas as pd
import pytest

from cazador import estrategias as E
from cazador import regimenes as R
from cazador.config import Config
from cazador.motor import DatosMoneda, Senales, Salida, simular_moneda, simular_universo
from tests.test_motor import gbm


def btc_sintetico(n=1200, seed=5):
    rng = np.random.default_rng(seed)
    mu = np.concatenate([np.full(400, 0.002), np.full(400, -0.002), np.full(400, 0.0)])[:n]
    sg = np.concatenate([np.full(400, 0.02), np.full(400, 0.03), np.full(400, 0.012)])[:n]
    c = 20000 * np.exp(np.cumsum(rng.normal(mu, sg)))
    return pd.DataFrame({"c": c}, index=pd.date_range("2021-01-01", periods=n, freq="D"))


def test_regimen_es_causal():
    btc = btc_sintetico()
    full = R.etiquetas_macro(btc)["regimen"]
    for corte in (500, 700, 950):
        parcial = R.etiquetas_macro(btc.iloc[:corte])["regimen"]
        a, b = full.iloc[:corte], parcial
        assert ((a == b) | (a.isna() & b.isna())).all(), f"la etiqueta cambia con datos futuros (corte {corte})"


def test_regimen_produce_varias_etiquetas_y_respeta_histeresis():
    btc = btc_sintetico()
    e = R.etiquetas_macro(btc, persistencia=3)
    assert e["regimen"].dropna().nunique() >= 2
    # histéresis: ninguna etiqueta dura menos de 3 días salvo la primera racha
    r = e["regimen"].dropna()
    tramos = (r != r.shift()).cumsum()
    largos = r.groupby(tramos).size()
    assert (largos.iloc[1:-1] >= 3).all()


def test_aplicar_a_1m_usa_el_dia_anterior():
    dias = pd.date_range("2025-01-01", periods=3)
    reg = pd.Series([R.ALCISTA, R.BAJISTA, R.ALCISTA], index=dias, dtype=object)
    t0 = int(dias[0].timestamp() * 1000)
    cod = R.aplicar_a_1m(reg, t0, 3 * 1440)
    assert cod[0] == -1                               # el día 1 no tiene 'ayer'
    assert cod[1440] == R.ORDEN.index(R.ALCISTA)      # durante el día 2 rige la etiqueta del día 1
    assert cod[2 * 1440] == R.ORDEN.index(R.BAJISTA)


def datos_sinteticos(n=60 * 24 * 40, seed=11):
    o, h, l, c = gbm(n, sigma_min=0.0007, seed=seed)
    rng = np.random.default_rng(seed)
    qv = rng.uniform(2e5, 8e5, n)
    return DatosMoneda("SINT", 0, o, h, l, c, qv, tb_qv=qv * rng.uniform(0.4, 0.6, n))


@pytest.mark.parametrize("nombre,tf", [("ema_cross", 15), ("donchian", 15), ("tsmom", 60), ("rsi2", 15),
                                       ("bollinger_rev", 15), ("orb_sesion", 15)])
def test_todas_las_estrategias_son_causales(nombre, tf):
    d = datos_sinteticos()
    assert len(E.generar(nombre, d, tf)) > 0, "la estrategia no emite señales en datos de prueba"
    assert E.comprobar_causalidad(nombre, d, tf)


def test_el_test_de_causalidad_detecta_una_fuga():
    def con_fuga(B, invertir=False):
        futuro = np.concatenate([B.c[1:] - B.c[:-1], [0.0]])       # usa la vela i+1: FUGA
        L, S = futuro > 0, futuro < 0
        return E._emitir(B, L, S, np.full(len(B), 1.0), invertir)
    E.REGISTRO["fuga"] = dict(fn=con_fuga, familia="X", params={}, rangos={}, enteros=())
    try:
        assert not E.comprobar_causalidad("fuga", datos_sinteticos(), 15)
    finally:
        del E.REGISTRO["fuga"]


def test_inversa_intercambia_lados():
    d = datos_sinteticos()
    a = E.generar("donchian", d, 15)
    b = E.generar("donchian", d, 15, invertir=True)
    assert np.array_equal(a.idx, b.idx) and np.array_equal(a.lado, -b.lado)


def test_barras_tf_alineadas_y_cerradas():
    d = datos_sinteticos(n=60 * 24 * 3 + 7)
    d.t0_ms = 7 * 60_000                                # empieza desalineado con la rejilla de 15 m
    B = E.barras_tf(d, 15)
    assert ((B.ts_apertura // 60_000) % 15 == 0).all()
    i = 10
    j0 = B.idx_cierre[i] - 14
    assert B.o[i] == d.o[j0] and B.c[i] == d.c[B.idx_cierre[i]]
    assert B.h[i] == d.h[j0:j0 + 15].max() and B.l[i] == d.l[j0:j0 + 15].min()
    assert B.idx_cierre[-1] < d.n


def test_tuberia_completa_y_no_hay_ventaja_en_ruido():
    """Humo de extremo a extremo: estrategias de catálogo sobre ruido (GBM) deben perder ~los costes, nunca ganar de forma robusta."""
    cfg = Config()
    d = datos_sinteticos(n=60 * 24 * 120, seed=21)
    for nombre, tf in (("donchian", 60), ("ema_cross", 60), ("rsi2", 15), ("bollinger_rev", 15)):
        s = E.generar(nombre, d, tf)
        t, _ = simular_universo({d.simbolo: d}, {d.simbolo: s}, cfg, Salida(objetivo_R=2.0, max_velas_1m=60 * 24 * 3))
        assert len(t) > 20
        se = t.pnl.std() / np.sqrt(len(t))
        assert t.pnl.mean() - 4 * se < 0, f"{nombre}: ganancia 'significativa' en ruido => fallo del motor o fuga"
