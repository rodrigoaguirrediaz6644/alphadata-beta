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

## El tope de tenencia de Sigma-6 genera comisiones

Medido sobre el recorrido calentado 2024-2026: **nueve salidas por tope, y las
nueve reingresan la semana siguiente.**

| nombre | entra | sale por tope | reingresa |
|---|---|---|---|
| ITAUCL | 05-01-2024 | 10-01-2025 | 17-01-2025 |
| LTM | 05-01-2024 | 10-01-2025 | 17-01-2025 |
| SALFACORP | 05-01-2024 | 10-01-2025 | 17-01-2025 |
| MALLPLAZA | 16-08-2024 | 22-08-2025 | 29-08-2025 |
| BCI | 11-10-2024 | 17-10-2025 | **24-10-2025** |
| CENCOSUD | 29-11-2024 | 05-12-2025 | 12-12-2025 |
| ITAUCL | 17-01-2025 | 23-01-2026 | 30-01-2026 |
| LTM | 17-01-2025 | 23-01-2026 | 30-01-2026 |
| SALFACORP | 17-01-2025 | 23-01-2026 | 30-01-2026 |

La causa está en el código: al soltarse, el nombre desaparece de
`sigma_entries`, así que en la revisión siguiente el contador parte de cero y
vuelve a calificar. El reloj se reinicia, de modo que un nombre que siga
gustando rota **una vez al año, para siempre**.

Cada rotación son dos operaciones sobre la misma acción, **$3.980 en mínimos**,
y la cartera queda idéntica. Nueve rotaciones en el tramo medido: $35.820 sobre
una pieza de $5.000.000. **No se arregla acá; queda reportado.**

### Consecuencia sobre la fila de BCI

La entrada publicada del 24-10-2025 **es uno de esos reingresos**. La tenencia
económica continua de BCI arranca el 11-10-2024.

| desde | precio | va ganando |
|---|---|---|
| 16-01-2026 (arranque sin calentar) | $64.500 | +4,3% |
| **24-10-2025 (lo que se publica)** | **$46.502** | **+44,7%** |
| 11-10-2024 (tenencia continua real) | $28.195 | +146,4% |

Y el tope vuelve a tocarse: con entrada el 24-10-2025, BCI llega a los 365 días
el **24-10-2026** y se suelta en la revisión semanal del **30-10-2026** (371
días), para ejecutarse el lunes 02-11. Con la fecha vieja no habría ocurrido
hasta el 22-01-2027. **Corregir la fecha no cambia sólo un número en pantalla:
cambia cuándo el modelo vende.**

El dividendo se revisó: BCI tiene dos en la tabla, 28-03-2025 y 26-03-2026.
Entre octubre de 2025 y enero de 2026 no hay ninguno, así que la ventana larga
captura el mismo dividendo que la corta y el +44,7% **no está corto**.

## La caja de Sigma-6 viene de las recomendaciones

Sigma-6 tiene $2.500.000 quietos, la mitad de su pieza. **No es el momentum y
no es el feed.** En la revisión del 17-09-2026 hay **cinco** nombres con
recomendación de compra vigente y **los cinco** pasan el momentum y están en
cartera. El cuello es la oferta de recomendaciones.

| revisión | con señal positiva vigente | elegibles | caja |
|---|---|---|---|
| 05-09-2025 | 13 | 11 | 0% |
| 26-12-2025 | 13 | 12 | 0% |
| 20-03-2026 | 10 | 9 | 10% |
| 15-05-2026 | 6 | 6 | 40% |
| 07-08-2026 | 6 | 5 | 50% |
| 04-09-2026 | 5 | 5 | 50% |

El flujo mensual de Credicorp cae de 17-19 filas a 4-8, y las compras de 5-6 al
mes a 1-4. **La caída empieza en enero de 2026, antes del congelamiento del
22-07.** El congelamiento no la causó; la vuelve irreversible.

Las ocho recomendaciones rechazadas **no son nuevas ni venían incompletas**:
son ocho filas de AESANDES entre 2021 y 2022, rechazadas por `ticker fuera del
catálogo`. Están fuera de la ventana de 365 días. Si hubieran entrado, la
cartera del 17-09 sería exactamente la misma.

### Lo que viene si no llega nada

Las recomendaciones vigentes expiran a los 365 días. Sin ninguna nueva:

| fecha | nombres que quedan | caja |
|---|---|---|
| 24-11-2026 | 4 (expira VAPORES) | 60% |
| 22-04-2027 | 3 (expira CENCOMALLS) | 70% |
| 01-07-2027 | 1 (expiran BCI y PARAUCO) | 90% |
| 09-07-2027 | 0 (expira LTM) | **100%** |

**Sigma-6 se apaga sola en julio de 2027** si el flujo no se restablece. Eso
convierte el problema de las recomendaciones en el más caro que tiene el
sistema, por encima del feed.

## Los dos calendarios mensuales son deliberados

Delta-12 corta con el último día hábil chileno y Gamma-6 con el estadounidense.
En 21 meses de 2025-2026 coinciden en 19; difieren en octubre de 2025 (30 vs
31) y diciembre de 2025 (30 vs 31), por feriados chilenos. Agosto de 2026 cae
el 31 en ambos, así que los ocho movimientos publicados llevan la misma fecha.

El `01-09-2026` que aparecía en Gamma-6 **no es una convención vigente**: es el
sello del único `portfolio_gamma6.csv` anterior al reinicio, que anotaba la
ejecución —la rueda siguiente— y no la señal. Hoy las dos anotan la señal.

Desglose de los ocho movimientos del 31-08: **cuatro entradas y cuatro
salidas.** Delta-12 compra ANDINA-B y BCI, vende ILC y LTM. Gamma-6 compra ABT
y JNJ, vende UNH y AAPL.
