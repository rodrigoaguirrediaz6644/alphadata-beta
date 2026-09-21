# Cinco esquemas de ponderación del conjunto, con el costo completo

Los esquemas están fijados de antemano. Las ponderaciones que dependen de la
volatilidad se recalculan en cada reequilibrio con los doce meses anteriores,
así que son reglas implementables y no lecturas del futuro.

## Primero: dos de los cinco son el mismo esquema

"Oro anclado en 25% con el resto parejo" reparte el 75% restante entre tres
piezas: 25% a cada una. Con cuatro piezas **es idéntico al peso igual**. Se
conserva en las tablas para que se vea, pero no es una alternativa distinta.
Quedan cuatro esquemas reales.

## El modelo de costos

La comisión variable ya venía en el NAV de cada pieza. Se agregan:

- **La tarifa mínima de $1.990**, sólo en las piezas chilenas, cobrando el
  exceso sobre el porcentual ya contado. Entra por la rotación interna —medida:
  Sigma-6 50 operaciones al año, Delta-12 80— y por el reequilibrio entre piezas.
- **El reequilibrio mensual**, con una banda de disparo de 0,5%: si ninguna
  pieza se apartó más que eso, no se opera. Corregir sólo algunas y reescalar
  movería a las demás sin operarlas, así que se reequilibra todo o nada.

## Retorno anual neto por capital total

### Ventana limpia (02-01-2025 a 17-09-2026)

| esquema | $8M | $20M | $50M | $100M | peor caída |
|---|---|---|---|---|---|
| peso igual | 23,50% | 29,23% | 31,32% | 31,71% | **-8,7%** |
| **inverso a volatilidad** | **25,32%** | **31,33%** | **33,33%** | **33,74%** | -9,9% |
| paridad de riesgo | 24,11% | 30,27% | 32,40% | 32,84% | -9,8% |
| oro 25% + resto parejo | 23,50% | 29,23% | 31,32% | 31,71% | -8,7% |
| oro 25% + resto inv. vol | 24,10% | 30,06% | 32,13% | 32,55% | -9,8% |

### Ventana larga (08-07-2021 a 17-09-2026)

| esquema | $8M | $20M | $50M | $100M | peor caída |
|---|---|---|---|---|---|
| peso igual | 15,65% | 21,33% | 23,36% | 23,72% | **-8,8%** |
| **inverso a volatilidad** | **17,04%** | **23,00%** | **24,89%** | **25,27%** | -9,9% |
| paridad de riesgo | 15,74% | 21,63% | 23,53% | 23,89% | -9,8% |
| oro 25% + resto parejo | 15,65% | 21,33% | 23,36% | 23,72% | -8,8% |
| oro 25% + resto inv. vol | 16,30% | 22,22% | 24,19% | 24,57% | -9,9% |

El capital cambia el nivel —de $8M a $100M hay entre 8 y 10 puntos anuales, que
es el peso de la tarifa mínima— pero **no cambia el orden**. El mismo esquema
gana en los cuatro niveles y en las dos ventanas.

## La frontera por techo de caída

Ninguno de los cinco esquemas supera el 10% de caída en ninguna de las dos
ventanas. **Los tres techos —10%, 15% y 20%— no restringen nada**, así que la
frontera devuelve el mismo esquema en las doce celdas: inverso a volatilidad.
Un techo que discriminara tendría que estar cerca del 9%, y ahí sólo pasarían
peso igual y su gemelo.

## Validación cruzada

Pesos ajustados en una submuestra y medidos en la otra, en ambos sentidos, a
$20M:

| | primero | ¿coincide el orden completo? |
|---|---|---|
| limpia, A→B | inverso a volatilidad | |
| limpia, B→A | inverso a volatilidad | no, los puestos 2 a 5 se barajan |
| larga, A→B | inverso a volatilidad | |
| larga, B→A | inverso a volatilidad | sí |

**El primer lugar no se da vuelta en ninguna de las cuatro pruebas.** El resto
del orden sí se baraja en la ventana limpia, así que entre paridad de riesgo,
peso igual y la variante con oro anclado no hay nada que distinguir.

La conclusión no es "no se puede distinguir, quedarse con peso igual". Es más
acotada: **inverso a volatilidad primero, con consistencia; los otros tres,
indistinguibles entre sí.** La ventaja es de 1,4 a 2,1 puntos anuales sobre peso
igual, a cambio de 1,1 a 1,2 puntos más de peor caída.

## La referencia, que no es una propuesta

La mejor combinación fija en rejilla de 10%:

| ventana | mejor combinación | anual | caída |
|---|---|---|---|
| limpia | Sigma-6 **100%** | 43,80% | -13,0% |
| larga | Delta-12 90% + Gamma-6 10% | 32,16% | -13,3% |

Dos cosas que esto dice, y ninguna es "hay que concentrar". Primero, cuánto
deja sobre la mesa cualquier regla: entre 9 y 12 puntos anuales. Segundo, y más
importante, **el óptimo no se parece a sí mismo entre ventanas**: en una es todo
Sigma-6 y en la otra casi todo Delta-12, sin una sola pieza en común. Optimizar
las ponderaciones habría producido dos respuestas incompatibles con la misma
confianza, y las dos abandonan la razón de tener cuatro piezas.

## Advertencia sobre el material

La ventana limpia son veinte meses, y en ella el conjunto quedó por debajo del
mercado: 168,1 contra 170,3 del MSCI IPSA Gross. Cualquier esquema favorecido
ahí puede estarlo por el periodo. Que el resultado se repita en la ventana
larga es lo que le da peso, y esa ventana arrastra sus propios defectos
conocidos: reconstrucción retrospectiva, sesgo de supervivencia, y los datos
anteriores a 2025 sin reparar.

## Dependencia

Este estudio mide las reglas oficiales vigentes. Si cambia el filtro RSI de
Delta-12, hay que rehacerlo.
