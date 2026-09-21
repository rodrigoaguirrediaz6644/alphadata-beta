# Cambio de aritmética del NAV reconstruido — 21-09-2026

La reconstrucción histórica pasa de calcular con **peso constante** a calcular
con **los pesos corriendo entre revisiones**, que es lo que dice
`POLITICA_REBALANCEO.md`.

La serie anterior queda en `reconstruccion_peso_constante_2026.csv`. No se
reescribe ni se encadena con la nueva.

## Por qué

`retorno_dia += peso * (precio_hoy/precio_ayer - 1)` con el peso fijo es la
aritmética de una cartera que vuelve al objetivo **todos los días**. El costo,
además, sólo se cobraba cuando cambiaba el objetivo, y partes iguales dan casi
siempre el mismo número: el rebalanceo salía gratis. Y como el modelo creía que
la posición ya estaba en su peso, la orden de recortar no se emitía nunca.

El NAV publicado describía una cartera que nadie tiene.

Se hace ahora y no más adelante porque **lo que se mueve es la reconstrucción,
no la serie en vivo**, que tiene cinco días y prácticamente no ha derivado.
Cada semana que pase vuelve el cambio más caro.

## Las cifras, antes y después

Ventana 2021-07-08 a 2026-07-15. Retorno anual y peor caída.

| serie | antes | ahora | |
|---|---|---|---|
| Sigma-6 | 355,40 · +28,75% · −17,3% | 229,88 · **+18,04%** · −19,9% | −10,7 pp |
| Delta-12 | 315,89 · +25,76% · −14,9% | 305,55 · **+24,93%** · −15,0% | −0,8 pp |
| Gamma-6 | 292,31 · +23,83% · −26,4% | 335,00 · **+27,24%** · −28,9% | +3,4 pp |
| Oro | 274,29 · +22,29% · −23,5% | igual | sin cambio |
| Conjunto | 321,85 · +26,23% · −9,5% | 297,72 · **+24,28%** · −9,1% | −2,0 pp |
| IPSA TR | 261,39 · +21,10% · −15,9% | igual | sin cambio |

Delta-12 y Gamma-6 se mueven lo medido: la aritmética explica los −0,8 y +3,4
puntos.

## Sigma-6 se mueve mucho más que lo medido, y la razón no es la aritmética

La brecha medida para Sigma-6 entre peso constante y pesos corriendo era de
**0,9 puntos anuales** (+18,94% contra +18,06%). La caída publicada es de
**10,7**. La diferencia no viene del cambio de política.

Viene de que **la serie de Sigma-6 nunca se reconstruía.** El pipeline
recalculaba Delta-12, Gamma-6 y Oro en cada corrida, y Sigma-6 se quedaba con
los valores congelados en `reconstruccion_historica.csv` desde antes del
incidente del feed: antes de reparar los precios chilenos de 2025-2026, antes
de reconstruir la tabla de dividendos, y antes de las correcciones de
metodología. Nadie la había vuelto a calcular.

Al agregarse `sigma6_historical_nav` —que no existía— la serie se recalcula por
primera vez con las reglas y los datos de hoy, y el +28,75% no sobrevive.

**Los 10,7 puntos son, casi todos, la corrección de una serie vieja, no el
efecto del rebalanceo.** No hay forma de separar las dos causas con precisión,
porque la serie anterior no dejó registro de cómo se había calculado.

## Control

Las tres funciones de producción reproducen exactamente lo medido en el banco
de pruebas, con desvío máximo `0,00000000%` en las tres:

- `delta12_historical_nav` → 305,5538
- `gamma6_historical_nav` → 335,0014
- `sigma6_historical_nav` → 230,0763

El Oro no cambia porque es una sola posición: no hay pesos que corran.
`data/strategy_nav.csv`, la serie en vivo, no se toca.
