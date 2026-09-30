"""§3 RÉGIMEN DE MERCADO – etiquetas causales (solo información pasada).

Macro (diario, sobre BTC): 🟢 ALCISTA · 🔴 BAJISTA · ⚪ LATERAL TRANQUILO · 🟠 LATERAL VOLÁTIL · 🚀 EUFORIA · 💥 CAPITULACIÓN.
Con histéresis: una etiqueta nueva solo se adopta si se mantiene >= 3 días seguidos.

Las reglas son explícitas y fijadas ANTES de mirar resultados. Los percentiles son expansivos (solo pasado).
Las etiquetas del día D se calculan con el cierre del día D y se USAN a partir del día D+1 (``aplicar_a_1m``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ALCISTA, BAJISTA, LAT_TRANQ, LAT_VOL, EUFORIA, CAPIT = "ALCISTA", "BAJISTA", "LATERAL_TRANQUILO", "LATERAL_VOLATIL", "EUFORIA", "CAPITULACION"
ORDEN = [ALCISTA, BAJISTA, LAT_TRANQ, LAT_VOL, EUFORIA, CAPIT]
ICONOS = {ALCISTA: "🟢", BAJISTA: "🔴", LAT_TRANQ: "⚪", LAT_VOL: "🟠", EUFORIA: "🚀", CAPIT: "💥"}


def _pct_expansivo(s: pd.Series, min_n: int = 60) -> pd.Series:
    """Percentil (0-1) del valor actual dentro de TODO el pasado hasta hoy (incluido). Sin mirar al futuro."""
    v = s.to_numpy(float)
    out = np.full(len(v), np.nan)
    hist: list = []
    import bisect
    for i, x in enumerate(v):
        if np.isfinite(x):
            bisect.insort(hist, x)
            if len(hist) >= min_n:
                out[i] = bisect.bisect_left(hist, x) / len(hist)
    return pd.Series(out, index=s.index)


def etiquetas_macro(btc_1d: pd.DataFrame, funding_mercado_7d: pd.Series | None = None,
                    amplitud: pd.Series | None = None, persistencia: int = 3) -> pd.DataFrame:
    """btc_1d: índice = fecha (día UTC), columnas c (cierre) y opcional h.

    Devuelve DataFrame con las variables usadas y la columna ``regimen`` (con histéresis).
    """
    d = pd.DataFrame(index=btc_1d.index)
    c = btc_1d["c"].astype(float)
    d["c"] = c
    d["sma50"] = c.rolling(50).mean()
    d["sma200"] = c.rolling(200).mean()
    d["pend200"] = d["sma200"] / d["sma200"].shift(20) - 1.0
    d["dd"] = c / c.cummax() - 1.0
    r = np.log(c).diff()
    d["vol30"] = r.rolling(30).std() * np.sqrt(365)
    d["vol_pct"] = _pct_expansivo(d["vol30"])
    d["ret7"] = c / c.shift(7) - 1.0
    d["ret30"] = c / c.shift(30) - 1.0
    d["ret30_pct"] = _pct_expansivo(d["ret30"])
    d["funding7"] = funding_mercado_7d if funding_mercado_7d is not None else np.nan
    d["fund_pct"] = _pct_expansivo(d["funding7"]) if funding_mercado_7d is not None else np.nan
    d["amplitud"] = amplitud if amplitud is not None else np.nan

    sobre200 = c > d["sma200"]
    bajo200 = c < d["sma200"]
    alcista = sobre200 & (d["sma50"] > d["sma200"]) & (d["pend200"] > 0)
    bajista = bajo200 & (d["sma50"] < d["sma200"]) & (d["pend200"] < 0)
    # Euforia: alcista y rendimiento 30 d en el decil superior histórico; si hay funding, también en su quintil alto
    calor = d["ret30_pct"] >= 0.90
    if funding_mercado_7d is not None:
        calor = calor & (d["fund_pct"] >= 0.80)
    euforia = alcista & calor
    # Capitulación: caída >= 15 % en 7 d con volatilidad en el quintil alto y precio bajo la SMA200
    capit = bajo200 & (d["ret7"] <= -0.15) & (d["vol_pct"] >= 0.80)

    crudo = pd.Series(LAT_TRANQ, index=d.index, dtype=object)
    crudo[d["vol_pct"] >= 0.50] = LAT_VOL
    crudo[alcista] = ALCISTA
    crudo[bajista] = BAJISTA
    crudo[euforia] = EUFORIA
    crudo[capit] = CAPIT
    crudo[d["sma200"].isna() | d["vol_pct"].isna()] = None   # sin historia suficiente: sin etiqueta
    d["regimen_crudo"] = crudo
    d["regimen"] = _histeresis(crudo, persistencia)
    return d


def _histeresis(s: pd.Series, k: int) -> pd.Series:
    """Cambia de etiqueta solo si la nueva se mantiene >= k días. La confirmación se conoce al día k-ésimo
    (causal: nunca se reescribe el pasado), es decir, el cambio se ACTIVA k-1 días después de empezar."""
    out = []
    actual = None
    cand, n = None, 0
    for x in s.to_numpy(object):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            out.append(None)
            continue
        if actual is None:
            actual = x
            cand, n = None, 0
        elif x == actual:
            cand, n = None, 0
        else:
            if x == cand:
                n += 1
            else:
                cand, n = x, 1
            if n >= k:
                actual, cand, n = x, None, 0
        out.append(actual)
    return pd.Series(out, index=s.index, dtype=object)


def aplicar_a_1m(reg_diario: pd.Series, t0_ms: int, n: int) -> np.ndarray:
    """Etiqueta (índice entero en ORDEN, -1 = sin etiqueta) de cada vela de 1 m usando el régimen del día ANTERIOR."""
    cod = reg_diario.map({k: i for i, k in enumerate(ORDEN)}).fillna(-1).astype(int)
    ayer = cod.shift(1).fillna(-1).astype(int)       # lo conocido al abrir el día
    dias = (t0_ms + np.arange(n, dtype=np.int64) * 60_000) // 86_400_000
    dia_num = (pd.DatetimeIndex(ayer.index) - pd.Timestamp("1970-01-01")) // pd.Timedelta(days=1)   # independiente de la unidad (ns/us)
    mapa = pd.Series(ayer.to_numpy(), index=np.asarray(dia_num, dtype=np.int64))
    return mapa.reindex(dias).fillna(-1).astype(int).to_numpy()


def sesion_utc(hora: np.ndarray) -> np.ndarray:
    """0 = Asia (00-08), 1 = Europa (08-14), 2 = EE. UU. (14-24), hora UTC."""
    return np.where(hora < 8, 0, np.where(hora < 14, 1, 2))


# ----------------------------------------------------------------------------------------------
# HMM causal (filtrado hacia delante, refit en ventana móvil)
# ----------------------------------------------------------------------------------------------
def hmm_causal(btc_1d: pd.DataFrame, estados: int = 3, ventana: int = 730, refit_cada: int = 30, semilla: int = 0) -> pd.Series:
    """Estado más probable con probabilidades FILTRADAS (forward), nunca suavizadas con el futuro.

    Cada ``refit_cada`` días se reajusta con la ventana previa [t-ventana, t). Las etiquetas de estados son
    arbitrarias entre refits, así que se ordenan por media de rendimiento (0 = peor, k-1 = mejor).
    """
    from hmmlearn.hmm import GaussianHMM
    c = btc_1d["c"].astype(float)
    r = np.log(c).diff()
    vol = r.rolling(7).std()
    X = pd.concat([r, vol], axis=1).dropna()
    out = pd.Series(np.nan, index=X.index)
    modelo = None
    orden = None
    for i in range(ventana // 2, len(X)):
        if modelo is None or (i % refit_cada == 0):
            tr = X.iloc[max(0, i - ventana):i].to_numpy()
            try:
                m = GaussianHMM(n_components=estados, covariance_type="diag", n_iter=100, random_state=semilla)
                m.fit(tr)
                modelo = m
                orden = np.argsort(m.means_[:, 0])
            except Exception:
                continue
        if modelo is None:
            continue
        # filtrado forward sobre la ventana hasta el día i INCLUIDO
        ventana_x = X.iloc[max(0, i - 120): i + 1].to_numpy()
        logB = modelo._compute_log_likelihood(ventana_x)
        log_alpha = np.log(modelo.startprob_ + 1e-300) + logB[0]
        for t in range(1, len(ventana_x)):
            log_alpha = logB[t] + np.logaddexp.reduce(log_alpha[:, None] + np.log(modelo.transmat_ + 1e-300), axis=0)
        est = int(np.argmax(log_alpha))
        out.iloc[i] = int(np.where(orden == est)[0][0])
    return out
