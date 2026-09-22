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

## Lo que se va a poder medir con esto

- **Deslizamiento**: `precio_pagado / precio_modelo - 1`, por estrategia y por
  instrumento. Es la diferencia entre el backtest y la realidad que el backtest
  no modela.
- **Comisión efectiva contra la modelada.** El sistema supone 0,1785% con
  mínimo de **$999,99**, y **la misma tarifa para acción chilena y para CDV**.
  Los tres parámetros están medidos sobre órdenes reales de Trii: cuatro
  chilenas para la tasa y el mínimo, y una de IAUCL —$612.000 de valor,
  $1.092,42 de comisión— para los CDV. Acá se ve si se sostienen. La primera comparación está calculada en
  `reports/cartera_de_ingreso.md`, bajo «lo que va a cobrar la corredora el
  primer día».
- **Órdenes que no se llenan.** Con `estado` y `cantidad_pedida` se puede medir
  qué proporción de las órdenes se ejecuta completa, que es un costo de
  ejecución que el modelo no supone en ninguna parte.
- **Retraso de ejecución**: `fecha_ejecucion - fecha_senal`, y cuánto cuesta.

Nada de eso se puede estimar sin los datos, y ninguno de los tres es
despreciable al capital con que se va a operar.
