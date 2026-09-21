# Incidente del feed chileno — julio a septiembre de 2026

## Qué pasó

El 17-07-2026 el proveedor dejó de actualizar el historial de los tickers
`.SN`. Durante dos meses, 34 de 40 acciones chilenas repitieron el mismo cierre
y `coverage_report.csv` siguió diciendo `status OK` con `lag_business_days 0`,
porque contaba filas y medía el rezago de la fecha pero nunca comprobaba si los
valores cambiaban.

Cada descarga traía **una sola fila viva**: la última. En la descarga siguiente
esa fecha revertía al valor congelado. Como la valorización medía desde
`valuation_date` —ya revertida— hasta esa punta viva, cada corrida volvía a
contabilizar íntegro el mismo movimiento acumulado.

Lo publicado en ese periodo:

| serie | publicado | real |
|---|---|---|
| Delta-12 | +30,2% | ~+3,0% |
| Sigma-6 | +11,2% | ~+0,5% |
| Conjunto | +20,8% | ~+1% |

Las carteras tampoco eran confiables: el momentum 12-1, la SMA200, el RSI(14) y
el filtro de liquidez se calcularon ocho semanas sobre precios repetidos, así
que las decisiones de esas semanas no son las que las reglas habrían tomado.

## Las reglas que deja

**Un dato que no cambia puede ser un dato muerto.** Medir variación, no sólo
presencia y frescura de fecha. Un instrumento con filas diarias, rezago cero y
el mismo número repetido cuarenta ruedas seguidas no está OK.

**Una fuente se valida contra datos que ya sabemos buenos.** En una ventana
común y explícita, exigiendo que la razón mediana sea 1 —misma convención de
cierre— y que lo que no calce sea pequeño. Una serie ajustada por dividendos se
separa del cierre crudo en escalones que se acumulan hacia atrás, así que sin
fijar la ventana los candidatos quedan ordenados por cuánta historia traen.

**Los hechos publicados se agregan, no se sobrescriben.** Una revisión del
pasado necesita una explicación. Si el archivo hubiera sido de sólo agregar, el
precio bueno del 15 de julio habría quedado grabado, los viernes siguientes no
habrían traído ninguna fila nueva, y la detención habría saltado a la vista esa
misma semana en vez de dos meses después.

**Verificar incluye preguntar si el número es real, no sólo si tiene el formato
correcto.** Los cuatro puntos de verificación del oro pasaron los cuatro, y
ninguno miraba si el suelo existía.

**Una prueba construida desde un caso afortunado no prueba nada, sólo lo
repite.** El primer criterio para distinguir un cierre de un precio intradía
exigía una operación posterior a la campana. Tenía ocho pruebas verdes, todas
sobre el bloque `meta` de ILC, que resultó ser uno de los nueve instrumentos de
cuarenta con remate de cierre. La corrida real rechazó treinta y uno. Un caso
de prueba tiene que elegirse por ser representativo, no por estar a mano.

**Ante la duda, el sistema calla.** Un informe que dice "no sé" es infinitamente
mejor que uno que dice +20,8%.

## Lo que quedó puesto

- **Almacén de sólo agregar** (`src/price_store.py`): lo grabado es definitivo;
  las diferencias sobre datos pasados se informan y no se aplican.
- **Tres guardias** (`src/guards.py`), todas frenan en vez de avisar: serie sin
  variación, contraste entre fuentes, y ADR contra acción local. La del ADR
  habría delatado el incidente el 18-07-2026.
- **Captura diaria** (`src/fetch_daily_close.py`): el cierre sale de la
  cotización viva, que nunca dejó de publicarse. Falla ruidosamente, porque un
  día perdido ya no se recupera.
- **Vara de medir** (`src/feed_validation.py`) para cualquier candidato a
  proveedor.
- **Benchmark real** (`src/benchmark_ipsa.py`): el MSCI IPSA Gross reemplaza al
  proxy congelado.
- **Fixture del incidente** (`tests/fixtures/incidente_feed_chileno.csv`): los
  datos reales del feed detenido, conservados para que las pruebas de regresión
  no dependan del archivo vivo.
