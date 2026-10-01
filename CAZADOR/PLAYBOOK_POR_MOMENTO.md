# PLAYBOOK — qué estrategia usar según el momento (solo lo que ha ganado en histórico real, en TODOS los periodos probados)

> Es lo que **ha pasado** en datos reales de Binance USDT-M (2020-2026) simulados con comisiones, deslizamiento y funding. No es una garantía: en las tres estrategias la ventaja **ha bajado con los años**.
> Sin límite de posiciones ni de operaciones por día. **Único tope: tamaño por operación** (recomendado 300–1.000 $ de nocional por posición; los resultados están en % del nocional, multiplica).

## 0. Qué régimen hay HOY
`python -m cazador.regimen_hoy` (descarga BTC diario y lo calcula). Al **29-sep-2026: 🟢 ALCISTA desde hace 20 días** (BTC 83.624 $ > SMA50 76.861 $ > SMA200 71.204 $, pendiente SMA200 +1,8 %). Regla causal: 🟢 = cierre de BTC > SMA200, SMA50 > SMA200 y SMA200 con pendiente positiva; la etiqueta de ayer rige para hoy; un régimen nuevo tiene que mantenerse 3 días.

## 1. Tabla de decisión (qué hacer en cada régimen)

| Régimen de BTC | 1) Corto de listados nuevos | 2) Carry de funding (1x) | 3) Momentum semanal 14 d (5+5) |
|---|---|---|---|
| 🟢 **ALCISTA** | **SÍ** — +5,97 $/op (4/4 periodos) | **SÍ** si funding ≥ 0,03 %/8 h | **SÍ** — +1,67 %/sem (4/4) |
| 🚀 **EUFORIA** | NO (perdió en 2 de 3 periodos) | **SÍ — donde más rinde** | SÍ (solo 20 semanas de datos) |
| ⚪ **LATERAL TRANQUILO** | **SÍ** — +5,30 $/op (2/3) | SÍ (si hay funding alto) | NO (≈ 0) |
| 🟠 **LATERAL VOLÁTIL** | **NO** — −4,91 $/op (0/2) | SÍ (positivo en el periodo con datos) | NO |
| 🔴 **BAJISTA** | NO / inconcluso (+1,72 $, IC cruza 0) | inconcluso: 7–10 posiciones por periodo y signo mixto (−0,9 / +1,7 / +0,4 $) | NO (−0,16 %) |
| 💥 **CAPITULACIÓN** | NO OPERAR (solo 7 días de datos en 6 años) | NO OPERAR | NO OPERAR |

Todo lo demás **no está en esta tabla porque no pasó la validación** (ver §6).

## 2. Estrategia A — CORTO DE LISTADOS NUEVOS
**Regla exacta:** para cada perpetuo USDT-M nuevo (no acciones/materias primas/stablecoins), a las **00:00 UTC del día d0+2** (d0 = día UTC del listado): **CORTO**, stop **+8 %** sobre la entrada, objetivo **−40 %**, salida a los **7 días**. Apalancamiento ≤ 8x (liquidación lejos del stop). Una posición por moneda.

| Periodo | Mercado | Ops | Aciertos | $/op (sobre 200 $) | PF | Total |
|---|---|---|---|---|---|---|
| feb–jul 2020 | subida | 9 | 67 % | +15,6 | 3,9 | +141 $ |
| sep 2020–may 2021 | **alcista (manía)** | 56 | 39 % | +7,3 | 1,77 | +409 $ |
| jul 2021–dic 2022 | desplome | 48 | 38 % | +7,1 | 1,75 | +343 $ |
| 2023–jul 2024 | recuperación | 134 | 40 % | +4,1 | 1,40 | +544 $ |
| ago 2024–jul 2026 | bajista alts | 370 | 28 % | +2,1 | 1,18 | +778 $ |

- **Probabilidad de acabar en beneficio** (operando solo 🟢/⚪): 77 % tras 20 ops, **91 % tras 60, 96 % tras 100**.
- **Aguanta** costes ×3 (reciente +0,51 $/op), retraso de 2 h y 0 liquidaciones en 608 operaciones. **Mejor que stops anchos:** stops 12–25 % con menos apalancamiento no mejoran (VAL2 cae a ≈ 0).
- **Variante refinada** (no abrir si BTC cayó > 1,2 % en 7 días ni con volumen 24 h < 31,4 M$): +3,91 $/op en reciente (p = 0,099, no significativo).
- **Ritmo:** ~15 listados/mes (reciente). Nunca hubo más de 2–8 posiciones abiertas a la vez.
- **Capital:** con 20 $ de margen por posición hace falta 600–1.200 $ para sobrevivir a la peor racha (26 pérdidas seguidas, −528 $).

## 3. Estrategia B — CARRY DE FUNDING (neutral al precio)
**Regla exacta:** perpetuo USDT-M con mercado spot, volumen 7 d ≥ 10 M$. Cuando la **media de las 3 últimas marcas de funding, normalizada a 8 h, ≥ 0,03 %** (≈ 33 % anual): a la hora en punto siguiente **comprar X $ de spot y vender X $ de perp (1x, margen = X $)**. **Salir** cuando esa media ≤ 0 o a los **30 días**. Descartar si |spot/perp − 1| > 2 % (mercado spot ilíquido o distinto activo). Con apalancamiento 2–3x rinde parecido pero se liquida más; **1x es lo mejor**.

| Periodo | Ops | Por posición de 200 $ | t | Aciertos | PF | Rentab. anual s/capital en posición | Posiciones abiertas de media |
|---|---|---|---|---|---|---|---|
| sep 2020–may 2021 | 385 | +8,26 $ (+2,06 %) | 19,4 | 89 % | 97 | **+41 %** | 27 |
| jul 2021–dic 2022 | 154 | +3,33 $ | 14,3 | 86 % | 40 | +14 % | 6 |
| 2023–jul 2024 | 190 | +3,71 $ | 14,4 | 90 % | 61 | +14 % | 8 |
| ago 2024–jul 2026 | 56 | +1,90 $ | 6,4 | 75 % | 10 | **+9 %** | **1,5** |

- **Costes ×2:** +7,5 / +2,6 / +2,9 / +1,1 $. **Costes ×3:** +6,7 / +1,8 / +2,2 / **+0,4 $** (reciente casi a cero). Pérdida máxima por posición: −1 a −4 $ sobre 200 $.
- **Umbral:** con funding ≥ 0,01 %/8 h **no hay ventaja** (−5 % a +4 %); 0,015–0,02 % da 8–13 %; 0,03 % rinde más pero hay menos posiciones.
- **Límite real:** la capacidad cae con los años (de ~27 posiciones abiertas a la vez en 2020-21 a ~1,5 en 2024-26). **Hoy es una fuente pequeña (~9 % anual sobre lo desplegado) y mecánica**, más útil en 🚀/🟢 cuando el funding sube.
- **Riesgos que la simulación no cubre:** riesgo de exchange, retiradas/transferencias, comisión spot real (0,10 % supuesta), y pumps de > 100 % en pocas horas (las 7–76 «liquidaciones» a 1x se compensan con la pata spot, pero hay que tener el margen disponible).

## 4. Estrategia C — MOMENTUM SEMANAL 14 DÍAS (5 largos / 5 cortos)
**Regla exacta:** cada **7 días**, entre los perpetuos con volumen 7 d ≥ 10 M$ (≈ 130–390 monedas según época), ordenar por **rendimiento de los últimos 14 días**; **largo las 5 que más subieron, corto las 5 que más cayeron**, mismo nocional por pata, mantener 7 días y repetir. **Solo en 🟢 y 🚀.** Cestas pequeñas funcionan mejor: con 20 por lado el efecto casi desaparece (+0,71 %).

| Periodo | 🟢+🚀 semanas | Neto %/semana (por pata, ya con costes 0,14 %) |
|---|---|---|
| 2020-21 | 36 | **+2,55 %** |
| 2021-22 | 9 | +3,84 % |
| 2023-24 | 61 | +0,32 % |
| 2024-26 | 43 | +2,38 % |
| **Agrupado** | **149** | **+1,67 % (t = 2,13)** |

- Con funding incluido (50 monedas): **+1,46 %/semana (t = 2,21)**; el diferencial de funding es ≈ 0 (−0,02 %/sem).
- **Es la más débil estadísticamente** (t ≈ 2) y la más volátil (desviación semanal ≈ 8–10 % por pata). Fuera de 🟢/🚀 el resultado es ≈ 0 o negativo. La pata corta sola pierde (−0,51 %): **la ventaja está en las ganadoras**.

## 5. Cómo combinar (sin límites)
- Las tres son **independientes en lo esencial**: A depende de eventos (listados), B del funding, C del cruce entre monedas. Puedes ejecutarlas a la vez.
- **Orden de confianza:** B (carry: t 6–19, pero poco volumen hoy) > A (listados: t 1,2–1,7 por periodo, 5/5 periodos) > C (momentum: t ≈ 2, solo en alcista/euforia).
- **Tamaño sugerido por posición:** 300–500 $ (A y C), 500–1.000 $ por pata (B). Escala el número de posiciones, no el tamaño.

## 6. Lo que se probó y NO se recomienda (con la razón)
| Qué | Resultado |
|---|---|
| **Cortos de velas diarias en alcista** (engulfing, pin bar, RSI2, tsmom, NR7…) | 803 variantes eran positivas en reciente + 2023-24 + 2021-22 (+2,2 $/op) y **en la manía de 2020-21 (VAL0) dan −3,2 $/op**; 49 de 458 positivas. Era beta del mercado |
| **Comprar caídas en lateral tranquilo** (tsmom invertida largos: +12 a +34 $/op en 3 periodos) | **No se pudo validar**: VAL0 no tiene días de ese régimen. Sin confirmación independiente, no se recomienda |
| Filtros de régimen sobre estrategias clásicas | 7/24 → 2/24 → 9/24 celdas ganan según periodo: ruido |
| ML (LightGBM), estacionalidad por hora/día, flujo taker, VWAP, ORB, Bollinger, cruces de EMA… | Rechazadas en validación o en el holdout (ver `INFORME_FINAL.md`) |
| Marcos de 5–15 min | 0 % de las pruebas son netas positivas: los costes (~0,3 $ por 200 $) se comen el movimiento |
| Segundos / market making | **No probado** (necesita aggTrades/libro) |

## 7. Qué NO te puedo decir
- **Que vaya a seguir funcionando.** Las tres bajan con los años (listados 7,3 → 2,1 $/op; carry 41 → 9 %; momentum 2,55 / 3,84 / 0,32 / 2,38 % por semana: irregular, con 2023-24 casi en cero).
- **El deslizamiento real** en listados recién lanzados o en monedas pequeñas: el modelo usa 0,02 % + impacto; no hay libro de órdenes histórico.
- Que las probabilidades de arriba apliquen si el mercado cambia de naturaleza (p. ej. si Binance cambiara las reglas de listados o de funding).
- **Siguiente paso:** hacer paper trading antes de dinero real: `python -m cazador.paper_listados registrar|resolver|informe` (A). Para B y C hay que vigilar el funding y el ranking semanales a mano o con tu propio script.

*Evidencia reproducible:* `resultados_final/playbook_carry_por_periodo.csv`, `playbook_carry_umbral_capacidad.csv`, `playbook_momentum_semanal.csv`, `listados_corto_trades.csv`; escáner de candidatos descartados: `playbook_candidatos.csv` (`python -m cazador.playbook_scan`).
