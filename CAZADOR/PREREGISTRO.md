# Pre-registro (escrito ANTES de abrir VAL2 y el holdout)

Fecha de este registro: ver historial de git. Nada de lo que sigue se cambia tras ver los resultados de VAL2 / holdout.

## Qué se somete a VAL2 (2023-01-01 a 2024-07-31, nunca visto)
Las 24 celdas de `CELDAS_CONGELADAS.json`, con el MISMO procedimiento de Ronda 2 (variantes de parámetros, walk-forward de 6 meses,
sin filtro de régimen como procedimiento principal; el procedimiento con filtros se informa pero se considera descartado porque
empeoró en VAL1: 2/24 frente a 7/24 sin filtro).
Universo reconstruido con el volumen de esa época (monedas retiradas incluidas), modo reducido (top 15 + 35 al azar, semilla fija).

## Criterio de éxito de una celda (se aplica tal cual)
Una celda se considera "consistente" si, SIN filtro de régimen, tiene beneficio fuera de muestra > 0 y profit factor > 1 en
los TRES periodos: reciente (2024-08..2026-07), VAL1 (2021-07..2022-12) y VAL2 (2023-01..2024-07).
Para considerarla PROMETEDORA además debe: tener >= 60 operaciones OOS por periodo, y beneficio > 0 sin su mejor semana en al menos 2 de 3 periodos.
APTA exige TODO lo de §8 del prompt (incluido DSR >= 0,90 con el total real de pruebas, PBO <= 0,35, meseta, estrés x1,5 y holdout).

## Lo que ya está descartado y por qué (no se reabre)
- Filtros de régimen: mejora aparente en el periodo reciente (7/24), empeora en VAL1 (2/24).
- ML (LightGBM, triple barrera): beneficio concentrado en 1 mes por periodo (feb-2025: +597 $ de +504 $; ene-2022: +1.797 $ de +1.289 $);
  con la cartera real de 5 posiciones pierde (-44 $ reciente, -154 $ VAL1).
- Estacionalidad horaria: -11.4 k$ OOS. Día de la semana: solo positiva restringiendo a cortos tras ver los datos (sesgo de selección).
- Carry funding: año 1 +45 $, año 2 +5 $, walk-forward -5 $.

## Holdout (2026-08-01..2026-09-29)
Se abre UNA sola vez, al final, con las celdas que superen el criterio "consistente" tras VAL2 (si hay alguna). Si ninguna lo supera
el holdout se abre igualmente UNA vez para la celda con mejor evidencia agregada, solo para documentar el resultado.

## Adenda (escrita tras VAL2 y antes de abrir el holdout)
Resultado de VAL2 y de la comparación entre periodos (ver `consistencia.py`): cumplen el criterio "consistente" las celdas 10 (donchian 1d) y
11 (dia_semana 1h invertida). La celda 11 no alcanza PF >= 1,25 en ningún periodo y a costes x1,5 queda en ~0 en VAL2.
Se registra además el factor transversal mom14 (semanal, k=10) como candidata informativa. Lista exacta en `CANDIDATAS_HOLDOUT.json`.
El holdout se abre UNA vez para esas candidatas y el resultado se informa sin ajustar nada.

## Adenda 2 (escrita ANTES de descargar VAL0 = 2020-09-15..2021-05-31): hipótesis "corto de listados nuevos"
Origen: estudio de eventos del periodo RECIENTE (mediana -10,6 % a 7 días) y exploración con barras diarias en reciente, VAL1 y VAL2
(`cazador/listados.py`): cortos +1,05/+1,18/+0,66 % netos por operación (media de las 81 combinaciones) frente a largos -2,1/-2,1/-1,6 %.
Los tres periodos quedan por tanto CONTAMINADOS para esta hipótesis; VAL0 es el primer dato nuevo.
Regla principal congelada (factible con 10x: stop 8 % < liquidación 9,5 %): CORTO al cierre del día 1 tras el primer día de cotización,
stop +8 %, objetivo -40 %, salida por tiempo a los 7 días; coste ida y vuelta 0,14 %. Variantes informativas (misma familia, k=1, stop 8 %):
objetivo {20 %, 40 %} x mantener {3, 7, 14} días (6 combinaciones, TODAS se informan).
Criterio en VAL0: neto medio por operación > 0 y PF > 1 para la regla principal, y >= 4 de las 6 variantes netas > 0. t-stat y n se informan;
con ~50-60 eventos la significación será baja y no bastará por sí sola: la regla pasaría después a simulación a 1 m con costes/slippage reales.

## Adenda 3 (escrita ANTES de calcular ninguna variable condicionante): refinamiento del corto de listados nuevos
Datos disponibles para refinar: las 608 operaciones a 1 m de la regla principal en VAL0, VAL1, VAL2 y reciente (ficheros de `resultados*/ficha_listados_trades*.parquet`).
Reparto: se ELIGE el refinamiento con VAL0+VAL1+VAL2 (238 operaciones) y se VALIDA en reciente (370 operaciones) y, aparte, en VAL00
(listados reales de 2020-02..2020-07; los futuros de data.binance.vision empiezan en 2020-01, así que antes no hay nada).
Variables condicionantes a examinar (lista CERRADA, no se añaden después): (1) run-up = precio de entrada / primer precio de cotización;
(2) funding conocido en la entrada; (3) régimen de BTC en la entrada; (4) volumen en USDT de las 24 h previas a la entrada (liquidez);
(5) horas transcurridas entre el primer trade y la entrada; (6) rendimiento de BTC en los 7 días previos.
Método: tercil (o 2 grupos para régimen/funding) de cada variable -> expectativa por operación en cada periodo.
Un refinamiento solo se acepta si (a) el filtro mejora la expectativa en AL MENOS 3 DE LOS 4 periodos, (b) conserva >= 50 % de las operaciones,
(c) mejora también en reciente (que no se usó para elegirlo). Se aceptan como máximo 2 refinamientos. Nada se ajusta después de ver VAL00.
Si ninguna variable cumple, la regla principal queda tal cual y se declara que no hay refinamiento robusto.
