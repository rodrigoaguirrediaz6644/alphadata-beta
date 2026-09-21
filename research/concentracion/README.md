# Concentración chilena: ¿son dos estrategias o una con dos nombres?

Con cuatro piezas al 25%, la mitad de la cartera está en acciones chilenas.
Sigma-6 y Delta-12 operan el mismo mercado. La objeción es estructural y se
responde midiendo.

## Diagnóstico: se parecen en el resultado, no en la cartera

| | limpia (2025-2026) | larga (2021-2026) |
|---|---|---|
| correlación mensual Sigma-6 / Delta-12 | **0,914** | **0,829** |
| nombres en común | 3,3 de 8,6 y 7,8 | 3,0 de 10,3 y 7,4 |
| Jaccard | 0,25 | 0,22 |
| peso solapado | 31,9% | 26,3% |
| caja media de Sigma-6 | 17% (rango 0-60%) | 13% (rango 0-60%) |
| caja media de Delta-12 | 3% | 5% |

Contra el resto de las piezas, en la ventana limpia: Sigma/Gamma **−0,21**,
Delta/Gamma **−0,18**, Sigma/Oro 0,15, Delta/Oro 0,34. Las dos chilenas se
parecen muchísimo más entre sí que a cualquier otra cosa de la cartera.

Pero **no comparten la cartera**: sólo un tercio de los nombres de Sigma-6 está
también en Delta-12, y el peso solapado no llega a un tercio. La correlación de
0,83-0,91 viene del mercado, no de tener los mismos papeles. Son dos selecciones
distintas del mismo mercado, y el mercado explica casi todo.

La diferencia real de estructura es **la caja**: Sigma-6 promedia 13-17% y llega
a 60% cuando hay pocas elegibles; Delta-12 está siempre invertida. Es el único
mecanismo automático de desexposición que tiene el sistema completo, y no
aparece en la correlación de retornos.

### Las fechas de los mínimos

En la ventana larga caen con un día de diferencia: Sigma-6 el 31-10-2023,
Delta-12 el 30-10. En la limpia no: 06-03-2026 y 19-05-2026. La explicación es
que en 2023 hubo una caída de mercado grande y común que dominó a las dos; en
2025-2026 no hubo un evento así, y veinte meses son pocos, así que el máximo
retroceso de cada una lo produce un episodio propio. Coinciden cuando el
mercado manda y difieren cuando no — que es otra forma de decir lo mismo que la
correlación.

## Los cinco esquemas, a $20 millones

| esquema | Chile | anual limpia | caída | anual larga | caída | costo/año | % cap |
|---|---|---|---|---|---|---|---|
| 1 actual: cuatro al 25% | 50% | **29,23%** | -8,0% | 21,33% | **-8,0%** | $272.730 | 1,36% |
| 2 sin Sigma-6 | 33% | 26,94% | -8,5% | **22,63%** | -9,7% | $181.887 | 0,91% |
| 3 sin Delta-12 *(control)* | 33% | 27,18% | -8,0% | 20,27% | -9,7% | **$124.177** | **0,62%** |
| 4 parejo por mercado | 33% | 25,16% | -8,0% | 19,68% | -9,6% | $279.397 | 1,40% |
| 5 Chile al 40% | 40% | 26,88% | **-7,5%** | 20,31% | -8,4% | $276.730 | 1,38% |

**El orden de retorno se da vuelta entre ventanas.** Gana el esquema actual en
la limpia y el esquema sin Sigma-6 en la larga. Por el protocolo acordado, eso
es no poder distinguir.

Y el control hace su trabajo: en la ventana limpia quitar Sigma-6 (26,94%) y
quitar Delta-12 (27,18%) dan casi lo mismo, así que **lo que manda es la
exposición a Chile y no cuál estrategia se va**. En la larga sí difieren, 2,4
puntos a favor de conservar Delta-12. Tampoco eso es consistente.

## El aporte marginal de la segunda chilena

| | retorno | peor caída | costo |
|---|---|---|---|
| **limpia** — agregar Sigma-6 a Delta-12+Gamma-6+Oro | +2,29pp | **−0,5pp** | +$90.843 |
| **limpia** — agregar Delta-12 a Sigma-6+Gamma-6+Oro | +2,05pp | 0,0pp | +$148.553 |
| **larga** — agregar Sigma-6 a Delta-12+Gamma-6+Oro | −1,30pp | **−1,7pp** | +$90.843 |
| **larga** — agregar Delta-12 a Sigma-6+Gamma-6+Oro | +1,06pp | **−1,7pp** | +$148.553 |

El retorno cambia de signo. **La caída mejora en las cuatro combinaciones**, y
mejora lo mismo agregando cualquiera de las dos: 1,7 puntos en la ventana
larga. O sea, lo que aporta la cuarta pieza es amortiguación, no retorno, y da
igual cuál de las dos chilenas sea.

## Lo que este estudio sí establece, sin depender de ninguna muestra

**El peaje es plano, así que bajar el peso chileno sin quitar una estrategia
empeora el costo por peso invertido en Chile.** El esquema 4 pone 33% en Chile
—$6,67 millones— y paga los mismos $252.730 de mínimos que el esquema 1 con
50%. Eso es 3,79% de lo invertido en Chile, contra 2,53% del esquema actual.

De ahí sale el resultado más sólido del estudio: **si la preocupación es la
concentración, repartir por mercado es la forma cara de arreglarla y quitar una
estrategia es la barata.** El esquema 4 es además el de menor retorno en las dos
ventanas y el de mayor costo. No hay ninguna lectura en que convenga.

Lo determinista, en pesos al año sobre $20 millones:

| | ahorro anual | % del capital |
|---|---|---|
| quitar Sigma-6 | $90.843 | 0,45% |
| quitar Delta-12 | $148.553 | 0,74% |

## Recomendación

**Por retorno no se puede distinguir entre los cinco esquemas.** El orden se da
vuelta entre ventanas, y las ventanas ni siquiera son independientes: la limpia
está contenida en la larga, así que no son dos pruebas sino una muestra partida
de dos maneras. Cualquier esquema que gane en las dos está diciendo algo del
periodo, no de la estructura.

La decisión se toma por costo y estructura, y ahí:

1. **Descartar el esquema 4.** Es la forma cara de bajar la exposición chilena,
   con el peor retorno en las dos ventanas y el costo más alto. La objeción de
   concentración es legítima pero este no es el modo de responderla.
2. **No quitar ninguna estrategia con esta evidencia.** La cuarta pieza compra
   1,7 puntos de menor caída de forma consistente, y quitar una ahorra entre
   0,45% y 0,74% al año. Es un trato parejo, y el lado del ahorro es cierto
   mientras el de la caída no lo es del todo.
3. **Si aun así hay que quitar una, el costo dice Delta-12 y la estructura dice
   Sigma-6**, y apuntan en direcciones opuestas. Quitar Delta-12 ahorra
   $148.553 contra $90.843; pero Sigma-6 es la única pieza del sistema con un
   mecanismo automático de caja —hasta 60%— y quitarla deja la mitad chilena
   permanentemente invertida al 100%.

El resultado honesto es que la objeción estructural es correcta —50% en un solo
mercado, con dos estrategias que correlacionan 0,9— y que ninguno de los
arreglos propuestos se puede justificar por retorno. Lo único que se sabe con
certeza es cuánto cuesta cada uno.
