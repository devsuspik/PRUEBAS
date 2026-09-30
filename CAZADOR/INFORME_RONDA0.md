# Informe Ronda 0 – 2026-09-30 22:19 UTC

- Python 3.11.15 · 4 CPU · disco libre 31 GB
- numpy 2.4.6
- pandas 3.0.6
- pyarrow 25.0.1
- scipy 1.17.1
- sklearn 1.9.1
- lightgbm 4.7.0
- optuna 5.0.0
- numba 0.68.0
- statsmodels 0.15.0
- hmmlearn 0.3.3
- matplotlib 3.11.2

## Acceso a datos

- data.binance.vision (histórico): SIN ACCESO (ProxyError: HTTPSConnectionPool(host='data.binance.vision', port=443): Max retries exceeded with url: )
- fapi.binance.com (API futuros): SIN ACCESO (ProxyError: HTTPSConnectionPool(host='fapi.binance.com', port=443): Max retries exceeded with url: /fa)

## Pruebas del motor (datos SINTÉTICOS, solo para validar el código)

```
............................................                             [100%]
44 passed in 4.09s
```

## Veredicto

**NO se puede empezar la búsqueda:** sin acceso a datos reales de mercado no hay nada que analizar. No se sustituyen por datos inventados. Habilita la red a estos hosts (o ejecuta esto en tu máquina) y repite.
