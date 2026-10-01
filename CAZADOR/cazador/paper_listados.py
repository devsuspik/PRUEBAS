"""PAPER TRADING del corto de listados nuevos (regla pre-registrada de INFORME_FINAL.md §5). No opera: solo registra y resuelve en papel.

  python -m cazador.paper_listados registrar   # detecta listados nuevos de Binance USDT-M y anota la operación en papel
  python -m cazador.paper_listados resolver    # resuelve con velas de 1 m reales las operaciones cuya salida ya ocurrió
  python -m cazador.paper_listados informe     # resumen acumulado frente a los umbrales de parada

REGLA: CORTO a las 00:00 UTC de d0+2 (d0 = día UTC del listado), stop +8 %, objetivo -40 %, salida a los 7 días. Nocional 200 $ (20 $ x 10x).
VARIANTE REFINADA (informativa, p = 0,10 en validación): solo si BTC no ha caído > 1,2 % en los 7 días previos y el volumen de las 24 h previas >= 31,4 M$.
Ambas se anotan siempre (columna 'refinada_ok'). Costes: comisión taker 0,05 % por lado + deslizamiento 0,02 % por lado (los del modelo). El funding
real se suma al resolver. ESTADO: lógica probada con datos sintéticos (tests/test_paper.py); NO probado contra la API real (fapi bloqueada donde se escribió).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CFG

FAPI = "https://fapi.binance.com"
CSV = Path(__file__).resolve().parent.parent / "paper_listados.csv"
DIA = 86_400_000
STOP, OBJ, DIAS = 0.08, 0.40, 7
UMBRAL_BTC7, UMBRAL_VOL24 = -0.012, 31.4e6
# parada (Monte Carlo del régimen reciente): beneficio acumulado en papel por debajo de esto tras N operaciones cerradas
PARADA = {30: -283.0, 45: -321.0, 60: -353.0}
COLS = ["simbolo", "d0", "entrada_ts", "entrada_px", "stop_px", "objetivo_px", "salida_max_ts", "btc7", "vol24h_usd", "refinada_ok",
        "estado", "salida_ts", "salida_px", "motivo", "pnl_usd", "funding_usd"]


def nuevos_listados(exchange_info: dict, ahora_ms: int, ventana_dias: int = 4) -> list:
    """Perpetuos USDT en TRADING con onboardDate en los últimos ``ventana_dias`` días (excluye cosas que no son cripto por subyacente)."""
    out = []
    for s in exchange_info.get("symbols", []):
        if s.get("contractType") != "PERPETUAL" or s.get("quoteAsset") != "USDT" or s.get("status") != "TRADING":
            continue
        if str(s.get("underlyingType", "COIN")).upper() not in ("COIN", ""):
            continue
        sub = ",".join(s.get("underlyingSubType", [])).upper()
        if any(x in sub for x in ("TRADFI", "EQUITY", "COMMODITY", "INDEX", "STOCK", "METAL")):
            continue
        ob = int(s.get("onboardDate", 0))
        if ahora_ms - ventana_dias * DIA <= ob <= ahora_ms:
            out.append((s["symbol"], ob))
    return out


def entrada_ts(onboard_ms: int) -> int:
    d0 = (onboard_ms // DIA) * DIA
    return d0 + 2 * DIA                                           # 00:00 UTC de d0+2


def abrir(simbolo: str, onboard_ms: int, klines_1m: pd.DataFrame, btc_cierre_t1: float, btc_cierre_t8: float) -> dict:
    """klines_1m: columnas t (ms), o, h, l, c, qv. Debe contener la vela de la hora de entrada y las 24 h previas."""
    t_e = entrada_ts(onboard_ms)
    k = klines_1m[klines_1m.t >= t_e]
    if k.empty:
        raise ValueError("todavía no hay datos de la hora de entrada")
    px = float(k.iloc[0].o)
    vol24 = float(klines_1m[(klines_1m.t < t_e) & (klines_1m.t >= t_e - DIA)].qv.sum())
    btc7 = btc_cierre_t1 / btc_cierre_t8 - 1.0
    return dict(simbolo=simbolo, d0=int((onboard_ms // DIA) * DIA), entrada_ts=int(k.iloc[0].t), entrada_px=px, stop_px=px * (1 + STOP),
                objetivo_px=px * (1 - OBJ), salida_max_ts=int(k.iloc[0].t) + DIAS * DIA, btc7=btc7, vol24h_usd=vol24,
                refinada_ok=bool(btc7 >= UMBRAL_BTC7 and vol24 >= UMBRAL_VOL24), estado="abierta")


def resolver_op(op: dict, klines_1m: pd.DataFrame, funding: pd.DataFrame | None = None, cfg=CFG) -> dict:
    """Recorre las velas de 1 m posteriores a la entrada. Conservador: si stop y objetivo caen en la misma vela cuenta el stop;
    hueco a través del stop -> sale a la apertura. Devuelve la operación con estado 'cerrada' o 'abierta' (si aún no terminó)."""
    k = klines_1m[(klines_1m.t >= op["entrada_ts"]) & (klines_1m.t <= op["salida_max_ts"])].sort_values("t")
    px_e, st, ob = op["entrada_px"], op["stop_px"], op["objetivo_px"]
    salida = None
    for r in k.itertuples():
        if r.t > op["entrada_ts"] and r.o >= st:
            salida = (r.t, r.o * (1 + cfg.slip_min), "stop_hueco"); break
        if r.h >= st:
            salida = (r.t, st * (1 + cfg.slip_min), "stop"); break
        if r.l <= ob:
            salida = (r.t, ob * (1 + cfg.slip_min), "objetivo"); break
    if salida is None:
        if k.empty or k.iloc[-1].t < op["salida_max_ts"] - 2 * 60_000:
            return {**op, "estado": "abierta"}
        r = k.iloc[-1]
        salida = (int(r.t), float(r.c) * (1 + cfg.slip_min), "tiempo_max")
    t_s, p_s, mot = salida
    entrada_real = px_e * (1 - cfg.slip_min)                      # corto: vende por debajo del precio de referencia
    qty = cfg.nocional_usd / px_e
    bruto = (entrada_real - p_s) * qty
    comis = cfg.fee_taker * qty * (entrada_real + p_s)
    fund = 0.0
    if funding is not None and len(funding):
        f = funding[(funding.t > op["entrada_ts"]) & (funding.t <= t_s)]
        fund = float((f.tasa * qty * px_e).sum())                 # el corto COBRA si la tasa es positiva
    return {**op, "estado": "cerrada", "salida_ts": int(t_s), "salida_px": float(p_s), "motivo": mot, "pnl_usd": bruto - comis + fund, "funding_usd": fund}


def informe(df: pd.DataFrame) -> str:
    c = df[df.estado == "cerrada"]
    if c.empty:
        return "sin operaciones cerradas todavía"
    n, tot = len(c), float(c.pnl_usd.sum())
    txt = f"cerradas {n} | abiertas {int((df.estado == 'abierta').sum())} | acumulado ${tot:+.1f} | exp ${tot / n:+.2f}/op | aciertos {np.mean(c.pnl_usd > 0):.0%}"
    r = c[c.refinada_ok == True]  # noqa: E712
    if len(r):
        txt += f" | variante refinada: {len(r)} ops ${r.pnl_usd.sum():+.1f}"
    for k, lim in PARADA.items():
        if n >= k and tot < lim:
            txt += f"\n  ⛔ PARADA: tras {n} operaciones el acumulado ${tot:+.0f} < umbral {lim:+.0f} (p5 del Monte Carlo para {k} ops)"
    if (c.motivo == "liquidacion").sum() >= 2:
        txt += "\n  ⛔ PARADA: 2 o más liquidaciones"
    return txt


def _get(url, params=None):
    from .datos import http_get
    r = http_get(url, params=params)
    return r.json() if r is not None else None


def _klines(simbolo, ini_ms, fin_ms):
    filas = []
    t = ini_ms
    while t < fin_ms:
        j = _get(f"{FAPI}/fapi/v1/klines", dict(symbol=simbolo, interval="1m", startTime=t, endTime=fin_ms, limit=1500))
        if not j:
            break
        filas += j
        t = int(j[-1][0]) + 60_000
        if len(j) < 1500:
            break
    df = pd.DataFrame(filas, columns=["t", "o", "h", "l", "c", "v", "tc", "qv", "n", "tb", "tbq", "x"])
    return df[["t", "o", "h", "l", "c", "qv"]].astype({"t": "int64", "o": float, "h": float, "l": float, "c": float, "qv": float})


def _btc_cierres(ahora_ms):
    j = _get(f"{FAPI}/fapi/v1/klines", dict(symbol="BTCUSDT", interval="1d", limit=10))
    c = [float(x[4]) for x in j[:-1]]                             # velas diarias CERRADAS
    return c[-1], c[-8]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "informe"
    df = pd.read_csv(CSV) if CSV.exists() else pd.DataFrame(columns=COLS)
    ahora = int(pd.Timestamp.utcnow().timestamp() * 1000)
    if cmd == "registrar":
        ei = _get(f"{FAPI}/fapi/v1/exchangeInfo")
        b1, b8 = _btc_cierres(ahora)
        for s, ob in nuevos_listados(ei, ahora):
            if s in set(df.simbolo) or entrada_ts(ob) > ahora:
                continue
            k = _klines(s, entrada_ts(ob) - DIA, entrada_ts(ob) + 5 * 60_000)
            try:
                df = pd.concat([df, pd.DataFrame([abrir(s, ob, k, b1, b8)])], ignore_index=True)
                print("registrada", s)
            except ValueError as e:
                print(s, e)
    elif cmd == "resolver":
        for i, op in df[df.estado == "abierta"].iterrows():
            k = _klines(op.simbolo, int(op.entrada_ts), min(ahora, int(op.salida_max_ts) + 60_000))
            fj = _get(f"{FAPI}/fapi/v1/fundingRate", dict(symbol=op.simbolo, startTime=int(op.entrada_ts), limit=1000)) or []
            f = pd.DataFrame([{"t": int(x["fundingTime"]), "tasa": float(x["fundingRate"])} for x in fj])
            r = resolver_op(op.to_dict(), k, f)
            for c, v in r.items():
                df.loc[i, c] = v
    df.to_csv(CSV, index=False)
    print(informe(df))


if __name__ == "__main__":
    main()
