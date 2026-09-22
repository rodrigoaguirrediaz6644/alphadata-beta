# El premio del CDV, y el spread que no se puede medir así

La hipótesis era que Trii cobra un margen en la conversión de dólar a peso, que
no aparece en la boleta, y que con la rotación mensual de Gamma-6 ese margen
domina a todos los costos que llevamos discutidos: **un spread de 0,3% por lado
sobre unos $54 millones transados al año son unos $160.000**, más que todo lo
demás junto.

El resultado es que **la hipótesis no se sostiene con la evidencia disponible**,
y que el método propuesto mide otra cosa de la que parece. Pero la medición
encontró, de paso, un error que sí toca la compra del 30-09.

## Lo primero: el sistema no tenía el precio del CDV

El almacén guarda el **subyacente en dólares** —ABT, IAU— y sintetiza el precio
en pesos multiplicando por el tipo de cambio. Nunca tuvo el precio del
instrumento que se compra de verdad. La orden daba por hecho que sí; no era así.

Se pueden bajar: **30 de los 31 CDV del universo** tienen serie en el proveedor,
dos años de historia. Ahora entran en la captura diaria, en
`data/cdv_precios.csv`.

## Y ahí apareció esto: el símbolo de Bank of America era el de Boeing

`BACL.SN` cotizaba a **3,6 veces** el valor teórico de BAC, de forma consistente
y durante dos años. Eso no es un premio; es otra empresa. El proveedor lo
confirma: `BACL.SN` es **The Boeing Company**. El CDV de Bank of America es
`BACCL`, que cotiza a 1,0012 del teórico.

**BAC está en la cartera vigente de Gamma-6**, así que el símbolo equivocado
era el que se iba a teclear en la corredora el 30-09. Corregido en
`config/tickers.csv`, que ahora lleva el símbolo del CDV en su propia columna
en vez de escondido dentro del nombre.

El otro: **`XOMCL` no existe** en el proveedor y no se encontró el símbolo del
CDV de Exxon. Queda **vacío en vez de adivinado**, que es exactamente el error
que tenía Bank of America. XOM no está hoy en Gamma-6.

## El dato está rancio, y eso decide el método

| | |
|---|---|
| ruedas con volumen cero | **71,2%** |
| ruedas que repiten el cierre anterior | **95,5%** de mediana entre nombres |
| racha más larga en el mismo precio | **453 ruedas** (ABTCL, y CVXCL igual) |

Dividir un precio de hace un año por un subyacente que sí se movió no mide un
premio: mide el rancio. Sobre todas las ruedas la dispersión de la razón es 2% y
no se puede afirmar nada.

Por eso sólo cuentan las ruedas **frescas** —con volumen y con cambio de
precio—, que son el **10,5%**. Es el mismo filtro que corre en producción.

## El CDV es uno a uno con la acción

Sobre ruedas frescas, los doce nombres con datos suficientes dan entre **1,0001
y 1,0059**:

| | mediana | | | mediana |
|---|---:|---|---|---:|
| AAPLCL | 1,0001 | | VCL | 1,0020 |
| IAUCL | 1,0003 | | AMZNCL | 1,0023 |
| BACCL | 1,0012 | | NVDACL | 1,0026 |
| WALMARTCL | 1,0012 | | GOOGLCL | 1,0030 |
| UNHCL | 1,0017 | | MSFTCL | 1,0036 |
| GOOGCL | 1,0018 | | INTCCL | 1,0059 |

**Esto cierra un pendiente que estaba abierto desde antes de la primera
compra.** `PENDIENTES.md` decía que el sistema asume el CDV uno a uno «y hay que
confirmarlo antes de comprar en real». Confirmado para doce nombres, entre ellos
los de la cartera vigente de Gamma-6 y el oro.

## El premio existe, es chico, y se está apagando

| ventana | premio | error estándar | ruedas | ¿distinguible de cero? |
|---|---:|---:|---:|---|
| dos años | **+0,301%** | 0,044% | 1.517 | sí |
| último año | +0,149% | 0,060% | 715 | sí |
| **2026** | **+0,047%** | 0,078% | 494 | **no** |

El CDV cotiza por encima de su valor teórico, y el orden de magnitud es el que
la hipótesis anticipaba. Pero **viene bajando y en 2026 ya no se distingue de
cero**.

## Por qué esto no entra al modelo de costo

**Un cierre no puede mostrar un spread de compra-venta.** Un cierre es una sola
punta, la del último negocio. La diferencia entre lo que la corredora cobra al
vender y paga al comprar no está en esta serie ni en ninguna serie de cierres.
Lo que se midió es un **desvío de nivel**, que es otra cosa.

**Y un desvío de nivel no es un cargo por lado.** Si se compra y se vende con el
mismo premio, se cancela. Lo que cuesta plata es que el premio **cambie** entre
la compra y la venta:

- premio medio por mes: **+0,273%**
- desviación mes a mes: **0,418%**
- cambio medio entre un mes y el siguiente: **0,439%**

Para Gamma-6, que rota mensual, eso es ruido de media cero: agrega varianza, no
un arrastre. Lo único direccional es la caída del premio a lo largo de los dos
años —de +0,59% en 2024 a +0,06% en 2026—, que sobre los $12,5 millones de las
piezas estadounidenses son del orden de **$30.000 al año**, en una sola
dirección y sin garantía de que siga.

**Meterlo como un cargo fijo por lado sería cobrar dos veces algo que se
cancela, y anclar en el modelo un número que ya no es el de hoy.** Queda
medido, publicado en el panel de salud, y fuera del modelo de costo.

## La línea del panel de salud

Se mide sobre el último año en cada corrida y se informa con su error. La banda
es **±1%**, ancha a propósito: lo que tiene que pillar es que la corredora
cambie de régimen —que meta un punto—, no el ruido de un mes flojo. Con un
error estándar de 0,06% sobre el año corrido, una banda estrecha sonaría sola
todas las semanas, y una alarma que suena siempre deja de ser alarma.

## Lo que esto abre y no se midió

Si el premio volviera a los niveles de 2024, **la comparación con Renta 4
cambiaría de signo para las piezas estadounidenses**. Queda anotado, no medido.

Y lo que no hay que construir: nada para «buscar el mejor precio» de los CDV. La
profundidad está vacía, el volumen es cero en el 71% de las ruedas y el máximo
que ofrece la pantalla es el saldo disponible dividido por el precio, no
liquidez. Trii cotiza y llena; no hay contraparte local contra la cual mejorar.
