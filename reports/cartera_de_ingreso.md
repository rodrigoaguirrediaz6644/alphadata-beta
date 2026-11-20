# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 19-11-2026.

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
| ILC | ILC | 41 | $ 22.700 | $ 930.700 | $ 6.800 | 50 días | por ranking, sin fecha | $ 3.323 · 0,36% |
| ITAUCL | ITAUCL | 40 | $ 22.950 | $ 918.000 | $ 19.500 | 265 días | por ranking, sin fecha | $ 3.277 · 0,36% |
| ECL | ECL | 477 | $ 1.965 | $ 937.305 | $ 195 | 142 días | por ranking, sin fecha | $ 3.346 · 0,36% |
| CHILE | CHILE | 4.955 | $ 189 | $ 937.486 | $ 14 | 142 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | BSANTANDER | 12.082 | $ 78 | $ 937.442 | $ 58 | 111 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 196 | $ 4.771 | $ 935.116 | $ 2.384 | 80 días | por ranking, sin fecha | $ 3.338 · 0,36% |
| VAPORES | VAPORES | 19.576 | $ 48 | $ 937.495 | $ 5 | 50 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| QUINENCO | QUINENCO | 207 | $ 4.523 | $ 936.261 | $ 1.239 | 20 días | por ranking, sin fecha | $ 3.342 · 0,36% |

Residuo de esta pieza: **$ 30.195**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| MRK | MRKCL.SN | 9 | $ 133.580 | $ 1.202.223 | $ 47.777 | 111 días | por ranking, sin fecha | $ 4.292 · 0,36% |
| CVX | CVXCL.SN | 6 | $ 207.698 | $ 1.246.186 | $ 3.814 | 50 días | por ranking, sin fecha | $ 4.449 · 0,36% |
| PFE | PFECL.SN | 45 | $ 27.700 | $ 1.246.488 | $ 3.512 | 20 días | por ranking, sin fecha | $ 4.450 · 0,36% |
| TGT | TGTCL.SN | 7 | $ 168.431 | $ 1.179.019 | $ 70.981 | 111 días | por ranking, sin fecha | $ 4.209 · 0,36% |
| AAPL | AAPLCL.SN | 3 | $ 351.235 | $ 1.053.706 | $ 196.294 | 20 días | por ranking, sin fecha | $ 3.762 · 0,36% |
| JNJ | JNJCL.SN | 4 | $ 268.689 | $ 1.074.758 | $ 175.242 | 20 días | por ranking, sin fecha | $ 3.837 · 0,36% |

Residuo de esta pieza: **$ 497.620**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 72 | $ 69.119 | $ 4.976.538 | $ 23.462 | 322 días | posición permanente | $ 17.766 · 0,36% |

Residuo de esta pieza: **$ 23.462**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.716** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.469.805 | $ 13.334 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 7.002.380 | $ 12.499 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.976.538 | $ 8.883 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 551.278 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.448.722 y quedan **$ 551.278** en caja, un 2,8%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

