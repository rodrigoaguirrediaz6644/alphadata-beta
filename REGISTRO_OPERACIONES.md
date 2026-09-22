# Registro de operaciones reales

`data/operaciones_reales.csv`. Se llena a mano, una fila por operación
efectivamente ejecutada.

## Por qué existe, y por qué hay que empezar antes de la primera compra

El resultado real va a diferir del publicado. Siempre difiere: el modelo compra
al cierre y una persona compra cuando puede, a un precio que no es ese, pagando
una comisión que el modelo estima pero no observa.

Sin este registro, cuando aparezca la diferencia no hay forma de saber si viene
de la estrategia o de la ejecución. Con él, se mide y se corrige.

**Es información que sólo existe en el momento.** El precio efectivamente
pagado y la comisión cobrada no se pueden reconstruir después: no están en
ningún archivo del proyecto ni en ningún proveedor. Si la primera compra ocurre
sin registrar, ese dato se perdió.

## Las columnas

| columna | qué va |
|---|---|
| `fecha_senal` | la fecha de la revisión que generó la orden |
| `fecha_ejecucion` | el día en que realmente se operó; vacío si no se ejecutó |
| `estrategia` | Delta-12, Gamma-6 u Oro (Sigma-6 si quedara algo de antes) |
| `instrumento` | el ticker AlphaData, igual que en `config/tickers.csv` |
| `accion` | COMPRA, VENTA, APORTE o RETIRO |
| **`estado`** | **EJECUTADA, PARCIAL, NO_EJECUTADA o ANULADA** |
| **`cantidad_pedida`** | **cuántas unidades se ordenaron** |
| `cantidad` | **cuántas se ejecutaron de verdad**; 0 si no se ejecutó |
| `precio_modelo` | el cierre que usó el modelo en la fecha de señal |
| `precio_pagado` | el precio efectivo de la transacción |
| `comision` | lo que cobró la corredora por esa operación, en pesos |
| `notas` | lo que haga falta |

### Las tres columnas nuevas, y por qué

El primer día van a pasar tres cosas que el archivo antes no podía representar,
y **reconstruirlas después no se hace nunca**: si las primeras semanas quedan
mal registradas, quedan mal para siempre.

**Una orden que no se ejecutó.** Va con `estado = NO_EJECUTADA`, `cantidad = 0`
y `fecha_ejecucion` vacía. La fila existe igual, porque una orden que no se
ejecutó es información: el modelo creía tener esa posición y la cuenta no la
tiene.

**Una orden parcialmente ejecutada.** `estado = PARCIAL`, con
`cantidad_pedida` y `cantidad` distintas. Sin las dos columnas no hay forma de
saber si se pidió poco o si el mercado no dio.

**El precio y la comisión efectivos de cada fill.** Si una orden se llenó en
varios tramos a precios distintos, va **una fila por fill**, cada una con su
`precio_pagado` y su `comision`. Promediar a mano pierde exactamente lo que
este archivo viene a medir.

La regla es la misma de siempre: **`cantidad` es lo que de verdad hay en la
cuenta.** Todo lo que lea tenencias reales suma esa columna y ninguna otra.

En un APORTE o un RETIRO, `instrumento` va vacío, `cantidad` lleva el monto en
pesos y `precio_pagado` la comisión o el costo de la transferencia si lo hubo.
`estrategia` dice a qué pieza entra o de cuál sale, o `Conjunto` si se reparte.

## Aportes y retiros: por qué hay una fila para algo que hoy no ocurre

El NAV supone **reinversión total, para siempre**. Nunca sale plata y nunca
entra. Es el supuesto correcto para medir una estrategia y es falso para una
cuenta.

El día que se retire plata para gastarla, el modelo y la cuenta se separan de
forma permanente: el modelo sigue componiendo sobre un capital que ya no está.
Y eso **no se puede reconstruir después** —igual que el precio pagado y la
comisión, es información que sólo existe en el momento—. Sin la fila, un año
más tarde la única explicación disponible para la diferencia es «la estrategia
anduvo peor», que sería falso.

Hay dos sentidos de «retirar utilidades» y conviene no confundirlos. Éste es
sacar plata del sistema. El otro —recortar un ganador dentro de una
estrategia— es la política de rebalanceo, que es otra cosa y vive en
`ARQUITECTURA.md`.

## La primera boleta: qué contestó

**Orden 11157665580442, 22-09-2026: 8 IAUCL a $77.300.** Valor $618.400, costos
(comisión + IVA) $1.103,84, total $619.503,84.

**La tarifa deja de ser una constante rara.** `618.400 × 0,001785 = 1.103,84`,
exacto al peso, y ahora sobre una orden **ejecutada** y no una
previsualización. Y el rótulo dice lo que faltaba —«comisión + IVA»—, así que
la estructura es **0,15% de comisión más 19% de IVA**: `0,15% × 1,19 =
0,1785%`. Eso cierra la pregunta de si falta algún cargo encima: no falta, el
total pagado es exactamente eso.

**La pantalla no dice a qué precio se llena.** IAUCL exhibió **$76.500 durante
toda la jornada** —cierre anterior, máximo, mínimo y último, los cuatro
iguales, volumen cero— y llenó a **$77.300**, un 1,05% por encima. Trii no
llena al precio exhibido: cotiza fresco al ejecutar. El «último precio» es el
último negocio, que puede ser de semanas antes.

De ahí salen dos cosas que valen para el 30-09:

**Las órdenes van a mercado, no con precio límite.** Poner un límite contra un
precio rancio sólo agrega el riesgo de no llenar siete órdenes el mismo día, y
no protege de nada.

**Y la verificación es posterior.** Se anota el precio de llenado de cada
posición y se contrasta contra el teórico **del día en que se ejecutó**; si
alguna se sale de ~1%, ahí sí hay algo que mirar. La comprobación ocurre igual,
sin riesgo operativo.

**Cuidado con contra qué se contrasta**, que ya casi falla en el primer caso:
el llenado del 22-09 queda 1,98% bajo el teórico que imprimió la guía, y eso es
sólo que la guía es del 21-09 y usó un cierre del subyacente de dos ruedas
antes. Contra el teórico del mismo día la diferencia es **0,05%**.

**El llenado fue limpio, y hay confirmación numérica.** El tipo de cambio
implícito en el precio pagado —`77.300 / 81,67 = 946,49`— contra los 947,57 que
ofrecía la pantalla de conversión de Trii ese mismo día: **difieren en 0,11%**.
El CDV se cotiza al subyacente por el tipo de cambio de Trii, en vivo y sin
margen apreciable encima.

**Y se pagó en pesos**, con saldo en dólares de $0,00. Lo más probable es que
Trii convierta solo por detrás, y el 0,11% lo respalda. **Mientras Rodrigo no
confirme lo contrario, la guía no lleva ningún paso de conversión**: si resulta
opcional, lo que corresponde es una línea diciendo que no hace falta convertir,
no una secuencia de pasos con esperas.

## La cuenta no va a calzar con el NAV publicado, y eso es esperado

**Esto es lo primero que hay que leer cuando aparezca la diferencia**, porque se
va a ver como una falla y no lo es.

El NAV publicado de Gamma-6 y del oro usa el **precio sintetizado**: el
subyacente en dólares por el tipo de cambio. La ejecución ocurre al precio del
**CDV**, que cotiza con un premio encima de ese teórico. Medido sobre dos años,
el premio es **+0,30%**, y lo que importa acá no es su nivel sino que **cambia
0,418% de un mes a otro**.

Un premio de nivel se cancela: si se compra y se vende con el mismo premio, no
cuesta nada. Lo que no se cancela es su variación, y con Gamma-6 rotando todos
los meses **la cuenta real va a separarse del informe del orden de un punto al
año, en cualquier dirección**.

Que sea en cualquier dirección es la parte que hay que retener. Si la cuenta va
un punto arriba del informe, tampoco es que el modelo se quedó corto: es el
mismo ruido con el otro signo.

**Cuándo sí preocuparse:** cuando la diferencia sea mucho mayor que eso, o
cuando tenga siempre el mismo signo durante varios meses. Lo segundo querría
decir que el premio dejó de ser ruido y se volvió un cargo, y para eso está la
guardia del panel de salud, con banda de ±1%. Ver `research/spread_cambio/`.

## Lo que se va a poder medir con esto

- **Deslizamiento**: `precio_pagado / precio_modelo - 1`, por estrategia y por
  instrumento. Es la diferencia entre el backtest y la realidad que el backtest
  no modela.
- **Comisión efectiva contra la modelada.** El sistema supone **0,15% más IVA
  = 0,1785%**, con mínimo de $999,99, y la misma tarifa para acción chilena y
  para CDV. Ya no hay nada que verificar acá: la primera orden ejecutada la
  confirmó al peso. Lo que queda es que siga siendo cierta. La primera comparación está calculada en
  `reports/cartera_de_ingreso.md`, bajo «lo que va a cobrar la corredora el
  primer día».
- **Órdenes que no se llenan.** Con `estado` y `cantidad_pedida` se puede medir
  qué proporción de las órdenes se ejecuta completa, que es un costo de
  ejecución que el modelo no supone en ninguna parte.
- **Retraso de ejecución**: `fecha_ejecucion - fecha_senal`, y cuánto cuesta.

Nada de eso se puede estimar sin los datos, y ninguno de los tres es
despreciable al capital con que se va a operar.
