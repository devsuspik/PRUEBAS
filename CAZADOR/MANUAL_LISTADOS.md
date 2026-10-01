# Manual del corto de listados nuevos — qué ha funcionado con histórico real y cuándo

> Esto describe lo que **ha pasado** en datos históricos reales simulados a 1 minuto con costes reales. No garantiza beneficios futuros: la ventaja ha ido bajando con los años.

## 1. La regla (exacta)
Para cada perpetuo USDT-M **nuevo** de Binance (no acciones/materias primas/stablecoins):
- **Abrir CORTO** a las **00:00 UTC del día d0+2** (d0 = día UTC en que se lista). Nocional 200 $ (20 $ de margen × 10x).
- **Stop +8 %** sobre la entrada (stops mayores no caben con 10x: liquidación al +9,5 %).
- **Objetivo −40 %**. **Salida a los 7 días** si no ha tocado ninguno.
- **Sin límite de posiciones**: nunca hubo más de 2–8 abiertas a la vez (media ≈ 1), porque los listados rara vez coinciden.
- Costes simulados: comisión taker 0,05 % por lado, deslizamiento ≥ 0,02 % + impacto, funding real, liquidación.

## 2. Cuándo funciona y cuándo no (régimen de BTC el día de la entrada)
Régimen causal: 🟢 ALCISTA = cierre diario de BTC > SMA200, SMA50 > SMA200 y SMA200 con pendiente positiva (etiqueta del día anterior, histéresis de 3 días).

| Régimen | Operaciones | Aciertos | Expectativa | IC 90 % | P(expectativa > 0) | Periodos positivos |
|---|---|---|---|---|---|---|
| 🟢 **ALCISTA** | 317 | 33 % | **+5,97 $** | [+2,9, +9,3] | **100 %** | **4/4** |
| ⚪ LATERAL TRANQUILO | 90 | 42 % | **+5,30 $** | [+0,3, +10,6] | 96 % | 2/3 |
| 🔴 BAJISTA | 76 | 29 % | +1,72 $ | [−4,1, +7,7] | 67 % | 1/2 |
| 🚀 EUFORIA | 50 | 30 % | −1,15 $ | [−6,6, +4,8] | 36 % | 1/3 |
| 🟠 **LATERAL VOLÁTIL** | 75 | 19 % | **−4,91 $** | [−9,5, +0,1] | **5 %** | **0/2** |

**Lectura práctica:** operar en 🟢 y ⚪; **no operar en 🟠** (perdió en los dos periodos donde apareció); 🔴 y 🚀 inconcluso (poca muestra). *Esta selección de regímenes es descriptiva y posterior a ver los datos; en el protocolo pre-registrado el filtro de régimen no pasó el criterio (mejoraba 2 de 4 periodos). Úsalo como guía, no como prueba.*

**Régimen HOY (29-sep-2026): 🟢 ALCISTA** (BTC 83.624 $ > SMA50 76.861 $ > SMA200 71.204 $; pendiente SMA200 a 20 días +1,8 %).

## 3. Qué habría pasado en una cuenta real (sin límite de posiciones)
| Periodo | Mercado | Ops | Aciertos | Beneficio | Posiciones máx. a la vez | Peor caída | Capital recomendado* |
|---|---|---|---|---|---|---|---|
| feb–jul 2020 | subida | 9 | 67 % | +140 $ | 3 | 26 $ | ~90 $ |
| sep 2020–may 2021 | alcista | 56 | 39 % | +409 $ | 7 | 316 $ | ~460 $ |
| jul 2021–dic 2022 | desplome | 48 | 38 % | +342 $ | 2 | 114 $ | ~150 $ |
| 2023–jul 2024 | recuperación | 134 | 40 % | +543 $ | 4 | 216 $ | ~300 $ |
| ago 2024–jul 2026 | bajista alts | 370 | 28 % | +778 $ | 8 | 528 $ | ~690 $ |

\*margen en uso en el pico + peor caída histórica. **Con 100 $ de capital la cuenta se habría quemado en el periodo reciente** (racha de 26 pérdidas seguidas); el orden de magnitud realista es **600–1.200 $** de capital para operar esto con 20 $ de margen por posición.

**Solo en 🟢/⚪** (misma regla): reciente 231 ops **+1.423 $**, 80 % de los meses con operaciones en positivo, peor caída 528 $; VAL2 117 ops +386 $; VAL0 42 ops +439 $; VAL1 17 ops +119 $.

## 4. Probabilidades (remuestreo de las operaciones reales)
Probabilidad de **terminar en beneficio** tras N operaciones:

| Condición | N = 20 | N = 60 | N = 100 |
|---|---|---|---|
| Todas las operaciones | 67 % | 80 % | 87 % |
| Solo 🟢 ALCISTA | 77 % | **91 %** | **96 %** |
| Evitando 🟠 y 🚀 | 76 % | 89 % | 95 % |

Al ritmo reciente (~15 listados/mes; ~13 al mes solo en 🟢/⚪) 60 operaciones son ≈ 4–5 meses. Supone operaciones independientes y un régimen similar al histórico.

## 5. Estabilidad con costes y retrasos (periodo reciente, 1 m)
Costes ×1,5: +1,92 $/op · ×2: +1,27 $/op · ×3: +0,51 $/op. Retraso de 2 h en la entrada: +2,25 $/op. 0 liquidaciones en 608 operaciones.

## 6. Lo que debes tener presente (honestidad)
- **La ventaja se erosiona:** 7,3 → 7,1 → 4,1 → 2,1 $/operación (de 2020-21 a 2024-26). Lo normal en un patrón conocido.
- Pocos aciertos (28–40 %) y ganancias grandes (+80 $): **las rachas de 20+ pérdidas son normales**.
- El deslizamiento real en listados recién lanzados no está medido con libro: el modelo usa 0,02 % + impacto. Con ×3 de costes aún sale positivo.
- Variante refinada (no abrir si BTC cayó > 1,2 % en 7 días ni con volumen 24 h < 31,4 M$): +3,91 $/op frente a +2,10 en reciente, pero p = 0,099 (no significativo).
- Estadísticamente: DSR 0,10 con el total de pruebas (0,59 con 162; 0,85 con 24), PBO 0,58. **Clasificación del protocolo: PROMETEDORA, no APTA.**
- **Siguiente paso real:** paper trading con `python -m cazador.paper_listados registrar|resolver|informe` (60–100 operaciones) antes de dinero real.

## 7. Segunda estrategia (más débil): momentum semanal a 14 días
Largo de las 10 monedas que más subieron en 14 días y corto de las 10 que más cayeron, rebalanceo semanal, ~400 monedas líquidas (datos diarios, 4 periodos, 297 rebalanceos): +0,60 % neto por semana (t = 1,44). **Por régimen:** 🟢 ALCISTA +1,31 % (n = 129, t = 2,0, positivo en reciente/VAL0/VAL1 y +0,20 en VAL2); resto ≈ 0 (bajista −0,16 %, lateral tranquilo −0,24 %). **Solo funciona en alcista y es débil**; sin significación suficiente para fiarse.
