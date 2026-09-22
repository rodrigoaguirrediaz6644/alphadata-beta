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

**Corregido el 22-09-2026.** Este estudio corrió con un 0,1% sin mínimo para los
CDV, que era un supuesto y resultó falso: una boleta real de IAUCL mostró la
misma tarifa chilena. La corrección pega más fuerte en C, que es la que más
Gamma-6 tiene, o sea **en contra de la cartera que gana**. Las tablas de abajo
son las de después de corregir; **el orden no cambió** y lo que se movió fue la
magnitud: mantener Sigma-6 costaba $4.880.898 y cuesta $4.658.161. La tarifa ya
no está escrita en este archivo: sale de `config/runtime.v2.json`.

**El capital por pieza cambia entre carteras y eso no es cosmético:** con el
mínimo por operación, una pieza de $7.500.000 paga proporcionalmente menos que
una de $5.000.000. Cada pieza se corrió con el capital que le toca en su
cartera.

## Ventana completa (2021-07 a 2026-07)

| cartera | los $20M quedan en | ganancia | anual | peor caída |
|---|---|---|---|---|
| **A** cuatro piezas al 25% | $48.323.631 | $28.323.631 | +18,50% | **−$3.915.943** (−8,1%) |
| **B** tres piezas en tercios | $49.920.998 | $29.920.998 | +19,25% | −$5.152.117 (−10,3%) |
| **C** control, oro en 25% | **$52.981.792** | **$32.981.792** | **+20,62%** | −$5.765.292 (−10,9%) |

**Mantener Sigma-6 cuesta $4.658.161 contra el control**, un 8,8% sobre el valor
final y 2,1 puntos anuales. Contra B, $1.597.366.

## Por ventana

### Selección (2021-07 a 2023-12)

| cartera | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| A | $26.388.746 | +11,85% | **−$1.777.048** (−6,7%) |
| B | $27.465.898 | +13,67% | −$2.845.393 (−10,3%) |
| **C** | **$28.248.289** | **+14,97%** | −$3.085.072 (−10,9%) |

### Evaluación (2024-01 a 2026-07)

| cartera | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| A | $37.016.974 | +25,50% | −$2.999.699 (−8,1%) |
| B | $36.872.537 | +25,32% | **−$2.532.710** (−6,9%) |
| **C** | **$38.094.206** | **+26,84%** | −$2.950.888 (−7,7%) |

## El invariante aritmético

Las dos ventanas parciales son cortes de **una sola corrida continua**, no dos
corridas que arrancan de nuevo con $20 millones, así que el corte no liquida ni
vuelve a comprar y no hay costo del corte que tolerar: la composición tiene que
dar exacto. Y da — **residuo máximo 2,2e-16, precisión de flotante**, en las
tres carteras.

Con una salvedad que importa saber leer: el 01-01-2024 no es rueda. La ventana
de selección termina el 29-12 y la de evaluación empieza el 02-01, y **el
retorno entre esas dos sesiones no está en ninguna de las dos**. Multiplicar los
factores de las ventanas sin devolverlo sobra 1,5%. Contando ese salto una vez
—que en las tres carteras es negativo, entre −1,1% y −1,5%— el producto reproduce
la ventana completa dígito por dígito.

## Lo que dice

**C gana en las tres ventanas.** No se da vuelta: sacar Sigma-6 y repartir su
cuarto entre Delta-12 y Gamma-6 produce más plata en la ventana de selección, en
la de evaluación y en la completa.

**A queda última en dos de las tres.** En la evaluación le gana a B por
$144.437 —un 0,39%, que es ruido— y pierde con C por $1.077.232.

**Lo único que A compra es una caída menor, y sólo a veces.** En la ventana
completa su peor caída es $3.915.943 contra $5.765.292 de C: **ahorra $1,85
millones de caída y renuncia a $4,66 millones de ganancia.** En la ventana de
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
