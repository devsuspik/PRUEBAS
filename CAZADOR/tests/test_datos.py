"""Lectores con ficheros sintéticos que imitan el formato oficial. NO sustituyen la prueba con red real."""
import io
import zipfile

import numpy as np
import pandas as pd

from cazador import datos
from cazador.datos import (leer_klines_zip, leer_metrics_zip, leer_funding_zip, leer_aggtrades_zip, a_rejilla_1m,
                           a_datos_moneda, parsear_exchange_info, es_cripto_puro, universo_por_fecha, modo_reducido)


def zipear(texto, nombre="x.csv"):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(nombre, texto)
    return b.getvalue()


KL = ("1735689600000,93000.0,93100.0,92900.0,93050.0,10.5,1735689659999,976000.0,120,5.0,465000.0,0\n"
      "1735689660000,93050.0,93200.0,93000.0,93150.0,8.0,1735689719999,745000.0,100,4.0,372000.0,0\n"
      "1735689780000,93150.0,93150.0,93100.0,93120.0,2.0,1735689839999,186000.0,30,1.0,93000.0,0\n")   # falta 1 minuto (…720000)


def test_klines_con_y_sin_cabecera():
    a = leer_klines_zip(zipear(KL))
    cab = ("open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,"
           "taker_buy_quote_volume,ignore\n" + KL)
    b = leer_klines_zip(zipear(cab))
    pd.testing.assert_frame_equal(a, b)
    assert list(a.columns) == ["t", "o", "h", "l", "c", "v", "qv", "n", "tb_v", "tb_qv"]
    assert a.t.iloc[0] == 1735689600000 and a.c.iloc[1] == 93150.0


def test_microsegundos_se_normalizan():
    us = KL.replace("1735689600000", "1735689600000000", 1)
    assert leer_klines_zip(zipear(us)).t.iloc[0] == 1735689600000


def test_rejilla_rellena_huecos_y_cuenta_calidad():
    g, rep = a_rejilla_1m(leer_klines_zip(zipear(KL)))
    assert len(g) == 4 and rep["minutos_faltantes"] == 1 and rep["racha_hueco_max_min"] == 1
    assert g.qv.iloc[2] == 0 and g.c.iloc[2] == g.c.iloc[1]        # hueco: cierre previo y volumen 0
    assert rep["duplicados"] == 0 and rep["velas_imposibles"] == 0


def test_calidad_detecta_duplicados_e_imposibles():
    df = leer_klines_zip(zipear(KL))
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    df.loc[1, "h"] = df.loc[1, "l"] - 1           # vela imposible (h < l)
    g, rep = a_rejilla_1m(df)
    assert rep["duplicados"] == 1 and rep["velas_imposibles"] == 1


def test_salto_de_redenominacion_se_marca():
    df = leer_klines_zip(zipear(KL))
    df.loc[1:, ["o", "h", "l", "c"]] *= 0.001      # tipo 1000PEPE: el precio cae 1000x de golpe
    _, rep = a_rejilla_1m(df)
    assert rep["saltos_mayores_40pct_1m"] >= 1


def test_metrics_funding_aggtrades():
    m = leer_metrics_zip(zipear(
        "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,"
        "sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
        "2025-01-01 00:05:00,BTCUSDT,80000.5,7.4e9,1.8,1.6,2.1,0.95\n"))
    assert m.t.iloc[0] == int(pd.Timestamp("2025-01-01 00:05:00", tz="UTC").timestamp() * 1000)
    assert m.oi.iloc[0] == 80000.5 and m.taker_ls_vol.iloc[0] == 0.95
    f = leer_funding_zip(zipear("calc_time,funding_interval_hours,last_funding_rate\n1735718400000,8,0.0001\n"))
    assert f.tasa.iloc[0] == 0.0001 and f.horas.iloc[0] == 8
    a = leer_aggtrades_zip(zipear(
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        "1,93000.1,0.5,1,1,1735689600123,true\n2,93000.2,0.1,2,3,1735689600456,false\n"))
    assert list(a.vendedor_maker) == [True, False] and a.px.iloc[1] == 93000.2


def test_exchange_info_y_exclusiones():
    j = {"symbols": [
        {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "PERPETUAL", "status": "TRADING",
         "underlyingType": "COIN", "underlyingSubType": ["PoW"], "onboardDate": 1569398400000,
         "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.10"}, {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                     {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001"}, {"filterType": "MIN_NOTIONAL", "notional": "100"}]},
        {"symbol": "TSLAUSDT", "baseAsset": "TSLA", "quoteAsset": "USDT", "contractType": "PERPETUAL", "status": "TRADING",
         "underlyingType": "EQUITY", "underlyingSubType": ["TRADFI"], "onboardDate": 1, "filters": []},
        {"symbol": "USDCUSDT", "baseAsset": "USDC", "quoteAsset": "USDT", "contractType": "PERPETUAL", "status": "TRADING",
         "underlyingType": "COIN", "underlyingSubType": [], "onboardDate": 1, "filters": []},
        {"symbol": "BTCUSDT_250627", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "CURRENT_QUARTER", "filters": []},
    ]}
    df = parsear_exchange_info(j)
    assert len(df) == 3
    puros = df[df.apply(es_cripto_puro, axis=1)]
    assert list(puros.simbolo) == ["BTCUSDT"]
    assert puros.tick.iloc[0] == 0.1 and puros.step.iloc[0] == 0.001 and puros.min_notional.iloc[0] == 100


def test_universo_sin_mirar_al_futuro_y_modo_reducido():
    dias = pd.date_range("2025-01-01", periods=20)
    v = pd.DataFrame({"A": 2e6, "B": 0.5e6}, index=dias)
    v.loc[dias[10]:, "B"] = 50e6                       # B se hace líquida el día 10
    u = universo_por_fecha(v)
    assert not u.loc[dias[10], "B"]                    # el propio día 10 aún no cuenta (volumen de los 7 d ANTERIORES)
    assert u.loc[dias[11], "B"] and u.loc[dias[8], "A"] and not u.loc[dias[3], "A"]   # A: 7*2=14M > 10M, pero sin 7 d previos no hay dato
    vol = pd.Series({f"S{i}": 100 - i for i in range(80)})
    sel = modo_reducido(vol, semilla=1)
    assert len(sel) == 50 and sel[:15] == [f"S{i}" for i in range(15)] and sel == modo_reducido(vol, semilla=1)


def test_a_datos_moneda_con_funding():
    g, _ = a_rejilla_1m(leer_klines_zip(zipear(KL)))
    f = leer_funding_zip(zipear("calc_time,funding_interval_hours,last_funding_rate\n1735689720000,8,0.0002\n"))
    d = a_datos_moneda("BTCUSDT", g, f, step=0.001)
    assert d.n == 4 and d.f_idx().tolist() == [2] and d.f_tasa().tolist() == [0.0002]
