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

| estrategia | qué se compra | cuándo | tramos |
|---|---|---|---|
| **Sigma-6** | la cartera vigente completa | justo después de la revisión semanal | **1** |
| **Delta-12** | la cartera vigente completa | justo después de la revisión de fin de mes | **1** |
| **Gamma-6** | las seis posiciones vigentes | después de la revisión mensual | 1, o hasta 12 semanales si se prefiere |
| **Oro** | la posición completa | cualquier día | **1** |

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
recortar 1,8 puntos de desviación típica. En Sigma-6, 4,4 puntos. Mal trato.

Los 3,6 puntos de media perdida **no se cuentan como costo del método**: en una
muestra donde el mercado subió 21% anual cualquier demora cuesta, y en un
mercado plano o a la baja eso se da vuelta. Es propiedad del periodo. Lo que sí
es determinista son las comisiones, y con ellas solas alcanza para cerrar el
caso en las piezas chilenas.

En Gamma-6 y Oro el costo **no cambia con el número de tramos**, porque el
modelo estadounidense cobra 0,1% sin mínimo. Ahí la reducción de dispersión
—que aguantó las dos submuestras— se aprovecha gratis. La medición de
dispersión se hizo sobre la cartera de Delta-12; no se midió sobre Gamma-6.

La intuición de escalonar donde es gratis y entrar de una donde cuesta queda
**confirmada en el costo**. Lo que no se confirma es que el beneficio valga la
pena en las piezas caras.

## Cuándo entrar: en la fecha de revisión, no en un día cualquiera

La regla más barata del protocolo no cuesta nada y no exige pronosticar: entrar
**justo después de la revisión de cada estrategia**. Delta-12 revisa a fin de
mes; Sigma-6, cada semana.

Medido sobre 63 revisiones y 8.959 combinaciones de día y posición:

| | vida restante media | mediana | costo por mes mantenido |
|---|---|---|---|
| entrando en la fecha de revisión | **79,3 días** (2,6 meses) | 61 días | **$764** |
| entrando un día cualquiera | 64,0 días (2,1 meses) | 43 días | $946 |

Son **15,2 días más de vida por posición, un 24%**, y el costo de entrada por
mes mantenido baja un 19%: de 1,82% a 1,47% anualizado sobre la posición.

El mecanismo no es el que podría parecer. La proporción de posiciones que se
venden en la primera revisión posterior apenas cambia —42% contra 45%—, así que
entrar en la revisión **no evita las posiciones moribundas**. Lo que hace es
regalar el periodo completo entre revisiones en vez de uno parcial: en promedio,
media ventana extra. El beneficio está acotado por construcción a la mitad del
intervalo de revisión, y eso es exactamente lo que se observa.

## Las posiciones que el modelo va a vender pronto

Aun entrando en la fecha de revisión, **4 de cada 10 posiciones heredadas se
venden en la revisión siguiente**. Se compran igual, por dos razones.

El costo es chico y es por una sola vez: entrar a las ocho posiciones de
Delta-12 con $5 millones cuesta $15.920, un **0,32% de la pieza**.

Y saltárselas es segundo-adivinar al modelo sin información: no se sabe cuáles
de las ocho caen en ese 40%. El que se salta las que "parecen" próximas a
venderse está aplicando un criterio propio encima de la estrategia, que es
exactamente lo que el protocolo existe para evitar.

## Los relojes: lo que hay que saber antes de la primera orden

La regla no cambia —se compra la cartera vigente completa— pero quien compra
tiene que **saber qué está comprando**, y eso son tres cosas que esta guía no
tenía porque hasta hace poco no existían. Están en
**`reports/cartera_de_ingreso.md`**, que se regenera en cada corrida: una tabla
de montos y fechas escrita a mano acá envejecería sola.

Para cada posición vigente:

- **El monto en pesos**, y cuántas unidades caben.
- **Hace cuánto la tiene el modelo.** Sin tope de tenencia, Sigma-6 puede
  sostener un nombre por años: BCI viene desde octubre de 2024, 706 días. No es
  lo mismo heredar una posición de dos semanas que una de dos años.
- **Su próxima salida conocida, si la tiene.** En Sigma-6 la recomendación
  caduca a los 365 días y eso es una fecha: VAPORES el 24-11-2026, BCI y
  PARAUCO el 01-07-2027, LTM el 09-07-2027. En Delta-12 y Gamma-6 las salidas
  son **por ranking y no tienen fecha**, que es distinto de no saberse, y la
  tabla lo dice en vez de dejar la celda vacía.
- **El costo del par entrada-salida en ese plazo**, en pesos, como porcentaje
  de la posición y anualizado.

Ese último es el que cambia una decisión. Con el mínimo de $1.990 por
operación, **VAPORES cuesta 0,80% por nueve semanas de tenencia —4,3%
anualizado— y BCI cuesta 0,87% repartido en diez meses, 1,1% anualizado.** El
mismo porcentaje, cuatro veces el costo por mes mantenido.

**Es información, no un filtro.** La decisión de comprar la cartera completa
está tomada y medida —ver más arriba— y saltarse las que parezcan caras es
exactamente el criterio propio que este protocolo existe para evitar. Lo que
esto impide es enterarse después.

## El redondeo, que aparece el primer día

Las acciones chilenas se transan por **unidades enteras**. $625.000 en BCI a
$65.600 son 9,53 acciones: se compran **9 por $590.400** y quedan **$34.600**
en caja.

La regla es **redondear hacia abajo, con el residuo a la caja de la pieza**,
igual que el producto de una venta.

Con veinte posiciones el residuo es real: al 17-09-2026 son **$433.493 de
$17.000.000, un 2,5%**. **Los pesos efectivos del primer día no van a calzar
con los de referencia, y eso es esperado, no un error.**

Cuanto más caro el instrumento, mayor el residuo, y por eso se concentra en
Gamma-6: **$318.804 de su pieza de $5 millones, un 6,4%**, porque en MRK a
$140.392 caben cinco unidades y sobran $131.369.

**Para los CDV estadounidenses hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo.** Es una pregunta para Trii, no un cálculo, y
ahí vale plata: es donde está casi todo el residuo.

## Lo que este documento no cubre

Las mediciones se hicieron sobre Delta-12. Sigma-6 comparte estructura —
revisión periódica, posiciones con fecha y precio de entrada— pero rota menos
(49 operaciones al año contra 78) y tiene diez posiciones en vez de ocho, así
que sus números de costo están calculados pero los de dispersión y vida
restante no se midieron por separado.
