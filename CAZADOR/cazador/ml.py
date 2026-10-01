"""Ronda 3 – aprendizaje automático (I): LightGBM con etiquetado de triple barrera, ventana móvil, purga y embargo.

Protocolo (todo causal):
  * Decisión en cada vela de 4 h CERRADA, para cada moneda que esté en el universo ese día.
  * Variables: rendimientos y volatilidad a varios plazos, volumen relativo, ratio taker, funding y su percentil, interés abierto y
    long/short (si hay metrics), contexto de BTC, ranking transversal y calendario. Solo información <= cierre de la vela.
  * Etiqueta: triple barrera en unidades de ATR (objetivo = stop = K_BARRERA x ATR(14), horizonte H velas). y=1 si el objetivo se toca
    antes que el stop (si ambos en la misma vela cuenta el stop).
  * Entrenamiento walk-forward: 6 meses previos -> predice el mes siguiente. PURGA: se descartan las muestras cuya ventana de
    etiqueta llega al mes de prueba. Solo se usan predicciones fuera de muestra.
  * Los umbrales de probabilidad (0,55 / 0,60 / 0,65) se fijan a priori y se registran TODOS como pruebas.
Valor añadido exigido: solo vale si supera a las reglas simples fuera de muestra (se compara en el informe).
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from numba import njit

from . import cargar
from . import estrategias as E
from .barrido import DIA0, ND, MES_DIA, dia_de
from .descarga import CACHE, PERIODO
from .motor import Senales, MS_MIN

TF = 240
K_BARRERA = 1.5
H_VELAS = 6                      # 24 h
FEATS = ["r1", "r3", "r6", "r18", "r42", "vol6", "vol18", "atr_pct", "rango", "vol_rel", "vol_rel7", "tb1", "tb6", "fund", "fund_pct",
         "rsi14", "dist_sma50", "dist_sma200", "hi_dist", "lo_dist", "btc_r6", "btc_vol18", "rank_r6", "rank_vol", "hora", "dow",
         "oi_d1", "oi_d6", "oi_rel", "ls_top", "ls_glob", "taker_ls", "corr_btc"]


@njit(cache=True)
def _triple_barrera(h, l, c, atr, k, H):
    n = len(c)
    yl = np.full(n, -1, np.int8)     # -1 = no calculable, 0 = no gana, 1 = gana (objetivo antes que stop)
    ys = np.full(n, -1, np.int8)
    for i in range(n - H):
        if not (atr[i] > 0):
            continue
        d = k * atr[i]
        up, dn = c[i] + d, c[i] - d
        r = 0
        for j in range(i + 1, i + H + 1):
            tu, td = h[j] >= up, l[j] <= dn
            if td:                   # stop antes (o a la vez) que objetivo
                r = 0
                break
            if tu:
                r = 1
                break
        yl[i] = r
        r = 0
        for j in range(i + 1, i + H + 1):
            tu, td = h[j] >= up, l[j] <= dn
            if tu:
                r = 0
                break
            if td:
                r = 1
                break
        ys[i] = r
    return yl, ys


def _metrics(sim: str) -> Optional[pd.DataFrame]:
    p = CACHE / "metrics" / f"{sim}.parquet"
    if not p.exists():
        return None
    g = pd.read_parquet(p)
    return g if len(g) and "oi" in g.columns else None


def dataset_moneda(sim: str, miembros: pd.DataFrame, btc: Optional[pd.DataFrame] = None) -> Optional[pd.DataFrame]:
    d = cargar.cargar_moneda(sim, "busqueda")
    if d is None:
        return None
    B = E.barras_tf(d, TF)
    n = len(B)
    if n < 300:
        return None
    c = pd.Series(B.c)
    ret = lambda k: (c / c.shift(k) - 1.0).to_numpy()
    lr = np.log(c).diff()
    a = E.atr(B, 14)
    f = pd.DataFrame({"sim": sim, "idx": B.idx_cierre, "t": B.ts_apertura + TF * MS_MIN})
    f["r1"], f["r3"], f["r6"], f["r18"], f["r42"] = ret(1), ret(3), ret(6), ret(18), ret(42)
    f["vol6"] = lr.rolling(6).std().to_numpy()
    f["vol18"] = lr.rolling(18).std().to_numpy()
    f["atr_pct"] = a / B.c
    f["rango"] = (B.h - B.l) / B.c
    qv = pd.Series(B.qv)
    f["vol_rel"] = (qv / qv.rolling(18).mean()).to_numpy()
    f["vol_rel7"] = (qv / qv.rolling(42).mean()).to_numpy()
    tb = pd.Series(B.tb_ratio)
    f["tb1"] = tb.to_numpy()
    f["tb6"] = tb.rolling(6).mean().to_numpy()
    f["fund"] = B.funding if B.funding is not None else np.nan
    f["fund_pct"] = B.fund_pct if B.fund_pct is not None else np.nan
    f["rsi14"] = E.rsi(B.c, 14)
    f["dist_sma50"] = B.c / E.sma(B.c, 50) - 1.0
    f["dist_sma200"] = B.c / E.sma(B.c, 200) - 1.0
    f["hi_dist"] = B.c / pd.Series(B.h).rolling(42).max().to_numpy() - 1.0
    f["lo_dist"] = B.c / pd.Series(B.l).rolling(42).min().to_numpy() - 1.0
    f["hora"] = ((B.ts_apertura // MS_MIN) % 1440) / 60.0
    f["dow"] = B.dow
    yl, ys = _triple_barrera(B.h, B.l, B.c, a, K_BARRERA, H_VELAS)
    f["y_long"], f["y_short"] = yl, ys
    f["atr"] = a
    # metrics (OI, L/S) si están descargadas: último valor conocido al cierre de la vela
    m = _metrics(sim)
    for col in ("oi_d1", "oi_d6", "oi_rel", "ls_top", "ls_glob", "taker_ls"):
        f[col] = np.nan
    if m is not None:
        m = m.sort_values("t")
        k = np.searchsorted(m["t"].to_numpy(), f["t"].to_numpy() - 300_000, side="right") - 1   # registro >= 5 min anterior
        ok = k >= 0
        kk = np.where(ok, k, 0)
        oi = m["oi_valor"].to_numpy(float)
        oi = np.where(oi > 0, oi, np.nan)                      # los ceros de la fuente son huecos, no OI real
        oi_ser = pd.Series(np.where(ok, oi[kk], np.nan))
        f["oi_d1"] = (oi_ser / oi_ser.shift(1) - 1.0).to_numpy()
        f["oi_d6"] = (oi_ser / oi_ser.shift(6) - 1.0).to_numpy()
        f["oi_rel"] = (oi_ser / (qv.rolling(6).sum().to_numpy() + 1.0)).to_numpy()
        f["ls_top"] = np.where(ok, m["top_ls_posiciones"].to_numpy(float)[kk], np.nan)
        f["ls_glob"] = np.where(ok, m["ls_global"].to_numpy(float)[kk], np.nan)
        f["taker_ls"] = np.where(ok, m["taker_ls_vol"].to_numpy(float)[kk], np.nan)
    # BTC: contexto
    if btc is not None:
        j = btc.reindex(f["t"].to_numpy())
        f["btc_r6"] = j["r6"].to_numpy()
        f["btc_vol18"] = j["vol18"].to_numpy()
        f["corr_btc"] = lr.rolling(42).corr(pd.Series(np.log(btc.reindex(f["t"].to_numpy())["c"].to_numpy()), index=lr.index).diff()).to_numpy()
    else:
        f["btc_r6"] = f["btc_vol18"] = f["corr_btc"] = np.nan
    # universo: miembro ese día y dentro del periodo de evaluación
    dia = dia_de(d.t0_ms + f["idx"].to_numpy() * MS_MIN)
    mem = (miembros[sim].reindex(pd.date_range(PERIODO["busqueda_ini"], periods=ND)).fillna(False).to_numpy(bool)
           if sim in miembros.columns else np.zeros(ND, bool))
    f["dia"] = dia
    f["miembro"] = (dia >= 0) & (dia < ND) & mem[np.clip(dia, 0, ND - 1)]
    f["en_eval"] = f["idx"].to_numpy() >= d.idx_eval
    return f


def btc_contexto() -> pd.DataFrame:
    d = cargar.cargar_moneda("BTCUSDT", "busqueda")
    B = E.barras_tf(d, TF)
    c = pd.Series(B.c)
    lr = np.log(c).diff()
    g = pd.DataFrame({"c": B.c, "r6": (c / c.shift(6) - 1.0).to_numpy(), "vol18": lr.rolling(18).std().to_numpy()},
                     index=B.ts_apertura + TF * MS_MIN)
    return g


def construir(simbolos: List[str], miembros: pd.DataFrame, log=print) -> pd.DataFrame:
    btc = btc_contexto()
    partes = []
    for s in simbolos:
        f = dataset_moneda(s, miembros, btc)
        if f is not None:
            partes.append(f)
    df = pd.concat(partes, ignore_index=True)
    # variables transversales (rango entre monedas en el mismo instante, solo entre miembros)
    m = df[df["miembro"]]
    df["rank_r6"] = m.groupby("t")["r6"].rank(pct=True).reindex(df.index)
    df["rank_vol"] = m.groupby("t")["vol_rel7"].rank(pct=True).reindex(df.index)
    log(f"dataset: {len(df)} filas, {int(df['miembro'].sum())} como miembro del universo, {df['sim'].nunique()} monedas")
    return df


# ----------------------------------------------------------------------------------------------
def walk_forward_ml(df: pd.DataFrame, train_meses: int = 6, semilla: int = 7, params: Optional[dict] = None, log=print,
                    feats: Optional[List[str]] = None) -> pd.DataFrame:
    """Predicciones FUERA DE MUESTRA p_long / p_short para cada fila en meses 6..23 (modelo reentrenado cada mes)."""
    import lightgbm as lgb
    feats = feats or FEATS
    P = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_child_samples=300, feature_fraction=0.7,
             bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, n_estimators=300, verbose=-1, n_jobs=4, random_state=semilla)
    if params:
        P.update(params)
    mes = np.where((df["dia"] >= 0) & (df["dia"] < ND), MES_DIA[np.clip(df["dia"].to_numpy(), 0, ND - 1)], -1)
    df = df.assign(mes=mes)
    base = df[df["miembro"] & df["en_eval"] & (df["y_long"] >= 0)]
    out = []
    imp = []
    for m in range(train_meses, int(MES_DIA.max()) + 1):
        ini_test_ms = None
        te = base[base["mes"] == m]
        if te.empty:
            continue
        t_ini_test = te["t"].min()
        tr = base[(base["mes"] >= m - train_meses) & (base["mes"] < m) & (base["t"] + H_VELAS * TF * MS_MIN < t_ini_test)]   # PURGA
        if len(tr) < 5000:
            continue
        pred = te[["sim", "idx", "t", "atr", "mes", "dia"]].copy()
        for lado, col in (("long", "y_long"), ("short", "y_short")):
            mdl = lgb.LGBMClassifier(**P)
            mdl.fit(tr[feats], tr[col])
            pred[f"p_{lado}"] = mdl.predict_proba(te[feats])[:, 1]
            imp.append(pd.Series(mdl.booster_.feature_importance("gain"), index=feats, name=(m, lado)))
        pred["y_long"], pred["y_short"] = te["y_long"].to_numpy(), te["y_short"].to_numpy()
        out.append(pred)
        log(f"  mes {m}: train {len(tr)} test {len(te)}")
    res = pd.concat(out, ignore_index=True)
    res.attrs["importancias"] = pd.concat(imp, axis=1).T if imp else None
    return res


def senales_ml(pred: pd.DataFrame, theta: float, k_barrera: float = K_BARRERA, solo: str = "ambos", margen: float = 0.0) -> Dict[str, Senales]:
    """Señal en cada vela donde max(p_long, p_short) >= theta y supera a la otra en ``margen``; stop = k x ATR."""
    out = {}
    for s, g in pred.groupby("sim"):
        pl, ps = g["p_long"].to_numpy(), g["p_short"].to_numpy()
        larg = (pl >= theta) & (pl >= ps + margen)
        cort = (ps >= theta) & (ps > pl + margen)
        if solo == "long":
            cort[:] = False
        if solo == "short":
            larg[:] = False
        m = larg | cort
        if not m.any():
            continue
        out[s] = Senales(g["idx"].to_numpy()[m].astype(np.int64), np.where(larg[m], 1, -1).astype(np.int8),
                         (k_barrera * g["atr"].to_numpy()[m]).astype(float))
    return out


def evaluar_prediccion(pred: pd.DataFrame) -> dict:
    """AUC y expectativa teórica (en R, sin costes) por decil de probabilidad, fuera de muestra."""
    from sklearn.metrics import roc_auc_score
    r = {}
    for lado in ("long", "short"):
        y, p = pred[f"y_{lado}"].to_numpy(), pred[f"p_{lado}"].to_numpy()
        ok = y >= 0
        r[f"auc_{lado}"] = float(roc_auc_score(y[ok], p[ok]))
        r[f"base_{lado}"] = float(y[ok].mean())
        q = pd.qcut(p[ok], 10, labels=False, duplicates="drop")
        r[f"tasa_por_decil_{lado}"] = [float(y[ok][q == i].mean()) for i in range(int(q.max()) + 1)]
    return r


CONTEXTO = ["btc_r6", "btc_vol18", "corr_btc", "hora", "dow"]
PROPIAS = [f for f in FEATS if f not in CONTEXTO]
CONJUNTOS = {"todas": FEATS, "solo_propias_moneda": PROPIAS, "solo_contexto_mercado": CONTEXTO,
             "propias_sin_oi_ls": [f for f in PROPIAS if f not in ("oi_d1", "oi_d6", "oi_rel", "ls_top", "ls_glob", "taker_ls")]}
