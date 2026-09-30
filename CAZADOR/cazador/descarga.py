"""Descarga masiva y paralela desde data.binance.vision (la API fapi está bloqueada por región: 451).

* Reanudable: si existe el parquet de un símbolo/intervalo no se vuelve a bajar.
* No guarda zips (ocuparían decenas de GB): parsea en memoria y escribe un parquet por símbolo.
* Períodos congelados en PERIODO (se escriben en PERIODO.json antes de mirar ningún resultado).

Uso:
  python -m cazador.descarga universo      # 1d de TODOS los perpetuos USDT -> volumen -> universo por fecha
  python -m cazador.descarga reducido      # 1m + funding del modo reducido (top 15 + 35 al azar)
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from . import datos as D
from .config import CFG

RAIZ = Path(__file__).resolve().parent.parent
CACHE = D.CACHE
PERIODO = {
    "busqueda_ini": "2024-08-01", "busqueda_fin": "2026-07-31",
    "holdout_ini": "2026-08-01", "holdout_fin": "2026-09-29",
    "previo_universo_ini": "2024-07-01",           # 1 mes previo para poder calcular volumen a 7 d en el primer día
    "calentamiento_ini": "2023-11-01",             # 9 meses de 1m SOLO para calcular indicadores (SMA200 diaria…); no se opera
}
LOG = RAIZ / "descarga.log"
_lock = threading.Lock()


def log(*a) -> None:
    msg = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    with _lock:
        print(msg, flush=True)
        with LOG.open("a") as f:
            f.write(msg + "\n")


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def simbolos_usdt() -> List[str]:
    pref = D.listar_prefijos("data/futures/um/monthly/klines/")
    syms = [p.rstrip("/").split("/")[-1] for p in pref]
    return sorted(s for s in syms if s.endswith("USDT") and "_" not in s and s.isascii())


def tareas_klines(sim: str, intervalo: str, ini: pd.Timestamp, fin: pd.Timestamp, diarios_solo_si: bool = True) -> List[str]:
    """URLs a bajar: mensuales completos + diarios del mes en curso (hasta ``fin``)."""
    urls = []
    for m in D.meses_entre(ini, fin):
        fin_mes = pd.Period(m, "M").end_time.normalize()
        if fin_mes <= fin:
            urls.append(f"{D.BASE}/monthly/klines/{sim}/{intervalo}/{sim}-{intervalo}-{m}.zip")
        else:
            for dia in pd.date_range(pd.Period(m, "M").start_time, fin, freq="D"):
                ds = dia.strftime("%Y-%m-%d")
                urls.append(f"{D.BASE}/daily/klines/{sim}/{intervalo}/{sim}-{intervalo}-{ds}.zip")
    return urls


def _bajar(url: str, lector: Callable[[bytes], pd.DataFrame]) -> Optional[pd.DataFrame]:
    r = D.http_get(url)
    return None if r is None else lector(r.content)


def bajar_klines(simbolos: List[str], intervalo: str, ini: pd.Timestamp, fin: pd.Timestamp,
                 workers: int = 16) -> Dict[str, int]:
    """Baja klines de todos los símbolos en paralelo y escribe CACHE/klines/<intervalo>/<SIM>.parquet."""
    destino = CACHE / "klines" / intervalo
    destino.mkdir(parents=True, exist_ok=True)
    pendientes = [s for s in simbolos if not (destino / f"{s}.parquet").exists()]
    log(f"klines {intervalo}: {len(pendientes)} símbolos pendientes de {len(simbolos)}")
    partes: Dict[str, list] = {s: [] for s in pendientes}
    faltan: Dict[str, int] = {}
    tareas = []
    for s in pendientes:
        urls = tareas_klines(s, intervalo, ini, fin)
        faltan[s] = len(urls)
        tareas += [(s, u) for u in urls]
    filas: Dict[str, int] = {}
    hechas = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(_bajar, u, D.leer_klines_zip): (s, u) for s, u in tareas}
        for f in as_completed(fut):
            s, u = fut[f]
            try:
                df = f.result()
            except Exception as e:  # noqa: BLE001
                log(f"ERROR {u}: {type(e).__name__} {str(e)[:100]}")
                df = None
                faltan[s] = -10 ** 9          # no escribir parquet incompleto
            if df is not None and len(df):
                partes[s].append(df)
            faltan[s] -= 1
            hechas += 1
            if faltan[s] == 0:
                p = partes.pop(s)
                g = (pd.concat(p, ignore_index=True).sort_values("t").drop_duplicates("t")
                     if p else pd.DataFrame(columns=["t", "o", "h", "l", "c", "v", "qv", "n", "tb_v", "tb_qv"]))
                g = g.astype({"qv": "float32", "v": "float32", "tb_v": "float32", "tb_qv": "float32", "n": "int32"})
                g.to_parquet(destino / f"{s}.parquet", compression="zstd")
                filas[s] = len(g)
            if hechas % 500 == 0:
                log(f"  {hechas}/{len(tareas)} ficheros ({hechas / (time.time() - t0):.1f}/s)")
    log(f"klines {intervalo}: terminado en {time.time() - t0:.0f}s; símbolos con datos: {sum(1 for v in filas.values() if v > 0)}")
    return filas


def bajar_funding(simbolos: List[str], ini: pd.Timestamp, fin: pd.Timestamp, workers: int = 16) -> None:
    destino = CACHE / "funding"
    destino.mkdir(parents=True, exist_ok=True)
    pend = [s for s in simbolos if not (destino / f"{s}.parquet").exists()]
    log(f"funding: {len(pend)} símbolos pendientes")
    partes: Dict[str, list] = {s: [] for s in pend}
    tareas = [(s, f"{D.BASE}/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip") for s in pend
              for m in D.meses_entre(ini, fin) if pd.Period(m, "M").end_time.normalize() <= fin]
    faltan = {s: sum(1 for x, _ in tareas if x == s) for s in pend}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(_bajar, u, D.leer_funding_zip): (s, u) for s, u in tareas}
        for f in as_completed(fut):
            s, u = fut[f]
            try:
                df = f.result()
            except Exception as e:  # noqa: BLE001
                log(f"ERROR {u}: {e}")
                df, faltan[s] = None, -10 ** 9
            if df is not None and len(df):
                partes[s].append(df)
            faltan[s] -= 1
            if faltan[s] == 0:
                p = partes.pop(s)
                g = pd.concat(p, ignore_index=True).sort_values("t").drop_duplicates("t") if p else pd.DataFrame(columns=["t", "tasa", "horas"])
                g.to_parquet(destino / f"{s}.parquet", compression="zstd")


def cargar_1d(sim: str) -> pd.DataFrame:
    return pd.read_parquet(CACHE / "klines" / "1d" / f"{sim}.parquet")


def volumen_diario(simbolos: List[str]) -> pd.DataFrame:
    """Matriz fecha(UTC) x símbolo con el volumen diario en USDT (NaN = no cotizaba)."""
    cols = {}
    for s in simbolos:
        p = CACHE / "klines" / "1d" / f"{s}.parquet"
        if not p.exists():
            continue
        g = pd.read_parquet(p, columns=["t", "qv"])
        if len(g):
            idx = pd.to_datetime(g["t"], unit="ms").dt.floor("D")
            cols[s] = pd.Series(g["qv"].astype("float64").to_numpy(), index=idx)
    return pd.DataFrame(cols).sort_index()


def fase_universo() -> None:
    (RAIZ / "PERIODO.json").write_text(json.dumps(PERIODO, indent=1))
    syms = simbolos_usdt()
    log(f"perpetuos USDT (incluye retirados): {len(syms)}")
    ini, fin = ts(PERIODO["previo_universo_ini"]), ts(PERIODO["holdout_fin"])
    # mensuales de todos; los diarios del mes en curso se piden también (los muertos dan 404 rápido)
    bajar_klines(syms, "1d", ini, fin)
    v = volumen_diario(syms)
    v.to_parquet(CACHE / "volumen_diario.parquet")
    log(f"matriz de volumen {v.shape}")


def fase_reducido() -> None:
    """1m + funding del modo reducido (UNIVERSO.json), desde el inicio del calentamiento hasta el final del holdout.
    El holdout se descarga pero NO se analiza (cargar.py lo bloquea)."""
    from . import universo
    info = universo.universo_y_seleccion()
    sel = info["seleccion"]
    log(f"modo reducido: {len(sel)} monedas")
    ini, fin = ts(PERIODO["calentamiento_ini"]), ts(PERIODO["holdout_fin"])
    bajar_funding(sel, ini, fin)
    bajar_klines(sel, "1m", ini, fin, workers=12)
    log("reducido: terminado")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "universo":
        fase_universo()
    elif len(sys.argv) > 1 and sys.argv[1] == "reducido":
        fase_reducido()
