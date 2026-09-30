"""§5 CATÁLOGO – familias adicionales (derivados, flujo, estacionalidad, velas, reversión y rupturas extra).

Todas causales: la señal de la vela i solo usa velas <= i y funding publicado <= cierre de i (test: comprobar_causalidad).
Cada una acepta ``invertir`` (versión inversa) y ``solo`` ('ambos'|'long'|'short').
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import estrategias as E
from .estrategias import Barras, _emitir, atr, ema, sma, rsi, REGISTRO
from .motor import Senales, MS_MIN


def _rolling_max(x: np.ndarray, n: int, previas: bool = True) -> np.ndarray:
    r = pd.Series(x).rolling(n).max()
    return (r.shift(1) if previas else r).to_numpy()


def _rolling_min(x: np.ndarray, n: int, previas: bool = True) -> np.ndarray:
    r = pd.Series(x).rolling(n).min()
    return (r.shift(1) if previas else r).to_numpy()


def _tendencia(B: Barras, n_rapida: int = 50, n_lenta: int = 200):
    """Filtro de tendencia: (alcista, bajista) = EMA rápida sobre/bajo la lenta y precio del lado correcto."""
    a, b = ema(B.c, n_rapida), ema(B.c, n_lenta)
    return (a > b) & (B.c > a), (a < b) & (B.c < a)


# ----------------------------------------------------------------------------------------------
# D. Derivados y flujo
# ----------------------------------------------------------------------------------------------
def funding_extremo(B: Barras, pct: float = 0.95, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False,
                    solo: str = "ambos") -> Senales:
    """Funding en percentil extremo (90 d, por moneda) recién publicado: contrario a la masa.
    Funding muy alto (longs pagan) -> short; muy bajo/negativo (shorts pagan) -> long."""
    if B.fund_pct is None:
        return Senales.vacia()
    hi = B.fund_nuevo & (B.fund_pct >= pct) & (B.funding > 0)
    lo = B.fund_nuevo & (B.fund_pct <= 1 - pct) & (B.funding < 0)
    return _emitir(B, lo, hi, k_atr * atr(B, atr_n), invertir, solo)


def flujo_taker(B: Barras, n: int = 6, umbral: float = 0.56, k_atr: float = 2.0, atr_n: int = 14,
                invertir: bool = False, solo: str = "ambos") -> Senales:
    """Presión compradora/vendedora agresiva sostenida (media móvil del % de compra taker) al cruzar el umbral,
    a favor del flujo si la vela también va en esa dirección (momentum de flujo)."""
    r = pd.Series(B.tb_ratio).rolling(n).mean().to_numpy()
    c_up = (r > umbral) & (B.c > B.o)
    c_dn = (r < 1 - umbral) & (B.c < B.o)
    p_up, p_dn = np.roll(c_up, 1), np.roll(c_dn, 1)
    p_up[0] = p_dn[0] = True
    return _emitir(B, c_up & ~p_up, c_dn & ~p_dn, k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# G. Estacionalidad
# ----------------------------------------------------------------------------------------------
def hora_dia(B: Barras, hora: float = 0.0, k_atr: float = 3.0, atr_n: int = 14, invertir: bool = False,
             solo: str = "ambos") -> Senales:
    """Abre LONG en la primera vela de cada día cuya apertura cae en la hora UTC dada (short si invertir).
    La salida la fija el tiempo máximo (exits t4h/t12h/t24h)."""
    m = np.abs(B.hora - hora) < 1e-9
    z = np.zeros(len(B), bool)
    return _emitir(B, m, z, k_atr * atr(B, atr_n), invertir, solo)


def dia_semana(B: Barras, dow: int = 0, hora: float = 0.0, k_atr: float = 3.0, atr_n: int = 14, invertir: bool = False,
               solo: str = "ambos") -> Senales:
    m = (B.dow == dow) & (np.abs(B.hora - hora) < 1e-9)
    return _emitir(B, m, np.zeros(len(B), bool), k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# H. Patrones de velas (con y sin filtro de tendencia)
# ----------------------------------------------------------------------------------------------
def engulfing(B: Barras, tendencia: bool = False, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False,
              solo: str = "ambos") -> Senales:
    po, pc = np.roll(B.o, 1), np.roll(B.c, 1)
    bull = (pc < po) & (B.c > B.o) & (B.c >= po) & (B.o <= pc)
    bear = (pc > po) & (B.c < B.o) & (B.c <= po) & (B.o >= pc)
    bull[0] = bear[0] = False
    if tendencia:
        up, dn = _tendencia(B)
        bull, bear = bull & up, bear & dn
    return _emitir(B, bull, bear, k_atr * atr(B, atr_n), invertir, solo)


def pin_bar(B: Barras, ratio: float = 2.0, tendencia: bool = False, k_atr: float = 2.0, atr_n: int = 14,
            invertir: bool = False, solo: str = "ambos") -> Senales:
    """Martillo / estrella fugaz: mecha >= ratio x cuerpo y cierre en el tercio opuesto."""
    cuerpo = np.maximum(np.abs(B.c - B.o), 1e-12 * B.c)
    mecha_inf = np.minimum(B.o, B.c) - B.l
    mecha_sup = B.h - np.maximum(B.o, B.c)
    rango = np.maximum(B.h - B.l, 1e-12 * B.c)
    bull = (mecha_inf >= ratio * cuerpo) & (mecha_inf >= 0.55 * rango) & ((B.c - B.l) / rango >= 0.6)
    bear = (mecha_sup >= ratio * cuerpo) & (mecha_sup >= 0.55 * rango) & ((B.h - B.c) / rango >= 0.6)
    if tendencia:
        up, dn = _tendencia(B)
        bull, bear = bull & up, bear & dn
    return _emitir(B, bull, bear, k_atr * atr(B, atr_n), invertir, solo)


def inside_bar(B: Barras, tendencia: bool = False, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False,
               solo: str = "ambos") -> Senales:
    """La vela i-1 está dentro de i-2 (madre); señal en la vela i si cierra fuera del rango de la madre."""
    mh, ml = np.roll(B.h, 2), np.roll(B.l, 2)
    ih, il = np.roll(B.h, 1), np.roll(B.l, 1)
    dentro = (ih < mh) & (il > ml)
    L = dentro & (B.c > mh)
    S = dentro & (B.c < ml)
    L[:2] = S[:2] = False
    if tendencia:
        up, dn = _tendencia(B)
        L, S = L & up, S & dn
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# C. Reversión (extra)
# ----------------------------------------------------------------------------------------------
def vwap_dev(B: Barras, k: float = 2.0, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False,
             solo: str = "ambos") -> Senales:
    """Desviación del VWAP diario (anclado a 00:00 UTC) mayor que k*ATR: fade hacia el VWAP (cruce de umbral)."""
    dia = B.ts_apertura // 86_400_000
    tp = (B.h + B.l + B.c) / 3.0
    pv = pd.Series(tp * B.qv).groupby(dia).cumsum().to_numpy()
    vv = pd.Series(B.qv).groupby(dia).cumsum().to_numpy()
    vwap = np.where(vv > 0, pv / np.where(vv > 0, vv, 1), np.nan)
    a = atr(B, atr_n)
    dev = (B.c - vwap) / a
    bajo = dev < -k
    alto = dev > k
    pb, pa = np.roll(bajo, 1), np.roll(alto, 1)
    pb[0] = pa[0] = True
    return _emitir(B, bajo & ~pb, alto & ~pa, k_atr * a, invertir, solo)


def barrida_liquidez(B: Barras, n: int = 20, k_atr: float = 1.5, atr_n: int = 14, invertir: bool = False,
                     solo: str = "ambos") -> Senales:
    """Stop hunt: la mecha rompe el mínimo (máximo) de las N velas previas pero la vela cierra DENTRO -> long (short)."""
    mn, mx = _rolling_min(B.l, n), _rolling_max(B.h, n)
    L = (B.l < mn) & (B.c > mn)
    S = (B.h > mx) & (B.c < mx)
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


def sobreextension(B: Barras, horas: int = 24, umbral: float = 0.15, k_atr: float = 3.0, atr_n: int = 14,
                   invertir: bool = False, solo: str = "ambos") -> Senales:
    """Fade de movimientos extremos: rendimiento de las últimas ``horas`` mayor que +/-umbral -> contra (al cruzar)."""
    n = max(1, int(round(horas * 60 / B.tf)))
    r = B.c / np.roll(B.c, n) - 1.0
    r[:n] = np.nan
    up = r > umbral
    dn = r < -umbral
    pu, pd_ = np.roll(up, 1), np.roll(dn, 1)
    pu[0] = pd_[0] = True
    # fade: sobrecompra -> corto; sobreventa -> largo
    return _emitir(B, dn & ~pd_, up & ~pu, k_atr * atr(B, atr_n), invertir, solo)


def zscore_rev(B: Barras, n: int = 50, k: float = 2.5, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False,
               solo: str = "ambos") -> Senales:
    m = sma(B.c, n)
    sd = pd.Series(B.c).rolling(n).std(ddof=0).to_numpy()
    z = (B.c - m) / np.where(sd > 0, sd, np.nan)
    bajo, alto = z < -k, z > k
    pb, pa = np.roll(bajo, 1), np.roll(alto, 1)
    pb[0] = pa[0] = True
    return _emitir(B, bajo & ~pb, alto & ~pa, k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# B. Ruptura (extra)
# ----------------------------------------------------------------------------------------------
def squeeze_bk(B: Barras, n: int = 20, pct_ancho: float = 0.2, k_atr: float = 2.0, atr_n: int = 14,
               invertir: bool = False, solo: str = "ambos") -> Senales:
    """Compresión: ancho de Bollinger en el quintil bajo de las 100 velas previas; señal al cerrar fuera de las bandas."""
    m = sma(B.c, n)
    sd = pd.Series(B.c).rolling(n).std(ddof=0).to_numpy()
    ancho = 4 * sd / np.where(m > 0, m, np.nan)
    umbral = pd.Series(ancho).rolling(100).quantile(pct_ancho).shift(1).to_numpy()
    comprimido = np.roll(ancho, 1) <= umbral                     # la vela ANTERIOR estaba comprimida
    comprimido[0] = False
    up, lo = m + 2 * sd, m - 2 * sd
    return _emitir(B, comprimido & (B.c > np.roll(up, 1)), comprimido & (B.c < np.roll(lo, 1)),
                   k_atr * atr(B, atr_n), invertir, solo)


def nr7(B: Barras, k_atr: float = 2.0, atr_n: int = 14, invertir: bool = False, solo: str = "ambos") -> Senales:
    """La vela i-1 tiene el rango más estrecho de las 7 últimas; señal si la vela i cierra fuera de su máximo/mínimo."""
    rango = B.h - B.l
    estrecha = rango <= pd.Series(rango).rolling(7).min().to_numpy()
    est_prev = np.roll(estrecha, 1)
    est_prev[0] = False
    L = est_prev & (B.c > np.roll(B.h, 1))
    S = est_prev & (B.c < np.roll(B.l, 1))
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


def max_min_ayer(B: Barras, k_atr: float = 1.5, atr_n: int = 14, invertir: bool = False, solo: str = "ambos") -> Senales:
    """Ruptura (primer cierre del día fuera) del máximo/mínimo del día UTC anterior."""
    dia = B.ts_apertura // 86_400_000
    g = pd.DataFrame({"d": dia, "h": B.h, "l": B.l})
    diario = g.groupby("d").agg(h=("h", "max"), l=("l", "min"))
    ayer_h = diario["h"].shift(1)
    ayer_l = diario["l"].shift(1)
    ph = ayer_h.reindex(dia).to_numpy()
    pl = ayer_l.reindex(dia).to_numpy()
    L = (B.c > ph) & np.isfinite(ph)
    S = (B.c < pl) & np.isfinite(pl)
    # solo la PRIMERA ruptura de cada día por lado
    L &= pd.Series(L).groupby(dia).cumsum().to_numpy() == 1
    S &= pd.Series(S).groupby(dia).cumsum().to_numpy() == 1
    return _emitir(B, L, S, k_atr * atr(B, atr_n), invertir, solo)


# ----------------------------------------------------------------------------------------------
# A. Tendencia (extra)
# ----------------------------------------------------------------------------------------------
def supertrend(B: Barras, periodo: int = 10, mult: float = 3.0, k_atr: float = 2.0, invertir: bool = False,
               solo: str = "ambos") -> Senales:
    a = atr(B, periodo)
    hl2 = (B.h + B.l) / 2
    ub, lb = hl2 + mult * a, hl2 - mult * a
    n = len(B)
    fub, flb = ub.copy(), lb.copy()
    tend = np.zeros(n, np.int8)
    for i in range(1, n):
        if not (np.isfinite(ub[i]) and np.isfinite(ub[i - 1])):
            continue
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or B.c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or B.c[i - 1] < flb[i - 1]) else flb[i - 1]
        if tend[i - 1] <= 0 and B.c[i] > fub[i - 1]:
            tend[i] = 1
        elif tend[i - 1] >= 0 and B.c[i] < flb[i - 1]:
            tend[i] = -1
        else:
            tend[i] = tend[i - 1]
    prev = np.roll(tend, 1)
    prev[0] = 0
    L = (tend == 1) & (prev != 1) & (prev != 0)
    S = (tend == -1) & (prev != -1) & (prev != 0)
    return _emitir(B, L, S, k_atr * a, invertir, solo)


def adx_retroceso(B: Barras, adx_min: float = 25.0, ema_n: int = 20, k_atr: float = 2.0, atr_n: int = 14,
                  invertir: bool = False, solo: str = "ambos") -> Senales:
    """ADX > umbral (tendencia fuerte) y retroceso a la EMA20 a favor de la tendencia (toca EMA y cierra del lado de la tendencia)."""
    up_m = B.h - np.roll(B.h, 1)
    dn_m = np.roll(B.l, 1) - B.l
    pdm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    ndm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    pdm[0] = ndm[0] = 0.0
    a = atr(B, atr_n)
    alpha = 1.0 / atr_n
    pdi = 100 * pd.Series(pdm).ewm(alpha=alpha, adjust=False, min_periods=atr_n).mean().to_numpy() / a
    ndi = 100 * pd.Series(ndm).ewm(alpha=alpha, adjust=False, min_periods=atr_n).mean().to_numpy() / a
    dx = 100 * np.abs(pdi - ndi) / np.where(pdi + ndi > 0, pdi + ndi, np.nan)
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False, min_periods=atr_n).mean().to_numpy()
    e = ema(B.c, ema_n)
    L = (adx > adx_min) & (pdi > ndi) & (B.l <= e) & (B.c > e)
    S = (adx > adx_min) & (ndi > pdi) & (B.h >= e) & (B.c < e)
    return _emitir(B, L, S, k_atr * a, invertir, solo)


def max_n_dias(B: Barras, dias: int = 180, k_atr: float = 3.0, atr_n: int = 14, invertir: bool = False,
               solo: str = "ambos") -> Senales:
    """Ruptura del máximo/mínimo de los últimos N días (aprox. del 'máximo de 52 semanas' con la historia disponible)."""
    n = max(2, int(dias * 1440 / B.tf))
    mx, mn = _rolling_max(B.h, n), _rolling_min(B.l, n)
    return _emitir(B, B.c > mx, B.c < mn, k_atr * atr(B, atr_n), invertir, solo, cooldown=max(1, n // 20))


# ----------------------------------------------------------------------------------------------
REGISTRO.update({
    "funding_extremo": dict(fn=funding_extremo, familia="D", params=dict(pct=0.95, k_atr=2.0), rangos=dict(pct=(0.85, 0.99), k_atr=(1.0, 4.0)), enteros=()),
    "flujo_taker": dict(fn=flujo_taker, familia="E*", params=dict(n=6, umbral=0.56, k_atr=2.0), rangos=dict(n=(3, 24), umbral=(0.52, 0.65), k_atr=(1.0, 4.0)), enteros=("n",)),
    "hora_dia": dict(fn=hora_dia, familia="G", params=dict(hora=0.0, k_atr=3.0), rangos=dict(hora=(0, 23)), enteros=()),
    "dia_semana": dict(fn=dia_semana, familia="G", params=dict(dow=0, hora=0.0, k_atr=3.0), rangos=dict(dow=(0, 6)), enteros=("dow",)),
    "engulfing": dict(fn=engulfing, familia="H", params=dict(tendencia=False, k_atr=2.0), rangos={}, enteros=()),
    "pin_bar": dict(fn=pin_bar, familia="H", params=dict(ratio=2.0, tendencia=False, k_atr=2.0), rangos=dict(ratio=(1.5, 3.5)), enteros=()),
    "inside_bar": dict(fn=inside_bar, familia="H", params=dict(tendencia=False, k_atr=2.0), rangos={}, enteros=()),
    "vwap_dev": dict(fn=vwap_dev, familia="C", params=dict(k=2.0, k_atr=2.0), rangos=dict(k=(1.0, 3.5), k_atr=(1.0, 4.0)), enteros=()),
    "barrida_liquidez": dict(fn=barrida_liquidez, familia="C", params=dict(n=20, k_atr=1.5), rangos=dict(n=(10, 60), k_atr=(1.0, 3.0)), enteros=("n",)),
    "sobreextension": dict(fn=sobreextension, familia="C", params=dict(horas=24, umbral=0.15, k_atr=3.0), rangos=dict(horas=(6, 72), umbral=(0.08, 0.35)), enteros=("horas",)),
    "zscore_rev": dict(fn=zscore_rev, familia="C", params=dict(n=50, k=2.5, k_atr=2.0), rangos=dict(n=(20, 120), k=(1.8, 3.5)), enteros=("n",)),
    "squeeze_bk": dict(fn=squeeze_bk, familia="B", params=dict(n=20, pct_ancho=0.2, k_atr=2.0), rangos=dict(n=(10, 40), pct_ancho=(0.1, 0.3)), enteros=("n",)),
    "nr7": dict(fn=nr7, familia="B", params=dict(k_atr=2.0), rangos=dict(k_atr=(1.0, 4.0)), enteros=()),
    "max_min_ayer": dict(fn=max_min_ayer, familia="B", params=dict(k_atr=1.5), rangos=dict(k_atr=(0.8, 3.0)), enteros=()),
    "supertrend": dict(fn=supertrend, familia="A", params=dict(periodo=10, mult=3.0, k_atr=2.0), rangos=dict(periodo=(7, 20), mult=(2.0, 4.0)), enteros=("periodo",)),
    "adx_retroceso": dict(fn=adx_retroceso, familia="A", params=dict(adx_min=25.0, ema_n=20, k_atr=2.0), rangos=dict(adx_min=(18, 35), ema_n=(10, 40)), enteros=("ema_n",)),
    "max_n_dias": dict(fn=max_n_dias, familia="A", params=dict(dias=180, k_atr=3.0), rangos=dict(dias=(60, 250)), enteros=("dias",)),
})
