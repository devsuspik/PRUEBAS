"""Periodos de datos. Selección con la variable de entorno CAZADOR_PERIODO:
  reciente (por defecto) : búsqueda 2024-08-01..2026-07-31 + holdout bloqueado 2026-08-01..2026-09-29
  val1                   : validación histórica 2021-07-01..2022-12-31 (euforia 2021 + desplome 2022), universo reconstruido
  val2                   : validación histórica 2023-01-01..2024-07-31 (RESERVADO: no se abre hasta congelar candidatas)
Cada periodo tiene su propia caché de datos, carpeta de resultados y UNIVERSO.json: nunca se mezclan.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOMBRE = os.environ.get("CAZADOR_PERIODO", "reciente")

PERIODOS = {
    "reciente": {
        "busqueda_ini": "2024-08-01", "busqueda_fin": "2026-07-31",
        "holdout_ini": "2026-08-01", "holdout_fin": "2026-09-29",
        "previo_universo_ini": "2024-07-01",
        "calentamiento_ini": "2023-11-01",
    },
    "val1": {
        "busqueda_ini": "2021-07-01", "busqueda_fin": "2022-12-31",
        "holdout_ini": "2023-01-01", "holdout_fin": "2023-01-31",       # ficticio: no se usa en las validaciones
        "previo_universo_ini": "2021-06-01",
        "calentamiento_ini": "2020-12-01",
    },
    "val2": {
        "busqueda_ini": "2023-01-01", "busqueda_fin": "2024-07-31",
        "holdout_ini": "2024-08-01", "holdout_fin": "2024-08-31",       # ficticio
        "previo_universo_ini": "2022-12-01",
        "calentamiento_ini": "2022-06-01",
    },
    # Los futuros de data.binance.vision empiezan en 2020-01: antes no hay nada. Se usan solo listados cuyo primer dato es >= 2020-02-15
    # (así el primer dato es de verdad el listado y no el inicio del histórico).
    "val00": {
        "busqueda_ini": "2020-02-15", "busqueda_fin": "2020-08-31",
        "holdout_ini": "2020-09-01", "holdout_fin": "2020-09-30",       # ficticio
        "previo_universo_ini": "2020-02-01",
        "calentamiento_ini": "2020-01-01",
    },
    "val0": {
        "busqueda_ini": "2020-09-15", "busqueda_fin": "2021-05-31",
        "holdout_ini": "2021-06-01", "holdout_fin": "2021-06-30",       # ficticio
        "previo_universo_ini": "2020-09-01",
        "calentamiento_ini": "2020-06-01",
    },
    # Apertura ÚNICA del holdout: 6 meses de entrenamiento (feb-jul 2026) + los 2 meses del holdout como meses de prueba del walk-forward.
    # Usa la MISMA caché y el MISMO universo que 'reciente'. Solo se ejecuta vía cazador.holdout (registra la apertura).
    "ho": {
        "busqueda_ini": "2026-02-01", "busqueda_fin": "2026-09-29",
        "holdout_ini": "2026-08-01", "holdout_fin": "2026-09-29",
        "previo_universo_ini": "2024-07-01",
        "calentamiento_ini": "2025-05-01",
    },
}
PERIODO = PERIODOS[NOMBRE]
SUF = "" if NOMBRE == "reciente" else f"_{NOMBRE}"
CACHE = RAIZ / ("datos_cache" if NOMBRE in ("reciente", "ho") else f"datos_cache{SUF}")
RES = RAIZ / f"resultados{SUF}"
UNIV = RAIZ / f"UNIVERSO{SUF}.json"
PERIODO_JSON = RAIZ / f"PERIODO{SUF}.json"
