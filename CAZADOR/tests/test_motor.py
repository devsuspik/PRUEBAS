"""Validación del motor (§4): casos sintéticos hechos a mano + estrategia aleatoria + retraso de 1 vela.

Los datos sintéticos SOLO se usan aquí para comprobar que el motor está bien. Nunca para buscar ventaja.
"""
import numpy as np
import pandas as pd
import pytest

from cazador.config import Config
from cazador.motor import (DatosMoneda, Senales, Salida, simular_moneda, filtro_cartera,
                           STOP, STOP_GAP, OBJETIVO, TIEMPO, LIQUIDACION, TIEMPO_SIN_AVANCE)

CFG = Config(deslizamiento_min_pct=0.0, comision_taker_pct=0.05, comision_maker_pct=0.02)


def barras(o, h, l, c, funding=None, step=0.0, min_notional=5.0):
    n = len(o)
    d = DatosMoneda("TEST", 0, np.array(o, float), np.array(h, float), np.array(l, float), np.array(c, float),
                    np.full(n, 1e9), step=step, min_notional=min_notional)
    d._slip = np.zeros(n)        # deslizamiento 0 para poder calcular a mano
    if funding:
        d.f_ts_ms = np.array([t * 60_000 for t, _ in funding], np.int64)
        d.f_rate = np.array([r for _, r in funding], float)
    return d


def sen(idx=0, lado=1, sd=1.0):
    return Senales(np.array([idx]), np.array([lado], np.int8), np.array([sd], float))


def test_objetivo_calculo_exacto():
    # entra en 100 (apertura de la vela 1), stop 99, objetivo 2R = 102
    d = barras([100, 100, 101, 102], [100, 101, 102.5, 103], [100, 99.5, 100.5, 101.5], [100, 100.5, 102, 102.5])
    t = simular_moneda(d, sen(0, 1, 1.0), CFG, Salida(objetivo_R=2.0))
    assert len(t) == 1 and t.motivo[0] == OBJETIVO
    qty = 200 / 100
    esperado = (102 - 100) * qty - 0.0005 * qty * 100 - 0.0005 * qty * 102
    assert t.pnl[0] == pytest.approx(esperado, rel=1e-9)
    assert t.R[0] == pytest.approx(esperado / (1 / 100 * 200), rel=1e-9)


def test_stop_y_objetivo_en_la_misma_vela_cuenta_el_stop():
    d = barras([100, 100, 100], [100, 103, 100], [100, 98.5, 100], [100, 101, 100])
    t = simular_moneda(d, sen(0, 1, 1.0), CFG, Salida(objetivo_R=2.0))
    assert t.motivo[0] == STOP
    assert t.pnl[0] < 0
    assert t.salida_px[0] == pytest.approx(99.0)


def test_short_simetrico():
    d = barras([100, 100, 99, 98], [100, 100.5, 99.5, 98.5], [100, 99, 97.5, 97.5], [100, 99.5, 98, 98])
    t = simular_moneda(d, sen(0, -1, 1.0), CFG, Salida(objetivo_R=2.0))
    assert t.motivo[0] == OBJETIVO and t.salida_px[0] == pytest.approx(98.0)
    assert t.pnl[0] > 0


def test_hueco_a_traves_del_stop_sale_a_la_apertura():
    d = barras([100, 100, 97, 97], [100, 100.4, 97.5, 97.5], [100, 99.5, 96.5, 96.5], [100, 100, 97, 97])
    t = simular_moneda(d, sen(0, 1, 1.0), CFG, Salida(objetivo_R=3.0))
    assert t.motivo[0] == STOP_GAP and t.salida_px[0] == pytest.approx(97.0)


def test_latencia_retrasa_la_entrada():
    d = barras([100, 100, 105, 105], [100, 100.4, 106, 106], [100, 99.5, 104, 104], [100, 100, 105, 105])
    t0 = simular_moneda(d, sen(0, 1, 50.0), CFG, Salida(max_velas_1m=1), latencia_velas=0)
    t1 = simular_moneda(d, sen(0, 1, 50.0), CFG, Salida(max_velas_1m=1), latencia_velas=1)
    assert t0.entrada_px[0] == pytest.approx(100.0)
    assert t1.entrada_px[0] == pytest.approx(105.0)


def test_funding_long_paga_si_la_tasa_es_positiva():
    n = 8
    d = barras([100] * n, [100.1] * n, [99.9] * n, [100] * n, funding=[(4, 0.0001)])
    t = simular_moneda(d, sen(0, 1, 5.0), CFG, Salida(max_velas_1m=6))
    assert t.funding[0] == pytest.approx(1 * 0.0001 * 2.0 * 100.0)
    # el short COBRA con tasa positiva
    t2 = simular_moneda(d, sen(0, -1, 5.0), CFG, Salida(max_velas_1m=6))
    assert t2.funding[0] == pytest.approx(-0.02)


def test_funding_fuera_de_la_posicion_no_se_cobra():
    n = 8
    d = barras([100] * n, [100.1] * n, [99.9] * n, [100] * n, funding=[(1, 0.001), (7, 0.001)])
    t = simular_moneda(d, sen(0, 1, 5.0), CFG, Salida(max_velas_1m=4))   # velas 1..4
    assert t.funding[0] == 0.0          # marca en vela 1 = la de entrada (no se cobra), la de 7 es posterior


def test_liquidacion_pierde_el_margen_y_no_mas():
    d = barras([100, 100, 95, 89], [100, 100.2, 96, 95], [100, 99.8, 94, 88], [100, 100, 95, 90])
    t = simular_moneda(d, sen(0, 1, 30.0), CFG, Salida())   # stop a 30 (mas alla de la liquidacion en ~90,5)
    assert t.motivo[0] == LIQUIDACION
    assert t.pnl[0] == pytest.approx(-20.0)


def test_step_y_min_notional():
    d = barras([100, 100, 100], [100, 100, 100], [100, 99.9, 100], [100, 100, 100], step=1.0, min_notional=300.0)
    assert len(simular_moneda(d, sen(0, 1, 5.0), CFG, Salida(max_velas_1m=1))) == 0   # 200 < 300
    d2 = barras([100, 100, 100], [100, 100, 100], [100, 99.9, 100], [100, 100, 100], step=3.0, min_notional=5.0)
    t = simular_moneda(d2, sen(0, 1, 5.0), CFG, Salida(max_velas_1m=1))
    assert len(t) == 0                               # floor(2/3)*3 = 0 -> se rechaza


def test_breakeven_mueve_el_stop_desde_la_vela_siguiente():
    # sube 1R en la vela 1 (max 101) -> BE se arma al CIERRE de la vela 1 y se aplica en la vela 2
    d = barras([100, 100, 100.5, 100], [100, 101.05, 100.6, 100.1], [100, 99.6, 99.5, 99.5], [100, 100.6, 100.0, 100])
    t = simular_moneda(d, sen(0, 1, 1.0), CFG, Salida(break_even_R=1.0, break_even_colchon_frac=0.0012, max_velas_1m=10))
    assert t.motivo[0] == STOP
    assert t.salida_px[0] == pytest.approx(100 * 1.0012)   # stop en BE + colchón


def test_trailing():
    o = [100, 100, 101, 102, 103, 103]
    h = [100, 101, 102, 103.5, 103.6, 102.2]
    l = [100, 99.8, 100.9, 101.9, 102.9, 101.0]
    c = [100, 101, 102, 103, 103.2, 101.2]
    d = barras(o, h, l, c)
    t = simular_moneda(d, sen(0, 1, 1.0), CFG, Salida(trailing_R=1.0, max_velas_1m=20))
    assert t.motivo[0] == STOP
    assert t.salida_px[0] == pytest.approx(103.6 - 1.0)


def test_salida_sin_avance():
    d = barras([100] * 8, [100.2] * 8, [99.8] * 8, [100] * 8)
    t = simular_moneda(d, sen(0, 1, 5.0), CFG, Salida(sin_avance_velas=3, sin_avance_R=0.5, max_velas_1m=7))
    assert t.motivo[0] == TIEMPO_SIN_AVANCE


def test_tiempo_maximo():
    d = barras([100] * 10, [100.2] * 10, [99.8] * 10, [100] * 10)
    t = simular_moneda(d, sen(0, 1, 5.0), CFG, Salida(max_velas_1m=3))
    assert t.motivo[0] == TIEMPO and t.salida_ts[0] == 4 * 60_000   # velas 1,2,3 -> cierre de la 3


def test_cartera_max_posiciones_y_una_por_moneda():
    base = dict(entrada_ts=0, salida_ts=100)
    filas = [
        dict(simbolo="A", **base), dict(simbolo="B", **base), dict(simbolo="C", **base),
        dict(simbolo="A", entrada_ts=50, salida_ts=60),          # misma moneda solapada
        dict(simbolo="D", entrada_ts=100, salida_ts=120),        # cuando A,B salen a 100 ya hay hueco
    ]
    t = pd.DataFrame(filas)
    acept, rech = filtro_cartera(t, 2)
    assert sorted(acept.simbolo) == ["A", "B", "D"]
    assert rech == 2


# ----------------------------------------------------------------------------------------------
# Estrategia aleatoria y retraso de 1 vela
# ----------------------------------------------------------------------------------------------
def gbm(n=120_000, sigma_min=0.0008, seed=1):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, sigma_min, n)
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[100], c[:-1]])
    j = np.abs(rng.normal(0, sigma_min * 0.6, n))
    h = np.maximum(o, c) * (1 + j)
    l = np.minimum(o, c) * (1 - j)
    return o, h, l, c


def test_estrategia_aleatoria_pierde_aproximadamente_los_costes():
    cfg = Config()                                   # costes reales por defecto (0,05 % + 0,02 % desliz.)
    o, h, l, c = gbm()
    n = len(c)
    d = DatosMoneda("RND", 0, o, h, l, c, np.full(n, 5e5))
    rng = np.random.default_rng(7)
    idx = np.arange(100, n - 200, 90)
    lado = rng.choice(np.array([-1, 1], np.int8), len(idx))
    sd = c[idx] * 0.004
    s = Senales(idx, lado, sd)
    t = simular_moneda(d, s, cfg, Salida(objetivo_R=1.5, max_velas_1m=120))
    bruto = (t.pnl + t.comisiones).mean()
    se = t.pnl.std() / np.sqrt(len(t))
    # sin costes la media debe ser ~0 (martingala), con costes claramente negativa
    assert abs(bruto) < 4 * se + 0.05
    assert t.pnl.mean() < -0.15 and t.pnl.mean() + 4 * se < 0


def test_ventaja_con_fuga_de_futuro_desaparece_con_retraso():
    """Una 'estrategia' que mira la vela siguiente gana muchísimo con latencia 0 y nada con latencia 1.
    Es la señal de alarma que el pipeline debe detectar (§4: retraso de 1 vela)."""
    cfg = Config(deslizamiento_min_pct=0.0, comision_taker_pct=0.0)
    o, h, l, c = gbm(seed=3)
    n = len(c)
    d = DatosMoneda("LEAK", 0, o, h, l, c, np.full(n, 5e6))
    idx = np.arange(100, n - 10, 7)
    futuro = c[idx + 1] - o[idx + 1]                # rendimiento de la vela que aún no ha ocurrido
    lado = np.where(futuro >= 0, 1, -1).astype(np.int8)
    s = Senales(idx, lado, c[idx] * 0.02)
    sal = Salida(max_velas_1m=1)
    e0 = simular_moneda(d, s, cfg, sal, latencia_velas=0).pnl.mean()
    e1 = simular_moneda(d, s, cfg, sal, latencia_velas=1).pnl.mean()
    # ventaja esperada con fuga = 200 $ * E|r| = 200 * 0,8 * 0,0008 = 0,128 $ por operación
    assert e0 == pytest.approx(0.128, rel=0.1)
    assert abs(e1) < 0.25 * e0                        # con 1 vela de retraso la ventaja se esfuma


def test_salida_forzada_por_senal_contraria():
    from cazador.motor import SENAL
    d = barras([100, 100, 101, 102, 103, 104], [100, 100.5, 101.5, 102.5, 103.5, 104.5],
               [100, 99.5, 100.5, 101.5, 102.5, 103.5], [100, 101, 102, 103, 104, 105])
    s = Senales(np.array([0]), np.array([1], np.int8), np.array([50.0]), np.array([3], np.int64))
    t = simular_moneda(d, s, CFG, Salida(max_velas_1m=100))
    assert t.motivo[0] == SENAL and t.salida_px[0] == pytest.approx(103.0)   # cierre de la vela 3
    assert t.salida_ts[0] == 4 * 60_000
