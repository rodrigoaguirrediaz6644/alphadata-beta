# Aporte marginal al conjunto: cuál cuarta pieza suma, si alguna

Sigma-6 no es una estrategia independiente: **es una de cuatro piezas.** Un
retroceso alto no es un defecto si no coincide con los de las otras tres. El
estudio anterior ordenó catorce corredoras por su resultado individual, que no
dice cuál sirve como complemento.

## Los cuatro candidatos y las reglas, fijados antes de medir

- **A — Sigma-6 v2.3.0, la actual.** Credicorp, momentum 12-1 > 0, sobre
  SMA200, tope 10%, semanal.
- **B — Consenso-6.** Las seis de v1.0.0, suma de señales, entrada con neto
  positivo, peso proporcional, tope 10%, salida con neto no positivo o 365
  días.
- **C — Fórmula inicial** del libro v6, **con las catorce corredoras de cien
  recomendaciones o más**, no con las seis: calidad histórica con shrinkage
  hacia 50%, decaimiento de vigencia a 180 días, confianza, liquidez, tope 12%,
  tope 5% para baja liquidez, máximo 12 posiciones.
- **D — Sin corredora.** Sólo momentum y SMA200, top 10 al 10%. Es el piso.

Cortes: selección hasta 31-12-2023, evaluación desde 01-01-2024. Costos de
Trii, 0,1785% con mínimo $999,99; 0,1% sin mínimo en lo estadounidense.
Capital $5.000.000 por pieza, con $2.500.000 de sensibilidad.

### Tres cosas que hay que declarar antes de leer los números

**El archivo no trae precio objetivo**, así que en la fórmula C el término de
precisión de target (peso 0,2) y la penalización por dispersión **no se pueden
calcular**. Sustituirlos por sus valores por defecto —0,5 y 0,75— hunde la
confianza por debajo de su propio umbral de 0,50 y **la fórmula no abre ninguna
posición en cinco años**; ésa fue la primera corrida. Lo correcto al faltar un
término es renormalizar los pesos (0,5 acierto + 0,5 exceso) y no penalizar una
dispersión desconocida. Aun así, **C corre sin uno de sus tres componentes.**

**La fórmula original rebalancea a diario.** Acá corre sobre el mismo
calendario semanal que los demás, para que el modelo de costo sea comparable.

**Un defecto propio, corregido:** en la primera corrida el oro nunca se compró
—la primera sesión sale antes de aplicar objetivos— así que el conjunto de tres
piezas era en realidad de dos. Los números de abajo son los de la corrida
corregida.

## Correlación, solape y concentración

| candidato | Delta-12 | Gamma-6 | Oro | solape con Δ12 | posiciones |
|---|---|---|---|---|---|
| A Sigma-6 actual | 0,77 | 0,12 | 0,06 | 0,23 | 7,8 |
| B Consenso-6 | 0,70 | −0,05 | 0,03 | 0,23 | 29,7 |
| **C Fórmula inicial** | **0,40** | −0,10 | **−0,14** | **0,00** | 3,9 |
| D Sin corredora | **0,81** | −0,04 | 0,05 | **0,38** | 9,3 |

Por estas métricas **C es de lejos la más diversificadora** y D la que menos.

## Coincidencia de los peores momentos

| | sus tres peores caídas |
|---|---|
| **Delta-12** | 10-2022 −15%, **10-2023 −15%**, **03-2026 −13%** |
| Gamma-6 | 04-2025 −26%, 06-2022 −23%, 03-2023 −23% |
| Oro | 06-2026 −13%, 03-2026 −8%, 11-2025 −6% |
| **A Sigma-6 actual** | **03-2026 −13%**, **10-2023 −12%**, 09-2022 −11% |
| B Consenso-6 | 10-2021 −22%, 06-2022 −14%, 10-2022 −12% |
| C Fórmula inicial | 10-2021 −18%, 06-2022 −15%, 02-2022 −12% |
| D Sin corredora | 11-2022 −23%, 12-2021 −20%, 02-2023 −19% |

**Dos de las tres peores caídas de A son las mismas de Delta-12**: octubre de
2023 y marzo de 2026. La correlación mensual de 0,77 ya lo insinuaba, pero esto
lo dice donde importa: **cuando Delta-12 lo pasa peor, Sigma-6 lo pasa peor
también.** B comparte una (10-2022) y C ninguna.

Y aquí aparece la tensión que las métricas agregadas esconden: **D tiene la
correlación más alta y el solape más alto, pero ninguno de sus tres peores
momentos coincide con los de Delta-12.** Se parecen mes a mes y no se hunden a
la vez. No es un resultado limpio a favor de nadie; es una advertencia contra
leer la correlación como si midiera las colas.

## Lo que decide: el aporte al conjunto

Conjunto de tres piezas en tercios contra conjunto de cuatro al 25%, con
$5.000.000 por pieza.

### Ventana de selección (2021-07 a 2023-12)

| conjunto | retorno anual | peor caída | Sharpe |
|---|---|---|---|
| tres piezas, sin cuarta | **+13,90%** | −10,2% | 1,05 |
| + A Sigma-6 actual | +12,02% | **−6,7%** | **1,09** |
| + B Consenso-6 | +12,72% | −7,6% | 1,05 |
| + C Fórmula inicial | +10,07% | −6,9% | 0,90 |
| + D Sin corredora | +11,32% | −9,4% | 0,94 |

### Ventana de evaluación (2024-01 a 2026-07)

| conjunto | retorno anual | peor caída | Sharpe |
|---|---|---|---|
| tres piezas, sin cuarta | +25,55% | **−6,9%** | 1,75 |
| + A Sigma-6 actual | +25,68% | −8,1% | 1,98 |
| + B Consenso-6 | +25,38% | −7,5% | 1,95 |
| + C Fórmula inicial | +18,67% | **−5,3%** | 1,72 |
| + D Sin corredora | **+27,50%** | −6,6% | **2,07** |

## Las tres conclusiones

**1. Ninguna cuarta pieza mejora el retorno del conjunto en la ventana de
selección.** Las cuatro lo bajan, entre 1,2 y 3,8 puntos anuales. En la
evaluación sólo A (+0,13) y D (+1,95) lo suben, y A apenas. **Lo que una cuarta
pieza chilena aporta no es retorno.**

**2. Lo que aporta es Sharpe, y el orden entre A y D se da vuelta.** En la
selección A es el único que lo mejora (+0,04) y D lo empeora (−0,11). En la
evaluación D lo mejora más que nadie (+0,32) y A queda segundo (+0,23). **Por
el protocolo de este proyecto, entre A y D no se distingue.** B queda pegado a
A en la evaluación (+0,20) y neutro en la selección.

**3. C queda descartado y no por poco.** Es el peor en las dos ventanas: −3,82
y −6,88 puntos de retorno del conjunto, con Sharpe peor o igual. Y lo pierde
**pese a ser el más diversificador de los cuatro** —correlación 0,40 con
Delta-12, solape 0,00, ninguna caída coincidente—. Su diversificación es real y
no alcanza para compensar su retorno. Hay que decir también que corre sin uno
de sus tres componentes de calidad por falta de precios objetivo, así que su
resultado es un piso y no una medición limpia.

### La sensibilidad no cambia nada

A $2.500.000 por pieza el cuadro es el mismo: A es el único que mejora el
Sharpe en la selección (+0,01) y D el que más lo mejora en la evaluación
(+0,28). Las diferencias de retorno se mueven entre 0,2 y 0,6 puntos. **La
trampa del mínimo por operación no da vuelta ninguna conclusión.**

## Qué contesta esto sobre Sigma-6

**No contesta que deba existir, y no contesta que no.** Entre mantenerla como
está (A) y reemplazarla por momentum puro (D), el aporte al conjunto **no se
distingue**: cada uno gana una ventana.

Lo que sí queda establecido, y es lo que faltaba:

- **Una cuarta pieza chilena no agrega retorno al conjunto.** Agrega Sharpe
  bajando la caída, y sólo eso.
- **A es la que peor diversifica de las tres viables**: comparte dos de sus
  tres peores momentos con Delta-12.
- **La opción más barata de operar —D, sin corredora— es la que más Sharpe
  aporta en la ventana de evaluación**, y es la única que elimina la
  dependencia manual. Que empeore el Sharpe en la ventana de selección es
  exactamente por qué no se puede declarar ganadora.

La decisión sigue siendo de Rodrigo, pero ahora el argumento a favor de
mantener la corredora ya no puede apoyarse en el aporte al conjunto, porque
ahí no se distingue de no tenerla.
