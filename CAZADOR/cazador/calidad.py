"""Informe de calidad de datos (§2): huecos, duplicados, velas imposibles, saltos tipo redenominación, minutos sin volumen.
Solo mira el periodo de búsqueda + calentamiento (el holdout no se toca)."""
from __future__ import annotations

import json

import pandas as pd

from . import cargar, datos as D
from .descarga import CACHE, PERIODO, RAIZ
from .periodo import RES, UNIV


def main() -> None:
    sel = json.loads(UNIV.read_text())["seleccion"]
    filas = []
    fin = int(pd.Timestamp(PERIODO["busqueda_fin"]).timestamp() * 1000) + 86_400_000
    for s in sel:
        df = pd.read_parquet(CACHE / "klines" / "1m" / f"{s}.parquet")
        df = df[df["t"] < fin].astype({"qv": "float64", "tb_qv": "float64", "v": "float64", "tb_v": "float64"})
        if df.empty:
            filas.append({"simbolo": s, "n": 0})
            continue
        g, rep = D.a_rejilla_1m(df)
        f = pd.read_parquet(CACHE / "funding" / f"{s}.parquet")
        rep.update(simbolo=s, desde=str(pd.to_datetime(df.t.min(), unit="ms").date()),
                   hasta=str(pd.to_datetime(df.t.max(), unit="ms").date()), marcas_funding=int(len(f)),
                   intervalos_funding_h=",".join(str(x) for x in sorted(f.horas.dropna().unique())) if len(f) else "")
        filas.append(rep)
    q = pd.DataFrame(filas).set_index("simbolo")
    q.to_csv(RES / "calidad_datos.csv")
    tot = q[["minutos_faltantes", "duplicados", "velas_imposibles", "saltos_mayores_40pct_1m"]].sum()
    print(q[["desde", "n", "minutos_faltantes", "racha_hueco_max_min", "duplicados", "velas_imposibles",
             "saltos_mayores_40pct_1m", "minutos_sin_volumen", "marcas_funding", "intervalos_funding_h"]].to_string())
    print("\nTOTALES:", tot.to_dict())


if __name__ == "__main__":
    RES.mkdir(exist_ok=True)
    main()
