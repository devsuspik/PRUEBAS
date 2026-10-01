"""§5-D Funding carry / cash-and-carry: LONG spot + SHORT perp cuando el funding es alto y persistente (delta neutral).

Contabilidad propia (no pasa por el motor de stops):
  * Entrada/salida a los precios de la vela de 1 h siguiente a la señal (spot y perp).
  * Cobra (paga) funding en cada marca mientras la posición está abierta: short perp cobra si tasa > 0.
  * PnL de base = q * [(S_sal - P_sal) - (S_ent - P_ent)]   (q = nocional / P_ent).
  * Costes: spot taker + perp taker en entrada y salida + deslizamiento en las 4 patas.
  * Liquidación del corto con el margen/apalancamiento de CFG: si el máximo del perp (1 m) toca el precio de liquidación,
    se pierde el margen del corto, la pata spot se cierra a ese precio y la operación termina.
  * Capital necesario = nocional (spot) + margen del perp. Con 20 $ de margen a 10x son ~220 $, no 20 $: el retorno sobre
    capital es ~11 veces menor que el retorno sobre margen.
Solo la versión 'long spot + short perp' (la contraria exigiría pedir prestado el spot).
"""
from __future__ import annotations

import itertools
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import cargar
from .config import CFG
from .descarga import CACHE, PERIODO
from .periodo import RES, UNIV
from .motor import MS_MIN

H_MS = 3_600_000
FEE_SPOT = 0.0010          # 0,10 % taker spot (sin descuento BNB): conservador


def _spot_1h(sim: str) -> Optional[pd.Series]:
    p = CACHE / "klines" / "spot_1h" / f"{sim}.parquet"
    if not p.exists():
        return None
    g = pd.read_parquet(p, columns=["t", "c"])
    if g.empty:
        return None
    return pd.Series(g["c"].astype("float64").to_numpy(), index=g["t"].to_numpy("int64"))


def _funding_normalizado(sim: str) -> Optional[pd.DataFrame]:
    p = CACHE / "funding" / f"{sim}.parquet"
    if not p.exists():
        return None
    f = pd.read_parquet(p).sort_values("t")
    f["horas"] = f["horas"].fillna(8).astype(float)
    f["tasa8h"] = f["tasa"] * 8.0 / f["horas"]        # equivalente a 8 h para comparar umbrales entre monedas
    return f


BASE_MAX_ENTRADA = 0.02      # si |spot/perp - 1| > 2 % al entrar, el mercado spot es ilíquido/rancio o no es el mismo activo: se ignora
BASE_SALTO_MAX = 0.08        # si la base se mueve > 8 % entre entrada y salida se considera dato spot dudoso y se DESCARTA la operación


def simular_simbolo(sim: str, d, spot: pd.Series, f: pd.DataFrame, miembro_dia: np.ndarray, m: int, th_in: float,
                    th_out: float, max_dias: int, cfg=CFG, apal: Optional[float] = None, descartadas: Optional[list] = None) -> List[dict]:
    """Trades de carry de una moneda. ``d`` = DatosMoneda 1 m del perp; ``spot`` = cierre spot 1 h indexado por ms de apertura."""
    t_f = f["t"].to_numpy("int64")
    rate = f["tasa"].to_numpy()
    n = len(t_f)
    if n < m + 2:
        return []
    media = pd.Series(f["tasa8h"].to_numpy()).rolling(m).mean().to_numpy()      # media de las m últimas marcas (ya conocidas)
    apal = apal or cfg.apalancamiento
    nocional = cfg.nocional_usd
    margen = nocional / apal
    liq_frac = 1.0 / apal - cfg.mantenimiento_margen_frac
    t0 = d.t0_ms
    eval_ms = t0 + d.idx_eval * MS_MIN
    fin_ms = t0 + (d.n - 1) * MS_MIN
    sp_idx = spot.index.to_numpy()

    def spot_en(t_ms: int) -> float:
        """Precio spot en t_ms = cierre de la vela horaria que termina en t_ms (o la última anterior)."""
        i = np.searchsorted(sp_idx, t_ms - H_MS, side="right") - 1
        return float(spot.iloc[i]) if i >= 0 and (t_ms - H_MS - sp_idx[i]) <= 6 * H_MS else np.nan

    out: List[dict] = []
    k = m - 1
    while k < n - 1:
        ts = int(t_f[k])
        if ts < eval_ms or not (np.isfinite(media[k]) and media[k] >= th_in):
            k += 1
            continue
        dia = ts // 86_400_000 - _dia0()
        if dia < 0 or dia >= len(miembro_dia) or not miembro_dia[dia]:
            k += 1
            continue
        t_ent = (ts // H_MS + 1) * H_MS                           # entra en la hora en punto siguiente a la publicación
        i_ent = int((t_ent - t0) // MS_MIN)
        S_e = spot_en(t_ent)
        if i_ent >= d.n - 1 or not np.isfinite(S_e) or not (d.o[i_ent] > 0):
            k += 1
            continue
        P_e = float(d.o[i_ent])
        if abs(S_e / P_e - 1.0) > BASE_MAX_ENTRADA:
            k += 1
            continue
        q = nocional / P_e
        liq_px = P_e * (1.0 + liq_frac)
        t_lim = t_ent + max_dias * 86_400_000
        fund, i_chk, j = 0.0, i_ent, k + 1
        t_sal, motivo, liquidado = None, "max_dias", False
        while j < n:
            tj = int(t_f[j])
            if tj > t_lim or tj > fin_ms:
                break
            i1 = int((tj - t0) // MS_MIN)
            seg = d.h[i_chk:i1 + 1]
            if len(seg) and seg.max() >= liq_px:                   # el corto toca su precio de liquidación
                t_sal = t0 + (i_chk + int(np.argmax(seg >= liq_px))) * MS_MIN
                motivo, liquidado = "liquidacion", True
                break
            i_chk = i1 + 1
            fund += rate[j] * q * d.o[min(i1, d.n - 1)]            # short perp cobra si la tasa > 0
            if np.isfinite(media[j]) and media[j] <= th_out:
                t_sal, motivo = (tj // H_MS + 1) * H_MS, "funding_bajo"
                j += 1
                break
            j += 1
        if t_sal is None:
            t_sal = (min(t_lim, fin_ms) // H_MS + 1) * H_MS
            if t_lim > fin_ms:
                break                                             # la operación no termina dentro de los datos
        if t_sal > fin_ms:
            break
        i_sal = int((t_sal - t0) // MS_MIN)
        # En una liquidación (pico súbito) el cierre horario previo del spot iría retrasado: se aproxima el spot por el mismo
        # movimiento porcentual que el perp (base constante). En el resto de salidas se usa el cierre horario real.
        S_x = S_e * (liq_px / P_e) if liquidado else spot_en(t_sal)
        if not np.isfinite(S_x):
            k = max(j, k + 1)
            continue
        P_x = liq_px if liquidado else float(d.o[i_sal])
        if not liquidado and abs((S_x / P_x) - (S_e / P_e)) > BASE_SALTO_MAX:
            if descartadas is not None:
                descartadas.append(sim)
            k = max(j, k + 1)
            continue
        if liquidado:
            # el corto pierde el margen entero; la pata spot se cierra en ese momento
            base = -margen + q * (S_x - S_e)
            costes = (FEE_SPOT + cfg.fee_taker) * nocional + FEE_SPOT * q * S_x + 3 * cfg.slip_min * nocional
        else:
            base = q * ((S_x - P_x) - (S_e - P_e))
            costes = (FEE_SPOT + cfg.fee_taker) * 2 * nocional + 4 * cfg.slip_min * nocional
        pnl = base + fund - costes
        out.append(dict(simbolo=sim, entrada_ts=t_ent, salida_ts=int(t_sal), lado=-1, entrada_px=P_e, salida_px=P_x, qty=q,
                        comisiones=costes, funding=-fund, pnl=pnl, riesgo_usd=margen, motivo=motivo, R=pnl / margen))
        k = max(j, k + 1)
    return out


def _dia0() -> int:
    return int(pd.Timestamp(PERIODO["busqueda_ini"]).timestamp() * 1000) // 86_400_000


def grid_carry() -> List[dict]:
    jobs, i = [], 30_000
    for m, th_in, th_out, dias in itertools.product((1, 3, 9), (0.0002, 0.0003, 0.0005, 0.001), (0.0, 0.0001), (3, 10, 30)):
        if th_out >= th_in:
            continue
        for ap in (10.0, 3.0):
            jobs.append(dict(id=i, fam="carry_funding", tf=480, m=m, th_in=th_in, th_out=th_out, dias=dias, apal=ap, inv=False))
            i += 1
    return jobs


def correr_carry(simbolos: List[str], miembros: pd.DataFrame, codigo_dia: np.ndarray, log=print) -> pd.DataFrame:
    """Ejecuta todo el grid de carry sobre todas las monedas con spot; devuelve métricas por prueba y guarda curvas diarias."""
    from . import barrido as BR
    jobs = grid_carry()
    fechas = pd.date_range(PERIODO["busqueda_ini"], periods=BR.ND)
    trades: Dict[int, List[dict]] = {j["id"]: [] for j in jobs}
    usadas, desc = [], []
    for s in simbolos:
        sp, f = _spot_1h(s), _funding_normalizado(s)
        if sp is None or f is None:
            continue
        d = cargar.cargar_moneda(s, "busqueda")
        if d is None:
            continue
        mem = (miembros[s].reindex(fechas).fillna(False).to_numpy(bool) if s in miembros.columns else np.zeros(BR.ND, bool))
        usadas.append(s)
        for j in jobs:
            trades[j["id"]] += simular_simbolo(s, d, sp, f, mem, j["m"], j["th_in"], j["th_out"], j["dias"], apal=j["apal"],
                                               descartadas=desc)
        del d
    log(f"carry: monedas con spot+funding: {len(usadas)} | operaciones descartadas por base dudosa: {len(desc)} ({sorted(set(desc))})")
    filas, diarios = [], {}
    for j in jobs:
        t = pd.DataFrame(trades[j["id"]])
        if t.empty:
            continue
        aggs = BR._agregar(t, codigo_dia)
        a = aggs["ambos"]
        mtr = BR.metricas(a)
        tid = f"{j['id']}|carry|ambos"
        fila = {"trial": tid, "fam": "carry_funding", "tf": 480, "inv": False,
                "params": f"m={j['m']},in={j['th_in']},out={j['th_out']},dias={j['dias']},apal={j['apal']:g}", "salida": "carry", "lado": "ambos", **mtr}
        for r in range(BR.NREG):
            fila[f"reg{r}_n"] = int(a["reg_n"][r])
            fila[f"reg{r}_pnl"] = float(a["reg_pnl"][r])
        fila["liquidaciones"] = int((t["motivo"] == "liquidacion").sum())
        filas.append(fila)
        diarios[tid] = a["d_pnl"].astype("float32")
    return pd.DataFrame(filas), diarios, trades


def main() -> None:
    import json
    from . import ronda1 as R1, trials, universo
    from .descarga import RAIZ
    sel = json.loads(UNIV.read_text())["seleccion"]
    miembros = universo.miembros_por_fecha()
    cod, _ = R1.codigo_dia_busqueda()
    df, diarios, _ = correr_carry(sel, miembros, cod)
    df.to_parquet(RES / "ronda1d.parquet")
    np.savez_compressed(RES / "ronda1d_diario.npz", **{k.replace("|", "__"): v for k, v in diarios.items()})
    for r in df.itertuples():
        trials.registrar(dict(ronda=1, estrategia=r.fam, marco_min=r.tf, params=r.params, salida=r.salida, segmento="reducido50",
                              regimen="todos", lado=r.lado, n_ops=r.n, exp_R=round(r.exp_R, 5), beneficio_usd=round(r.beneficio, 2),
                              sharpe_periodo=round(r.sharpe_dia, 5), tramo="busqueda_24m"))
    print(f"carry: {len(df)} pruebas con operaciones de {len(grid_carry())}")


if __name__ == "__main__":
    main()
