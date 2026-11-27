# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 26-11-2026.

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
| ILC | ILC | 40 | $ 23.200 | $ 928.000 | $ 9.500 | 57 días | por ranking, sin fecha | $ 3.313 · 0,36% |
| ITAUCL | ITAUCL | 40 | $ 22.940 | $ 917.600 | $ 19.900 | 272 días | por ranking, sin fecha | $ 3.276 · 0,36% |
| ECL | ECL | 472 | $ 1.986 | $ 937.392 | $ 108 | 149 días | por ranking, sin fecha | $ 3.346 · 0,36% |
| CHILE | CHILE | 4.918 | $ 191 | $ 937.371 | $ 129 | 149 días | por ranking, sin fecha | $ 3.346 · 0,36% |
| BSANTANDER | BSANTANDER | 11.363 | $ 82 | $ 937.448 | $ 52 | 118 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 203 | $ 4.610 | $ 935.850 | $ 1.650 | 87 días | por ranking, sin fecha | $ 3.341 · 0,36% |
| VAPORES | VAPORES | 19.820 | $ 47 | $ 937.486 | $ 14 | 57 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| QUINENCO | QUINENCO | 209 | $ 4.480 | $ 936.320 | $ 1.180 | 27 días | por ranking, sin fecha | $ 3.343 · 0,36% |

Residuo de esta pieza: **$ 32.533**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| MRK | MRKCL.SN | 8 | $ 144.856 | $ 1.158.852 | $ 91.148 | 118 días | por ranking, sin fecha | $ 4.137 · 0,36% |
| CVX | CVXCL.SN | 5 | $ 217.816 | $ 1.089.082 | $ 160.918 | 57 días | por ranking, sin fecha | $ 3.888 · 0,36% |
| PFE | PFECL.SN | 42 | $ 29.386 | $ 1.234.228 | $ 15.772 | 27 días | por ranking, sin fecha | $ 4.406 · 0,36% |
| TGT | TGTCL.SN | 7 | $ 177.826 | $ 1.244.780 | $ 5.220 | 118 días | por ranking, sin fecha | $ 4.444 · 0,36% |
| AAPL | AAPLCL.SN | 3 | $ 367.154 | $ 1.101.462 | $ 148.538 | 27 días | por ranking, sin fecha | $ 3.932 · 0,36% |
| JNJ | JNJCL.SN | 4 | $ 282.857 | $ 1.131.427 | $ 118.573 | 27 días | por ranking, sin fecha | $ 4.039 · 0,36% |

Residuo de esta pieza: **$ 540.169**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 72 | $ 69.346 | $ 4.992.917 | $ 7.083 | 329 días | posición permanente | $ 17.825 · 0,36% |

Residuo de esta pieza: **$ 7.083**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.665** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.467.467 | $ 13.329 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 6.959.831 | $ 12.423 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.992.917 | $ 8.912 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 579.786 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.420.214 y quedan **$ 579.786** en caja, un 2,9%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

