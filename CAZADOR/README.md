# CAZADOR DE VENTAJAS – futuros cripto (Binance USDT-M)

**Estado (1-oct-2026): 0 estrategias APTAS, 1 PROMETEDORA (corto de listados nuevos), el resto rechazadas.**
Lee primero **[INFORME_FINAL.md](INFORME_FINAL.md)**. No es asesoramiento financiero.

| Fichero | Para qué |
|---|---|
| `INFORME_FINAL.md` | Resumen ejecutivo, matriz régimen, top, ficha de la PROMETEDORA, cementerio, veredicto por marco, plan de paper trading, lagunas |
| `PREREGISTRO.md`, `CELDAS_CONGELADAS.json`, `CANDIDATAS_HOLDOUT.json`, `HOLDOUT_HASH.json`, `HOLDOUT_LOG.json` | Congelación y pre-registro (verificables en el historial de git) |
| `resultados_final/` | Operaciones de la PROMETEDORA (CSV), top 20 de la Ronda 1, tabla de 24 celdas en 3 periodos |
| `trials_log.csv` | Pruebas registradas (Ronda 1, ML, carry) |
| `cazador/` | Código (motor, datos, estrategias, validación) · `tests/` 66 pruebas |
| `CHECKPOINT.md` | Estado y siguiente ronda |

Datos: `data.binance.vision` (la API `fapi` da 451 por región). Modo reducido de 50 monedas por periodo. `datos_cache*/` no se versiona.
Reproducir: ver §13 del informe.
