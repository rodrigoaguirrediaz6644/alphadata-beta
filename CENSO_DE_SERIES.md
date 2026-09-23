# Censo de series publicadas

Para cada número que aparece en el informe: **¿se recalcula desde datos
primarios en cada corrida, o está guardado?**

Todo lo guardado es sospechoso hasta que se demuestre que su insumo no cambió.

## Por qué existe este documento

Que la serie de Sigma-6 nunca se recalculara no fue un descuido aislado. Es la
**cuarta aparición del mismo defecto**: un número publicado que nadie volvió a
calcular después de que cambiara aquello de lo que dependía.

1. El feed chileno congelado: precios que se repetían y un informe de cobertura
   que decía `OK` porque contaba filas y no miraba si los valores cambiaban.
2. Las fechas de entrada recalculadas en cada corrida, que daban una respuesta
   distinta cada vez.
3. La suite de pruebas pisando el gráfico publicado con una curva de fixture.
4. La serie histórica de Sigma-6, intacta desde antes de reparar los precios
   chilenos, de reconstruir la tabla de dividendos y de los cambios de
   metodología, publicando +28,75% anual cuando el número era diez puntos menos.

**Todo lo que verificamos en estas semanas lo dejó pasar.** Las guardias miran
el feed, la cobertura mira los instrumentos, las pruebas de aceptación miran
las carteras y el libro. Nadie preguntaba si cada serie publicada se vuelve a
calcular.

## El censo

### Reconstrucción histórica — `data/reconstruccion_historica.csv`

| serie | estado | desde qué |
|---|---|---|
| Sigma-6 | **recalculada** desde 21-09-2026 | `sigma6_historical_nav`, precios y recomendaciones |
| Delta-12 | recalculada | `delta12_historical_nav`, precios |
| Gamma-6 | recalculada | `gamma6_historical_nav`, precios y tipo de cambio |
| Oro | recalculada | `oro_historical_nav`, precios y tipo de cambio |
| Mercado chileno (canasta igual peso) | **recalculada** | `canasta_chilena`, los precios chilenos del almacén |
| Conjunto AlphaData | recalculada | `combined_equal_weight` sobre las cuatro |

Sigma-6 y el benchmark eran las dos guardadas. El benchmark resultó estar sano
—desvío máximo 0,87% contra su recálculo, mismo valor final 261,39— pero estaba
en la misma forma que falló, así que se recalculó igual.

**Desde el 22-09-2026 el benchmark ya no es el MSCI IPSA** sino una canasta de
partes iguales del mercado chileno, que se construye con los precios que el
sistema ya baja. Cerró la última dependencia manual con consecuencia. La vara
baja de 261,39 a 235,97 en base 100, unos 2 puntos anuales **en la dirección
que halaga a las estrategias**: está medido, no es sistemático, y hay que
tenerlo presente al leer cualquier «le ganamos al mercado». Ver
`DEPENDENCIAS_MANUALES.md`.

**Hay una guardia que lo sostiene.** `SERIES_RECONSTRUIDAS` en
`src/run_pipeline.py` enumera lo que se recalcula, y la corrida **se detiene**
si aparece en el archivo una columna que no esté en esa lista. Agregar una
serie publicada sin recalcularla deja de ser posible en silencio.

### Seguimiento en vivo — `data/strategy_nav.csv`

**Guardado por diseño, y es correcto**, con una excepción: la columna del
benchmark **se recalcula entera en cada corrida** desde la canasta. Sin eso, el
cambio de benchmark habría empalmado el MSCI y la canasta en la misma columna, y
un empalme así no se ve roto, se ve como una serie.

Las series de las estrategias sí son bitácora: cada fila se calcula
una vez, con los precios de esa jornada, y no se vuelve a tocar. Reescribirla
sería reescribir el pasado, que es lo que el reinicio vino a terminar.

La contrapartida hay que decirla: **si mañana se corrige un precio del pasado,
las filas anteriores del NAV en vivo quedan calculadas con el dato viejo.** Hoy
la serie tiene cinco días, así que no hay pasado que corregir. Cuando lo haya,
la decisión es entre dejarla como está —fiel a lo que se publicó— o rehacerla
y archivar la anterior, como se hizo con el benchmark.

### Carteras y posiciones

| número | estado |
|---|---|
| Selección de cada cartera | recalculada en cada corrida, desde precios y recomendaciones |
| Peso de entrada | recalculado |
| Peso hoy | recalculado desde la última revisión |
| Precio hoy | del almacén de precios, que es append-only y se valida con las guardias |
| **Fecha y precio de entrada** | **guardados a propósito, en el libro** |
| Dividendos cobrados | recalculados desde `data/dividendos.csv` |
| Tiempo en cartera | recalculado contra la fecha del libro |

El libro es la excepción **buscada**: es un registro, no un derivado, y hay una
prueba de perturbación que lo exige —alterar veinte ruedas de un precio pasado
y verificar que ninguna fila cambia—. La diferencia con el defecto de Sigma-6
es que el libro guarda **hechos** (cuándo se decidió, a qué precio), no
**resultados calculados**.

Cuando cambia una regla, el libro se reconstruye entero con el recorrido, y la
prueba de aceptación exige que reproduzca las cuatro carteras publicadas.

### Estrategia Horizonte — retirada del informe el 23-09-2026

**Ya no publica nada**, así que no está en este censo por lo que publica sino
por lo que enseñó. La reemplazó Ahorro Generacional; ver `registro/README.md`
y la nota en `src/horizonte.py`.

Era el candidato obvio y **no tenía el defecto**. `src/horizonte.py` corre como
paso propio del workflow, baja las cuotas de Cuprum y las series de FRED,
rehace el backtest completo y reescribe todas sus tablas, incluida
`horizonte_backtest_summary.csv`, que es la forma que acaba de fallar.

Verificado corriéndolo: el resumen publicado queda **idéntico** —CAGR 13,372%,
acumulado 104,64%, peor caída −13,970% para el tramo fuera de muestra—. Se
recalcula y da lo mismo, que es lo que había que comprobar.

Dos observaciones del censo:

- **Una fila de `horizonte_annual.csv` sí estaba desactualizada**: el año 2012
  de la Estrategia Horizonte pasó de 332 a 366 observaciones y de +4,51% a
  +6,59% al recalcular. Es el borde del primer año y no toca ninguna cifra
  publicada, pero prueba que el recálculo es real y que el archivo había
  quedado detrás de sus insumos.
- **No hay operaciones desde el 31-01-2023**, y es correcto: la recomendación
  es Fondo A de forma continua desde entonces —la última distinta fue el
  31-12-2022—. No es una señal detenida.

### Lo que queda guardado a sabiendas

| artefacto | por qué |
|---|---|
| `data/libro_posiciones.csv` | registro de hechos; ver arriba |
| `data/strategy_nav.csv` | bitácora en vivo; ver arriba |
| `data/operaciones_reales.csv` | se llena a mano; sólo existe en el momento |
| `data/dividendos.csv` | tabla de hechos, con su propio procedimiento de confirmación |
| `data/archivo/*` | series retiradas; no se reescriben nunca, por definición |
| `data/market_prices_daily.csv` | almacén append-only, con guardias propias |

## Lo que quedó pendiente del censo, contestado

### `SERIES_RECONSTRUIDAS` declaraba; ahora también obliga

Era una **declaración**, no un motor: el pipeline llamaba a cada función por
separado y después comparaba el conjunto de columnas contra la lista. Una serie
listada cuyo recálculo quedara en nada habría pasado igual —que es exactamente
el fallo de Sigma-6— porque cada reconstrucción estaba envuelta en un
`if len(...)` que, al venir vacía, **conservaba los valores anteriores en
silencio**.

Cerrado: cada reconstrucción es obligatoria y **la corrida se detiene** si
alguna viene vacía. No hay camino por el que una serie publicada conserve
valores viejos sin que nadie se entere.

### La prueba que lo zanja

Perturbación sobre una copia de trabajo: **1.629 filas de mayo de 2023, 74
instrumentos, multiplicadas por 1,30**, y la corrida completa.

| serie | desvío máximo | |
|---|---|---|
| Sigma-6 | 28,69% | se movió |
| Delta-12 | 29,25% | se movió |
| Gamma-6 | 69,00% | se movió |
| Oro | 69,00% | se movió |
| Mercado chileno (canasta igual peso) | 30,00% | se movió, entonces como IPSA Total Return |
| Conjunto AlphaData | 49,15% | se movió |

**Las seis se movieron.** Y el primer intento tiene su propia lección: alterando
sólo BCI, INTC, IAU, el IPSA y el tipo de cambio, **Sigma-6 no se movió**, y no
era un fallo —Sigma-6 no tenía BCI en mayo de 2023, sino BESALCO, CCU,
CENCOSUD, ECL, ENELCHILE, FORUS, ILC, QUINENCO, RIPLEY, SMSAAM y SMU—. Una
prueba de perturbación sólo prueba lo que toca.

### El 0,87% del IPSA TR

La serie guardada y su recálculo divergen en tres ruedas —09 y 10 de julio de
2026, y 23 de marzo de 2026— y coinciden en todo lo demás. La causa es la
**costura del reemplazo del benchmark**: la columna guardada se calculó cuando
la serie empalmada `IPSA_TR` todavía no existía en su forma actual, y en esas
ruedas tomó valores del ETF proxy (`CFMITNIPSA`), que es un instrumento
distinto del índice y puede separarse de él en un día. El 09-07-2026 el proxy
sube 1,02% y el índice baja 0,11%.

Los extremos calzan porque el reemplazo se calibró a razón 1,000000. Ahora hay
una sola fuente leída de punta a punta.

### `cartera_publicada.json` arranca con una semilla

Anotado **dentro del propio archivo**, en un campo `procedencia`: sembrado a
mano el 21-09-2026 con la cartera del commit `c945d8a`, el último informe
emitido antes de encender la SMA200. Sin la semilla la primera comparación
habría sido contra nada. No es registro continuo desde antes de esa fecha.

### Completitud de lo que baja Horizonte

**Hecha.** Los 332 → 366 datos de 2012 eran treinta y cuatro días que el
recálculo rellenó: la corrida anterior tenía huecos y que el resumen publicado
no se moviera fue suerte, no control.

`verificar_completitud` corre antes del backtest y **detiene la corrida** si los
insumos no están completos. Comprueba cuatro cosas:

- que no falte ningún **día calendario** en el rango de las cuotas —el valor
  cuota se publica todos los días, así que un día ausente es un hueco y no un
  feriado—;
- que no haya valores cuota nulos;
- que las cuotas no lleven más de **14 días** sin actualizarse, que es lo que
  tolera el atraso normal de la AFP más un fin de semana;
- que no falte ningún día hábil en las series de FRED.

Estado al 21-09-2026: **8.813 de 8.813 días calendario presentes, sin nulos**,
último dato del 16-09-2026 con cinco días de rezago. Las series de FRED, sin
huecos en 14.511 días hábiles.

## La regla que queda

**Ninguna serie publicada puede quedar guardada sin que alguien pueda decir de
qué insumo depende y por qué no cambió.** Si la respuesta no existe, se
recalcula.
