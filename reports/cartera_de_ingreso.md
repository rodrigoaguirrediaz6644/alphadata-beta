# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 15-10-2026.

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
| ILC | ILC | 37 | $ 25.200 | $ 932.400 | $ 5.100 | 15 días | por ranking, sin fecha | $ 3.329 · 0,36% |
| ITAUCL | ITAUCL | 40 | $ 23.200 | $ 928.000 | $ 9.500 | 230 días | por ranking, sin fecha | $ 3.313 · 0,36% |
| BCI | BCI | 14 | $ 65.143 | $ 912.002 | $ 25.498 | 45 días | por ranking, sin fecha | $ 3.256 · 0,36% |
| ECL | ECL | 504 | $ 1.860 | $ 937.440 | $ 60 | 107 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| CHILE | CHILE | 4.893 | $ 192 | $ 937.499 | $ 1 | 107 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | BSANTANDER | 11.602 | $ 81 | $ 937.442 | $ 58 | 76 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | ANDINA-B | 195 | $ 4.800 | $ 936.000 | $ 1.500 | 45 días | por ranking, sin fecha | $ 3.342 · 0,36% |
| VAPORES | VAPORES | 18.821 | $ 50 | $ 937.474 | $ 26 | 15 días | por ranking, sin fecha | $ 3.347 · 0,36% |

Residuo de esta pieza: **$ 41.744**, que queda en su caja.

## Gamma-6

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| INTC | INTCCL.SN | 13 | $ 93.926 | $ 1.221.039 | $ 28.961 | 380 días | por ranking, sin fecha | $ 4.359 · 0,36% |
| TGT | TGTCL.SN | 8 | $ 154.259 | $ 1.234.069 | $ 15.931 | 76 días | por ranking, sin fecha | $ 4.406 · 0,36% |
| MSFT | MSFTCL.SN | 2 | $ 531.273 | $ 1.062.546 | $ 187.454 | 15 días | por ranking, sin fecha | $ 3.793 · 0,36% |
| FCX | FCXCL.SN | 18 | $ 68.999 | $ 1.241.987 | $ 8.013 | 15 días | por ranking, sin fecha | $ 4.434 · 0,36% |
| MRK | MRKCL.SN | 8 | $ 142.992 | $ 1.143.935 | $ 106.065 | 76 días | por ranking, sin fecha | $ 4.084 · 0,36% |
| CVX | CVXCL.SN | 5 | $ 215.999 | $ 1.079.997 | $ 170.003 | 15 días | por ranking, sin fecha | $ 3.856 · 0,36% |

Residuo de esta pieza: **$ 516.427**, que queda en su caja.

## Oro

| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---|---:|---:|---:|---:|---:|---|---:|
| IAU | IAUCL.SN | 64 | $ 77.282 | $ 4.946.046 | $ 53.954 | 287 días | posición permanente | $ 17.657 · 0,36% |

Residuo de esta pieza: **$ 53.954**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 34.607** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.458.256 | $ 13.313 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 6.983.573 | $ 12.466 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |
| Oro | $ 4.946.046 | $ 8.829 | 0,15% + IVA = 0,1785%, con mínimo de $999,99 |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso
durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió
al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque
la base no son $20 millones. El redondeo a unidades enteras deja $ 612.125 sin
invertir, y sobre lo que sí se invierte la cuenta da exacta.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.387.875 y quedan **$ 612.125** en caja, un 3,1%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

