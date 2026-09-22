# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 21-09-2026.

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
| PARAUCO | PARAUCO | 240 | $ 3.899 | $ 935.736 | $ 1.764 | 174 días | por ranking, sin fecha | $ 3.341 · 0,36% |
| BCI | BCI | 14 | $ 66.748 | $ 934.472 | $ 3.028 | 21 días | por ranking, sin fecha | $ 3.336 · 0,36% |
| MALLPLAZA | MALLPLAZA | 246 | $ 3.803 | $ 935.464 | $ 2.036 | 206 días | por ranking, sin fecha | $ 3.340 · 0,36% |
| ITAUCL | ITAUCL | 38 | $ 24.149 | $ 917.662 | $ 19.838 | 206 días | por ranking, sin fecha | $ 3.276 · 0,36% |
| ECL | ECL | 493 | $ 1.900 | $ 936.700 | $ 800 | 83 días | por ranking, sin fecha | $ 3.344 · 0,36% |
| CHILE | CHILE | 4.699 | $ 200 | $ 937.450 | $ 50 | 83 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | BSANTANDER | 11.391 | $ 82 | $ 937.479 | $ 21 | 52 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 191 | $ 4.900 | $ 935.900 | $ 1.600 | 21 días | por ranking, sin fecha | $ 3.341 · 0,36% |

Residuo de esta pieza: **$ 29.136**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| TGT | TGTCL.SN | 8 | $ 151.389 | $ 1.211.112 | $ 38.888 | 52 días | por ranking, sin fecha | $ 4.324 · 0,36% |
| INTC | INTCCL.SN | 10 | $ 116.899 | $ 1.168.991 | $ 81.009 | 356 días | por ranking, sin fecha | $ 4.173 · 0,36% |
| MRK | MRKCL.SN | 8 | $ 143.508 | $ 1.148.064 | $ 101.936 | 52 días | por ranking, sin fecha | $ 4.099 · 0,36% |
| BAC | BACCL.SN | 22 | $ 55.637 | $ 1.224.013 | $ 25.987 | 52 días | por ranking, sin fecha | $ 4.370 · 0,36% |
| JNJ | JNJCL.SN | 4 | $ 258.670 | $ 1.034.679 | $ 215.321 | 21 días | por ranking, sin fecha | $ 3.694 · 0,36% |
| ABT | ABTCL.SN | 12 | $ 98.853 | $ 1.186.231 | $ 63.769 | 21 días | por ranking, sin fecha | $ 4.235 · 0,36% |

Residuo de esta pieza: **$ 526.911**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 63 | $ 78.397 | $ 4.938.990 | $ 61.010 | 263 días | posición permanente | $ 17.632 · 0,36% |

Residuo de esta pieza: **$ 61.010**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.599** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.470.864 | $ 13.335 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 6.973.089 | $ 12.447 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.938.990 | $ 8.816 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 617.057 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.382.943 y quedan **$ 617.057** en caja, un 3,1%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

