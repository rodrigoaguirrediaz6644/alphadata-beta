# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 12-11-2026.

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
| ILC | ILC | 41 | $ 22.630 | $ 927.830 | $ 9.670 | 43 días | por ranking, sin fecha | $ 3.312 · 0,36% |
| ITAUCL | ITAUCL | 41 | $ 22.710 | $ 931.110 | $ 6.390 | 258 días | por ranking, sin fecha | $ 3.324 · 0,36% |
| ECL | ECL | 468 | $ 2.000 | $ 936.000 | $ 1.500 | 135 días | por ranking, sin fecha | $ 3.342 · 0,36% |
| CHILE | CHILE | 4.856 | $ 193 | $ 937.354 | $ 146 | 135 días | por ranking, sin fecha | $ 3.346 · 0,36% |
| BSANTANDER | BSANTANDER | 11.711 | $ 80 | $ 937.466 | $ 34 | 104 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 195 | $ 4.789 | $ 933.835 | $ 3.665 | 73 días | por ranking, sin fecha | $ 3.334 · 0,36% |
| VAPORES | VAPORES | 19.470 | $ 48 | $ 937.480 | $ 20 | 43 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| QUINENCO | QUINENCO | 208 | $ 4.500 | $ 936.000 | $ 1.500 | 13 días | por ranking, sin fecha | $ 3.342 · 0,36% |

Residuo de esta pieza: **$ 22.925**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| MRK | MRKCL.SN | 8 | $ 144.509 | $ 1.156.073 | $ 93.927 | 104 días | por ranking, sin fecha | $ 4.127 · 0,36% |
| CVX | CVXCL.SN | 5 | $ 212.756 | $ 1.063.782 | $ 186.218 | 43 días | por ranking, sin fecha | $ 3.798 · 0,36% |
| PFE | PFECL.SN | 44 | $ 28.351 | $ 1.247.450 | $ 2.550 | 13 días | por ranking, sin fecha | $ 4.453 · 0,36% |
| TGT | TGTCL.SN | 7 | $ 158.227 | $ 1.107.592 | $ 142.408 | 104 días | por ranking, sin fecha | $ 3.954 · 0,36% |
| AAPL | AAPLCL.SN | 3 | $ 348.985 | $ 1.046.956 | $ 203.044 | 13 días | por ranking, sin fecha | $ 3.738 · 0,36% |
| JNJ | JNJCL.SN | 4 | $ 278.811 | $ 1.115.243 | $ 134.757 | 13 días | por ranking, sin fecha | $ 3.981 · 0,36% |

Residuo de esta pieza: **$ 762.903**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 69 | $ 71.581 | $ 4.939.086 | $ 60.914 | 315 días | posición permanente | $ 17.633 · 0,36% |

Residuo de esta pieza: **$ 60.914**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.189** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.477.075 | $ 13.347 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 6.737.097 | $ 12.026 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.939.086 | $ 8.816 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 846.742 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.153.258 y quedan **$ 846.742** en caja, un 4,2%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

