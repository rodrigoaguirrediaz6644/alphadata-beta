# Verificación del libro de posiciones contra el historial del repositorio

Qué salió al contrastar las fechas de entrada del libro con las que producción
publicó en su momento. **Se reporta tal como salió.** Donde no calza, se
explica; no se ajustó nada del recorrido para que calzara.

## La comparación pedida no se puede hacer, y la razón importa

La idea era comparar contra `opened_at` tal como producción lo escribió antes
del incidente. Ese registro no existe:

| | |
|---|---|
| Primer commit del repositorio | 15-07-2026 |
| El feed chileno se congela | 17-07-2026 |
| Primera aparición de `opened_at` | **27-07-2026** |

La columna nació diez días **después** del congelamiento. No hay una sola
fecha de entrada escrita sobre datos buenos.

Y hay algo peor que su ausencia: **esas fechas se recalculaban en cada
corrida**. El 27-07-2026, dos commits del mismo día dan fechas distintas para
las mismas posiciones —BCI pasa de `2025-11-03` a `2026-03-02`, MALLPLAZA de
`2024-10-01` a `2026-01-02`—. La causa está entre ambos: `274de5c Adoptar
nueva Delta-12 con RSI`. El historial no registra cuándo entró cada posición;
registra qué respondía el recálculo ese día. Es exactamente el problema que el
libro vino a terminar.

## La verificación que sí se puede hacer

`reconstruct_entry_dates` sigue en el código. Se la corrió con **los datos
reparados de hoy**, cortada al 27-07-2026, y se comparó con el libro.

La convención difiere en una rueda y es sistemática: producción anotaba la
**ejecución** —`next_session(review)`— y el libro anota la **señal**. Toda la
comparación se hace corriendo el libro una sesión hacia adelante.

### Delta-12: 8 de 8, y lo que eso vale

**Esto no es evidencia independiente de que las fechas sean correctas.** Las
dos rutinas comparten la regla del calendario y leen la misma serie reparada,
las dos aplicando las reglas de hoy: si la regla estuviera mal, se
equivocarían igual. Lo que sí atrapa es error de programación —el recorrido
implementado distinto de producción— y eso tiene valor propio.

La evidencia que sí vale es otra, y es de otra clase: **el calentamiento no
mueve ninguna de estas ocho fechas.** Arrancando el recorrido en 2024, 2023 o
2021 en vez de 2025, Delta-12 da exactamente las mismas entradas. Eso descarta
la dependencia del camino, que era el defecto que quedaba vivo.

| posición | reconstrucción | libro (señal) | |
|---|---|---|---|
| BCI | 2026-03-02 | 2026-02-27 | calza |
| CHILE | 2026-07-01 | 2026-06-30 | calza |
| ECL | 2026-07-01 | 2026-06-30 | calza |
| ILC | 2026-07-01 | 2026-06-30 | calza |
| ITAUCL | 2026-03-02 | 2026-02-27 | calza |
| MALLPLAZA | 2026-03-02 | 2026-02-27 | calza |
| PARAUCO | 2026-04-01 | 2026-03-31 | calza |
| SQM-B | 2026-02-02 | 2026-01-30 | calza |

Incluye posiciones ya cerradas (ILC, SQM-B), que es donde una reconstrucción
equivocada se delataría.

**Dos de estas ocho no calzaban contra el historial publicado**: ECL aparecía
con `2026-04-01` y MALLPLAZA con `2026-01-02`. Las dos son exactamente las que
el libro registra con una salida intermedia —ECL fuera entre el 29-05 y el
30-06, MALLPLAZA entre el 30-01 y el 27-02—.

El hallazgo es que **lo que movió esas fechas fue el dato y no el recorrido**.
Lo que no se puede decir es que eso las valide: datos reparados más reglas de
hoy *es* el libro, así que resolverse a su favor era el único resultado
posible.

### La regla del calendario: la pregunta es inconducente

Lo escribí como si estuviera contestada y no lo está. Que
`reconstruct_entry_dates` y el recorrido usen el mismo
`sessions.to_period("M") < as_of.to_period("M")` dice que **dos rutinas del
código de hoy coinciden**, no que producción haya usado esa regla en febrero.
La única evidencia posible era el historial, y el historial empieza el
15-07-2026.

Lo correcto es: **no hay evidencia en ningún sentido**, y la pregunta es
inconducente, porque nunca hubo un sistema en vivo que pudiera haber tenido
otra regla. La diferencia de una rueda entre las dos rutinas es señal contra
ejecución.

### Gamma-6 y el oro: sin información

Sus archivos nacen el 20-09-2026 y `reconstruct_entry_dates` nunca los cubrió:
las seis posiciones de Gamma-6 quedaron estampadas con `2026-09-01` y el oro
con `2026-09-18`. Que ABT y JNJ coincidan con el libro es casualidad. **El
historial no dice nada sobre estas siete posiciones.**

### Sigma-6: el borde se propagaba un año, y se corrigió

Sigma-6 tiene **tenencia máxima de 365 días**, así que es dependiente del
camino: la fecha de entrada depende de dónde arranque el recorrido.
Arrancando en 2025, BCI quedaba con entrada el 16-01-2026; arrancando antes,
queda el **24-10-2025**, que calza exacto con la reconstrucción.

De ahí sale el calentamiento: el recorrido arranca el 02-01-2024 y publica
desde el 02-01-2025. Ver `tools/construir_libro.py`.

LTM y VAPORES siguen sin calzar contra la reconstrucción, y ahí la causa es
otra: la reconstrucción arma su calendario semanal con **todos los
instrumentos, incluidos los estadounidenses**, mientras el libro usa sólo
ruedas chilenas. Para una estrategia chilena semanal el calendario del libro
es el correcto, pero los dos no coinciden.

### Cuánto calentar: medido

Mismo corte, cuatro arranques:

| arranque | Sigma-6 | Delta-12 | Gamma-6 |
|---|---|---|---|
| 2025-01-02 | — | — | — |
| 2024-01-02 | BCI 16-01-2026 → **24-10-2025** | idéntico | idéntico |
| 2023-01-02 | BCI → 24-10-2025 | idéntico | idéntico |
| 2021-07-09 | BCI → 24-10-2025 | idéntico | idéntico |

Un año basta y converge. Para Sigma-6 la suficiencia es **estructural**: con
tope de 365 días, el camino desde 365 días antes determina el estado. Para
Delta-12 y Gamma-6, que no tienen tope, es **empírica**: se midió que no
cambia nada hasta 2021, no se demostró que no pueda cambiar. **Si alguna de
esas dos reglas se modifica, hay que volver a medirlo.**

## Las tres preguntas sobre el libro

**¿Alguna posición con fecha 02-01-2025?** **No**, y no tranquiliza. El borde
no se manifiesta como una fila fechada en el borde, sino como fechas
equivocadas un año después —BCI era exactamente eso—. La verificación que lo
reemplaza es la comparación entre arranques de la tabla de más arriba.

**¿Registra reentradas?** **Sí.** 42 de los 71 pares (estrategia, instrumento)
tienen más de una fila, con las cerradas conservadas aparte. COPEC entra y sale
seis veces de Sigma-6; ECL, ITAUCL, MALLPLAZA, CHILE y LTM, cinco de Delta-12.
La posición viva de ECL muestra 30-06-2026 y las cuatro anteriores siguen en el
archivo con su fecha de salida.

**¿Deriva?** **No.** Sobre una copia de trabajo, veinte ruedas de ITAUCL de
febrero de 2026 multiplicadas por 0,4, y de nuevo la corrida completa:

- un recálculo **sí** se mueve: el recorrido pasa la entrada de ITAUCL del
  27-02 al 31-03, o sea la prueba tiene filo;
- el libro **no cambió ni un byte**.

Pero la misma prueba destapó que el **precio** mostrado sí derivaba: el informe
pasaba a mostrar ITAUCL a $8.360 y +207,3%. Corregido: el precio de entrada lo
manda el libro. La variación sigue saliendo del ajustado, a propósito, para que
una corrección de dividendos se propague.

## Dos verificaciones sueltas

**VAPORES.** El dividendo dentro de la ventana de tenencia actual es el del
**08-05-2026 por $6,71**, que está en `data/dividendos.csv` confirmado por el
precio (caída esperada −12,46%, observada −14,20%). El que falta confirmar es
el del **13-05-2025**, diez meses anterior a la entrada del 27-03-2026: queda
fuera de la ventana y no toca el +12,9%. **El número no descansa en un dato sin
confirmar.**

**INTC +220,6%.** Verificado a mano y por separado:

| | USD | tipo de cambio | pesos |
|---|---|---|---|
| 30-09-2025 | 33,55 | 964,94 | 32.373,74 |
| 17-09-2026 | 108,80 | 954,08 | 103.803,91 |
| variación | +224,3% | −1,1% | **+220,6%** |

El tipo de cambio alrededor de ambas fechas se mueve entre 926 y 965, sin nada
anómalo. El único valor imposible de la serie —22-12-2016 = 5,00— lo descarta
la corrida y está a diez años de lo que importa acá. **El número se sostiene.**

## Pendiente anotado

El sistema convierte los instrumentos estadounidenses multiplicando por el tipo
de cambio, o sea asume el CDV uno a uno con la acción. Si la razón real no es
uno a uno, los precios en pesos del lado estadounidense están escalados por ese
factor. No afecta porcentajes ni NAV, pero sí cuántas unidades se compran con
$833.333. **Confirmar antes de comprar en real.**
