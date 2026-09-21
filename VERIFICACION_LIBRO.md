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

### Delta-12: 8 de 8

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
30-06, MALLPLAZA entre el 30-01 y el 27-02— y las dos se resuelven a favor del
libro al reparar la serie de precios. **Lo que movió esas dos fechas fue la
reparación del dato, no el recorrido.**

### La regla del calendario no cambió

Era la pregunta de fondo. `reconstruct_entry_dates` usa
`sessions.to_period("M") < as_of.to_period("M")` y toma el máximo de cada mes:
**idéntico** a lo que hace el recorrido. `as_of.to_period('M') - 1` fue siempre
el comportamiento de producción. La diferencia de una rueda es señal contra
ejecución, no calendario.

### Gamma-6 y el oro: sin información

Sus archivos nacen el 20-09-2026 y `reconstruct_entry_dates` nunca los cubrió:
las seis posiciones de Gamma-6 quedaron estampadas con `2026-09-01` y el oro
con `2026-09-18`. Que ABT y JNJ coincidan con el libro es casualidad. **El
historial no dice nada sobre estas siete posiciones.**

### Sigma-6: no reconcilia, y la causa es estructural

Sigma-6 tiene **tenencia máxima de 365 días**, así que es dependiente del
camino: la fecha de entrada depende de dónde arranque el recorrido. El libro
arranca el 02-01-2025 porque hacia atrás no hay dato reparado en que confiar.

Corriendo el mismo recorrido desde 2021-07-09, **BCI se mueve del 16-01-2026
al 24-10-2025 y calza exacto** con la reconstrucción. CENCOMALLS y PARAUCO
calzan con cualquiera de los dos arranques. LTM y VAPORES siguen sin calzar, y
ahí la causa es otra: la reconstrucción arma su calendario semanal con **todos
los instrumentos, incluidos los estadounidenses**, mientras el libro usa sólo
ruedas chilenas. Para una estrategia chilena semanal el calendario del libro es
el correcto, pero los dos no coinciden.

**Consecuencia, dicha sin adorno:** las fechas de Sigma-6 anteriores a
2026-01 cargan el efecto del borde de la ventana. Las de Delta-12 no.

## Las tres preguntas sobre el libro

**¿Alguna posición con fecha 02-01-2025?** **No.** Ninguna de las 153 filas
entra en el borde: la primera revisión mensual del recorrido es el 31-01-2025 y
la primera semanal, el 03-01-2025. El resguardo existe y nunca se activó.

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
