# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 01-10-2026.

Se compra **la cartera vigente completa**, sin mirar si cada posición va
arriba o abajo del precio de entrada del modelo y sin saltarse las que
parezcan próximas a venderse. Las columnas de abajo son **información, no
un filtro**: ver `GUIA_INGRESO.md` para por qué.

## Órdenes a mercado, y el precio teórico es para después

**Las órdenes van a mercado, no con precio límite.** La pantalla de la
corredora muestra el último negocio, que puede ser de hace semanas: el día de
la primera compra IAUCL exhibió $76.500 durante toda la jornada —cierre
anterior, máximo, mínimo y último, los cuatro iguales, volumen cero— y llenó a
**$77.300**. Trii no llena al precio exhibido: cotiza fresco al ejecutar. Poner
un límite contra un precio rancio sólo agrega el riesgo de no llenar.

**El precio teórico de la tabla es para contrastar después, no para poner un
límite.** Es el subyacente en dólares por el tipo de cambio. Después de operar,
anotar en `data/operaciones_reales.csv` el precio de llenado de cada posición:
**si alguna se sale de ~1%, ahí sí hay algo que mirar.**

**Con una trampa que ya apareció en la primera orden.** El contraste va contra el
teórico **del día en que se ejecutó**, no contra el de esta tabla. El llenado de
IAUCL a $77.300 el 22-09 queda 1,98% bajo el teórico de esta guía, que es del
21-09 y se calculó con un cierre del subyacente de dos ruedas antes. Contra el
teórico del 22-09 la diferencia es 0,05%. **Si se contrasta contra la columna
impresa, la guardia va a sonar sola cada vez que el almacén venga un par de
ruedas atrasado.**

Para referencia de lo que es normal: en la orden del 22-09 el tipo de cambio
implícito en el precio pagado fue 946,49 contra los 947,57 que ofrecía la
pantalla de conversión de Trii el mismo día. **Difieren en 0,11%.**

## Delta-12

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| ILC | ILC | 37 | $ 24.800 | $ 917.600 | $ 19.900 | 1 días | por ranking, sin fecha | $ 3.276 · 0,36% |
| ITAUCL | ITAUCL | 41 | $ 22.799 | $ 934.759 | $ 2.741 | 216 días | por ranking, sin fecha | $ 3.337 · 0,36% |
| BCI | BCI | 14 | $ 65.000 | $ 910.000 | $ 27.500 | 31 días | por ranking, sin fecha | $ 3.249 · 0,36% |
| ECL | ECL | 509 | $ 1.840 | $ 936.560 | $ 940 | 93 días | por ranking, sin fecha | $ 3.344 · 0,36% |
| CHILE | CHILE | 4.908 | $ 191 | $ 937.428 | $ 72 | 93 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | BSANTANDER | 11.742 | $ 80 | $ 937.481 | $ 19 | 62 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 199 | $ 4.700 | $ 935.300 | $ 2.200 | 31 días | por ranking, sin fecha | $ 3.339 · 0,36% |
| VAPORES | VAPORES | 18.436 | $ 51 | $ 937.471 | $ 29 | 1 días | por ranking, sin fecha | $ 3.347 · 0,36% |

Residuo de esta pieza: **$ 53.401**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| INTC | INTCCL.SN | 10 | $ 116.722 | $ 1.167.216 | $ 82.784 | 366 días | por ranking, sin fecha | $ 4.167 · 0,36% |
| TGT | TGTCL.SN | 8 | $ 152.419 | $ 1.219.352 | $ 30.648 | 62 días | por ranking, sin fecha | $ 4.353 · 0,36% |
| MSFT | MSFTCL.SN | 2 | $ 498.790 | $ 997.581 | $ 252.419 | 1 días | por ranking, sin fecha | $ 3.561 · 0,36% |
| FCX | FCXCL.SN | 18 | $ 67.387 | $ 1.212.971 | $ 37.029 | 1 días | por ranking, sin fecha | $ 4.330 · 0,36% |
| MRK | MRKCL.SN | 8 | $ 139.881 | $ 1.119.049 | $ 130.951 | 62 días | por ranking, sin fecha | $ 3.995 · 0,36% |
| CVX | CVXCL.SN | 6 | $ 201.442 | $ 1.208.652 | $ 41.348 | 1 días | por ranking, sin fecha | $ 4.315 · 0,36% |

Residuo de esta pieza: **$ 575.180**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 65 | $ 76.326 | $ 4.961.203 | $ 38.797 | 273 días | posición permanente | $ 17.711 · 0,36% |

Residuo de esta pieza: **$ 38.797**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.509** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.446.599 | $ 13.292 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 6.924.820 | $ 12.361 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.961.203 | $ 8.856 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 667.378 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.332.622 y quedan **$ 667.378** en caja, un 3,3%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

