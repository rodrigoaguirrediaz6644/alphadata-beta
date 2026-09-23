# Un valor, una casa

Norma del proyecto. No es una preferencia de estilo: es el diagnóstico de los
cuatro defectos más caros que hemos encontrado, que resultaron ser **el mismo**.

## Los cuatro casos

| | qué pasó | cuánto duró |
|---|---|---|
| `SERIES_RECONSTRUIDAS` | la serie de Sigma-6 se guardaba en vez de recalcularse, y sobrevivió intacta a la reparación de los precios chilenos | publicó **+28,75%** cuando el número era diez puntos menos |
| El mínimo de **$1.990** | un supuesto escrito en el código, mientras la medición decía $999,99 | meses |
| La tasa de **0,1%** de los CDV | un supuesto escrito en el código; la boleta de IAUCL dice 0,1785% | meses |
| El mapa de **símbolos** | `BACL` en vez de `BACCL`: el símbolo de Boeing en la fila de Bank of America | **dos años** |

**Ninguno fue un cálculo malo.** Los cuatro fueron una copia que se quedó atrás
mientras el original cambiaba, y los cuatro sobrevivieron porque **nada los
contrastaba contra su fuente**.

El de los símbolos es el más instructivo porque enseña cómo se ve la falla:
`BA + CL = BACL` y `BAC + CL = BACCL`. Cuando un ticker es prefijo de otro, la
regla produce **un instrumento real y equivocado**. No falla con ruido ni con
una excepción; falla con una serie de precios perfectamente válida de otra
empresa. Por eso nadie lo vio.

## La norma

**Un valor, una casa. Y la prueba lee la casa, no una copia.**

El modelo a seguir es la prueba que contrasta la boleta de IAUCL contra
`config/runtime.v2.json`: entra un dato del mundo real por un lado, la
configuración por el otro, y **si alguien inventa un número en el medio,
falla**. Una prueba que compara una constante del código contra otra constante
escrita en la prueba no verifica nada: verifica que alguien copió bien dos
veces.

Tres corolarios:

**Un número derivado no tiene casa propia.** El umbral bajo el cual el mínimo
sale más caro que el porcentual es mínimo/tasa. Estaba escrito como constante
*y* guardado en la configuración: dos casas para algo que no tiene ninguna.
Ahora lo calcula `src.ingreso.umbral_minimo`.

**Un valor por omisión es una casa.** Cuatro funciones de
`src/strategy_engine.py` traían la tarifa como valor por omisión, y una traía la
refutada. Producción las llamaba explícitamente, así que el error estaba
dormido esperando al próximo que llamara sin el argumento. Los cuatro valores
por omisión se eliminaron: el costo ahora es obligatorio.

**Un estudio publicado es una casa.** `research/carteras_en_pesos/` decidió el
retiro de Sigma-6 con su propia copia de la tarifa, incluido el 0,1% refutado.
Se corrigió, se volvió a correr, y **la conclusión se sostuvo** —C gana las tres
ventanas— pero el número cambió: mantener Sigma-6 costaba $4.880.898 y cuesta
$4.658.161. Que esta vez no se diera vuelta fue suerte, no diseño.

## Tres reglas que salieron de aplicarla

**«Verde» y «funciona» son dos afirmaciones distintas.** Quitar los valores por
omisión dejó la corrida caída en dos sitios y **248 pruebas siguieron en
verde**, porque todas llamaban funciones sueltas con datos de juguete y ninguna
llamaba al pipeline. Ahora hay una prueba de humo que lo corre entero sobre un
árbol copiado y exige que llegue al final —`tests/test_humo_pipeline.py`—, y se
verificó que falla al reintroducir esa misma regresión. No mira contenido: de
eso se encargan las rápidas.

**El recorte de valores absurdos pertenece al consumidor, no al productor.** El
filtro que descartaba razones lejanas a 1 vivía en `frescas`, y las dos cosas
que leen de ahí quieren lo contrario: para medir el premio un 3,6 es un dato
roto que ensucia una media, y para la puerta de símbolos es **la evidencia** que
delata a Boeing. Dejarlo en el productor le quitó a la puerta con qué rechazar.
No es una excepción de este caso: cuando dos consumidores discrepan sobre qué es
basura, el que decide es cada uno.

**El artefacto de rancio no tiene techo.** Un precio congelado dividido por un
subyacente que se movió puede dar cualquier número: HONCL llegó a 2,08 estando
perfectamente sano. Por eso el umbral de razón imposible está en ±25% y es
**ancho a propósito**: las ruedas frescas de HON dispersan 10%, así que una sola
rueda dirime un 3,5 pero **no dirimiría un 1,4**. Que nadie lo apriete después
creyendo que es un instrumento preciso; no lo es, y su precisión no se puede
subir sin más ruedas frescas, que es justo lo que no hay.

## La lista: lo que queda con más de una casa

No hay que arreglarlo todo ahora. Hay que tener la lista.

### Cerrado en esta pasada

- La tarifa y el mínimo: una sola casa en `config/runtime.v2.json`, leída por
  `src.run_pipeline.modelo_de_costo()`. Se eliminaron `transaction_cost_us`,
  `US_COST_RATE`, los literales en `run_pipeline` y los cuatro valores por
  omisión de `strategy_engine`.
- El umbral del mínimo: pasó a derivarse.
- El símbolo del CDV: columna propia en `config/tickers.csv`, y una puerta en
  `src.cdv.estado` que no deja imprimir un símbolo sin verificar.
- `research/carteras_en_pesos/` y `research/aporte_marginal/` leen la
  configuración.
- El parámetro `buy_cost` de `enrich_open_positions`, que **el cuerpo no leía
  nunca**. Un parámetro muerto con valor por omisión es lo peor de las dos
  cosas: parece que el costo entra ahí y no entra. Eliminado.
- La regla general, hecha prueba: ninguna constante del dominio puede tener
  valor por omisión en `src/`, con las excepciones escritas y no silenciosas.
  **Si el parámetro no llega, la llamada falla.**

### La norma se aplica también a la prosa

**Quien hace una cuenta declara sus insumos y de dónde vienen.**

Salió de `POLITICA_REBALANCEO.md`, que calculó una política entera —la que está
implementada en `src/nav_historico.py`— con tres insumos que hoy están vencidos:
la tarifa mínima, el reparto del capital y el lugar de ejecución. **El defecto no
fue que un número estuviera mal: fue que el documento hacía cuentas vivas sin
decir de dónde salían sus entradas.**

Si hubiera nombrado sus tres insumos y su procedencia, el mínimo se habría caído
solo el día que se midió la boleta, en vez de sobrevivir meses sosteniendo una
decisión. Un documento que calcula es código que nadie ejecuta: se le aplica la
misma regla.

`tests/test_un_valor_una_casa.py` ya cubre una parte —falla si un documento
vigente repite un número que la medición desmintió— pero la declaración de
insumos no se puede probar sola. Es una norma de escritura.

### Abierto, por orden de lo que puede costar

**Los estudios congelados llevan la tarifa vieja.** `research/ingreso/`,
`research/ponderaciones/` y `research/histeresis/` tienen el mínimo de $1.990 y
el 0,1% de los CDV. **No hay que corregirlos en su lugar**: sus números
publicados se calcularon con esos valores y reescribir el script sin reescribir
el resultado deja el archivo mintiendo con más convicción. Lo que hay que hacer
es decidir, uno por uno, si su conclusión todavía se usa —y entonces volver a
correrlo entero— o si es historia y basta con fecharlo.

**El límite de concentración del 25%** (`src.nav_historico.LIMITE_CONCENTRACION`)
es una decisión de política que vive en el código y no en la configuración,
donde ya viven el reparto del capital y el costo. Una casa sola, así que hoy no
puede desincronizarse; el riesgo es que alguien escriba la segunda.

**La vigencia de 90 días** (`src.strategy_engine.DIAS_VIGENCIA_RECOMENDACIONES`),
igual: política en el código. Aplica sólo a Sigma-6, que está retirada.

**Las ventanas de 252 y 200 ruedas** aparecen repetidas en `strategy_engine` y
en `fetch_prices`. Son parámetros de método, no datos del mundo, así que no
pueden quedar desmentidos por una boleta. Riesgo bajo, pero la repetición es
real.

### Lo que no entra a la lista

Las constantes de las guardias y de la tabla de dividendos —`UMBRAL_ESCALON`,
`TOLERANCIA_CRUCE`, `MAX_RUEDAS_SIN_VARIACION` y compañía— tienen una sola casa
cada una y no representan nada del mundo exterior que pueda contradecirlas. Son
umbrales elegidos, y el lugar correcto para un umbral elegido es junto al código
que lo usa, con el comentario que dice por qué es ese número.

**El criterio que separa las dos listas:** un valor entra acá si **algo fuera
del repositorio puede desmentirlo** —una boleta, una pantalla de la corredora,
el nombre que publica el proveedor— o si está escrito más de una vez. Lo demás
es una decisión nuestra, y una decisión nuestra no se desincroniza con la
realidad, sólo puede estar mal pensada.
