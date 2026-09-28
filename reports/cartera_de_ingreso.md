# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 28-09-2026.

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
| PARAUCO | PARAUCO | 255 | $ 3.670 | $ 935.876 | $ 1.624 | 181 días | por ranking, sin fecha | $ 3.341 · 0,36% |
| BCI | BCI | 14 | $ 64.350 | $ 900.900 | $ 36.600 | 28 días | por ranking, sin fecha | $ 3.216 · 0,36% |
| MALLPLAZA | MALLPLAZA | 264 | $ 3.550 | $ 937.226 | $ 274 | 213 días | por ranking, sin fecha | $ 3.346 · 0,36% |
| ITAUCL | ITAUCL | 40 | $ 23.290 | $ 931.600 | $ 5.900 | 213 días | por ranking, sin fecha | $ 3.326 · 0,36% |
| ECL | ECL | 497 | $ 1.885 | $ 936.845 | $ 655 | 90 días | por ranking, sin fecha | $ 3.345 · 0,36% |
| CHILE | CHILE | 4.671 | $ 201 | $ 937.470 | $ 30 | 90 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | BSANTANDER | 11.406 | $ 82 | $ 937.459 | $ 41 | 59 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 190 | $ 4.910 | $ 932.900 | $ 4.600 | 28 días | por ranking, sin fecha | $ 3.330 · 0,36% |

Residuo de esta pieza: **$ 49.724**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| TGT | TGTCL.SN | 8 | $ 152.259 | $ 1.218.073 | $ 31.927 | 59 días | por ranking, sin fecha | $ 4.349 · 0,36% |
| INTC | INTCCL.SN | 11 | $ 111.511 | $ 1.226.617 | $ 23.383 | 363 días | por ranking, sin fecha | $ 4.379 · 0,36% |
| MRK | MRKCL.SN | 8 | $ 142.899 | $ 1.143.188 | $ 106.812 | 59 días | por ranking, sin fecha | $ 4.081 · 0,36% |
| BAC | BACCL.SN | 23 | $ 53.309 | $ 1.226.117 | $ 23.883 | 59 días | por ranking, sin fecha | $ 4.377 · 0,36% |
| JNJ | JNJCL.SN | 4 | $ 261.358 | $ 1.045.430 | $ 204.570 | 28 días | por ranking, sin fecha | $ 3.732 · 0,36% |
| ABT | ABTCL.SN | 12 | $ 97.047 | $ 1.164.562 | $ 85.438 | 28 días | por ranking, sin fecha | $ 4.157 · 0,36% |

Residuo de esta pieza: **$ 476.012**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 67 | $ 74.481 | $ 4.990.252 | $ 9.748 | 270 días | posición permanente | $ 17.815 · 0,36% |

Residuo de esta pieza: **$ 9.748**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.744** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.450.276 | $ 13.299 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 7.023.988 | $ 12.538 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.990.252 | $ 8.908 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 535.485 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.464.515 y quedan **$ 535.485** en caja, un 2,7%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

