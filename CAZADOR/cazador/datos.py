"""§2 DATOS REALES (Binance USDT-M perpetuos) – descarga, caché Parquet, control de calidad.

ESTADO: los lectores se prueban con ficheros sintéticos que imitan el formato oficial (tests/test_datos.py).
NO se han probado contra data.binance.vision porque el entorno donde se escribió no tenía acceso a ese host.
Antes de fiarte de un resultado, ejecuta ``python -m cazador.datos --probar`` con red real.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd
import requests

from .motor import DatosMoneda, MS_MIN

BASE = "https://data.binance.vision/data/futures/um"
LISTADO = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FAPI = "https://fapi.binance.com"
CACHE = Path(__file__).resolve().parent.parent / "datos_cache"

COLS_KLINES = ["t", "o", "h", "l", "c", "v", "t_cierre", "qv", "n", "tb_v", "tb_qv", "_ignore"]
STABLES = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "EURI", "AEUR", "USDE", "USD1", "RLUSD", "XUSD"}


# ----------------------------------------------------------------------------------------------
# Red
# ----------------------------------------------------------------------------------------------
_sesion = requests.Session()


def http_get(url: str, reintentos: int = 6, pausa0: float = 1.0, timeout: float = 60.0,
             params: Optional[dict] = None) -> Optional[requests.Response]:
    """GET con reintentos y espera exponencial. 404 => None (el fichero no existe). 403/451 => excepción clara."""
    for i in range(reintentos):
        try:
            r = _sesion.get(url, timeout=timeout, params=params)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            if r.status_code in (403, 451):
                raise PermissionError(f"{r.status_code} en {url}: bloqueado por región o por política de red")
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(60.0, pausa0 * 2 ** i))
                continue
            r.raise_for_status()
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(min(60.0, pausa0 * 2 ** i))
    raise ConnectionError(f"sin respuesta tras {reintentos} intentos: {url}")


def descargar(url: str, destino: Path) -> Optional[Path]:
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    r = http_get(url)
    if r is None:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    tmp.write_bytes(r.content)
    tmp.replace(destino)
    return destino


def listar_prefijos(prefijo: str) -> List[str]:
    """Lista 'carpetas' del bucket público (p. ej. todos los símbolos con klines mensuales)."""
    out, marker = [], ""
    while True:
        r = http_get(LISTADO, params={"delimiter": "/", "prefix": prefijo, "marker": marker})
        if r is None:
            break
        txt = r.text
        # <Prefix> aparece una vez como eco de la consulta y luego una vez por cada CommonPrefixes
        out += [p for p in re.findall(r"<Prefix>([^<]+)</Prefix>", txt) if p != prefijo]
        if "<IsTruncated>true</IsTruncated>" not in txt:
            break
        m = re.findall(r"<NextMarker>([^<]+)</NextMarker>", txt)
        marker = m[0] if m else out[-1]
    return sorted(set(out))


# ----------------------------------------------------------------------------------------------
# Lectores (formato oficial de data.binance.vision)
# ----------------------------------------------------------------------------------------------
def _leer_csv_zip(contenido: bytes, nombres: List[str]) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as f:
            crudo = f.read().decode("utf-8")
    primera = crudo.split("\n", 1)[0]
    cabecera = 0 if re.search(r"[A-Za-z]", primera) else None
    return pd.read_csv(io.StringIO(crudo), header=cabecera, names=None if cabecera == 0 else nombres)


def leer_klines_zip(contenido: bytes) -> pd.DataFrame:
    df = _leer_csv_zip(contenido, COLS_KLINES)
    df = df.rename(columns={"open_time": "t", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v",
                            "close_time": "t_cierre", "quote_volume": "qv", "count": "n",
                            "taker_buy_volume": "tb_v", "taker_buy_quote_volume": "tb_qv"})
    df = df[["t", "o", "h", "l", "c", "v", "qv", "n", "tb_v", "tb_qv"]].copy()
    t = df["t"].astype("int64")
    # A partir de 2025 algunos ficheros spot usan microsegundos; los de futuros siguen en ms. Se normaliza por si acaso.
    df["t"] = np.where(t > 10 ** 14, t // 1000, t)
    for c in ["o", "h", "l", "c", "v", "qv", "tb_v", "tb_qv"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    df["n"] = pd.to_numeric(df["n"], errors="coerce").fillna(0).astype("int64")
    return df


def leer_metrics_zip(contenido: bytes) -> pd.DataFrame:
    """metrics (cada 5 m): create_time, symbol, sum_open_interest, sum_open_interest_value,
    count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, count_long_short_ratio,
    sum_taker_long_short_vol_ratio."""
    df = _leer_csv_zip(contenido, ["create_time", "symbol", "oi", "oi_valor", "top_ls_cuentas", "top_ls_posiciones",
                                  "ls_global", "taker_ls_vol"])
    df = df.rename(columns={"create_time": "create_time", "sum_open_interest": "oi",
                            "sum_open_interest_value": "oi_valor", "count_toptrader_long_short_ratio": "top_ls_cuentas",
                            "sum_toptrader_long_short_ratio": "top_ls_posiciones",
                            "count_long_short_ratio": "ls_global", "sum_taker_long_short_vol_ratio": "taker_ls_vol"})
    ct = df["create_time"]
    if pd.api.types.is_numeric_dtype(ct):
        df["t"] = ct.astype("int64")                                   # ms desde la época
    else:                                                               # "2025-01-01 00:05:00" (UTC)
        df["t"] = (pd.to_datetime(ct, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    keep = ["t", "oi", "oi_valor", "top_ls_cuentas", "top_ls_posiciones", "ls_global", "taker_ls_vol"]
    for c in keep[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[keep]


def leer_funding_zip(contenido: bytes) -> pd.DataFrame:
    """fundingRate: calc_time, funding_interval_hours, last_funding_rate."""
    df = _leer_csv_zip(contenido, ["calc_time", "funding_interval_hours", "last_funding_rate"])
    df = df.rename(columns={"calc_time": "t", "last_funding_rate": "tasa", "funding_interval_hours": "horas"})
    df["t"] = df["t"].astype("int64")
    df["tasa"] = pd.to_numeric(df["tasa"], errors="coerce")
    return df[["t", "tasa", "horas"]]


def leer_aggtrades_zip(contenido: bytes) -> pd.DataFrame:
    df = _leer_csv_zip(contenido, ["id", "px", "qty", "first_id", "last_id", "t", "vendedor_maker"])
    df = df.rename(columns={"agg_trade_id": "id", "price": "px", "quantity": "qty", "transact_time": "t",
                            "is_buyer_maker": "vendedor_maker"})
    df["vendedor_maker"] = df["vendedor_maker"].astype(str).str.lower().eq("true")
    return df[["id", "px", "qty", "t", "vendedor_maker"]]


# ----------------------------------------------------------------------------------------------
# exchangeInfo y universo
# ----------------------------------------------------------------------------------------------
def parsear_exchange_info(j: dict) -> pd.DataFrame:
    filas = []
    for s in j.get("symbols", []):
        if s.get("contractType") != "PERPETUAL" or s.get("quoteAsset") != "USDT":
            continue
        f = {x["filterType"]: x for x in s.get("filters", [])}
        filas.append({
            "simbolo": s["symbol"], "base": s.get("baseAsset"), "estado": s.get("status"),
            "tipo_subyacente": s.get("underlyingType", "COIN"),
            "subtipos": ",".join(s.get("underlyingSubType", [])),
            "tick": float(f.get("PRICE_FILTER", {}).get("tickSize", 0) or 0),
            "step": float(f.get("MARKET_LOT_SIZE", f.get("LOT_SIZE", {})).get("stepSize", 0) or 0),
            "min_notional": float(f.get("MIN_NOTIONAL", {}).get("notional", 5) or 5),
            "alta_ms": int(s.get("onboardDate", 0)),
        })
    return pd.DataFrame(filas)


def es_cripto_puro(fila: pd.Series) -> bool:
    """Excluye acciones tokenizadas, materias primas, índices y stablecoins."""
    if fila["base"] in STABLES:
        return False
    if str(fila["tipo_subyacente"]).upper() not in ("COIN", ""):
        return False
    sub = str(fila["subtipos"]).upper()
    return not any(x in sub for x in ("TRADFI", "EQUITY", "COMMODITY", "INDEX", "STOCK", "METAL"))


def universo_por_fecha(volumen_diario_usdt: pd.DataFrame, umbral_7d: float = 10e6) -> pd.DataFrame:
    """Matriz booleana fecha x símbolo: volumen de los 7 días ANTERIORES > umbral (sin mirar al futuro).

    Incluye las monedas retiradas después (no hay sesgo de supervivencia mientras se descarguen sus ficheros).
    """
    v7 = volumen_diario_usdt.rolling(7, min_periods=7).sum().shift(1)
    return v7 > umbral_7d


def modo_reducido(volumen_total: pd.Series, semilla: int = 20250930, top: int = 15, azar: int = 35) -> List[str]:
    """Top 15 por volumen + 35 al azar (semilla fija). Hay que declararlo en el informe."""
    orden = volumen_total.sort_values(ascending=False)
    cabeza = list(orden.index[:top])
    resto = list(orden.index[top:])
    rng = np.random.default_rng(semilla)
    elegidas = list(rng.choice(resto, size=min(azar, len(resto)), replace=False)) if resto else []
    return cabeza + elegidas


# ----------------------------------------------------------------------------------------------
# Rejilla regular de 1 m y calidad
# ----------------------------------------------------------------------------------------------
def a_rejilla_1m(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Devuelve velas en rejilla regular (huecos = cierre previo, volumen 0) + informe de calidad."""
    if df.empty:
        return df, {"n": 0}
    df = df.sort_values("t")
    dup = int(df["t"].duplicated().sum())
    df = df.drop_duplicates("t", keep="last")
    imposibles = ((df.h < df.l) | (df.o > df.h + 1e-12) | (df.o < df.l - 1e-12) | (df.c > df.h + 1e-12)
                  | (df.c < df.l - 1e-12) | (df[["o", "h", "l", "c"]] <= 0).any(axis=1) | df[["o", "h", "l", "c"]].isna().any(axis=1))
    n_imp = int(imposibles.sum())
    df = df[~imposibles]
    t0, t1 = int(df.t.iloc[0]), int(df.t.iloc[-1])
    idx = np.arange(t0, t1 + MS_MIN, MS_MIN, dtype=np.int64)
    g = df.set_index("t").reindex(idx)
    faltan = g["c"].isna().to_numpy()
    c = g["c"].ffill()
    for col in ("o", "h", "l"):
        g[col] = g[col].fillna(c)
    g["c"] = c
    for col in ("v", "qv", "tb_v", "tb_qv", "n"):
        g[col] = g[col].fillna(0.0)
    # saltos imposibles en 1 m (>50 %): típico de redenominaciones (1000PEPE...) o errores
    saltos = int((np.abs(np.log(g["c"]).diff()) > 0.4).sum())
    huecos = int(faltan.sum())
    # racha de huecos más larga
    racha = mx = 0
    for x in faltan:
        racha = racha + 1 if x else 0
        mx = max(mx, racha)
    rep = {"n": int(len(g)), "duplicados": dup, "velas_imposibles": n_imp, "minutos_faltantes": huecos,
           "racha_hueco_max_min": mx, "saltos_mayores_40pct_1m": saltos,
           "minutos_sin_volumen": int((g["qv"] <= 0).sum())}
    return g.reset_index().rename(columns={"index": "t"}), rep


def a_datos_moneda(simbolo: str, grid: pd.DataFrame, funding: Optional[pd.DataFrame] = None,
                   tick: float = 0.0, step: float = 0.0, min_notional: float = 5.0) -> DatosMoneda:
    d = DatosMoneda(simbolo=simbolo, t0_ms=int(grid.t.iloc[0]),
                    o=grid.o.to_numpy("float64"), h=grid.h.to_numpy("float64"), l=grid.l.to_numpy("float64"),
                    c=grid.c.to_numpy("float64"), qv=grid.qv.to_numpy("float64"),
                    tb_qv=grid.tb_qv.to_numpy("float64"), tick=tick, step=step, min_notional=min_notional)
    if funding is not None and len(funding):
        f = funding.sort_values("t")
        d.f_ts_ms = f["t"].to_numpy("int64")
        d.f_rate = f["tasa"].to_numpy("float64")
    return d


# ----------------------------------------------------------------------------------------------
# Descarga con caché
# ----------------------------------------------------------------------------------------------
def meses_entre(ini: pd.Timestamp, fin: pd.Timestamp) -> List[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(ini, fin, freq="M")]


def klines_simbolo(simbolo: str, intervalo: str, ini: pd.Timestamp, fin: pd.Timestamp) -> pd.DataFrame:
    """Mensuales completos + diarios del mes en curso. Caché Parquet por símbolo/intervalo."""
    ruta = CACHE / "klines" / intervalo / f"{simbolo}.parquet"
    if ruta.exists():
        return pd.read_parquet(ruta)
    partes = []
    hoy = pd.Timestamp.utcnow().tz_localize(None).normalize()
    for m in meses_entre(ini, fin):
        ultimo_dia_mes = (pd.Period(m, "M").end_time).normalize()
        if ultimo_dia_mes < hoy - pd.Timedelta(days=1):
            url = f"{BASE}/monthly/klines/{simbolo}/{intervalo}/{simbolo}-{intervalo}-{m}.zip"
            p = descargar(url, CACHE / "zips" / f"{simbolo}-{intervalo}-{m}.zip")
            if p is not None:
                partes.append(leer_klines_zip(p.read_bytes()))
        else:
            for dia in pd.date_range(pd.Period(m, "M").start_time, min(hoy - pd.Timedelta(days=1), fin), freq="D"):
                ds = dia.strftime("%Y-%m-%d")
                url = f"{BASE}/daily/klines/{simbolo}/{intervalo}/{simbolo}-{intervalo}-{ds}.zip"
                p = descargar(url, CACHE / "zips" / f"{simbolo}-{intervalo}-{ds}.zip")
                if p is not None:
                    partes.append(leer_klines_zip(p.read_bytes()))
    df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["t", "o", "h", "l", "c", "v", "qv", "n", "tb_v", "tb_qv"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta)
    return df


def funding_simbolo(simbolo: str, ini: pd.Timestamp, fin: pd.Timestamp) -> pd.DataFrame:
    ruta = CACHE / "funding" / f"{simbolo}.parquet"
    if ruta.exists():
        return pd.read_parquet(ruta)
    partes = []
    for m in meses_entre(ini, fin):
        url = f"{BASE}/monthly/fundingRate/{simbolo}/{simbolo}-fundingRate-{m}.zip"
        p = descargar(url, CACHE / "zips" / f"{simbolo}-fundingRate-{m}.zip")
        if p is not None:
            partes.append(leer_funding_zip(p.read_bytes()))
    df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["t", "tasa", "horas"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta)
    return df


def probar() -> None:
    """Comprobación mínima con red real: baja 1 mes de BTCUSDT 1h y 1d de funding y lo valida."""
    ini, fin = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-31")
    k = klines_simbolo("BTCUSDT", "1h", ini, fin)
    assert len(k) >= 700, f"pocas velas: {len(k)}"
    assert k["t"].is_unique and (k[["o", "h", "l", "c"]] > 0).all().all(), "duplicados o precios no positivos"
    print("klines OK:", len(k), "velas de 1h, del", pd.to_datetime(k.t.min(), unit="ms"), "al", pd.to_datetime(k.t.max(), unit="ms"))
    f = funding_simbolo("BTCUSDT", ini, fin)
    print("funding OK:", len(f), "marcas; intervalos:", sorted(f.horas.unique()) if len(f) else "?")


if __name__ == "__main__":
    import sys
    if "--probar" in sys.argv:
        probar()
