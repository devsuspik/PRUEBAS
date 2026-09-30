"""§4 MOTOR DE SIMULACIÓN.

Reglas (todas conservadoras):
* Las señales se conocen al CIERRE de una vela de marco superior; la orden entra en la apertura de la
  siguiente vela de 1 m (+ latencia en velas), nunca antes.
* Si en la misma vela se tocan stop y objetivo, cuenta el stop.
* Los stops nuevos (break-even, trailing) solo se aplican desde la vela siguiente.
* Si hay hueco a través del stop, se ejecuta al precio de apertura.
* Costes: comisión taker/maker + deslizamiento por lado (mínimo fijo + impacto ~ sigma*sqrt(nocional/volumen))
  + funding en cada marca de funding cruzada + comisión de liquidación si se liquida.
* Liquidación aislada: si el precio toca el precio de liquidación antes que el stop, se pierde el margen.
* Redondeo a stepSize y rechazo por minNotional.
* Un objetivo solo se llena si el precio lo CRUZA (estrictamente), tocarlo no basta, y por defecto paga taker.
* Cartera: máximo de posiciones simultáneas y una posición por moneda (filtro posterior, ver ``filtro_cartera``).

NO implementado todavía (se declara, no se disimula): entradas con orden límite / market making y
simulación sobre aggTrades por debajo de 1 minuto. Las estrategias de segundos quedan fuera hasta
que exista la simulación tick a tick.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

import numpy as np
import pandas as pd
from numba import njit

from .config import Config

# Motivos de salida
STOP, STOP_GAP, OBJETIVO, TIEMPO, TIEMPO_SIN_AVANCE, SENAL, LIQUIDACION, RECHAZADA = range(8)
MOTIVOS = ["stop", "stop_hueco", "objetivo", "tiempo_max", "tiempo_sin_avance", "senal_contraria",
           "liquidacion", "rechazada"]

MS_MIN = 60_000


@dataclass(frozen=True)
class Salida:
    """Reglas de salida (§5 'Salidas'). Todo en múltiplos de la distancia al stop (R) o % del margen."""
    objetivo_R: float = 0.0            # 0 = sin objetivo en R
    objetivo_pct_margen: float = 0.0   # 0 = sin objetivo en % del margen (tiene prioridad sobre objetivo_R)
    break_even_R: float = 0.0          # 0 = nunca
    break_even_colchon_frac: float = 0.0012  # el stop se mueve a entrada +- colchón (cubre ~costes)
    trailing_R: float = 0.0            # 0 = sin trailing; distancia en R desde el máximo favorable
    max_velas_1m: int = 60 * 24 * 7    # tiempo máximo en posición
    sin_avance_velas: int = 0          # si a las y velas no hay +x R, salir
    sin_avance_R: float = 0.0

    def clave(self) -> str:
        return "|".join(f"{k}={v}" for k, v in asdict(self).items())


@dataclass
class DatosMoneda:
    """Velas de 1 m en rejilla regular (huecos rellenados con cierre previo y volumen 0)."""
    simbolo: str
    t0_ms: int
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    qv: np.ndarray                      # volumen en USDT por minuto
    tb_qv: Optional[np.ndarray] = None  # volumen comprador agresivo (taker buy) en USDT
    f_ts_ms: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int64))
    f_rate: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float64))
    step: float = 0.0
    min_notional: float = 5.0
    tick: float = 0.0
    idx_eval: int = 0                   # primer índice 1 m en el que se puede operar (antes: calentamiento de indicadores)
    _slip: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def n(self) -> int:
        return len(self.c)

    def ts(self) -> np.ndarray:
        return self.t0_ms + np.arange(self.n, dtype=np.int64) * MS_MIN

    def f_idx(self) -> np.ndarray:
        """Índice de la vela de 1 m cuya apertura coincide con (o sigue a) cada marca de funding."""
        if len(self.f_ts_ms) == 0:
            return np.zeros(0, np.int64)
        idx = np.ceil((self.f_ts_ms - self.t0_ms) / MS_MIN).astype(np.int64)
        ok = (idx >= 0) & (idx < self.n)
        return idx[ok]

    def f_tasa(self) -> np.ndarray:
        if len(self.f_ts_ms) == 0:
            return np.zeros(0, np.float64)
        idx = np.ceil((self.f_ts_ms - self.t0_ms) / MS_MIN).astype(np.int64)
        ok = (idx >= 0) & (idx < self.n)
        return self.f_rate[ok]

    def slip(self, cfg: Config) -> np.ndarray:
        if self._slip is None:
            self._slip = calcular_slip(self.c, self.qv, cfg.nocional_usd, cfg.slip_min)
        return self._slip


def calcular_slip(c: np.ndarray, qv: np.ndarray, nocional: float, slip_min: float, ventana: int = 60) -> np.ndarray:
    """Deslizamiento por lado = mínimo + sigma_1m * sqrt(nocional / volumen_medio_1m) (ley de la raíz cuadrada).

    Se calcula con datos PASADOS (ventana móvil que termina en la propia vela anterior) para no mirar al futuro.
    """
    s = pd.Series(np.log(np.where(c > 0, c, np.nan)))
    sigma = s.diff().rolling(ventana, min_periods=10).std().shift(1).to_numpy()
    vol = pd.Series(qv).rolling(ventana, min_periods=10).mean().shift(1).to_numpy()
    sigma = np.where(np.isfinite(sigma), sigma, 0.002)
    vol = np.where(np.isfinite(vol) & (vol > 0), vol, 1e3)
    impacto = sigma * np.sqrt(nocional / vol)
    return np.minimum(slip_min + impacto, 0.05)


@dataclass
class Senales:
    """Señales de una moneda. ``idx`` = índice de 1 m de la última vela de 1 m de la vela de señal (cerrada)."""
    idx: np.ndarray
    lado: np.ndarray          # +1 long, -1 short
    dist_stop: np.ndarray     # distancia al stop en precio (>0)
    salida_idx: Optional[np.ndarray] = None  # índice 1 m de salida forzada (-1 = ninguna)

    def __len__(self) -> int:
        return len(self.idx)

    @staticmethod
    def vacia() -> "Senales":
        return Senales(np.zeros(0, np.int64), np.zeros(0, np.int8), np.zeros(0, np.float64))

    def filtrar(self, mask: np.ndarray) -> "Senales":
        return Senales(self.idx[mask], self.lado[mask], self.dist_stop[mask],
                       None if self.salida_idx is None else self.salida_idx[mask])


@njit(cache=True)
def _simular(o, h, l, c, qv, slip, f_idx, f_rate,
             s_idx, s_lado, s_sd, s_fexit,
             latencia, nocional, apal, mmr, fee_taker, fee_maker,
             obj_R, obj_frac, obj_maker, be_R, be_colchon, trail_R,
             max_velas, ts_velas, ts_R, step, min_notional):
    n = len(c)
    m = len(s_idx)
    ok = np.zeros(m, np.int8)
    e_i = np.zeros(m, np.int64)
    x_i = np.zeros(m, np.int64)
    lado_o = np.zeros(m, np.int8)
    e_px = np.zeros(m, np.float64)
    x_px = np.zeros(m, np.float64)
    qty_o = np.zeros(m, np.float64)
    fee_o = np.zeros(m, np.float64)
    fund_o = np.zeros(m, np.float64)
    pnl_o = np.zeros(m, np.float64)
    risk_o = np.zeros(m, np.float64)
    mot_o = np.full(m, 7, np.int8)
    margen = nocional / apal

    for k in range(m):
        side = float(s_lado[k])
        e = s_idx[k] + 1 + latencia
        if e >= n or e < 0:
            continue
        if qv[e] <= 0.0 or not (o[e] > 0.0):
            continue
        ep = o[e] * (1.0 + side * slip[e])
        qty = nocional / ep
        if step > 0.0:
            qty = np.floor(qty / step) * step
        if qty <= 0.0 or qty * ep < min_notional:
            continue
        sd = s_sd[k]
        if not (sd > 0.0):
            continue

        stop = ep - side * sd
        liq = ep * (1.0 - side * (1.0 / apal - mmr))
        # stop efectivo: el más cercano a la entrada entre stop y liquidación
        stop_es_liq = False
        if side > 0.0:
            if liq > stop:
                stop = liq
                stop_es_liq = True
        else:
            if liq < stop:
                stop = liq
                stop_es_liq = True

        if obj_frac > 0.0:
            target = ep * (1.0 + side * obj_frac)
        elif obj_R > 0.0:
            target = ep + side * obj_R * sd
        else:
            target = np.nan

        hwm = ep
        mfe = 0.0
        fexit = s_fexit[k]
        last = min(n - 1, e + max_velas - 1)
        xi = last
        xpx = c[last]
        motivo = 3  # tiempo máximo por defecto
        usa_taker_salida = True
        liq_fee = 0.0

        for j in range(e, last + 1):
            # 1) hueco a través del stop al abrir (el stop fijado al cierre anterior)
            if j > e:
                if side * (o[j] - stop) <= 0.0:
                    xi = j
                    xpx = o[j] * (1.0 - side * slip[j])
                    motivo = 6 if stop_es_liq else 1
                    if stop_es_liq:
                        xpx = liq
                        liq_fee = mmr * nocional
                    break
            # 2) stop / liquidación dentro de la vela (manda sobre el objetivo)
            tocado_stop = (l[j] <= stop) if side > 0.0 else (h[j] >= stop)
            if tocado_stop:
                xi = j
                if stop_es_liq:
                    xpx = stop
                    motivo = 6
                    liq_fee = mmr * nocional
                else:
                    xpx = stop * (1.0 - side * slip[j])
                    motivo = 0
                break
            # 3) objetivo (debe cruzarse estrictamente si es límite)
            if not np.isnan(target):
                if side > 0.0:
                    tocado_obj = (h[j] > target) if obj_maker else (h[j] >= target)
                else:
                    tocado_obj = (l[j] < target) if obj_maker else (l[j] <= target)
                if tocado_obj:
                    xi = j
                    if obj_maker:
                        xpx = target
                        usa_taker_salida = False
                    else:
                        xpx = target * (1.0 - side * slip[j])
                    motivo = 2
                    break
            # 4) actualizaciones de fin de vela (se aplican desde la siguiente)
            if side > 0.0:
                if h[j] > hwm:
                    hwm = h[j]
                fav = h[j] - ep
            else:
                if l[j] < hwm:
                    hwm = l[j]
                fav = ep - l[j]
            if fav > mfe:
                mfe = fav
            if be_R > 0.0 and mfe >= be_R * sd:
                nuevo = ep + side * be_colchon * ep
                if side > 0.0:
                    if nuevo > stop:
                        stop = nuevo
                        stop_es_liq = False
                else:
                    if nuevo < stop:
                        stop = nuevo
                        stop_es_liq = False
            if trail_R > 0.0:
                nuevo = hwm - side * trail_R * sd
                if side > 0.0:
                    if nuevo > stop:
                        stop = nuevo
                        stop_es_liq = False
                else:
                    if nuevo < stop:
                        stop = nuevo
                        stop_es_liq = False
            if ts_velas > 0 and (j - e + 1) == ts_velas:
                if side * (c[j] - ep) < ts_R * sd:
                    xi = j
                    xpx = c[j] * (1.0 - side * slip[j])
                    motivo = 4
                    break
            if fexit >= 0 and j >= fexit:
                xi = j
                xpx = c[j] * (1.0 - side * slip[j])
                motivo = 5
                break
        else:
            # terminó el bucle sin break: salida por tiempo máximo al cierre
            xi = last
            xpx = c[last] * (1.0 - side * slip[last])
            motivo = 3

        # comisiones
        fee_ent = fee_taker * qty * ep
        if motivo == 6:
            fee_sal = liq_fee              # en una liquidación no hay comisión taker: se paga la de liquidación
        elif usa_taker_salida:
            fee_sal = fee_taker * qty * xpx
        else:
            fee_sal = fee_maker * qty * xpx

        # funding: marcas con e < f_idx <= xi (en la vela de salida se cobra)
        fund = 0.0
        if len(f_idx) > 0:
            a = np.searchsorted(f_idx, e, side="right")
            b = np.searchsorted(f_idx, xi, side="right")
            for q in range(a, b):
                fund += side * f_rate[q] * qty * o[f_idx[q]]   # long paga si tasa>0

        bruto = side * (xpx - ep) * qty
        pnl = bruto - fee_ent - fee_sal - fund
        if motivo == 6 and pnl < -margen:
            pnl = -margen                  # margen aislado: no se puede perder más que el margen

        ok[k] = 1
        e_i[k] = e
        x_i[k] = xi
        lado_o[k] = s_lado[k]
        e_px[k] = ep
        x_px[k] = xpx
        qty_o[k] = qty
        fee_o[k] = fee_ent + fee_sal
        fund_o[k] = fund
        pnl_o[k] = pnl
        risk_o[k] = sd / ep * nocional
        mot_o[k] = motivo
    return ok, e_i, x_i, lado_o, e_px, x_px, qty_o, fee_o, fund_o, pnl_o, risk_o, mot_o


def simular_moneda(d: DatosMoneda, s: Senales, cfg: Config, sal: Salida, latencia_velas: int = 0) -> pd.DataFrame:
    """Simula TODAS las señales de una moneda de forma independiente (la cartera se aplica después)."""
    if len(s) == 0:
        return _vacio()
    fexit = s.salida_idx if s.salida_idx is not None else np.full(len(s), -1, np.int64)
    obj_frac = cfg.objetivo_frac_precio(sal.objetivo_pct_margen) if sal.objetivo_pct_margen > 0 else 0.0
    r = _simular(d.o.astype(np.float64), d.h.astype(np.float64), d.l.astype(np.float64), d.c.astype(np.float64),
                 d.qv.astype(np.float64), d.slip(cfg), d.f_idx(), d.f_tasa(),
                 s.idx.astype(np.int64), s.lado.astype(np.int8), s.dist_stop.astype(np.float64),
                 fexit.astype(np.int64),
                 int(latencia_velas), cfg.nocional_usd, cfg.apalancamiento, cfg.mantenimiento_margen_frac,
                 cfg.fee_taker, cfg.fee_maker,
                 float(sal.objetivo_R), float(obj_frac), bool(cfg.objetivo_es_maker), float(sal.break_even_R),
                 float(sal.break_even_colchon_frac), float(sal.trailing_R),
                 int(sal.max_velas_1m), int(sal.sin_avance_velas), float(sal.sin_avance_R),
                 float(d.step), float(d.min_notional))
    ok, e_i, x_i, lado, e_px, x_px, qty, fee, fund, pnl, risk, mot = r
    m = ok == 1
    if not m.any():
        return _vacio()
    t0 = d.t0_ms
    df = pd.DataFrame({
        "simbolo": d.simbolo,
        "entrada_ts": t0 + e_i[m] * MS_MIN,
        "salida_ts": t0 + x_i[m] * MS_MIN + MS_MIN,   # la salida ocurre dentro de la vela: cierre de la vela como cota
        "lado": lado[m].astype(int),
        "entrada_px": e_px[m], "salida_px": x_px[m], "qty": qty[m],
        "comisiones": fee[m], "funding": fund[m], "pnl": pnl[m], "riesgo_usd": risk[m],
        "motivo": mot[m].astype(int),
    })
    df["R"] = df["pnl"] / df["riesgo_usd"]
    return df


def _vacio() -> pd.DataFrame:
    cols = ["simbolo", "entrada_ts", "salida_ts", "lado", "entrada_px", "salida_px", "qty", "comisiones",
            "funding", "pnl", "riesgo_usd", "motivo", "R"]
    return pd.DataFrame({c: pd.Series(dtype="float64" if c not in ("simbolo",) else "object") for c in cols})


def filtro_cartera(trades: pd.DataFrame, max_pos: int) -> tuple[pd.DataFrame, int]:
    """Aplica 'máximo de posiciones simultáneas' y 'una posición por moneda' por orden cronológico.

    Devuelve (operaciones aceptadas, nº de señales rechazadas por falta de hueco).
    La prioridad es la hora de entrada; a igualdad, orden alfabético (determinista, sin preferir monedas).
    """
    if trades.empty:
        return trades, 0
    t = trades.sort_values(["entrada_ts", "simbolo"], kind="mergesort").reset_index(drop=True)
    abiertas: list[tuple[int, str]] = []   # heap (salida_ts, simbolo)
    en_moneda: dict[str, int] = {}
    acepta = np.zeros(len(t), bool)
    ent = t["entrada_ts"].to_numpy()
    sal = t["salida_ts"].to_numpy()
    sim = t["simbolo"].to_numpy()
    rech = 0
    for i in range(len(t)):
        while abiertas and abiertas[0][0] <= ent[i]:
            ts_, s_ = heapq.heappop(abiertas)
            if en_moneda.get(s_) == ts_:
                del en_moneda[s_]
        if len(abiertas) >= max_pos or sim[i] in en_moneda:
            rech += 1
            continue
        acepta[i] = True
        heapq.heappush(abiertas, (int(sal[i]), sim[i]))
        en_moneda[sim[i]] = int(sal[i])
    return t[acepta].reset_index(drop=True), rech


def simular_universo(datos: Dict[str, DatosMoneda], senales: Dict[str, Senales], cfg: Config, sal: Salida,
                     latencia_velas: int = 0, aplicar_cartera: bool = True) -> tuple[pd.DataFrame, int]:
    partes = []
    for sym, s in senales.items():
        if sym in datos and len(s):
            partes.append(simular_moneda(datos[sym], s, cfg, sal, latencia_velas))
    if not partes:
        return _vacio(), 0
    t = pd.concat(partes, ignore_index=True)
    if aplicar_cartera:
        return filtro_cartera(t, cfg.max_posiciones_simultaneas)
    return t.sort_values("entrada_ts").reset_index(drop=True), 0
