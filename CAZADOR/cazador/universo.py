"""Universo de monedas (§2): perpetuos USDT con volumen 7 d previos > 10 M$ en cada fecha, sin acciones tokenizadas,
materias primas, índices ni stablecoins, e INCLUYENDO las monedas retiradas (sin sesgo de supervivencia).

Sin exchangeInfo (la API fapi da 451 desde este entorno) el tipo de subyacente se infiere así:
  1) cociente de volumen fin de semana / entre semana < 0,33 (los activos de bolsa y materias primas casi no se negocian en fin de
     semana; las criptos dan 0,5-0,8) calculado SOLO con datos del periodo de búsqueda, y
  2) una lista manual de nombres (materias primas, stablecoins, índices, tokens de oro) que el cociente no atrapa.
La selección de monedas usa SOLO volumen hasta ``busqueda_fin``: nunca se mira el holdout para elegir.
"""
from __future__ import annotations

import json
from typing import List

import numpy as np
import pandas as pd

from . import datos as D
from .config import CFG
from .descarga import CACHE, PERIODO, RAIZ
from .periodo import UNIV

MANUAL_NO_CRIPTO = {
    "XAUUSDT", "XAGUSDT", "PAXGUSDT", "XAUTUSDT", "CLUSDT", "BZUSDT", "NATGASUSDT", "COPPERUSDT", "XPDUSDT", "XPTUSDT",
    "BTCDOMUSDT", "DEFIUSDT", "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "USDPUSDT", "FWDIUSDT", "SPYUSDT", "QQQUSDT",
    # acciones / ETF / pre-IPO tokenizados en la zona gris del cociente (0,33-0,50) o con < 21 días de historia
    "HDUSDT", "BRKBUSDT", "EBAYUSDT", "VUSDT", "DKNGUSDT", "GMEUSDT", "BXUSDT", "FLEXUSDT", "EWJUSDT", "OPENAIUSDT",
    "ANTHROPICUSDT", "MINIMAXUSDT", "ZHIPUUSDT", "GEVUSDT", "HK1810USDT", "VRTUSDT", "MUUUSDT", "SHAZUSDT", "SKHYUSDT",
    "SNXXUSDT", "SOXSUSDT", "INTWUSDT", "BOTUSDT", "SMCIUSDT", "TERUSDT", "STXXUSDT", "SNDKUSDT",
}
# Criptos reales con volumen de fin de semana algo bajo (cociente 0,28-0,32) que la regla excluiría por error
RESCATE_CRIPTO = {"TAIKOUSDT", "VICUSDT", "OLUSDT"}
UMBRAL_FIN_SEMANA = 0.33
MIN_DIAS_RATIO = 21
MIN_DIAS_SELECCION = 60       # para el modo reducido: monedas con al menos 60 días de historia en el periodo de búsqueda


def volumen_busqueda() -> pd.DataFrame:
    v = pd.read_parquet(CACHE / "volumen_diario.parquet")
    return v.loc[: PERIODO["busqueda_fin"]]


def excluidos(v: pd.DataFrame) -> dict:
    per = v.loc[PERIODO["busqueda_ini"]:]
    fin = per.index.dayofweek >= 5
    ratio = per[fin].mean() / per[~fin].mean()
    n = per.notna().sum()
    por_ratio = set(ratio[(ratio < UMBRAL_FIN_SEMANA) & (n >= MIN_DIAS_RATIO)].index) - RESCATE_CRIPTO
    return {"ratio": sorted(por_ratio), "manual": sorted(MANUAL_NO_CRIPTO & set(v.columns))}


def universo_y_seleccion() -> dict:
    v = volumen_busqueda()
    ex = excluidos(v)
    malos = set(ex["ratio"]) | set(ex["manual"])
    miembros = D.universo_por_fecha(v)
    miembros = miembros.drop(columns=[c for c in miembros.columns if c in malos])
    per = miembros.loc[PERIODO["busqueda_ini"]:]
    alguna = per.any()
    dias = v.loc[PERIODO["busqueda_ini"]:].notna().sum()
    elegibles = [s for s in alguna.index[alguna] if dias.get(s, 0) >= MIN_DIAS_SELECCION]
    tot = v.loc[PERIODO["busqueda_ini"]:, elegibles].sum().sort_values(ascending=False)
    sel = D.modo_reducido(tot, semilla=CFG.semilla, top=15, azar=35)
    info = {
        "periodo": PERIODO, "modo": "REDUCIDO: top 15 por volumen + 35 al azar (semilla %d)" % CFG.semilla,
        "n_simbolos_con_datos": int(v.shape[1]), "n_excluidos_no_cripto": len(malos),
        "excluidos_por_ratio_fin_semana": ex["ratio"], "excluidos_manual": ex["manual"],
        "n_elegibles_alguna_vez_en_universo": len(elegibles), "seleccion": sel,
    }
    UNIV.write_text(json.dumps(info, indent=1, ensure_ascii=False))
    return info


def miembros_por_fecha() -> pd.DataFrame:
    v = volumen_busqueda()
    ex = excluidos(v)
    malos = set(ex["ratio"]) | set(ex["manual"])
    m = D.universo_por_fecha(v)
    return m.drop(columns=[c for c in m.columns if c in malos])


if __name__ == "__main__":
    i = universo_y_seleccion()
    print(json.dumps({k: v for k, v in i.items() if k not in ("periodo", "excluidos_por_ratio_fin_semana")}, indent=1, ensure_ascii=False))
    print("excluidos por ratio:", len(i["excluidos_por_ratio_fin_semana"]), i["excluidos_por_ratio_fin_semana"][:80])
