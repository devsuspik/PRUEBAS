"""Factores transversales en datos DIARIOS sobre todo el universo líquido de cada época (cientos de monedas, retiradas incluidas).

Para cada factor y cada periodo: en cada rebalanceo (cada R días) se ordenan las monedas del universo (volumen 7 d previos > 10 M$,
no-TradFi) por el factor calculado con datos hasta el cierre del día t; largo del grupo alto, corto del grupo bajo; se mantiene R días.
Retorno por rebalanceo = (media largos - media cortos)/2 - coste de ida y vuelta por pata (0,07 % por lado x2). Sin financiación (se declara).
Entrada al cierre de t (cripto cotiza 24/7: cierre de t = apertura de t+1), salida al cierre de t+R.
Uso: CAZADOR_PERIODO=<p> python -m cazador.factores_1d
"""
import json
import numpy as np
import pandas as pd

from . import universo
from .config import CFG
from .periodo import CACHE, NOMBRE, PERIODO, RES

COSTE_PATA = 2 * (CFG.fee_taker + CFG.slip_min)       # ida y vuelta de una posición: 0,14 %


def panel() -> dict:
    v = universo.volumen_busqueda()
    mem = universo.miembros_por_fecha()
    sims = [s for s in mem.columns if (CACHE / "klines" / "1d" / f"{s}.parquet").exists()]
    C, H, L, Q = {}, {}, {}, {}
    for s in sims:
        g = pd.read_parquet(CACHE / "klines" / "1d" / f"{s}.parquet", columns=["t", "o", "h", "l", "c", "qv"])
        g.index = pd.to_datetime(g["t"], unit="ms").dt.floor("D")
        g = g[~g.index.duplicated()]
        C[s], H[s], L[s], Q[s] = g["c"].astype(float), g["h"].astype(float), g["l"].astype(float), g["qv"].astype(float)
    C, H, L, Q = (pd.DataFrame(x).sort_index() for x in (C, H, L, Q))
    fin = pd.Timestamp(PERIODO["busqueda_fin"])
    C, H, L, Q = (x.loc[:fin] for x in (C, H, L, Q))
    return dict(C=C, H=H, L=L, Q=Q, M=mem.reindex(C.index).fillna(False))


def factores(P: dict) -> dict:
    C, Q = P["C"], P["Q"]
    r = C.pct_change()
    f = {}
    for k in (1, 3, 7, 14, 30, 60):
        f[f"mom{k}"] = C / C.shift(k) - 1
    for k in (14, 30):
        f[f"vol{k}"] = r.rolling(k).std()
    f["volumen_rel"] = Q.rolling(7).mean() / Q.rolling(60).mean()
    f["maxret30"] = r.rolling(30).max()
    f["dist_max90"] = C / C.rolling(90).max() - 1
    return f


def evaluar(P: dict, f: dict, R: int, k: int = 10, min_reb: int = 10) -> pd.DataFrame:
    C, M = P["C"], P["M"]
    fecha0 = pd.Timestamp(PERIODO["holdout_ini"] if NOMBRE == "ho" else PERIODO["busqueda_ini"])   # en 'ho' solo se puntúa el holdout
    fut = C.shift(-R) / C - 1                                   # retorno de mantener R días desde el cierre de t
    filas = []
    for nom, F in f.items():
        reb = [d for i, d in enumerate(C.index) if d >= fecha0 and (C.index.get_loc(d) % R == 0) and d + pd.Timedelta(days=R) <= C.index[-1]]
        spreads, nl = [], []
        for d in reb:
            ok = M.loc[d] & F.loc[d].notna() & fut.loc[d].notna()
            if ok.sum() < 2 * k + 6:
                continue
            x = F.loc[d][ok]; y = fut.loc[d][ok]
            orden = x.sort_values()
            bajo, alto = orden.index[:k], orden.index[-k:]
            spreads.append((y[alto].mean() - y[bajo].mean()) / 2.0)     # largo alto - corto bajo, por 1 $ de nocional por pata promedio
            nl.append(len(orden))
        s = np.array(spreads)
        if len(s) < min_reb:
            continue
        bruto = s.mean()
        for direccion, signo in (("alto", 1), ("bajo", -1)):
            neto = signo * s - COSTE_PATA
            t = neto.mean() / (neto.std(ddof=1) / np.sqrt(len(neto)))
            filas.append(dict(periodo=NOMBRE, factor=nom, R=R, k=k, largo=direccion, n_reb=len(s), universo_medio=int(np.mean(nl)),
                              bruto_pct=signo * bruto * 100, neto_pct=neto.mean() * 100, t=t, pct_pos=(neto > 0).mean(),
                              sharpe_anual=neto.mean() / neto.std(ddof=1) * np.sqrt(365 / R)))
    return pd.DataFrame(filas)


def main() -> None:
    if NOMBRE == "ho":
        from . import cargar
        if not cargar._holdout_abierto():
            raise PermissionError("El holdout está bloqueado: usa cazador.holdout")
    P = panel()
    f = factores(P)
    if NOMBRE == "ho":
        # SOLO la candidata registrada en CANDIDATAS_HOLDOUT.json (no se puntúan otros factores sobre el holdout)
        from .periodo import RAIZ
        c = json.loads((RAIZ / "CANDIDATAS_HOLDOUT.json").read_text())["factor_transversal"]
        out = evaluar(P, {c["factor"]: f[c["factor"]]}, c["R_dias"], c["k_por_lado"], min_reb=5)
        out = out[out["largo"] == c["largo"]]
    else:
        out = pd.concat([evaluar(P, f, R, k) for R in (1, 3, 7) for k in (5, 10)], ignore_index=True)
    RES.mkdir(exist_ok=True)
    out.to_csv(RES / "factores_1d.csv", index=False)
    print(f"{NOMBRE}: panel {P['C'].shape[1]} monedas x {P['C'].shape[0]} días | universo medio por día {int(P['M'].sum(axis=1).mean())}")


if __name__ == "__main__":
    main()
