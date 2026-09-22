# Cartera de ingreso

Lo que compra hoy el que entra, al cierre del 21-09-2026.

Se compra **la cartera vigente completa**, sin mirar si cada posición va
arriba o abajo del precio de entrada del modelo y sin saltarse las que
parezcan próximas a venderse. Las columnas de abajo son **información, no
un filtro**: ver `GUIA_INGRESO.md` para por qué.

## Delta-12

| acción | unidades | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---:|---:|---:|---:|---|---:|
| PARAUCO | 240 | $ 935.736 | $ 1.764 | 174 días | por ranking, sin fecha | $ 3.341 · 0,36% |
| BCI | 14 | $ 934.472 | $ 3.028 | 21 días | por ranking, sin fecha | $ 3.336 · 0,36% |
| MALLPLAZA | 246 | $ 935.464 | $ 2.036 | 206 días | por ranking, sin fecha | $ 3.340 · 0,36% |
| ITAUCL | 38 | $ 917.662 | $ 19.838 | 206 días | por ranking, sin fecha | $ 3.276 · 0,36% |
| ECL | 493 | $ 936.700 | $ 800 | 83 días | por ranking, sin fecha | $ 3.344 · 0,36% |
| CHILE | 4.699 | $ 937.450 | $ 50 | 83 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| BSANTANDER | 11.391 | $ 937.479 | $ 21 | 52 días | por ranking, sin fecha | $ 3.347 · 0,36% |
| ANDINA-B | 191 | $ 935.900 | $ 1.600 | 21 días | por ranking, sin fecha | $ 3.341 · 0,36% |

Residuo de esta pieza: **$ 29.136**, que queda en su caja.

## Gamma-6

| acción | unidades | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---:|---:|---:|---:|---|---:|
| TGT | 8 | $ 1.213.634 | $ 36.366 | 52 días | por ranking, sin fecha | $ 2.427 · 0,20% |
| INTC | 12 | $ 1.249.769 | $ 231 | 356 días | por ranking, sin fecha | $ 2.500 · 0,20% |
| MRK | 8 | $ 1.126.787 | $ 123.213 | 52 días | por ranking, sin fecha | $ 2.254 · 0,20% |
| BAC | 22 | $ 1.217.988 | $ 32.012 | 52 días | por ranking, sin fecha | $ 2.436 · 0,20% |
| JNJ | 4 | $ 1.035.682 | $ 214.318 | 21 días | por ranking, sin fecha | $ 2.071 · 0,20% |
| ABT | 12 | $ 1.180.836 | $ 69.164 | 21 días | por ranking, sin fecha | $ 2.362 · 0,20% |

Residuo de esta pieza: **$ 475.306**, que queda en su caja.

## Oro

| acción | unidades | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |
|---|---:|---:|---:|---:|---|---:|
| IAU | 63 | $ 4.968.090 | $ 31.910 | 263 días | posición permanente | $ 9.936 · 0,20% |

Residuo de esta pieza: **$ 31.910**, que queda en su caja.

## Lo que va a cobrar la corredora el primer día

Comprar las 15 posiciones cuesta **$ 25.328** en comisiones.

| pieza | se invierte | comisión | tarifa |
|---|---:|---:|---|
| Delta-12 | $ 7.470.864 | $ 13.335 | 0,1785%, con mínimo de $999,99 |
| Gamma-6 | $ 7.024.694 | $ 7.025 | 0,1% de CDV, sin mínimo |
| Oro | $ 4.968.090 | $ 4.968 | 0,1% de CDV, sin mínimo |

**Ninguna posición paga el mínimo**: todas superan el umbral de $ 560.218, bajo el cual el mínimo sale más caro que el porcentual.

**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones. Sólo
Delta-12 paga la tarifa chilena; Gamma-6 y el oro se compran como CDV y pagan 0,1% sin
mínimo. Y el redondeo a unidades enteras deja parte del capital sin invertir, así que
la base tampoco son $20 millones.

Este número es lo primero que se puede contrastar contra la boleta de la corredora, y
es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo
está mal y hay que corregirlo antes de que la diferencia se acumule.

## El residuo del redondeo

Las acciones se transan por **unidades enteras, hacia abajo, residuo a la caja de la pieza**. De $ 20.000.000 de referencia se gastan $ 19.463.648 y quedan **$ 536.352** en caja, un 2,7%.

**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso
es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una
posición donde caben cinco unidades deja mucho más suelto que una donde caben
veinte mil.

Para los CDV estadounidenses **hay que confirmar con la corredora si admiten
fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y
aquí vale plata: es donde se concentra el residuo.

