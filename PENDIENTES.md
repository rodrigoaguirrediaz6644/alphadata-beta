# Pendientes con su condición de reapertura

Lo que está decidido que no se hace ahora, con lo que tendría que pasar para
volver a mirarlo. La idea es que ninguna de estas discusiones empiece de cero,
y que ninguna se reabra por cansancio.

## La caja en un money market

**Parqueado, y con menos caja que antes.** Los $3.000.000 que motivaron esta
discusión eran de Sigma-6, que salió de la asignación. Lo que queda es la caja
de redondeo de las tres piezas.

**Se reabre si la caja sube bastante por encima de lo que deja el redondeo.**
Cuando se reabra, lo ya decidido sigue valiendo: money market, serie sin
permanencia mínima ni comisión de salida, y la remuneración hay que mirarla
dentro de la cuenta.

## El futuro de Sigma-6 como pieza — **cerrado**

**Salió de la asignación el 22-09-2026.** El control que reparte su cuarto
entre Delta-12 y Gamma-6, dejando el oro en 25%, ganó las tres ventanas sin
darse vuelta y mantenerla costaba $4.880.898 sobre $20 millones en cinco años.
Ver `ESTRATEGIAS_ALPHADATA_v2.md` y `research/carteras_en_pesos/`.

El código y las series se conservan. **Se reabriría si apareciera una señal de
corredora que aporte**, medida con el mismo protocolo: aporte al conjunto y en
pesos, con los cortes fijados antes.

Y con esto **la carga del inbox deja de ser un requisito operativo**: las tres
piezas que quedan corren sólo con precios.

## El tope de concentración por posición, más allá del 25%

El límite del 25% está puesto como límite de cola. **No se reabre por
resultado**: la medición dice que cuesta 1,16 puntos anuales en Gamma-6 y
compra 2 puntos de peor caída, y eso ya se aceptó al ponerlo. Ver
`POLITICA_REBALANCEO.md`.

## Las nueve fechas ex que se apartan dos o tres ruedas

**Cerrado, no pendiente.** El desfase está censurado en cero y la distribución
58/34/8/1 es la forma de un instrumento con resolución de una rueda, no de dos
poblaciones. No traen evidencia de estar mal fechadas. Ver
`research/dividendos/CONFIRMACION_POR_CONTRASTE.md`.

## MALLPLAZA del 03-09-2026

Es el **único** dato sin respaldo de precio que sostiene una cifra publicada.
Corroborado en magnitud y calendario contra la fuente primaria, que no tiene
2026. **Se reabre cuando Mallplaza publique su dividendo de 2026.**

## Los tres asuntos que el panel de salud aparta

El panel del informe los deja fuera a propósito: **una alarma que siempre está
roja por una razón conocida deja de ser una alarma.** Están acá para que
apartarlos no sea una forma de esconderlos, y hay una prueba que exige que cada
uno tenga su entrada en este archivo.

**AESANDES**, congelado desde el 14-04-2025 y generando ruido en dos informes.
Hay que averiguar si está deslistado o renombrado y cerrarlo de una vez. No
afecta ningún número publicado: está fuera del universo operable.

**MULTIFOODS**, con una rueda de historia tras corregir el símbolo a
`MULTI-X.SN`. Queda fuera del universo de Sigma-6 hasta acumular 252 ruedas. Se
puede rellenar desde el archivo de investing.com que ya está validado.

**MALLPLAZA del 03-09-2026**, el dividendo de $30 sin respaldo de precio. Ver
más arriba.

## La razón del CDV: **confirmada**, uno a uno

Estaba abierto «hay que confirmarlo antes de comprar en real». Se confirmó
midiendo el precio del CDV contra su subyacente por el tipo de cambio, sobre las
ruedas en que el CDV de verdad transó: doce nombres entre **1,0001 y 1,0059**,
incluidos los de la cartera vigente de Gamma-6 y el oro. Ver
`research/spread_cambio/`.

Y de paso apareció un error que sí valía plata: **el símbolo anotado para Bank
of America era el de Boeing**. Corregido.

Queda una punta: **el símbolo del CDV de Exxon no se encontró** y quedó vacío en
vez de adivinado. XOM no está hoy en Gamma-6; si entra, hay que conseguirlo
antes de operarlo.

## `reconstruccion_historica.csv` cambia sin que cambie nada

Cada corrida reescribe las 1.249 filas y el diff sale de 1.027 líneas por
diferencias en el último dígito: la máxima diferencia relativa medida es
**1,3e-15**, precisión de flotante. El ruido tapa los cambios reales cuando los
haya. Se arregla redondeando la salida a una precisión que tenga sentido
—cuatro decimales sobre base 100 son diezmilésimas de punto— y no antes de que
alguien lo necesite.

## El contraste contra investing.com baja a trimestral

No se puede cerrar: las guardias miran variación y el contraste detecta un
precio que se mueve bien y está mal de nivel. Pero su valor no es detectar
rápido —un error de nivel es persistente, no urgente— así que trimestral cubre
lo mismo a un tercio del trabajo. Ver `DEPENDENCIAS_MANUALES.md`.
