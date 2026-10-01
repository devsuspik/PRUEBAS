"""Régimen actual de BTC y qué estrategias del PLAYBOOK tocan hoy. Uso: python -m cazador.regimen_hoy
Descarga BTCUSDT 1d de data.binance.vision (mensuales + diarios del mes en curso). Régimen = regla causal de regimenes.etiquetas_macro
(se aplica al día SIGUIENTE a la etiqueta). Los datos de apoyo están en MANUAL / PLAYBOOK_POR_MOMENTO.md."""
import pandas as pd

from . import datos as D
from . import regimenes as RG

PLAN = {
    RG.ALCISTA: ["1) CORTO de listados nuevos: SÍ (+5,97 $/op sobre 200 $, 4/4 periodos)",
                 "2) CARRY de funding (largo spot + corto perp, 1x): SÍ cuando el funding medio (3 marcas) >= 0,03 % por 8 h",
                 "3) MOMENTUM semanal 14 d (largo top-5 / corto bottom-5): SÍ (+1,67 %/semana, 4/4 periodos)"],
    RG.EUFORIA: ["1) CARRY de funding: SÍ (es donde más rinde: funding alto)", "2) MOMENTUM semanal 14 d: SÍ (poca muestra, n=20)",
                 "3) CORTO de listados nuevos: NO (perdió en 2 de 3 periodos)"],
    RG.LAT_TRANQ: ["1) CORTO de listados nuevos: SÍ (+5,30 $/op, 2/3 periodos)", "2) CARRY de funding: SÍ (si hay funding >= 0,03 %)", "3) MOMENTUM: NO (≈ 0)"],
    RG.LAT_VOL: ["1) CORTO de listados nuevos: NO (−4,91 $/op, perdió en los 2 periodos con datos)", "2) CARRY de funding: SÍ (positivo en el periodo con datos)", "3) MOMENTUM: NO"],
    RG.BAJISTA: ["1) CARRY de funding: inconcluso (pocas posiciones y signo mixto)", "2) Listados nuevos: inconcluso (+1,72 $, IC cruza 0) -> mejor no", "3) MOMENTUM: NO (−0,16 %)"],
    RG.CAPIT: ["NO OPERAR: solo 7 días de datos en 6 años; sin evidencia"],
}


def btc_diario(desde="2022-01-01") -> pd.DataFrame:
    hoy = pd.Timestamp.now("UTC").tz_localize(None).normalize()
    partes = []
    for m in D.meses_entre(pd.Timestamp(desde), hoy):
        fin_mes = pd.Period(m, "M").end_time.normalize()
        r = D.http_get(f"{D.BASE}/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{m}.zip") if fin_mes < hoy else None
        if r is not None:
            partes.append(D.leer_klines_zip(r.content))
        else:                                   # mes en curso o mensual aún no publicado: ficheros diarios
            for dia in pd.date_range(pd.Period(m, "M").start_time, hoy - pd.Timedelta(days=1)):
                r = D.http_get(f"{D.BASE}/daily/klines/BTCUSDT/1d/BTCUSDT-1d-{dia:%Y-%m-%d}.zip")
                if r is not None:
                    partes.append(D.leer_klines_zip(r.content))
    g = pd.concat(partes, ignore_index=True).sort_values("t").drop_duplicates("t")
    g.index = pd.to_datetime(g["t"], unit="ms").dt.floor("D")
    return g


def main():
    g = btc_diario()
    e = RG.etiquetas_macro(g)
    ult = e.dropna(subset=["regimen"]).iloc[-1]
    reg = ult["regimen"]
    dias = int((e["regimen"] == reg).iloc[::-1].cumprod().sum())
    print(f"BTC {e.index[-1].date()}: cierre {ult['c']:.0f} | SMA50 {ult['sma50']:.0f} | SMA200 {ult['sma200']:.0f} | pendiente SMA200 (20 d) {ult['pend200'] * 100:+.1f} %")
    print(f"RÉGIMEN {RG.ICONOS[reg]} {reg} (lleva {dias} días). Rige para las entradas de HOY ({(e.index[-1] + pd.Timedelta(days=1)).date()}).")
    for linea in PLAN[reg]:
        print("  -", linea)


if __name__ == "__main__":
    main()
