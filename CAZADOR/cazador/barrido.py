"""Ronda 1 – barrido del catálogo con datos reales (sin cartera: cada señal opera 200 $; la cartera se aplica a las finalistas).

Diseño:
* El universo de monedas se reparte entre N procesos; cada proceso carga SU trozo una vez y ejecuta TODAS las pruebas.
* Cada prueba devuelve agregados ADITIVOS (pnl diario, conteos, sumas por régimen, por moneda, top-5 operaciones) que se suman
  entre procesos. Así no hay que mover listas de operaciones y el consumo de memoria es pequeño.
* Una 'prueba' (trial) = estrategia × parámetros × marco × inversa × salida × lado (ambos/long/short). Todas se anotan en
  trials_log.csv: es la base del Deflated Sharpe y del PBO. Los filtros de régimen posteriores cuentan como pruebas nuevas.
"""
from __future__ import annotations

import dataclasses
import itertools
import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import cargar, regimenes
from . import estrategias as E
from .config import CFG
from .descarga import PERIODO, CACHE
from .motor import DatosMoneda, Senales, Salida, simular_moneda, MS_MIN

DIA_MS = 86_400_000
DIA0 = int(pd.Timestamp(PERIODO["busqueda_ini"]).timestamp() * 1000) // DIA_MS
ND = (int(pd.Timestamp(PERIODO["busqueda_fin"]).timestamp() * 1000) // DIA_MS) - DIA0 + 1     # días de búsqueda
NREG = len(regimenes.ORDEN) + 1                                                                   # + 'sin etiqueta'
LADOS = {"ambos": None, "long": 1, "short": -1}


def dia_de(ts_ms: np.ndarray) -> np.ndarray:
    return (ts_ms // DIA_MS - DIA0).astype(np.int64)


# ----------------------------------------------------------------------------------------------
@dataclass
class Prep:
    d: DatosMoneda
    miembro: np.ndarray          # bool por día de búsqueda: ¿está en el universo (vol. 7 d previos > 10 M$)?
    barras: Dict[int, E.Barras]

    def bar(self, tf: int) -> E.Barras:
        if tf not in self.barras:
            self.barras[tf] = E.barras_tf(self.d, tf)
        return self.barras[tf]


def preparar(sim: str, miembros: pd.DataFrame) -> Optional[Prep]:
    d = cargar.cargar_moneda(sim, "busqueda")
    if d is None:
        return None
    d.slip(CFG)                                                     # precalcula deslizamiento
    fechas = pd.date_range(PERIODO["busqueda_ini"], periods=ND)
    m = (miembros[sim].reindex(fechas).fillna(False).to_numpy(bool) if sim in miembros.columns
         else np.zeros(ND, bool))
    return Prep(d, m, {})


def filtrar_senales(p: Prep, s: Senales, sin_universo: bool = False) -> Senales:
    """Solo señales dentro del periodo de búsqueda y con la moneda dentro del universo ese día
    (``sin_universo`` se reserva a estrategias de listados nuevos, que por definición operan antes de los 7 días de volumen)."""
    if len(s) == 0:
        return s
    ok = s.idx >= p.d.idx_eval
    dia = dia_de(p.d.t0_ms + s.idx * MS_MIN)
    ok &= (dia >= 0) & (dia < ND)
    if not sin_universo:
        ok &= p.miembro[np.clip(dia, 0, ND - 1)]
    return s.filtrar(ok)


# ----------------------------------------------------------------------------------------------
CLAVES_ADITIVAS = ("d_pnl", "d_n", "reg_n", "reg_pnl", "d_gw", "d_gl", "d_R", "dr_pnl", "dr_n", "dr_gw", "dr_gl", "dr_R")


def _agregar(t: pd.DataFrame, codigo_dia: np.ndarray, detalle: bool = False) -> Dict[str, dict]:
    """Agregados aditivos por lado (ambos/long/short) de una lista de operaciones."""
    out = {}
    if t.empty:
        return out
    dia_sal = np.clip(dia_de(t["salida_ts"].to_numpy()), 0, ND - 1)
    dia_ent = np.clip(dia_de(t["entrada_ts"].to_numpy()), 0, ND - 1)
    reg = codigo_dia[dia_ent]
    pnl, R, lado = t["pnl"].to_numpy(), t["R"].to_numpy(), t["lado"].to_numpy()
    cost = (t["comisiones"] + t["funding"]).to_numpy()
    for nombre, l in LADOS.items():
        m = np.ones(len(t), bool) if l is None else (lado == l)
        if not m.any():
            continue
        p, r = pnl[m], R[m]
        a = {
            "n": int(m.sum()), "pnl": float(p.sum()), "pnl_sq": float((p ** 2).sum()), "R": float(r.sum()),
            "gw": float(p[p > 0].sum()), "gl": float(-p[p <= 0].sum()), "wins": int((p > 0).sum()),
            "costes": float(cost[m].sum()),
            "d_pnl": np.bincount(dia_sal[m], weights=p, minlength=ND),
            "d_n": np.bincount(dia_sal[m], minlength=ND).astype(np.int64),
            "d_gw": np.bincount(dia_sal[m], weights=np.where(p > 0, p, 0.0), minlength=ND),
            "d_gl": np.bincount(dia_sal[m], weights=np.where(p <= 0, -p, 0.0), minlength=ND),
            "d_R": np.bincount(dia_sal[m], weights=r, minlength=ND),
            "reg_n": np.bincount(reg[m], minlength=NREG).astype(np.int64),
            "reg_pnl": np.bincount(reg[m], weights=p, minlength=NREG),
            "top5": np.sort(p)[-5:],
            "sym": {t["simbolo"].iloc[0]: float(p.sum())},
        }
        if detalle:                               # curvas diarias POR RÉGIMEN (régimen de la entrada, día de la salida)
            ix = reg[m] * ND + dia_sal[m]
            sz = NREG * ND
            f32 = np.float32                          # float32: los agregados por régimen de Ronda 2 ocupan ~4 GB en float64
            a["dr_pnl"] = np.bincount(ix, weights=p, minlength=sz).reshape(NREG, ND).astype(f32)
            a["dr_n"] = np.bincount(ix, minlength=sz).reshape(NREG, ND).astype(np.int32)
            a["dr_gw"] = np.bincount(ix, weights=np.where(p > 0, p, 0.0), minlength=sz).reshape(NREG, ND).astype(f32)
            a["dr_gl"] = np.bincount(ix, weights=np.where(p <= 0, -p, 0.0), minlength=sz).reshape(NREG, ND).astype(f32)
            a["dr_R"] = np.bincount(ix, weights=r, minlength=sz).reshape(NREG, ND).astype(f32)
        out[nombre] = a
    return out


def _fusionar(a: Optional[dict], b: dict) -> dict:
    if a is None:
        return b
    for k in ("n", "pnl", "pnl_sq", "R", "gw", "gl", "wins", "costes"):
        a[k] += b[k]
    for k in CLAVES_ADITIVAS:
        if k in a:
            a[k] = a[k] + b[k]
    a["top5"] = np.sort(np.concatenate([a["top5"], b["top5"]]))[-5:]
    for s, v in b["sym"].items():
        a["sym"][s] = a["sym"].get(s, 0.0) + v
    return a


def salida_para(nombre: str, tf: int) -> Salida:
    """Catálogo de salidas de Ronda 1 (§5 'Salidas'): objetivos en R, en % del margen, trailing."""
    mv = int(np.clip(tf * 40, 240, 43_200))
    tabla = {
        "obj1R": Salida(objetivo_R=1.0, max_velas_1m=mv), "obj2R": Salida(objetivo_R=2.0, max_velas_1m=mv),
        "obj3R": Salida(objetivo_R=3.0, max_velas_1m=mv),
        "trail2R": Salida(trailing_R=2.0, max_velas_1m=mv), "trail3R": Salida(trailing_R=3.0, max_velas_1m=mv),
        "obj3R_be": Salida(objetivo_R=3.0, break_even_R=1.5, max_velas_1m=mv),
    }
    tabla["ml_1R_24h"] = Salida(objetivo_R=1.0, max_velas_1m=1440)       # objetivo = stop (1R) o salida a las 24 h (la etiqueta del modelo)
    tabla["hold"] = Salida(max_velas_1m=43_200)         # solo stop de catástrofe + salida forzada por señal contraria (30 d máx.)
    tabla["hold_trail4R"] = Salida(trailing_R=4.0, max_velas_1m=43_200)
    for h in (4, 12, 24, 48, 72, 168):                  # salidas solo por tiempo (estacionalidad): el stop sigue activo
        tabla[f"t{h}h"] = Salida(max_velas_1m=h * 60)
    for pct in CFG.objetivos_beneficio_pct_margen:
        tabla[f"obj{pct}pct"] = Salida(objetivo_pct_margen=float(pct), max_velas_1m=mv)
    return tabla[nombre]


EXITS_TIEMPO_G = ["t4h", "t12h", "t24h"]
EXITS_R1 = ["obj1R", "obj2R", "obj3R", "trail2R", "trail3R", "obj3R_be", "obj5pct", "obj10pct", "obj20pct", "obj30pct", "obj50pct"]


def _trabajador(idx: int, simbolos: List[str], miembros: pd.DataFrame, codigo_dia: np.ndarray,
                q_in: "mp.Queue", q_out: "mp.Queue") -> None:
    preps: Dict[str, Prep] = {}
    for s in simbolos:
        p = preparar(s, miembros)
        if p is not None:
            preps[s] = p
    q_out.put(("listo", idx, sorted(preps)))
    while True:
        lote = q_in.get()
        if lote is None:
            return
        res: Dict[Tuple[int, str, str], dict] = {}
        for job in lote:
            for sim, p in preps.items():
                try:
                    if job.get("senales_pre") is not None:
                        s = job["senales_pre"].get(sim)
                        if s is None or len(s) == 0:
                            continue
                        s = filtrar_senales(p, s, job.get("sin_universo", False))
                    else:
                        B = p.bar(job["tf"])
                        if len(B) < 30:
                            continue
                        s = E.REGISTRO[job["fam"]]["fn"](B, **{**E.REGISTRO[job["fam"]]["params"], **job["params"],
                                                                "invertir": job["inv"]})
                        if job.get("contraria"):
                            s = E.con_salida_contraria(s)       # ANTES de filtrar: la señal contraria puede caer fuera del universo
                        s = filtrar_senales(p, s, job.get("sin_universo", False))
                    if len(s) == 0:
                        continue
                    m_c = job.get("cfg_mult", 1.0)
                    cfg_j = CFG if m_c == 1.0 else dataclasses.replace(
                        CFG, comision_taker_pct=CFG.comision_taker_pct * m_c, comision_maker_pct=CFG.comision_maker_pct * m_c,
                        deslizamiento_min_pct=CFG.deslizamiento_min_pct * m_c)
                    for ex in job["exits"]:
                        t = simular_moneda(p.d, s, cfg_j, salida_para(ex, job["tf"]), job.get("latencia", 0), slip_mult=m_c)
                        for lado, agg in _agregar(t, codigo_dia, job.get("detalle", False)).items():
                            k = (job["id"], ex, lado)
                            res[k] = _fusionar(res.get(k), agg)
                except Exception as e:  # noqa: BLE001
                    res[("ERROR", job["id"], sim)] = {"error": f"{type(e).__name__}: {e}"}
        q_out.put(("res", idx, res))


def barrido(jobs: List[dict], simbolos: List[str], miembros: pd.DataFrame, codigo_dia: np.ndarray,
            nproc: int = 4, tam_lote: int = 8, log=print) -> Dict[Tuple[int, str, str], dict]:
    ctx = mp.get_context("fork")
    q_out = ctx.Queue()
    trozos = [simbolos[i::nproc] for i in range(nproc)]
    colas = [ctx.Queue() for _ in range(nproc)]
    procs = [ctx.Process(target=_trabajador, args=(i, trozos[i], miembros, codigo_dia, colas[i], q_out), daemon=True)
             for i in range(nproc)]
    for p in procs:
        p.start()
    cargados = []
    for _ in range(nproc):
        _, i, syms = q_out.get()
        cargados += syms
    log(f"monedas cargadas: {len(cargados)}/{len(simbolos)}")
    total: Dict[Tuple[int, str, str], dict] = {}
    t0 = time.time()
    lotes = [jobs[i:i + tam_lote] for i in range(0, len(jobs), tam_lote)]
    for k, lote in enumerate(lotes):
        for c in colas:
            c.put(lote)
        for _ in range(nproc):
            _, i, res = q_out.get()
            for key, agg in res.items():
                if key[0] == "ERROR":
                    log(f"ERROR en trabajo {key[1]} / {key[2]}: {agg['error']}")
                    continue
                total[key] = _fusionar(total.get(key), agg)
        if (k + 1) % 5 == 0 or k == len(lotes) - 1:
            log(f"  lote {k + 1}/{len(lotes)} ({time.time() - t0:.0f}s)")
    for c in colas:
        c.put(None)
    for p in procs:
        p.join(timeout=30)
    return total


# ----------------------------------------------------------------------------------------------
# Métricas derivadas de los agregados
# ----------------------------------------------------------------------------------------------
def _mes_de_dia() -> np.ndarray:
    fechas = pd.date_range(PERIODO["busqueda_ini"], periods=ND)
    return (fechas.year * 12 + fechas.month).to_numpy() - (fechas[0].year * 12 + fechas[0].month)


MES_DIA = _mes_de_dia()
SEM_DIA = np.arange(ND) // 7


def metricas(a: dict) -> dict:
    n = a["n"]
    d = a["d_pnl"]
    mensual = np.bincount(MES_DIA, weights=d)
    mens_n = np.bincount(MES_DIA, weights=a["d_n"])
    semanal = np.bincount(SEM_DIA, weights=d)
    sd = d.std(ddof=1)
    sym = a["sym"]
    pos = sum(v for v in sym.values() if v > 0)
    return {
        "n": n, "exp_usd": a["pnl"] / n, "exp_R": a["R"] / n, "aciertos": a["wins"] / n,
        "pf": (a["gw"] / a["gl"]) if a["gl"] > 0 else np.nan, "beneficio": a["pnl"],
        "sharpe_dia": (d.mean() / sd) if sd > 0 else 0.0,
        "meses_pos": float((mensual[mens_n > 0] > 0).mean()) if (mens_n > 0).any() else np.nan,
        "sin_mejor_sem": a["pnl"] - float(semanal.max()), "sin_top5": a["pnl"] - float(a["top5"].sum()),
        "peso_mejor_moneda": (max(sym.values()) / pos) if pos > 0 else np.nan,
        "costes": a["costes"], "costes_por_op": a["costes"] / n,
        "ops_dia": n / ND,
    }
