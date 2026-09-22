# Cuatro piezas contra tres, en pesos, sobre $20 millones

La decisión de si Sigma-6 se queda vista en pesos y no en Sharpe.

## Las tres carteras

- **A — cuatro piezas al 25%.** $5.000.000 cada una: Delta-12, Gamma-6, Oro y
  Sigma-6 tal como está hoy, con Credicorp. Es lo que existe si no se cambia
  nada.
- **B — tres piezas en tercios.** $6.666.667 cada una, sin Sigma-6.
- **C — control.** Sin Sigma-6, pero dejando el oro en 25% y repartiendo el
  cuarto libre entre las dos de acciones: Delta-12 37,5%, Gamma-6 37,5%, Oro
  25%.

**C es la comparación que importa.** B no aísla el efecto de sacar Sigma-6: al
pasar a tercios el oro sube de 25% a 33%, y eso cambia el perfil por una razón
que no tiene nada que ver con Sigma-6.

Reglas de producción tal como están —pesos que corren, sólo entradas y salidas,
entradas financiadas con lo que liberan las salidas, límite de concentración del
25%—, costos de Trii 0,1785% con mínimo $999,99, caja a 0%.

**El capital por pieza cambia entre carteras y eso no es cosmético:** con el
mínimo por operación, una pieza de $7.500.000 paga proporcionalmente menos que
una de $5.000.000. Cada pieza se corrió con el capital que le toca en su
cartera.

## Ventana completa (2021-07 a 2026-07)

| cartera | los $20M quedan en | ganancia | anual | peor caída |
|---|---|---|---|---|
| **A** cuatro piezas al 25% | $48.685.107 | $28.685.107 | +18,67% | **−$3.940.468** (−8,1%) |
| **B** tres piezas en tercios | $50.413.295 | $30.413.295 | +19,47% | −$5.165.604 (−10,2%) |
| **C** control, oro en 25% | **$53.566.005** | **$33.566.005** | **+20,88%** | −$5.784.514 (−10,8%) |

**Mantener Sigma-6 cuesta $4.880.898 contra el control**, un 9,1% sobre el valor
final y 2,2 puntos anuales. Contra B, $1.728.188.

## Por ventana

### Selección (2021-07 a 2023-12)

| cartera | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| A | $26.485.606 | +12,02% | **−$1.772.157** (−6,7%) |
| B | $27.598.510 | +13,90% | −$2.838.236 (−10,2%) |
| **C** | **$28.400.433** | **+15,22%** | −$3.077.619 (−10,8%) |

### Evaluación (2024-01 a 2026-07)

| cartera | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| A | $37.157.486 | +25,68% | −$3.007.447 (−8,1%) |
| B | $37.057.235 | +25,55% | **−$2.539.993** (−6,9%) |
| **C** | **$38.307.934** | **+27,10%** | −$2.961.203 (−7,7%) |

## Lo que dice

**C gana en las tres ventanas.** No se da vuelta: sacar Sigma-6 y repartir su
cuarto entre Delta-12 y Gamma-6 produce más plata en la ventana de selección, en
la de evaluación y en la completa.

**A queda última en dos de las tres.** En la evaluación le gana a B por
$100.251 —un 0,27%, que es ruido— y pierde con C por $1.150.448.

**Lo único que A compra es una caída menor, y sólo a veces.** En la ventana
completa su peor caída es $3.940.468 contra $5.784.514 de C: **ahorra $1,84
millones de caída y renuncia a $4,88 millones de ganancia.** En la ventana de
evaluación ni siquiera compra eso: A tiene la peor caída de las tres.

## Esto apunta al revés que el Sharpe, y hay que decirlo

El estudio anterior, midiendo contra un control de caja, mostraba que mantener
la corredora aportaba Sharpe de forma consistente en las dos ventanas (+0,05 y
+0,24). **En pesos el signo se invierte.**

No es una contradicción, es qué premia cada métrica. **Sigma-6 es caja en su
mayor parte por construcción** —cuatro posiciones con tope de 10% son 40%
invertido y 60% en caja— así que baja la volatilidad del conjunto y el Sharpe la
premia por eso. El resultado en pesos **le cobra** esa misma caja, porque no
rinde nada.

Las dos mediciones son correctas sobre cosas distintas. La pregunta que se hizo
acá —cuánta plata hay al final— la contesta la de pesos, y la contesta en contra
de mantener Sigma-6.

## Lo que no dice

No dice qué pasa con una Sigma-6 distinta. Todos estos números son de
**Sigma-6 tal como está hoy**: con Credicorp, con cuatro posiciones y 60% en
caja por falta de recomendaciones vigentes. Una versión con más nombres
invertiría más de su cuarto, y este estudio no la mide.

Y no dice nada del futuro del insumo: la carga manual, la guardia de vigencia
del 21-10-2026 y el apagado de julio de 2027 siguen donde estaban, en
`DEPENDENCIAS_MANUALES.md`.
