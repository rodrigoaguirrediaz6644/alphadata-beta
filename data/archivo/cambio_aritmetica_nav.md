# Cambio de aritmética del NAV reconstruido — 21-09-2026

La reconstrucción histórica pasa de calcular con **peso constante** a calcular
con **los pesos corriendo entre revisiones**, que es lo que dice
`POLITICA_REBALANCEO.md`.

La serie anterior queda en `reconstruccion_peso_constante_2026.csv`. No se
reescribe ni se encadena con la nueva.

## Por qué

`retorno_dia += peso * (precio_hoy/precio_ayer - 1)` con el peso fijo es la
aritmética de una cartera que vuelve al objetivo **todos los días**. El costo,
además, sólo se cobraba cuando cambiaba el objetivo, y partes iguales dan casi
siempre el mismo número: el rebalanceo salía gratis. Y como el modelo creía que
la posición ya estaba en su peso, la orden de recortar no se emitía nunca.

El NAV publicado describía una cartera que nadie tiene.

Se hace ahora y no más adelante porque **lo que se mueve es la reconstrucción,
no la serie en vivo**, que tiene cinco días y prácticamente no ha derivado.
Cada semana que pase vuelve el cambio más caro.

## Las cifras, antes y después

Ventana 2021-07-08 a 2026-07-15. Retorno anual y peor caída.

| serie | antes | ahora | |
|---|---|---|---|
| Sigma-6 | 355,40 · +28,75% · −17,3% | 229,88 · **+18,04%** · −19,9% | −10,7 pp |
| Delta-12 | 315,89 · +25,76% · −14,9% | 305,55 · **+24,93%** · −15,0% | −0,8 pp |
| Gamma-6 | 292,31 · +23,83% · −26,4% | 335,00 · **+27,24%** · −28,9% | +3,4 pp |
| Oro | 274,29 · +22,29% · −23,5% | igual | sin cambio |
| Conjunto | 321,85 · +26,23% · −9,5% | 297,72 · **+24,28%** · −9,1% | −2,0 pp |
| IPSA TR | 261,39 · +21,10% · −15,9% | igual | sin cambio |

Delta-12 y Gamma-6 se mueven lo medido: la aritmética explica los −0,8 y +3,4
puntos.

## Sigma-6: los 10,7 puntos, separados

La primera versión de este registro decía que las dos causas no se podían
separar. **Sí se pueden**, usando el banco de pruebas como punto intermedio:
el banco midió Sigma-6 con las reglas y los datos de hoy bajo las dos
políticas de rebalanceo, así que provee el eslabón que faltaba.

| tramo | de | a | cuánto | qué es |
|---|---|---|---|---|
| serie vieja → peso constante de hoy | +28,75% | +18,94% | **−9,8 pp** | corrección de datos y metodología |
| peso constante → pesos corriendo | +18,94% | +18,06% | **−0,9 pp** | el cambio de política |
| publicado | | +18,04% | | (la reconstrucción alinea fechas con `ffill`) |

**El número que importa no es el de la política sino el otro: la serie vieja
sobreestimaba el retorno anual de Sigma-6 en cerca de diez puntos.** Ésa es la
magnitud del defecto.

La causa es que **la serie de Sigma-6 nunca se reconstruía.** El pipeline
recalculaba Delta-12, Gamma-6 y Oro en cada corrida, y Sigma-6 se quedaba con
los valores congelados en `reconstruccion_historica.csv` desde antes del
incidente del feed: antes de reparar los precios chilenos de 2025-2026, antes
de reconstruir la tabla de dividendos, y antes de las correcciones de
metodología. Nadie la había vuelto a calcular.

Al agregarse `sigma6_historical_nav` —que no existía— la serie se recalcula por
primera vez con las reglas y los datos de hoy, y el +28,75% no sobrevive.

Lo que **no** se puede desglosar es el −9,8 dentro de sí mismo: cuánto es la
reparación de los precios chilenos, cuánto la tabla de dividendos y cuánto los
cambios de metodología, porque la serie anterior no dejó registro de cómo se
había calculado. Ver `CENSO_DE_SERIES.md`.

## Control

Las tres funciones de producción reproducen exactamente lo medido en el banco
de pruebas, con desvío máximo `0,00000000%` en las tres:

- `delta12_historical_nav` → 305,5538
- `gamma6_historical_nav` → 335,0014
- `sigma6_historical_nav` → 230,0763

El Oro no cambia porque es una sola posición: no hay pesos que corran.
`data/strategy_nav.csv`, la serie en vivo, no se toca.

# Dos cambios de regla posteriores, y lo que movieron — 21-09-2026

La serie de la reconstrucción se mueve cuando cambia una regla. Se anotan las
dos, con la cifra anterior al lado, porque un número publicado que se mueve sin
registro es la forma del defecto que este proyecto vino a terminar.

## La SMA200 entra en Sigma-6

| | antes | después | |
|---|---|---|---|
| Sigma-6 | 229,88 · +18,04% · −19,9% | 216,32 · **+16,62%** · −12,2% | −1,4 pp |
| Conjunto | 297,72 · +24,28% | 292,72 · **+23,86%** | −0,4 pp |

Baja el retorno y **baja mucho la peor caída**, de −19,9% a −12,2%. Es lo que
la medición decía —el retorno no se distingue, la caída mejora de forma
consistente— y ésa fue la regla con que se decidió. Ver
`research/sma200_sigma6/`.

Esta tabla faltaba: la regla se encendió sin dejar registro de lo que movió en
la serie publicada.

## Sale el tope de tenencia de 365 días

| | antes | después | |
|---|---|---|---|
| Sigma-6 | 216,32 · +16,62% · −12,2% | 217,16 · **+16,71%** · −13,0% | +0,1 pp |
| Conjunto | 292,72 · +23,86% | 293,05 · **+23,89%** | +0,03 pp |

Sube poco, y por la razón esperada: desaparecen dieciocho operaciones de costo
—nueve ventas y nueve recompras— que no cambiaban la cartera.

**El libro pasa de 276 a 272 filas**, todas en Sigma-6 (99 → 95). Delta-12,
Gamma-6 y el oro no se mueven ni una fila. Las nueve rotaciones se convierten en
cinco posiciones continuas:

| | antes | ahora |
|---|---|---|
| BCI | 11-10-2024 → 17-10-2025, y de nuevo 24-10-2025 → abierta | **11-10-2024 → abierta** |
| ITAUCL | 17-01-2025 → 23-01-2026, y 30-01-2026 → 15-05-2026 | 17-01-2025 → 15-05-2026 |
| LTM | 18-10-2024 → 24-10-2025, y 30-10-2025 → 06-03-2026 | 18-10-2024 → 06-03-2026 |
| MALLPLAZA | 16-08-2024 → 22-08-2025, y 29-08-2025 → 17-09-2025 | 16-08-2024 → 17-09-2025 |
| SALFACORP | 24-01-2025 → 30-01-2026, y 06-02-2026 | 24-01-2025 → 06-02-2026 |

**Ninguna selección cambió.** No aparece ni desaparece ningún nombre: el cupo
que liberaba una salida por tope nunca alcanzó a cambiar una elección, porque
Sigma-6 casi nunca tuvo diez candidatos. El único efecto es que las posiciones
dejan de partirse en dos.

**El bloque de movimientos no emitió ninguna orden**, verificado sobre esta
corrida: el informe dice «Sin cambios desde el informe anterior» aunque BCI haya
cambiado de fecha. Un cambio de fecha no es una operación.

## BCI queda con entrada anterior al piso de publicación

La tenencia continua de BCI arranca el **11-10-2024**, anterior al piso del
02-01-2025. La guardia del recorrido lo detectó y se negó a escribir el libro,
que es lo que tenía que hacer.

La regla del piso se afina: **una posición cerrada que entró antes del piso no
se publica; una posición abierta sí.** Ocultarle la fecha a una posición viva
es peor que mostrar una que viene de un tramo sin reparar, y es exactamente el
error del piso del reinicio, que fechaba todo el 17-09-2026 porque no sabía.
Queda marcada en `origen`.

**El precio de entrada de BCI, $28.195 del 11-10-2024, viene del tramo sin
reparar.** Lo que se pudo verificar: el factor de ajuste de la serie es
coherente (0,944190 antes del dividendo de marzo de 2025, 0,975207 entre los
dos, 1,0 después), así que el crudo es genuinamente crudo y el ajuste lo aplica
nuestra propia tabla. `relleno_sobrescrituras.csv` confirma que BCI sólo se
reparó desde el 28-03-2025.

### El precio de entrada de BCI, verificado

Quedó pegado al borde de un hueco conocido: **las tres ruedas siguientes —14, 15
y 16 de octubre de 2024— repiten el mismo cierre con volumen cero**, y la
fracción del mercado chileno sin variación esos días es 97,5%, 100% y 100%. Son
los tres días de octubre de 2024 que `guards.py` ya documenta como mercado
entero detenido en el dato viejo.

Tres comprobaciones, todas a favor del número:

1. **El 11-10-2024 fue rueda real.** Apertura 27.890, máximo 28.195, mínimo
   27.601, cierre 28.195, volumen 65.317. La fracción del mercado sin variación
   ese día fue 12,5%, dentro de la banda normal (mediana 10,3%, nunca sobre
   25,6% en periodo sano).
2. **El nivel sobrevive al hueco.** El 17-10, con el mercado normalizado (2,5%
   sin variación), BCI **abre en 28.200**: +0,02% sobre el cierre del 11-10. Si
   28.195 hubiera sido un nivel falso o rancio, el mercado no habría reabierto
   encima de él.
3. **La serie de 2024 no viene ajustada por dividendos.** Era el riesgo real —el
   defecto tipo SALFACORP, donde el tramo viejo está ajustado y el nivel sale
   deflactado—. La reparación del 28-03-2025 corrigió **cinco ruedas
   consecutivas, todas por exactamente −3,17%**, que es el ajuste del dividendo
   de marzo de 2025 (caída esperada −3,2754%). Cinco ruedas es el
   `DESFASE_POR_CONVENCION` que ya está documentado: el proveedor aplica la
   caída con cinco sesiones de retraso. **Una serie retroajustada no mostraría
   ninguna caída**; ésta la muestra, tarde. Así que el nivel de 2024 es crudo y
   no está deflactado por dividendos posteriores.

**Lo que no se pudo verificar:** no existe fuente externa que cubra BCI en 2024.
El relleno de investing.com abarcó once instrumentos desde 2025, y el 2024 de
BCI es Yahoo original. El riesgo residual queda acotado: si el nivel estuviera
corrido por un dividendo, el error sería del orden de 3%, y el +146,4% pasaría
a ~+143%. No es un orden de magnitud.

Lo que sí quedó sin confirmar, y es otra cosa: **los dos dividendos de BCI
entraron por convención y nunca se confirmaron por precio** —`caida_observada`
va vacía en los dos—. Eso no afecta el precio de entrada, que es crudo, pero sí
entra en la variación publicada.
