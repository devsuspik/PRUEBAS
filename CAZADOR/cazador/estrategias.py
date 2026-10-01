"""§5 CATÁLOGO DE ESTRATEGIAS – primeras familias implementadas.

Implementadas en esta entrega (estado real, no el catálogo completo):
  A. ema_cross, donchian, tsmom
  B. orb_sesion
  C. rsi2, bollinger_rev
Cada una admite ``invertir=True`` (versión inversa) y <= 5 parámetros libres.
PENDIENTES (Ronda 1 al disponer de datos reales): resto de A (Supertrend, SAR, Ichimoku, ADX), resto de B,
C (VWAP, barrida de liquidez), D (funding, OI, L/S, liquidaciones, basis), E (microestructura, necesita aggTrades),
F (transversales), G (estacionalidad, eventos), H (velas), I (genética, ML, meta-etiquetado).

Regla de oro anti-fuga: la señal de la vela i solo usa velas <= i. ``comprobar_causalidad`` lo verifica recortando datos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd

from .motor import DatosMoneda, Senales, MS_MIN


@dataclass
class Barras:
    """Velas de marco superior construidas a partir de 1 m. ``idx_cierre`` = índice de 1 m de su última vela."""
    tf: int
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    qv: np.ndarray
    tb_qv: np.ndarray
    idx_cierre: np.ndarray
    ts_apertura: np.ndarray        # ms
    funding: Optional[np.ndarray] = None       # último funding CONOCIDO al cierre de la vela (ffill)
    fund_pct: Optional[np.ndarray] = None      # percentil (0-1) de ese funding en los 90 días previos de la propia moneda
    fund_nuevo: Optional[np.ndarray] = None    # True si entre la vela anterior y esta se publicó un funding nuevo

    def __len__(self) -> int:
        return len(self.c)

    @property
    def tb_ratio(self) -> np.ndarray:
        """Fracción del volumen que fue compra agresiva (taker buy) en la vela."""
        return np.where(self.qv > 0, self.tb_qv / np.where(self.qv > 0, self.qv, 1.0), np.nan)

    @property
    def hora(self) -> np.ndarray:
        """Hora UTC (0-23.99) de la APERTURA de la vela."""
        return ((self.ts_apertura // MS_MIN) % 1440) / 60.0

    @property
    def dow(self) -> np.ndarray:
        """Día de la semana de la apertura (0 = lunes)."""
        return ((self.ts_apertura // 86_400_000) + 3) % 7


def barras_tf(d: DatosMoneda, tf_min: int) -> Barras:
    """Agrupa la rejilla de 1 m en velas alineadas a múltiplos de tf_min (desde la época). Se descarta la vela parcial inicial
    y la final incompleta, así que todas las velas devueltas están COMPLETAS (cerradas)."""
    n = d.n
    t0_min = d.t0_ms // MS_MIN
    ini = (-t0_min) % tf_min
    nb = (n - ini) // tf_min
    if nb <= 0:
        z = np.zeros(0)
        return Barras(tf_min, z, z, z, z, z, z, np.zeros(0, np.int64), np.zeros(0, np.int64))
    sl = slice(ini, ini + nb * tf_min)
    sh = lambda a: a[sl].reshape(nb, tf_min)
    tb = d.tb_qv if d.tb_qv is not None else np.zeros(n)
    idx_ap = ini + np.arange(nb, dtype=np.int64) * tf_min
    B = Barras(tf_min, sh(d.o)[:, 0], sh(d.h).max(1), sh(d.l).min(1), sh(d.c)[:, -1], sh(d.qv).sum(1),
               sh(tb).sum(1), idx_ap + tf_min - 1, d.t0_ms + idx_ap * MS_MIN)
    if len(d.f_ts_ms):
        _anadir_funding(B, d)
    return B


def _anadir_funding(B: Barras, d: DatosMoneda) -> None:
    """Funding conocido al cierre de cada vela y su percentil a 90 días (todo con información pasada)."""
    f_ts, f_rate = d.f_ts_ms, d.f_rate
    serie = pd.Series(f_rate, index=pd.to_datetime(f_ts, unit="ms"))
    pct = serie.rolling("90D", min_periods=30).rank(pct=True).to_numpy()
    cierre_ms = B.ts_apertura + B.tf * MS_MIN - 1
    k = np.searchsorted(f_ts, cierre_ms, side="right") - 1          # último funding con calc_time <= cierre de la vela
    ok = k >= 0
    kk = np.where(ok, k, 0)
    B.funding = np.where(ok, f_rate[kk], np.nan)
    B.fund_pct = np.where(ok, pct[kk], np.nan)
    nuevo = np.zeros(len(B), bool)
    nuevo[1:] = k[1:] != k[:-1]
    B.fund_nuevo = nuevo & ok


# ----------------------------------------------------------------------------------------------
# Indicadores (todos causales: el valor en i usa datos <= i)
# ----------------------------------------------------------------------------------------------
def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).mean().to_numpy()


def atr(B: Barras, n: int = 14) -> np.ndarray:
    pc = np.concatenate([[np.nan], B.c[:-1]])
    tr = np.nanmax(np.vstack([B.h - B.l, np.abs(B.h - pc), np.abs(B.l - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def rsi(x: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(x, prepend=np.nan)
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy()


def _emitir(B: Barras, cond_larga: np.ndarray, cond_corta: np.ndarray, stop_dist: np.ndarray,
            invertir: bool, solo: str = "ambos", cooldown: int = 0, extra_ok: Optional[np.ndarray] = None) -> Senales:
    """Convierte condiciones booleanas por vela en señales. Quita velas sin ATR, aplica cooldown y filtros de lado."""
    if invertir:
        cond_larga, cond_corta = cond_corta, cond_larga
    if solo == "long":
        cond_corta = np.zeros_like(cond_corta)
    elif solo == "short":
        cond_larga = np.zeros_like(cond_larga)
    ok = np.isfinite(stop_dist) & (stop_dist > 0)
    if extra_ok is not None:
        ok &= extra_ok
    L, S = cond_larga & ok, cond_corta & ok & ~cond_larga
    i = np.flatnonzero(L | S)
    if cooldown > 0 and len(i):
        keep, ult = [], -10 ** 12
        for k in i:
            if k - ult > cooldown:
                keep.append(k)
                ult = k
        i = np.array(keep, dtype=np.int64)
    lado = np.where(L[i], 1, -1).astype(np.int8)
    return Senales(B.idx_cierre[i].astype(np.int64), lado, stop_dist[i])


# ----------------------------------------------------------------------------------------------
# A. Tendencia y momentum
# ----------------------------------------------------------------------------------------------
def ema_cross(B: Barras, rapida: int = 20, lenta: int = 50, atr_n: int = 14, k_atr: float = 2.0,
              invertir: bool = False, solo: str = "ambos") -> Senales:
    a, b = ema(B.c, rapida), ema(B.c, lenta)
    up = (a > b) & (np.roll(a, 1) <= np.roll(b, 1))
    dn = (a < b) & (np.roll(a, 1) >= np.roll(b, 1))
    up[0] = dn[0] = False
    return _emitir(B, up, dn, k_atr * atr(B, atr_n), invertir, solo)


def donchian(B: Barras, n: int = 20, atr_n: int = 14, k_atr: float = 2.0, invertir: bool = False,
             solo: str = "ambos") -> Senales:
    mx = pd.Series(B.h).rolling(n).max().shift(1).to_numpy()     # máximo de las N velas PREVIAS
    mn = pd.Series(B.l).rolling(n).min().shift(1).to_numpy()
    return _emitir(B, B.c > mx, B.c < mn, k_atr * atr(B, atr_n), invertir, solo)


def tsmom(B: Barras, n: int = 30, atr_n: int = 14, k_atr: float = 3.0, invertir: bool = False, solo: str = "ambos",
          cada: int = 1) -> Senales:
    """Signo del rendimiento de N velas; se reevalúa cada ``cada`` velas y solo emite al cambiar de signo."""
    r = B.c / np.roll(B.c, n) - 1.0
    r[:n] = np.nan
    pos = np.where(r > 0, 1, np.where(r < 0, -1, 0))
    cambia = np.zeros(len(pos), bool)
    cambia[1:] = pos[1:] != pos[:-1]
    cambia &= (np.arange(len(pos)) % cada == 0) & np.isfinite(r)
    return _emitir(B, cambia & (pos > 0), cambia & (pos < 0), k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# B. Ruptura intradía
# ----------------------------------------------------------------------------------------------
def orb_sesion(B: Barras, hora_inicio_utc: float = 0.0, minutos_rango: int = 60, atr_n: int = 14, k_atr: float = 1.5,
               invertir: bool = False, solo: str = "ambos") -> Senales:
    """Opening Range Breakout: rango de los primeros ``minutos_rango`` de la sesión; primer cierre fuera del rango = señal
    (una vez por día). B.tf debe dividir a ``minutos_rango``."""
    n = len(B)
    if n == 0:
        return Senales.vacia()
    min_dia = ((B.ts_apertura // MS_MIN) % 1440).astype(int)
    dia = (B.ts_apertura // 86_400_000).astype(int)
    ini = int(hora_inicio_utc * 60)
    en_rango = (min_dia >= ini) & (min_dia < ini + minutos_rango)
    a = atr(B, atr_n)
    L = np.zeros(n, bool)
    S = np.zeros(n, bool)
    rango_hi = rango_lo = np.nan
    dia_act, usado = -1, False
    for i in range(n):
        if dia[i] != dia_act:
            dia_act, usado, rango_hi, rango_lo = dia[i], False, np.nan, np.nan
        if en_rango[i]:
            rango_hi = B.h[i] if np.isnan(rango_hi) else max(rango_hi, B.h[i])
            rango_lo = B.l[i] if np.isnan(rango_lo) else min(rango_lo, B.l[i])
        elif min_dia[i] >= ini + minutos_rango and not usado and np.isfinite(rango_hi):
            if B.c[i] > rango_hi:
                L[i], usado = True, True
            elif B.c[i] < rango_lo:
                S[i], usado = True, True
    return _emitir(B, L, S, k_atr * a, invertir, solo)


# ----------------------------------------------------------------------------------------------
# C. Reversión a la media
# ----------------------------------------------------------------------------------------------
def rsi2(B: Barras, n_rsi: int = 2, umbral: float = 10.0, sma_filtro: int = 200, atr_n: int = 14, k_atr: float = 2.0,
         invertir: bool = False, solo: str = "ambos") -> Senales:
    """Connors: compra RSI(2) < umbral con precio sobre SMA(200) (sobreventa dentro de tendencia), venta simétrica."""
    r = rsi(B.c, n_rsi)
    s = sma(B.c, sma_filtro)
    L = (r < umbral) & (B.c > s)
    S = (r > 100 - umbral) & (B.c < s)
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


def bollinger_rev(B: Barras, n: int = 20, k_sigma: float = 2.5, atr_n: int = 14, k_atr: float = 2.0,
                  invertir: bool = False, solo: str = "ambos") -> Senales:
    """Reversión de Bollinger: la vela anterior cerró fuera de la banda y esta vuelve a cerrar dentro (long si venía de abajo)."""
    m = sma(B.c, n)
    sd = pd.Series(B.c).rolling(n).std(ddof=0).to_numpy()
    hi, lo = m + k_sigma * sd, m - k_sigma * sd
    prev_c = np.roll(B.c, 1)
    prev_hi, prev_lo = np.roll(hi, 1), np.roll(lo, 1)
    L = (prev_c < prev_lo) & (B.c > prev_lo)       # estaba fuera por abajo y vuelve a entrar
    S = (prev_c > prev_hi) & (B.c < prev_hi)
    L[0] = S[0] = False
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


def con_salida_contraria(s: Senales) -> Senales:
    """Convierte una secuencia de señales en 'mantener hasta la señal contraria': se conservan solo las señales que CAMBIAN de lado
    (la primera de cada racha) y cada una sale en el cierre de la 1 m siguiente a la vela de la siguiente señal contraria
    (-1 = sin salida forzada, la última). Las salidas solo dependen de señales que ya ocurrieron: causal."""
    if len(s) == 0:
        return s
    orden = np.argsort(s.idx, kind="stable")
    idx, lado, sd = s.idx[orden], s.lado[orden], s.dist_stop[orden]
    cambia = np.ones(len(idx), bool)
    cambia[1:] = lado[1:] != lado[:-1]
    idx, lado, sd = idx[cambia], lado[cambia], sd[cambia]
    sal = np.full(len(idx), -1, np.int64)
    sal[:-1] = idx[1:] + 1
    return Senales(idx, lado, sd, sal)


# ----------------------------------------------------------------------------------------------
# Registro y utilidades
# ----------------------------------------------------------------------------------------------
REGISTRO: Dict[str, dict] = {
    "ema_cross": dict(fn=ema_cross, familia="A", params=dict(rapida=20, lenta=50, k_atr=2.0),
                      rangos=dict(rapida=(5, 50), lenta=(20, 200), k_atr=(1.0, 4.0)), enteros=("rapida", "lenta")),
    "donchian": dict(fn=donchian, familia="A", params=dict(n=20, k_atr=2.0),
                     rangos=dict(n=(10, 100), k_atr=(1.0, 4.0)), enteros=("n",)),
    "tsmom": dict(fn=tsmom, familia="A", params=dict(n=30, k_atr=3.0),
                  rangos=dict(n=(5, 120), k_atr=(1.5, 5.0)), enteros=("n",)),
    "orb_sesion": dict(fn=orb_sesion, familia="B", params=dict(hora_inicio_utc=0.0, minutos_rango=60, k_atr=1.5),
                       rangos=dict(minutos_rango=(15, 120), k_atr=(0.8, 3.0)), enteros=("minutos_rango",)),
    "rsi2": dict(fn=rsi2, familia="C", params=dict(umbral=10.0, sma_filtro=200, k_atr=2.0),
                 rangos=dict(umbral=(3, 25), sma_filtro=(50, 300), k_atr=(1.0, 4.0)), enteros=("sma_filtro",)),
    "bollinger_rev": dict(fn=bollinger_rev, familia="C", params=dict(n=20, k_sigma=2.5, k_atr=2.0),
                          rangos=dict(n=(10, 60), k_sigma=(2.0, 3.5), k_atr=(1.0, 4.0)), enteros=("n",)),
}


def generar(nombre: str, d: DatosMoneda, tf_min: int, **params) -> Senales:
    """Señales de una estrategia del registro para una moneda y un marco temporal. Descarta señales en minutos sin volumen."""
    reg = REGISTRO[nombre]
    p = dict(reg["params"])
    p.update(params)
    B = barras_tf(d, tf_min)
    if len(B) < 10:
        return Senales.vacia()
    s = reg["fn"](B, **p)
    return s


def comprobar_causalidad(nombre: str, d: DatosMoneda, tf_min: int, cortes: int = 5, semilla: int = 0, **params) -> bool:
    """Test anti-fuga: la señal emitida con los datos recortados en T debe ser idéntica a la emitida con todos los datos
    (para las señales con idx <= T). Si difiere, la estrategia usa información futura."""
    rng = np.random.default_rng(semilla)
    full = generar(nombre, d, tf_min, **params)
    for corte in rng.integers(d.n // 3, d.n - tf_min * 3, size=cortes):
        corte = int(corte // tf_min * tf_min)
        rec = DatosMoneda(d.simbolo, d.t0_ms, d.o[:corte], d.h[:corte], d.l[:corte], d.c[:corte], d.qv[:corte],
                          None if d.tb_qv is None else d.tb_qv[:corte], f_ts_ms=d.f_ts_ms, f_rate=d.f_rate,
                          step=d.step, min_notional=d.min_notional)
        a = generar(nombre, rec, tf_min, **params)
        m = full.idx < corte
        if len(a) != int(m.sum()) or not (np.array_equal(a.idx, full.idx[m]) and np.array_equal(a.lado, full.lado[m])
                                          and np.allclose(a.dist_stop, full.dist_stop[m], equal_nan=True)):
            return False
    return True


def _cargar_extra() -> None:
    from . import estrategias2  # noqa: F401  (registra las familias adicionales en REGISTRO)


_cargar_extra()
