# CAZADOR DE VENTAJAS — Informe final (1-oct-2026)

> Esto es investigación, no asesoramiento financiero. Nada de lo siguiente pasa a dinero real sin paper trading previo.

## 1. Resumen ejecutivo (1 página)

**Objetivo del prompt: ≥ 3 estrategias APTAS. Resultado: 0 APTAS, 1 PROMETEDORA, el resto RECHAZADAS.** No se rebajó ningún criterio para completar el número.

| | |
|---|---|
| 🟢 APTAS | **0** |
| 🟡 PROMETEDORAS | **1** — *corto de listados nuevos* (ver §5) |
| ❌ RECHAZADAS | todo lo demás (≈ 47.000 combinaciones evaluadas) |

**Lo que se hizo:** datos reales de Binance USDT-M (solo `data.binance.vision`; la API `fapi` devuelve 451 por región), motor 1 m con comisiones, deslizamiento, funding y liquidación a 10x (66 pruebas automáticas de motor, datos, estrategias y carry), 5 periodos de datos separados, catálogo de ~46 familias (A–H más carry, transversales y ML), 24 celdas congeladas validadas en 2 periodos históricos nunca vistos y un holdout abierto una sola vez.

**Lo que se encontró:**
1. **Antes de costes, la estrategia media no tiene ventaja** (−0,07 $/operación bruto; el 28 % de las 11.238 pruebas de la Ronda 1 con n ≥ 150 tiene margen bruto > 0 y solo el 11 % neto > 0). Los costes totales rondan 0,3 $ por operación de 200 $.
2. **Ninguna de las 11.784 pruebas de la Ronda 1 supera el DSR** con el total de pruebas; y la selección **no persiste**: el 1 % mejor del año 1 rinde Sharpe +0,095 ese año y −0,054 el siguiente (solo el 20 % sigue en positivo).
3. **Marcos de 5–15 min: 0 % de las pruebas son netas positivas.** El mejor tramo son 4 h – 1 d, aunque la mediana bruta es negativa en todos. *Segundos: no probado* (§10).
4. **Los filtros de régimen no aportan:** mejora aparente 7/24 en el periodo reciente, 2/24 en VAL1, 9/24 en VAL2 — es ruido de selección.
5. **Pistas que parecían ventaja y se cayeron en validación:** ML (LightGBM; AUC 0,55 reproducible, pero el beneficio es un solo mes por periodo y con 5 posiciones simultáneas pierde), estacionalidad por día de la semana (−221 $ en el holdout), carry de funding (año 2 ≈ 0), `inside_bar`/`max_n_dias` (fallan en VAL2), `donchian` 1 d (−138 $ en el holdout).
6. **Única candidata viva — corto de listados nuevos:** gana neta en los **4 periodos** (2020-21 alcista, 2021-22 bajista, 2023-24, 2024-26), con costes ×3, 0 liquidaciones y 26/26 vecinos de parámetros positivos. Pero **su ventaja decrece** (7,3 → 7,1 → 4,1 → 2,1 $/operación), en el periodo reciente es débil (PF 1,18, t = 1,2), el DSR no llega (0,10 con el total de pruebas) y el PBO es 0,58.

**Qué esperar de la candidata con 20 $ de margen y 10x** (periodo reciente, ~15 listados/mes): ≈ +2 $ por operación en esperanza, 28 % de aciertos, ganancias de hasta +80 $ y pérdidas de −16 a −28 $. Drawdown p95 histórico agrupado ≈ 1.013 $; peor racha p95 ≈ 28 pérdidas seguidas. **No es una estrategia para una cuenta de 100 $ de margen.**

## 2. Qué se hizo (resumen técnico)

| Pieza | Estado |
|---|---|
| Descarga Binance (`data.binance.vision`): klines 1 d/1 m/1 h spot, funding, metrics (OI, L/S) | ✅ verificado con ficheros reales. `fapi`/exchangeInfo **no disponible** (451): tick/step/minNotional **no aplicados** |
| Universo sin sesgo de supervivencia (retiradas incluidas), exclusión de no-cripto por cociente fin de semana + lista manual | ✅ |
| Modo de datos | **REDUCIDO**: 50 monedas por periodo (top 15 + 35 al azar, semilla fija). Disco/RAM no daban para 600+ |
| Motor 1 m (stop antes que objetivo, hueco a la apertura, funding, liquidación, cartera 5 pos.) | ✅ 66 pruebas, aleatoria ≈ pierde costes, fuga detectada con 1 vela de retraso |
| Régimen macro (6 etiquetas, causal, histéresis 3 d) | ✅ — 💥 CAPITULACIÓN **no ocurrió** en el periodo reciente; HMM implementado pero **no usado** |
| Catálogo | A (ema, donchian, tsmom, supertrend, adx, máx. N días), B (ORB, squeeze, NR7, máx/mín ayer), C (RSI2, Bollinger, VWAP, barrida, sobreextensión, z-score), D (funding extremo, **carry**), E\* (flujo taker 1 m, sin aggTrades), F (momentum/reversión transversal 1 h y **factores diarios 400–700 monedas**), G (hora/día, **listados nuevos**), H (engulfing, pin bar, inside bar), I (**LightGBM triple barrera + ablación**) |
| Periodos | Reciente 2024-08→2026-07 · Holdout 2026-08→09 (bloqueado por hash antes de buscar) · VAL1 2021-07→2022-12 · VAL2 2023-01→2024-07 · VAL0 2020-09→2021-05 |

**Disciplina anti-trampa verificable en git:** hash del holdout fijado a las 23:09 UTC del 30-sep antes de calcular nada; 24 celdas congeladas (`CELDAS_CONGELADAS.json` con hashes de código) antes de ver VAL1/VAL2; `PREREGISTRO.md` (criterios y adendas) subido antes de cada validación; apertura del holdout registrada en `HOLDOUT_LOG.json`.

## 3. Matriz estrategia × régimen (periodo reciente, EN MUESTRA, $ / nº operaciones)

Días por régimen: 🟢 273 · 🔴 259 · ⚪ 78 · 🟠 89 · 🚀 31 · 💥 **0**. Pocos episodios (5 alcistas, 2 bajistas): régimen y época están confundidos.

| Estrategia | 🟢 ALCISTA | 🔴 BAJISTA | ⚪ LAT. TRANQ. | 🟠 LAT. VOL. | 🚀 EUFORIA |
|---|---|---|---|---|---|
| inside_bar 1d inv, obj 2R, corto | +4.850 / 285 | +482 / 191 | +312 / 85 | −667 / 97 | −283 / 34 |
| dia_semana 1h inv, t24h, corto | +4.157 / 1524 | +2.170 / 1380 | +444 / 409 | −564 / 469 | −317 / 132 |
| donchian 1d, 50 %m, corto | −206 / 287 | +1.231 / 361 | +57 / 30 | +432 / 56 | — |
| zscore_rev 4h inv, corto | +989 / 719 | +1.176 / 570 | −125 / 171 | +163 / 84 | −143 / 30 |
| max_n_dias 4h, corto | +183 / 77 | +140 / 80 | +5 / 4 | +108 / 19 | — |

Es **en muestra**: ninguna de estas filas sobrevivió a VAL2/holdout (ver §6). **Corto de listados nuevos, 4 periodos agrupados (1 m):**

| Régimen BTC en la entrada | n | $/op | PF | por periodo (reciente / VAL0 / VAL1 / VAL2) |
|---|---|---|---|---|
| 🟢 ALCISTA | 317 | **+5,97** | 1,54 | +4,7 / +10,5 / +12,1 / +6,2 |
| ⚪ LATERAL TRANQUILO | 90 | +5,30 | 1,55 | +12,5 / — / +4,9 / −3,5 |
| 🔴 BAJISTA | 76 | +1,72 | 1,15 | −2,3 / — / +12,1 / — |
| 🚀 EUFORIA | 50 | −1,15 | 0,89 | −9,7 / −2,2 / — / +9,3 |
| 🟠 LATERAL VOLÁTIL | 75 | **−4,91** | 0,63 | −5,2 / — / −3,2 / — |

Leer con cautela: son subdivisiones de 5–90 operaciones, y la regla "operar solo en 🟢/⚪" sería una selección **post hoc** (no está pre-registrada).

## 4. Top de la Ronda 1 y su destino (periodo reciente, en muestra)

Detalle completo en `resultados_final/top20_ronda1_en_muestra.csv`. Los mejores por Sharpe diario (DSR = 0,0 en todos con N = 11.784; "NO CALCULADO": drawdown y ganancia/pérdida media, que la Ronda 1 agrega sin guardar la lista de operaciones):

| Prueba | n | aciertos | $/op | PF | meses + | Sharpe/día | Destino |
|---|---|---|---|---|---|---|---|
| inside_bar 1d inv, obj 2R, corto | 692 | 40 % | +6,78 | 1,59 | 54 % | 0,095 | VAL2: **−1.508 $ (PF 0,29)** ❌ |
| max_n_dias 4h, 30 %m, corto | 180 | 87 % | +2,42 | 1,98 | 67 % | 0,094 | VAL2: −291 $ ❌ |
| dia_semana 1h inv, t24h, corto | 3.914 | 55 % | +1,51 | 1,47 | 75 % | 0,074 | holdout **−221 $** ❌ |
| bollinger_rev 4h inv, 30 %m, corto | 260 | 77 % | +1,64 | 1,61 | 71 % | 0,072 | celda congelada (no invertida): −756 / +811 / +240 $ (reciente/VAL1/VAL2) ❌ |
| donchian 1d, 50 %m, corto | 734 | 74 % | +2,06 | 1,41 | 54 % | 0,065 | holdout **−138 $** ❌ |

## 5. Ficha de la única PROMETEDORA: **corto de listados nuevos**

**Reglas exactas (pre-registradas antes de ver VAL0):**
```
para cada perpetuo USDT-M NUEVO (primer día de datos d0, no TradFi, sin filtro de volumen de universo):
  a las 00:00 UTC de d0+2 (cierre del día d0+1):  ABRIR CORTO, nocional 200 $ (20 $ × 10x)
  stop      = +8 % sobre la entrada   (menor que la liquidación de 9,5 %; stops mayores NO son factibles a 10x)
  objetivo  = −40 % (5R)              (orden contra el mercado + deslizamiento: conservador)
  salida    = a los 7 días si no ha tocado ninguno
  máx. 5 posiciones simultáneas; una por moneda
```
**Resultados con el motor a 1 minuto** (costes taker 0,05 %, deslizamiento ≥ 0,02 % + impacto, funding, liquidación):

| Periodo | Mercado | n | Aciertos | $/op | PF | Total | ×1,5 | ×2 | ×3 | Latencia +2 h |
|---|---|---|---|---|---|---|---|---|---|---|
| VAL0 2020-09→2021-05 | alcista | 56 | 39 % | +7,31 | 1,77 | +409 | +7,09 | +6,85 | +5,80 | +4,41 |
| VAL1 2021-07→2022-12 | desplome | 48 | 38 % | +7,14 | 1,75 | +343 | +6,95 | +6,76 | +6,26 | +8,03 |
| VAL2 2023-01→2024-07 | recuperación | 134 | 40 % | +4,06 | 1,40 | +544 | +3,69 | +3,48 | +1,89 | +2,55 |
| Reciente 2024-08→2026-07 | bajista alts | 370 | 28 % | +2,10 | 1,18 | +778 | +1,92 | +1,27 | +0,51 | +2,25 |
| **Agrupado** | | **608** | 32 % | **+3,41** | **1,31** | **+2.074** | | | | |

Con la cartera de 5 posiciones apenas se rechazan señales (2 y 6 en VAL0 y reciente). **0 liquidaciones** en las 608 operaciones; peor operación ≈ −28 $.

**Criterios §8:**

| Criterio | Resultado | |
|---|---|---|
| Operaciones ≥ 150 | 608 agrupadas (56/48/134/370 por periodo) | ✅ |
| Expectativa con costes ×1,5 > 0 | positiva en los 4 periodos | ✅ |
| PF ≥ 1,25 | 1,31 agrupado; **reciente 1,18** | ✅ agrupado / ❌ reciente |
| Meses positivos ≥ 60 % | 61 % (67 meses con operaciones) | ✅ justo |
| Meseta ±20 % | **26/26** vecinos > 0 (mín. +1,37 $, mediana +3,21 $) | ✅ |
| Sin mejor semana / sin 5 mejores | +1.858 $ / +1.664 $ (en VAL0 y VAL1 por separado, sin 5 mejores: +35 $ / −33 $) | ✅ agrupado |
| Moneda con > 25 % del beneficio | máx. 0,9 % (608 monedas) | ✅ |
| **DSR ≥ 0,90** | **0,10** con N = 23.466; 0,59 con N = 162; 0,85 con N = 24; 0,999 con N = 1 | ❌ |
| **PBO ≤ 0,35** | **0,576** (el mejor parámetro en muestra no es mejor fuera: la ventaja es *el evento*, no un parámetro) | ❌ |
| Holdout | **no evaluado**: ≈ 10 eventos en el periodo y el periodo ya se abrió una vez | — |

**Monte Carlo (10.000 remuestreos por bloques de 10, 608 operaciones):** beneficio p5/p50/p95 = +366 / +1.939 / +3.542 $; drawdown p5/p50/p95 = 329 / 549 / 1.013 $; peor racha de pérdidas p95 = 28.

**Por qué PROMETEDORA y no APTA:** falla DSR y PBO, y la ventaja se está **erosionando** con el tiempo — lo esperable de un patrón conocido. **Riesgos**: cola de pérdidas largas (aciertos 28–40 %), estimación de deslizamiento en listados recién lanzados (no medido con libro real), funding no verificado como favorable en todos los eventos, datos de barras 1 m pero sin libro/aggTrades.

**Para no engañarse:** la hipótesis nació del estudio de eventos del periodo reciente; VAL1/VAL2/VAL0 son su confirmación (VAL0 es el único dato realmente nuevo para una regla congelada antes: 6/6 variantes positivas, pero con ≈ 59 eventos y t = 1,7).

## 6. Cementerio — qué estrategias famosas NO funcionan aquí con costes reales

Mediana de expectativa neta por operación y % de variantes netas positivas (Ronda 1, pruebas con n ≥ mínimo, 50 monedas, periodo reciente):

| Familia | $/op mediana | % netas > 0 | Comentario |
|---|---|---|---|
| ORB por sesión (5–30 min) | −0,37 | 0,4 % | los costes (0,2 $) superan el movimiento |
| VWAP desviación | −0,37 | 0,8 % | idem |
| Flujo taker 1 m–1 h | −0,43 | 0,8 % | el peor (Sharpe −0,41) |
| Bollinger (reversión) | −0,38 | 7,8 % | solo sobrevive invertida, corta, 4 h, en muestra |
| RSI(2) Connors | −0,39 | 9,1 % | |
| Cruces de EMA (9/21, 20/50, 50/200) | −0,34 | 15,5 % | ninguna celda positiva en 3 periodos |
| Patrones de velas (engulfing, pin bar, inside bar) | −0,36…−0,40 | 12–14 % | `inside_bar` 1 d inv: +1.269 $ en VAL1 y −1.508 $ en VAL2 |
| Estacionalidad por hora | −0,37 | 0 % | −11 k$ en walk-forward |
| Momentum transversal 1 h (long top-k / short bottom-k) | −0,37 | 22 % | bruto positivo (+0,19 $) pero costes 0,2 $ |
| Carry funding long spot + short perp **a 10x** | −0,76 | 0 % | las liquidaciones lo destruyen; a 3x año 1 +45 $, año 2 +5 $ |
| Funding extremo (contrario) | −0,38 | 11,6 % | bruto ≈ 0 |

## 7. Veredicto por marco temporal (para un minorista con estas comisiones)

| Marco | Pruebas | $/op neta mediana | $/op bruta mediana | % netas > 0 | % con PF ≥ 1,25 |
|---|---|---|---|---|---|
| 5 min | 990 | −0,38 | −0,10 | **0 %** | 0 % |
| 15 min | 2.376 | −0,38 | −0,10 | **0 %** | 0 % |
| 30 min | 396 | −0,37 | −0,09 | 1,3 % | 0 % |
| 1 h | 3.470 | −0,38 | −0,09 | 6,4 % | 0,5 % |
| 4 h | 2.486 | −0,37 | −0,04 | 22,8 % | 0,9 % |
| 1 d | 1.540 | −0,53 | −0,05 | 27,0 % | 3,1 % |
| **Segundos (1–30 s)** | **NO CALCULADO** | | | | necesita simulación sobre aggTrades (no implementada) |

Conclusión: por debajo de 1 h no hay ventaja con comisiones de minorista; entre 4 h y 1 d hay *menos pérdida*, no ganancia.

## 8. Mejor cartera combinada

**No existe.** Una cartera exige estrategias APTAS o PROMETEDORAS poco correlacionadas y hay **una** PROMETEDORA. La combinación del corto de listados con el momentum transversal diario (mom14) queda **sin evaluar**: mom14 semanal da +0,39 / +0,34 / +0,63 % netos por rebalanceo en los 3 periodos pero con t = 0,56–0,73 y +1,5 % (t = 0,45, 8 semanas) en el holdout: no hay base estadística para combinarlo.

## 9. Plan de paper trading (4–6 semanas) y criterios de parada

**Solo para el corto de listados nuevos**, y como investigación (no esperando beneficio): registrar cada listado nuevo de Binance USDT-M, abrir en papel la regla exacta del §5, anotar entrada/stop/salida/costes reales de comisión y el deslizamiento observado en el libro.
- Ritmo esperado ≈ 15 listados/mes → 4–6 semanas dan **~15–20 operaciones: insuficiente para concluir nada**. Se necesitan ≥ 60–100 (4–7 meses).
- **Parada** (Monte Carlo del régimen reciente, bloques de 10): beneficio acumulado en papel tras 30 operaciones **< −283 $**, tras 45 **< −321 $**, tras 60 **< −353 $** (p5), o 2 liquidaciones, o deslizamiento medio observado > 3× el del modelo, o expectativa en vivo < 0 con ≥ 60 operaciones.
- Probabilidad de acabar en negativo tras 60 operaciones **aun siendo la ventaja real**: 34 %.

## 10. Lo que NO se hizo / NO CALCULADO (sin maquillar)

- **Segundos y microestructura** (aggTrades, bookTicker, absorción, lead-lag, market making con órdenes límite y selección adversa): **no implementado**. Es la mayor laguna.
- **Universo**: 50 monedas por periodo (modo reducido), no 600+. Los factores diarios sí usan 400–700 monedas.
- **tick/step/minNotional**: no aplicados (sin `exchangeInfo`).
- **Datos externos**: calendario macro (CPI/FOMC), liquidaciones reales, dominancia/basis spot-perp como señal: no usados.
- **Segmentos y variantes**: sin segmentación por sector/antigüedad/beta; ensembles y meta-etiquetado solo esbozados (el ML sin meta-etiquetado fue rechazado).
- **Funding de los listados nuevos**: incluido en el motor (valores reales de los ficheros) pero **no analizado como señal ni como riesgo**.
- **`trials_log.csv`** itemiza R1/ML/carry (≈ 11.7 k filas). Las ≈ 35 k combinaciones de la Ronda 2 (3 periodos) **se contaron** para el DSR pero **no se escribieron una a una**.
- **DSR del corto de listados:** depende de N; se informan 4 valores. El umbral del prompt (N total) no se cumple.
- **HMM de régimen**: implementado (`regimenes.hmm_causal`), **sin ejecutar**.

## 11. Incidencias de proceso (para transparencia)

1. **Commit con 1,3 GB de caché subido por error** (`e93f142`): mi `.gitignore` solo cubría `datos_cache/`. Reescribí la rama, pero el push original ya había llegado; intenté un `force-with-lease` y **el clasificador de permisos lo denegó** (con razón: es una reescritura de historia). Lo corregí sin reescribir: un merge que deja la **punta limpia (0 ficheros de caché)**. **El historial de GitHub conserva ese commit (~1,4 GB).** Si quieres purgarlo, la orden es `git push --force-with-lease origin claude/cazador-estrategias-prompt-wni2bh` desde un historial reconstruido; no la ejecuto sin tu decisión.
2. **El holdout se evaluó una vez para 3 candidatas registradas.** Un fallo mío de diseño (mínimo de 10 rebalanceos) hizo que el factor mom14 no devolviera filas; lo reevalué **solo para esa candidata registrada** con mínimo 5 y borré sin leer el CSV que contenía otros factores. Queda declarado.
3. **El corto de listados no se evaluó en el holdout** a propósito (≈ 10 eventos, y ya se había abierto).

## 12. Qué probaría la siguiente ronda (por probabilidad de ventaja real)

1. **Listados nuevos, versión refinada y a 1 m:** entrada y stop dependientes del run-up y del funding al entrar; filtro de régimen (🟢/⚪) **pre-registrado**; universo completo de listados (descarga barata: solo ~20 días por moneda).
2. **Datos de microestructura** sobre las 10 monedas más líquidas (aggTrades/bookTicker) para por fin evaluar segundos y maker.
3. **Universo completo de 1 m** para los transversales de baja rotación (semanal/mensual, k = 2–3 por lado para cumplir 5 posiciones).
4. **Momentum de BTC/ETH con volatilidad objetivo** a horizonte de semanas (poca rotación, costes irrelevantes).
5. **Forward real**: la única validación nueva posible es esperar. El paper trading de §9 es literalmente el siguiente conjunto de datos virgen.

## 13. Reproducir

```bash
pip install -r requirements.txt
python -m pytest tests -q                                 # 66 pruebas del motor/datos/estrategias/carry
CAZADOR_PERIODO=reciente python -m cazador.descarga universo && python -m cazador.descarga reducido
python -m cazador.ronda1 && python -m cazador.ronda1 --grid-b && python -m cazador.ronda1 --grid-c && python -m cazador.carry
python -m cazador.ranking && python -m cazador.ronda2 --celdas 24
CAZADOR_PERIODO=val1|val2 ... python -m cazador.ronda2 --congeladas
python -m cazador.consistencia                            # criterio pre-registrado, 3 periodos
CAZADOR_PERIODO=<p> python -m cazador.listados && python -m cazador.listados_1m --descargar && python -m cazador.ficha_listados
```
Semillas fijas; versiones en `requirements.txt`; datos en `datos_cache*/` (no versionados, regenerables).
