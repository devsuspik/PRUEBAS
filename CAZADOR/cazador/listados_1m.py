"""Corto de listados nuevos simulado a 1 MINUTO con el motor real (costes, deslizamiento, funding, liquidación, cartera de 5 posiciones).

Regla (pre-registrada): corto al cierre del día UTC siguiente al del listado (00:00 UTC de d0+2), stop +8 %, objetivo -40 % (5R), salida
por tiempo a los 7 días. Sin filtro de volumen de universo (un listado nuevo no tiene 7 días de volumen previo).
Datos: SOLO los ~20 días posteriores al listado de cada moneda (ficheros diarios de 1 m + funding mensual) en datos_cache_listados/.
Uso: CAZADOR_PERIODO=<p> python -m cazador.listados_1m [--descargar]"""
import dataclasses
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

from . import datos as D
from . import listados as LI
from . import metricas as M
from .config import CFG
from .motor import DatosMoneda, Salida, Senales, filtro_cartera, simular_moneda, MS_MIN
from .periodo import NOMBRE, RAIZ, RES

DIA = 86_400_000
CACHE_L = RAIZ / "datos_cache_listados"
DIAS_ANTES, DIAS_DESPUES = 1, 18


def _bajar_dia(sim, fecha):
    r = D.http_get(f"{D.BASE}/daily/klines/{sim}/1m/{sim}-1m-{fecha}.zip")
    return None if r is None else D.leer_klines_zip(r.content)


def descargar(eventos, workers=16):
    CACHE_L.mkdir(exist_ok=True)
    tareas = []
    for s, g in eventos:
        if (CACHE_L / f"{s}.parquet").exists():
            continue
        d0 = g.index[0]
        for k in range(-DIAS_ANTES, DIAS_DESPUES + 1):
            tareas.append((s, (d0 + pd.Timedelta(days=k)).strftime("%Y-%m-%d")))
    partes = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(_bajar_dia, s, f): (s, f) for s, f in tareas}
        for i, f in enumerate(as_completed(fut)):
            s, _ = fut[f]
            try:
                df = f.result()
            except Exception:
                df = None
            if df is not None and len(df):
                partes.setdefault(s, []).append(df)
            if (i + 1) % 2000 == 0:
                print(f"  {i + 1}/{len(tareas)} ({(i + 1) / (time.time() - t0):.0f}/s)", flush=True)
    # respaldo: monedas sin ningún fichero diario -> ficheros MENSUALES recortados a la ventana del evento
    for s, g in eventos:
        if s in partes or (CACHE_L / f"{s}.parquet").exists():
            continue
        d0 = g.index[0]
        lo, hi = int((d0 - pd.Timedelta(days=DIAS_ANTES)).timestamp() * 1000), int((d0 + pd.Timedelta(days=DIAS_DESPUES + 1)).timestamp() * 1000)
        ms = sorted({(d0 + pd.Timedelta(days=k)).strftime("%Y-%m") for k in range(-DIAS_ANTES, DIAS_DESPUES + 1)})
        fs = []
        for m in ms:
            r = D.http_get(f"{D.BASE}/monthly/klines/{s}/1m/{s}-1m-{m}.zip")
            if r is not None:
                df = D.leer_klines_zip(r.content)
                fs.append(df[(df.t >= lo) & (df.t < hi)])
        if fs:
            partes[s] = fs
    for s, p in partes.items():
        pd.concat(p, ignore_index=True).sort_values("t").drop_duplicates("t").astype(
            {"qv": "float64", "v": "float64", "tb_v": "float64", "tb_qv": "float64", "n": "int64"}).to_parquet(CACHE_L / f"{s}.parquet")
    # funding (mensual) de cada moneda
    for s, g in eventos:
        if (CACHE_L / f"{s}_f.parquet").exists():
            continue
        d0 = g.index[0]
        ms = sorted({(d0 + pd.Timedelta(days=k)).strftime("%Y-%m") for k in range(-1, DIAS_DESPUES + 1)})
        fs = []
        for m in ms:
            r = D.http_get(f"{D.BASE}/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip")
            if r is not None:
                fs.append(D.leer_funding_zip(r.content))
        pd.concat(fs, ignore_index=True).to_parquet(CACHE_L / f"{s}_f.parquet") if fs else None


def cargar_evento(s, g):
    p = CACHE_L / f"{s}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if len(df) < 2000:
        return None
    grid, _ = D.a_rejilla_1m(df)
    f = pd.read_parquet(CACHE_L / f"{s}_f.parquet") if (CACHE_L / f"{s}_f.parquet").exists() else None
    return D.a_datos_moneda(s, grid, f)


def simular(eventos, cfg=CFG, slip_mult=1.0, latencia=0, stop=0.08, obj_R=5.0, dias=7, entrada_dias=2, lado=-1):
    partes = []
    for s, g in eventos:
        d = cargar_evento(s, g)
        if d is None:
            continue
        t_ent = int((g.index[0] + pd.Timedelta(days=entrada_dias)).timestamp() * 1000)        # 00:00 UTC de d0+2 = cierre del día d0+1
        i = int((t_ent - d.t0_ms) // MS_MIN) - 1                                              # señal en la vela anterior; entra en la siguiente apertura
        if i < 0 or i + 1 + dias * 1440 >= d.n:
            continue
        px = d.c[i]
        sen = Senales(np.array([i], np.int64), np.array([lado], np.int8), np.array([stop * px]))
        t = simular_moneda(d, sen, cfg, Salida(objetivo_R=obj_R, max_velas_1m=dias * 1440), latencia, slip_mult=slip_mult)
        if len(t):
            partes.append(t)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def resumen(t, etiqueta):
    if t.empty:
        print(f"{NOMBRE} | {etiqueta}: sin operaciones"); return {}
    pnl = t["pnl"].to_numpy()
    se = pnl.std(ddof=1) / np.sqrt(len(pnl)) if len(pnl) > 1 else np.nan
    liq = int((t["motivo"] == 6).sum())
    print(f"{NOMBRE} | {etiqueta}: n={len(t)} aciertos={np.mean(pnl > 0):.2f} exp=${pnl.mean():+.2f} (t={pnl.mean() / se:+.2f}) PF={M.profit_factor(pnl) or float('nan'):.2f} "
          f"total=${pnl.sum():+.0f} liquidaciones={liq} peor=${pnl.min():.1f} mejor=${pnl.max():.1f}", flush=True)
    return dict(n=len(t), exp=pnl.mean(), pf=M.profit_factor(pnl), total=pnl.sum(), liq=liq)


def main():
    ev = LI.eventos()
    if "--descargar" in sys.argv:
        descargar(ev)
    base = simular(ev)
    resumen(base, "base (costes x1)")
    for m in (1.5, 2.0, 3.0):
        cfg = dataclasses.replace(CFG, comision_taker_pct=CFG.comision_taker_pct * m, comision_maker_pct=CFG.comision_maker_pct * m,
                                  deslizamiento_min_pct=CFG.deslizamiento_min_pct * m)
        resumen(simular(ev, cfg=cfg, slip_mult=m), f"costes x{m}")
    for lat in (5, 30, 120):
        resumen(simular(ev, latencia=lat), f"latencia +{lat} min")
    c, rech = filtro_cartera(base, CFG.max_posiciones_simultaneas)
    resumen(c, f"cartera máx. 5 pos. (rechazadas {rech})")
    base.to_parquet(RES / "listados_1m_trades.parquet")


if __name__ == "__main__":
    main()
