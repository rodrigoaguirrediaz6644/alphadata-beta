# Rotación de Delta-12: de dónde viene y qué se puede hacer

Delta-12 hace **64 operaciones al año** con ocho posiciones en la muestra
2021-2026: casi toda la cartera rota cada mes. A capital bajo eso no es un
detalle de costo sino lo que decide si la estrategia sirve.

## De dónde viene la rotación

De las 181 salidas en 63 revisiones mensuales:

| | salidas | |
|---|---|---|
| forzadas por dejar de ser elegible | **134** | **74%** |
| desplazadas por otra candidata | 47 | 26% |

Y el motivo de las forzadas:

| motivo | salidas | |
|---|---|---|
| **RSI14 superior a 65** | **73** | **54%** |
| bajo SMA200 | 39 | 29% |
| liquidez bajo el percentil 20 | 11 | 8% |
| momentum no positivo | 11 | 8% |

**Delta-12 vende sus ganadoras en cuanto se ponen fuertes.** El RSI está
actuando como condición de permanencia cuando su sentido natural es evitar
comprar algo ya sobrecomprado.

## Por qué la histéresis sobre el ranking no sirve

Sólo puede actuar sobre el 26% de desplazamientos. Medido, la rotación baja de
64 a 49 operaciones al año en el mejor caso —una banda de ranking de +6— y el
efecto sobre el retorno cambia de signo entre submuestras: +1,69pp en la
primera mitad y -2,69pp en la segunda. Un margen de puntaje da lo mismo: de 64
a 53 operaciones, con +0,80pp y -2,58pp. Es ruido.

## La palanca que sí existe

Quitar el RSI como condición de permanencia y dejarlo sólo como filtro de
entrada baja la rotación **de 64 a 20 operaciones al año, un 69%**.

## Pero el efecto sobre el retorno no se puede medir con estos datos

| variante | ops/año | completa | 1ª mitad | 2ª mitad |
|---|---|---|---|---|
| oficial | 64 | 29,5% | 27,2% | 29,5% |
| RSI sólo al entrar | 20 | -0,72pp | -3,89pp | -0,80pp |
| RSI salida 70 | 35 | +0,17pp | **+3,02pp** | **-3,12pp** |
| RSI salida 75 | 25 | -2,61pp | -3,71pp | -1,89pp |
| RSI salida 80 | 21 | -2,08pp | -2,85pp | -4,89pp |

El efecto no es monótono en el umbral —75 sale peor que 70 y que 80— y cambia
de signo entre mitades. Cinco años y 63 revisiones no alcanzan para resolver un
efecto de menos de un punto anual.

## La consecuencia práctica

El ahorro de costo sí es determinista. Contando sólo el exceso del mínimo de
$1.990 sobre el porcentual que el backtest ya cobra:

| capital de la pieza | oficial | RSI sólo al entrar | diferencia |
|---|---|---|---|
| $1.000.000 | 18,19% | 25,27% | +7,07pp |
| $2.000.000 | 24,56% | 27,26% | +2,70pp |
| $5.000.000 | 28,38% | 28,45% | +0,07pp |
| $8.900.000 o más | 29,50% | 28,80% | -0,70pp |

Es decir: se cambiaría un ahorro **conocido** de entre 0 y 7 puntos anuales,
según el capital, por un cambio de retorno **desconocido** dentro de un rango
de más o menos cuatro puntos. No es un almuerzo gratis y no es una decisión que
estos datos puedan tomar.

Lo que sí queda establecido es el diagnóstico: la rotación de Delta-12 no viene
del ranking sino de sus propios filtros de elegibilidad, y el RSI es más de la
mitad. Cualquier intento futuro de bajar el costo tiene que actuar ahí.
