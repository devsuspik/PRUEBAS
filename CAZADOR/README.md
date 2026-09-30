# CAZADOR DE VENTAJAS – futuros cripto (Binance USDT-M)

Implementación del prompt v3 "Cazador de ventajas". **Estado: Ronda 0 completada; la búsqueda NO ha empezado
porque el entorno donde se escribió no tiene acceso a datos de mercado reales.** No hay ninguna estrategia APTA,
ni PROMETEDORA, ni resultado alguno. Cualquier cifra de rentabilidad que veas en otro sitio sobre esto no sale de aquí.

## Qué hay (y está probado)

| Módulo | Contenido | Probado |
|---|---|---|
| `cazador/config.py` | §1 configuración (20 $ × 10x, comisiones, deslizamiento, objetivos % del margen…) | sí |
| `cazador/motor.py` | §4 motor: entrada tras la señal + latencia, stop antes que objetivo en la misma vela, hueco a la apertura, stops nuevos desde la vela siguiente, BE, trailing, salida sin avance, tiempo máx., funding, liquidación aislada, stepSize/minNotional, deslizamiento = mínimo + σ·√(nocional/volumen), cartera (máx. 5 posiciones, 1 por moneda) | 16 pruebas a mano, estrategia aleatoria ≈ pierde los costes, fuga de futuro desaparece con 1 vela de retraso |
| `cazador/metricas.py` | expectativa, PF, DD, rachas, Sharpe, concentración, supervivencia, **DSR**, **PBO (CSCV)**, Monte Carlo por bloques, meseta ±20 %, criterios §8, score §9 | sí (ruido no pasa DSR/PBO; señal real sí) |
| `cazador/regimenes.py` | §3 régimen macro diario (6 etiquetas, histéresis 3 d, percentiles expansivos, uso con 1 día de retraso) + HMM filtrado causal | causalidad verificada recortando datos; **HMM sin probar** |
| `cazador/estrategias.py` | 6 familias del catálogo (EMA, Donchian, TSMOM, ORB, RSI2, Bollinger) + versión inversa + test anti-fuga | causalidad verificada; detecta una fuga puesta a propósito |
| `cazador/datos.py` | descarga data.binance.vision con reintentos, lectores (klines, metrics, funding, aggTrades), rejilla 1 m, informe de calidad, universo sin sesgo de supervivencia, modo reducido | lectores con ficheros sintéticos; **NO probado contra Binance real** |
| `cazador/trials.py` | `trials_log.csv` de todas las pruebas (base del DSR/PBO) | sí |

## Qué NO hay todavía (declarado)

- Rondas 1–5: barrido de las 46 familias, optimización Optuna, walk-forward de 24 meses, CPCV, holdout con hash, genética, ML, carteras.
- 40 de las 46 familias del catálogo (D derivados, E microestructura, F transversales, G estacionalidad, H velas, I automáticas).
- Simulación sobre aggTrades (segundos) y entradas con orden límite / market making.
- Descarga real, calendario de regímenes sobre BTC real, matriz estrategia × régimen.
- Entregables §11.

## Por qué está parado

`data.binance.vision`, `fapi.binance.com` y otros exchanges devuelven 403 desde el entorno en la nube (política de red).
Sin datos reales no se puede medir nada, y **no se sustituyen por datos sintéticos** (los sintéticos solo validan el motor).

## Cómo continuar

```bash
pip install -r requirements.txt
python -m cazador.ronda0          # comprueba red + pruebas; escribe INFORME_RONDA0.md
python -m cazador.datos --probar  # con red real: baja 1 mes de BTCUSDT y valida lectores
python -m pytest tests -q
```
Siguiente paso real: descargar (Ronda 0, datos) → informe de calidad → calendario de regímenes → Ronda 1.
