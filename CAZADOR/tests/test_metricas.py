import numpy as np
import pandas as pd
import pytest

from cazador import metricas as M


def test_dsr_ruido_no_pasa_y_senal_real_si():
    rng = np.random.default_rng(0)
    T, N = 500, 300
    ruido = rng.normal(0, 1, (T, N))
    srs = np.array([M.sharpe_periodo(ruido[:, i]) for i in range(N)])
    mejor = int(np.argmax(srs))
    dsr_ruido = M.dsr(ruido[:, mejor], N, float(np.var(srs, ddof=1)))
    assert dsr_ruido < 0.90                              # el mejor de 300 pruebas de puro ruido NO es significativo
    real = rng.normal(0.25, 1, T)                         # Sharpe por periodo 0,25 (muy alto), una sola prueba
    assert M.dsr(real, 1) > 0.99
    assert M.dsr(real, 300) is None                       # sin varianza de las pruebas => NO CALCULADO, no se inventa


def test_pbo_ruido_ronda_05_y_senal_real_es_baja():
    rng = np.random.default_rng(1)
    T, N = 640, 40
    ruido = rng.normal(0, 1, (T, N))
    p = M.pbo_cscv(ruido, S=16)
    assert 0.3 < p["pbo"] < 0.7
    real = ruido.copy()
    real[:, 0] += 0.2                                     # una configuración con ventaja genuina y estable
    assert M.pbo_cscv(real, S=16)["pbo"] < 0.15


def test_montecarlo_y_metricas_basicas():
    pnl = np.array([1.0, -1.0, 2.0, -0.5, -0.5, 1.5] * 20)
    mc = M.monte_carlo_bloques(pnl, n=2000, bloque=6)
    assert mc["dd"]["p5"] <= mc["dd"]["p50"] <= mc["dd"]["p95"]
    assert M.max_drawdown(np.array([1, -2, -1, 3, -4.0])) == pytest.approx(4.0)
    assert M.peor_racha(np.array([1, -1, -1, -1, 1, -1.0])) == 3
    assert M.profit_factor(np.array([2, 2, -1.0])) == pytest.approx(4.0)
    assert M.monte_carlo_bloques(pnl[:10]) is None       # muy pocas operaciones => NO CALCULADO


def test_supervivencia():
    # stop 1R, objetivo 1R, costes 0,1R => hay que acertar 55 %
    assert M.supervivencia(1.0, 0.1) == pytest.approx(0.55)
    assert M.supervivencia(3.0, 0.1) == pytest.approx(1.1 / 4.0)


def test_meseta():
    r = M.meseta(lambda p: 1.0 if p["a"] > 0 else -1.0, {"a": 10.0}, rel=0.2)
    assert r["frac_positivos"] == 1.0
    r2 = M.meseta(lambda p: 1.0 if abs(p["a"] - 10) < 1e-9 else -1.0, {"a": 10.0}, rel=0.2)     # pico aislado
    assert r2["frac_positivos"] == 0.0


def base_ok():
    return dict(n=300, exp_x15=0.05, profit_factor=1.4, meses_positivos=0.7, dsr=0.95, pbo=0.2, meseta=0.8,
                sin_mejor_semana=10.0, sin_5_mejores_ops=8.0, holdout_exp=0.1)


def test_clasificar():
    assert M.clasificar(base_ok())[0] == "APTA"
    c = base_ok(); c["dsr"] = 0.85
    assert M.clasificar(c)[0] == "PROMETEDORA"
    c = base_ok(); c["profit_factor"] = 1.0
    assert M.clasificar(c)[0] == "RECHAZADA"
    c = base_ok(); c["dsr"] = None                        # dato que falta => nunca APTA
    assert M.clasificar(c)[0] == "INCOMPLETA"
    c = base_ok(); c["holdout_exp"] = None; c["holdout_regimen_ausente"] = True
    assert M.clasificar(c)[0] == "APTA"
    c = base_ok(); c["holdout_exp"] = -0.1
    assert M.clasificar(c)[0] == "RECHAZADA"
