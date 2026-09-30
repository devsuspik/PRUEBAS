# CHECKPOINT – fin de Ronda 0 (parcial)

- Hecho: config, motor validado, métricas/estadística de validación, régimen macro, 6 familias, lectores de datos, trials_log.
- Bloqueo: sin acceso a data.binance.vision / fapi.binance.com (403 de la política de red). Ningún otro exchange accesible.
- pruebas acumuladas en trials_log.csv: 0
- APTAS 0 · PROMETEDORAS 0 · RECHAZADAS 0 (no se ha evaluado ninguna estrategia con datos reales)

## Siguiente ronda (cuando haya datos)
1. `python -m cazador.datos --probar` para confirmar formatos reales (los lectores se escribieron de memoria del formato oficial).
2. Descargar exchangeInfo + klines 1d de todos los perpetuos -> universo por fecha; 1m/1h de los elegidos; funding; metrics.
3. Informe de calidad + calendario de regímenes sobre BTC real.
4. Ronda 1: barrido del catálogo (>= 5.000 pruebas, todas a trials_log.csv), holdout de 2 meses bloqueado con hash ANTES de mirar nada.
5. Implementar el resto del catálogo (D, F y G primero: es donde el prompt sitúa más probabilidad de ventaja real).
