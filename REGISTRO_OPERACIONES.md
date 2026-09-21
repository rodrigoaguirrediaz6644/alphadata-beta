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
| `fecha_ejecucion` | el día en que realmente se operó |
| `estrategia` | Sigma-6, Delta-12, Gamma-6 u Oro |
| `instrumento` | el ticker AlphaData, igual que en `config/tickers.csv` |
| `accion` | COMPRA, VENTA, APORTE o RETIRO |
| `cantidad` | número de acciones o CDV |
| `precio_modelo` | el cierre que usó el modelo en la fecha de señal |
| `precio_pagado` | el precio efectivo de la transacción |
| `comision` | lo que cobró la corredora por esa operación, en pesos |
| `notas` | lo que haga falta: orden parcial, cambio de precio, lo que sea |

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
  mínimo de $1.990 en lo chileno y 0,1% en lo estadounidense. Acá se ve si es
  así.
- **Retraso de ejecución**: `fecha_ejecucion - fecha_senal`, y cuánto cuesta.

Nada de eso se puede estimar sin los datos, y ninguno de los tres es
despreciable al capital con que se va a operar.
