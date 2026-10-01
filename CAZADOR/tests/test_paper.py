import numpy as np
import pandas as pd
import pytest

from cazador import paper_listados as P

DIA = 86_400_000
D0 = 1_760_000_000_000 // DIA * DIA                                  # un día UTC cualquiera


def velas(t0, n, px=100.0, f=None):
    t = t0 + np.arange(n) * 60_000
    o = np.full(n, px) if f is None else f(n)
    return pd.DataFrame({"t": t, "o": o, "h": o + 0.01, "l": o - 0.01, "c": o, "qv": np.full(n, 1e6)})


def test_nuevos_listados_filtra_tradfi_y_ventana():
    ahora = D0 + 3 * DIA
    ei = {"symbols": [
        {"symbol": "NEWUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING", "underlyingType": "COIN", "onboardDate": ahora - DIA},
        {"symbol": "OLDUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING", "underlyingType": "COIN", "onboardDate": ahora - 30 * DIA},
        {"symbol": "TSLAUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING", "underlyingType": "EQUITY", "onboardDate": ahora - DIA},
        {"symbol": "XUSDC", "contractType": "PERPETUAL", "quoteAsset": "USDC", "status": "TRADING", "underlyingType": "COIN", "onboardDate": ahora - DIA},
    ]}
    assert [s for s, _ in P.nuevos_listados(ei, ahora)] == ["NEWUSDT"]


def test_entrada_es_medianoche_de_d0_mas_2():
    ob = D0 + 14 * 3_600_000 + 123                                   # listado a las 14:00 UTC
    assert P.entrada_ts(ob) == D0 + 2 * DIA


def op_base(px=100.0, vol=2e6, b1=100.0, b8=100.0):
    ob = D0 + 10 * 3_600_000
    t_e = P.entrada_ts(ob)
    k = velas(t_e - DIA, 2 * 1440 + 10, px)
    return ob, t_e, k, P.abrir("TESTUSDT", ob, k, b1, b8)


def test_abrir_calcula_stop_objetivo_y_filtros():
    ob, t_e, k, op = op_base()
    assert op["entrada_ts"] == t_e and op["entrada_px"] == 100.0
    assert op["stop_px"] == pytest.approx(108.0) and op["objetivo_px"] == pytest.approx(60.0)
    assert op["vol24h_usd"] == pytest.approx(1e6 * 1440)
    assert op["refinada_ok"] is True                                  # btc7 = 0 >= -1,2 % y vol24h = 1,44e9 >= 31,4e6
    ob2, _, k2, op2 = op_base(b1=97.0, b8=100.0)                      # BTC -3 % en 7 días -> la variante refinada NO opera
    assert op2["refinada_ok"] is False


def test_resolver_objetivo_stop_hueco_y_tiempo():
    ob, t_e, k, op = op_base()
    def con(f):
        kk = velas(t_e - DIA, 1440 + 5 * 1440 + 3 * 1440, 100.0, f)
        return kk
    # objetivo: el precio cae un 41 % a las 3 h -> gana ~ 40 % del nocional menos costes
    k1 = con(lambda n: np.where(np.arange(n) >= 1440 + 180, 59.0, 100.0))
    r = P.resolver_op(op, k1)
    assert r["estado"] == "cerrada" and r["motivo"] == "objetivo" and r["pnl_usd"] == pytest.approx(200 * 0.40 - 0.0005 * 200 * 1.6 - 200 * 0.0002 * 2, abs=0.6)
    # stop: sube un 9 % a las 2 h
    k2 = con(lambda n: np.where(np.arange(n) >= 1440 + 120, 109.0, 100.0))
    r = P.resolver_op(op, k2)
    assert r["motivo"] in ("stop", "stop_hueco") and r["pnl_usd"] < -15
    # tiempo máximo: sin movimiento durante los 7 días
    r = P.resolver_op(op, con(lambda n: np.full(n, 100.0)))
    assert r["motivo"] == "tiempo_max" and abs(r["pnl_usd"]) < 1.0
    # abierta: solo hay datos de 1 día
    r = P.resolver_op(op, velas(t_e, 1440, 100.0))
    assert r["estado"] == "abierta"


def test_funding_positivo_lo_cobra_el_corto():
    ob, t_e, k, op = op_base()
    kk = velas(t_e - DIA, 1440 + 8 * 1440, 100.0)
    f = pd.DataFrame({"t": [t_e + 8 * 3_600_000], "tasa": [0.001]})
    r0, r1 = P.resolver_op(op, kk), P.resolver_op(op, kk, f)
    assert r1["pnl_usd"] - r0["pnl_usd"] == pytest.approx(0.001 * 2.0 * 100.0)


def test_informe_parada():
    filas = [dict(estado="cerrada", pnl_usd=-12.0, refinada_ok=True, motivo="stop") for _ in range(30)]
    txt = P.informe(pd.DataFrame(filas))
    assert "PARADA" in txt and "tras 30 operaciones" in txt                  # 30 x -12 = -360 < -283
