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
