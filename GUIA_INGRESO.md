# Guía de ingreso — qué compra el que entra hoy

Capital de referencia: **$20 millones**, repartidos entre las cuatro piezas.
Todos los números de abajo están medidos sobre Delta-12 en la reconstrucción
2021-2026, 63 revisiones mensuales, salvo donde se indique otra cosa.

## Lo que ya estaba definido, y sigue valiendo

`strategies.v2.json`, dentro de `common_controls.subscriber_onboarding`:

- El que entra recibe **la cartera vigente**, los pesos objetivo vigentes, el
  peso en caja, la fecha de la próxima revisión y la versión de metodología.
- **No se reconstruye el precio de entrada original.**
- El resultado se reporta sobre la cartera modelo oficial, no sobre el retorno
  personal del suscriptor.

Confirmado: sigue siendo lo correcto, y las mediciones de abajo lo respaldan.

## Qué se compra el primer día, por estrategia

| estrategia | qué se compra | tramos | separación |
|---|---|---|---|
| **Sigma-6** | la cartera vigente completa | **1** | — |
| **Delta-12** | la cartera vigente completa | **1** | — |
| **Gamma-6** | las seis posiciones vigentes | 1, o hasta 12 si se prefiere | semanal |
| **Oro** | la posición completa | **1** | — |

Y con las posiciones que el modelo ya tiene abiertas: **se compran todas**, sin
mirar si van arriba o abajo del precio de entrada del modelo, y sin saltarse
las que parezcan próximas a venderse.

## Por qué no se filtra por "las que van abajo"

Se midió comprar la cartera completa contra comprar sólo las posiciones bajo su
precio de entrada del modelo, en 63 fechas de ingreso:

| | completa | sólo las que van abajo | |
|---|---|---|---|
| **muestra completa** | | | |
| 3 meses | 7,70% | 10,15% | +2,45pp |
| 6 meses | 16,52% | 17,24% | +0,72pp |
| 12 meses | 31,71% | 33,09% | +1,38pp |
| **1ª mitad** | | | |
| 6 meses | 16,93% | 15,53% | **−1,40pp** |
| 12 meses | 23,08% | 19,35% | **−3,72pp** |
| **2ª mitad** | | | |
| 6 meses | 16,17% | 18,70% | +2,54pp |
| 12 meses | 41,41% | 48,54% | +7,12pp |

**El orden se da vuelta entre submuestras, así que no se puede distinguir.**
En la muestra completa el filtro sale mejor; en la primera mitad sale peor a
seis y doce meses; en la segunda sale mejor en todo. Por el protocolo acordado,
eso es un empate, no una ventaja.

Hay además una objeción que no depende de la medición: **la canasta filtrada
tiene 2,0 posiciones de 8 en promedio.** No es la misma estrategia con un
filtro encima; es una cartera de dos acciones con 75% en caja. Aunque su
retorno medido fuera mayor, no es comparable en riesgo ni es lo que la
estrategia dice hacer.

Y el precio de entrada del modelo no es un nivel de mercado: es contabilidad
interna. El papel no sabe que existe.

## Por qué no se escalona lo chileno

El escalonamiento **sí reduce la dispersión**, de forma consistente en las dos
submuestras. Desviación típica del resultado a 12 meses:

| | completa | 1ª mitad | 2ª mitad |
|---|---|---|---|
| un día | 18,3% | 12,0% | 18,4% |
| 4 semanas | 18,2% | 11,3% | 18,4% |
| 8 semanas | 17,4% | 10,6% | 17,0% |
| **12 semanas** | **16,5%** | **9,7%** | **15,9%** |

Doce semanas gana en los tres tramos. Pero cuesta dos cosas. La media del
resultado a 12 meses baja de 27,5% a 23,9%, **3,6 puntos**, porque retrasar la
entrada en un mercado que sube cuesta. Y la comisión se multiplica por el
número de tramos, con capital de $5 millones por pieza:

| estrategia | 1 tramo | 4 tramos | 8 tramos | 12 tramos |
|---|---|---|---|---|
| Delta-12 | $15.920 | $63.680 | $127.360 | $191.040 |
| Sigma-6 | $19.900 | $79.600 | $159.200 | $238.800 |
| **Gamma-6** | **$5.000** | **$5.000** | **$5.000** | **$5.000** |
| **Oro** | **$5.000** | **$5.000** | **$5.000** | **$5.000** |

En Delta-12, pasar de un tramo a doce cuesta **3,5 puntos de una vez** para
recortar 1,8 puntos de desviación típica. En Sigma-6, 4,4 puntos. Es un mal
trato incluso antes de contar los 3,6 puntos de media perdida.

En Gamma-6 y Oro el costo **no cambia con el número de tramos**, porque el
modelo estadounidense cobra 0,1% sin mínimo. Ahí escalonar es gratis, así que
es una preferencia y no una decisión económica. La medición de dispersión se
hizo sobre la cartera de Delta-12; no se midió sobre Gamma-6.

La intuición de escalonar donde es gratis y entrar de una donde cuesta queda
**confirmada en el costo**. Lo que no se confirma es que el beneficio valga la
pena en las piezas caras.

## Las posiciones que el modelo va a vender pronto

| | |
|---|---|
| vida restante media de una posición heredada | **1,7 meses** |
| mediana | 1 mes |
| se vende en la revisión siguiente | **40%** de las veces |

Cuatro de cada diez posiciones que se heredan se venden dentro del mes. Aun
así **se compran**, por dos razones.

El costo es chico y es por una sola vez: entrar a las ocho posiciones de
Delta-12 con $5 millones cuesta $15.920, un **0,32% de la pieza**. Repartido
sobre la vida restante media son $1.192 por mes mantenido.

Y saltárselas es segundo-adivinar al modelo sin información: no se sabe cuáles
de las ocho caen en ese 40%. El que se salta las que "parecen" próximas a
venderse está aplicando un criterio propio encima de la estrategia, que es
exactamente lo que el protocolo existe para evitar.

## Lo que este documento no cubre

Las mediciones se hicieron sobre Delta-12. Sigma-6 comparte estructura —
revisión periódica, posiciones con fecha y precio de entrada— pero rota menos
(49 operaciones al año contra 78) y tiene diez posiciones en vez de ocho, así
que sus números de costo están calculados pero los de dispersión y vida
restante no se midieron por separado.
