# Auditoría de Horizonte

Lo que existe, revisado contra lo que publica. No se tocó nada: ni umbrales, ni
series, ni el informe del viernes.

**Las dos predicciones del protocolo salieron al revés**, y conviene empezar por
ahí porque cambia dónde hay que mirar.

| predicción | resultado |
|---|---|
| «El problema de vintage está presente y no está tratado» | **No aplica.** Horizonte usa dos series, `NASDAQCOM` y `VIXCLS`, y las dos son **cierres diarios de mercado**: no se revisan y no tienen rezago de publicación apreciable. No hay una sola serie macro en la estrategia. |
| «El registro fuera de muestra va a rendir peor que el backtest» | **No se puede saber, y la razón es peor que rendir mal.** El registro existe —once publicaciones— y **no contiene ni una sola decisión**. |

Lo que sí apareció está en otro lado: un *lookahead* chico y real en el rezago
de la cuota, y una señal de afinado en los parámetros.

---

## 1. El origen de la regla

**La regla llegó completa en un solo commit**, `9a29d61` del 27-07-2026, como
`src/cuprum_ae.py`. En ese primer archivo ya estaban los cinco indicadores, el
corte en 2 de 5, las ventanas de 6 y 12 meses, `VIX < 30`, el arranque en
2012-08-01, el corte de muestra en 2021-01-01 y el rezago de ejecución. **Nada
de eso se movió nunca después**: los commits posteriores son renombre,
reintentos de descarga, la verificación de completitud y el lenguaje del
informe.

O sea: **dentro del repositorio no hubo afinado sobre resultados.** Pero la
regla no nació acá, y de dónde salió no está escrito en ninguna parte. Es la
misma posición epistémica que tuvimos con Credicorp: no se puede descartar el
ajuste dentro de muestra porque **no hay registro de la procedencia**.

Lo que sí se puede hacer sin ese registro es sondear la regla por sus
consecuencias, y eso está en la sección de sensibilidad.

## 2. Las vintage de FRED: no aplica, y hay que decirlo así de claro

`FRED_URL` pide exactamente dos series:

| serie | qué es | ¿se revisa? | rezago |
|---|---|---|---|
| `NASDAQCOM` | cierre del índice Nasdaq Composite | no | el cierre del día |
| `VIXCLS` | cierre del VIX | no | el cierre del día |

Las dos son **de mercado**. Un cierre no se revisa: no es una primera
estimación de nada. **No hay empleo, ni producción, ni actividad, ni ninguna
serie que FRED corrija meses después.** El problema que el protocolo anticipaba
—usar el valor revisado de hoy en una fecha del pasado— no tiene dónde ocurrir,
y no hace falta ALFRED para nada.

**Donde sí hay un dato con rezago de publicación es en otra parte**, y el
protocolo no lo miraba: el valor cuota de Cuprum. Está en la sección 4.

## 3. ¿Reproduce?

**Sí, exactamente.** Corriendo `monthly_features` y `backtest` desde cero contra
los insumos frescos, las ocho cifras publicadas en
`data/horizonte_backtest_summary.csv` salen iguales con un desvío máximo de
**9,71e-17**, que es precisión de flotante.

| | recalculado | publicado |
|---|---:|---:|
| Horizonte, completo desde 2012 | +10,6164% | +10,6164% |
| Horizonte, fuera de muestra 2021+ | +13,3243% | +13,3243% |
| Fondo A, completo | +10,1274% | +10,1274% |
| Fondo A, fuera de muestra | +11,4824% | +11,4824% |

## 4. El rezago del cambio de fondo

**Está modelado.** Producción ejecuta en la cuarta fecha posterior a la señal.
Como el valor cuota se publica todos los días de calendario, eso son **4 días
corridos**, no 4 hábiles — la distinción importa y no está dicha en el código.

**El resultado no se da vuelta.** Con el rezago entre 1 y 15 días, el retorno
anual de la ventana completa se mueve entre +10,46% y +11,39%, y **todas las
variantes le ganan al Fondo A** (+10,13%):

| rezago | completo | fuera de muestra |
|---:|---:|---:|
| 1 día | +10,46% | +13,06% |
| 2 días | +10,69% | +13,06% |
| 3 días | +10,66% | +13,30% |
| **4 días (producción)** | **+10,62%** | **+13,32%** |
| 5 días | +10,70% | +13,33% |
| 7 días | +11,39% | +14,42% |
| 15 días | +10,65% | +12,79% |

No hay knife-edge entre dos y tres días. Por ese lado es robusto.

### Pero acá está el único lookahead del sistema

El protocolo pedía el rezago **medido y no supuesto**. Medido en el historial de
`data/horizonte_quotes.csv` —once versiones, comparando la fecha del commit
contra la última cuota que traía—:

| rezago de publicación del valor cuota | |
|---|---|
| mediana | **2 días** |
| mínimo | 2 días |
| **máximo observado** | **5 días** |

Producción ejecuta a los 4 días. **En el peor caso observado, el backtest
ejecuta con un dato que todavía no se había publicado**: margen de −1 día. Pasó
en 1 de las 11 observaciones, y otra quedó con margen de 1 día.

Es pequeño y su efecto económico está acotado por la tabla de arriba —mover el
rezago un día entero cambia el resultado en menos de 0,3 puntos—, pero **es
lookahead y estaba sin detectar**. Lo correcto sería fijar la ejecución en
función del rezago observado, no en una constante. **No se cambió**, porque el
punto 8 dice que no se toca nada durante la auditoría.

## 5. La prueba nula, y la década que el backtest no mira

El backtest arranca en 2012-08. **Las cuotas de A y de E existen desde
2002-08**, así que podría arrancar en 2003 y no lo hace. Nadie escribió por qué.

| ventana | Horizonte | Fondo A | Fondo E | 50/50 | ¿gana a A? |
|---|---:|---:|---:|---:|---|
| todo lo medible, 2003-08+ | **+10,82%** | +9,49% | +6,62% | +8,20% | **+1,32%** |
| la década excluida, 2003-2012 | **+11,14%** | +8,51% | +7,24% | +8,05% | **+2,63%** |
| la crisis, 2007-2010 | **+10,48%** | +1,67% | +7,56% | +4,87% | **+8,81%** |
| el backtest publicado, 2012-08+ | **+10,62%** | +10,13% | +6,23% | +8,30% | +0,49% |
| fuera de muestra, 2021+ | **+13,32%** | +11,48% | +4,79% | +8,27% | +1,84% |

**Le gana al Fondo A en las cinco ventanas.** Y la exclusión de 2008 no la
favorece: la perjudica. En la crisis el Fondo A hizo +1,67% anual con una caída
de **−44,00%**, y Horizonte hizo +10,48% con **−20,79%**. Ese es el único tramo
donde la estrategia hace lo que dice que hace.

**Y ese es justo el problema de la ventana publicada.** En 2012-08 en adelante
la ventaja cae a +0,49% anual y **la peor caída es la misma que la del Fondo A,
−26,48%**: en catorce años el filtro no evitó una sola caída grande. Lo que
publica el informe es el tramo donde la estrategia menos se distingue de
quedarse quieto.

### El latigazo que no ocurrió

El protocolo advertía que los dos filtros de tiempo anteriores del proyecto
fracasaron por latigazos. En 2022 Horizonte hizo seis cambios en diez meses
—A→E→A→E→A→E→A—, que es exactamente la forma del latigazo. **Resultado: −0,40%
contra −10,14% del Fondo A.** Los latigazos de 2022 ganaron 9,74 puntos.

De 22 cambios en dieciocho años, **el último fue el 04-02-2023**: la estrategia
lleva **3,6 años sin moverse**.

## 6. El registro fuera de muestra: existe y está vacío

Once publicaciones en el historial de `data/horizonte_state.json`, del
28-07-2026 al 22-09-2026:

| | |
|---|---|
| publicaciones | 11 |
| recomendaciones «Fondo A» | **11** |
| recomendaciones «Fondo E» | 0 |
| score, todas las veces | **5 de 5** |
| cambios de fondo | **0** |

En esos 60 días el Fondo A hizo +1,44% y el Fondo E −1,95%, así que estar en A
fue lo correcto. Pero **Horizonte no lo decidió**: en toda la ventana publicada
su recomendación fue idéntica a quedarse quieto, y con el puntaje máximo, o sea
ni siquiera cerca de cambiar.

**El protocolo llamaba a esto «la única evidencia verdaderamente fuera de
muestra del proyecto entero». Lo es, y no contiene información.** Un registro
sin una sola decisión no puede distinguir la estrategia de comprar A y no
mirar. No es que rinda peor que el backtest: es que no dice nada.

Y no es una casualidad de estos dos meses: el backtest tampoco movió nada desde
febrero de 2023. **Para que este registro empiece a valer hay que esperar a la
próxima caída**, que es cuando la estrategia hace lo único que hace.

## 7. Qué está publicando hoy, con FRED degradado

**Los números publicados salieron de la serie completa**, no de la degradada:
la reproducción de la sección 3 calza al flotante usando FRED.

**Pero el archivo que quedó en el repositorio es la serie degradada.**
`data/horizonte_external.csv` en `main` tiene **3.704 filas desde 2012-01-03**,
que es lo que dejó la corrida del 22-09 en Actions: `_fetch_external` escribe la
caché **antes** de que la verificación de completitud rechace, así que el
rechazo no impidió que la serie mala reemplazara a la buena. Los números y su
insumo **ya no son consistentes entre sí**.

### Y el rechazo es un falso positivo

Con la serie de Yahoo, los números publicados **no cambian**:

| | FRED (14.512 filas) | Yahoo (3.703 filas) |
|---|---:|---:|
| completo desde 2012 | +10,6164% | +10,6164% |
| fuera de muestra 2021+ | +13,3243% | +13,3243% |
| peor caída | −26,48% | −26,48% |

Lo que cambia es el **alcance hacia atrás**: con FRED hay señales desde 2003 —22
cambios de fondo—, con Yahoo sólo desde 2013 —14—. Todo eso está fuera de la
ventana que se publica.

Los «138 días hábiles faltantes» que dispararon la guardia son **feriados de
mercado**: 16-01-2012 y 20-02-2012 son Lunes de Martin Luther King y de los
Presidentes, 04-07-2012 es el 4 de julio. FRED trae una fila por cada día hábil
con el valor vacío en los feriados; Yahoo omite el feriado entero. **La guardia
cuenta filas, no datos**, así que está calibrada contra la convención de relleno
de FRED y no contra la completitud de la serie.

**Ninguna de las dos cosas se arregló**, por el punto 8. Las dos quedan
anotadas.

## Lo que esta auditoría no cubre

**El hecho regulatorio y el remapeo a fondos generacionales antes del 1 de abril
de 2027.** El complemento dice que se mantiene del protocolo anterior; ese
protocolo no llegó a esta sesión y no se auditó acá. Si el remapeo cambia qué
son el Fondo A y el Fondo E, **toda la serie de cuotas cambia de significado en
esa fecha** y eso pesa más que cualquier cosa de esta lista.

## Lo que queda anotado para decidir después

1. **El lookahead del rezago de la cuota.** Ejecutar a 4 días fijos cuando la
   publicación llega a demorar 5. Efecto económico acotado, pero es lookahead.
2. **La caché se escribe antes de validar.** Una fuente rechazada reemplaza a la
   buena en disco.
3. **La guardia de completitud cuenta filas**, no datos, y rechaza una serie de
   mercado sana por no traer los feriados rellenos.
4. **El arranque en 2012-08 no tiene razón escrita** y deja fuera el único tramo
   donde la estrategia se distingue con claridad.
5. **Los parámetros están en el máximo de tres de los cuatro barridos.** Ver
   abajo.

## Sensibilidad: la señal de afinado

Sin registro de procedencia, la única forma de sondear si los umbrales están
afinados es ver cuánto depende el resultado de ellos. Diecisiete variantes,
moviendo un parámetro por vez, sobre la ventana completa y contra el Fondo A:

| barrido | variantes | dónde cae producción |
|---|---|---|
| umbral del VIX | 20, 25, **30**, 35, 40 | 2º de 5 (VIX 20 da +0,55%) |
| corte del score | 1, **2**, 3, 4 | **máximo** |
| ventana de la media | 3, **6**, 9, 12 | **máximo** |
| ventana de momento | 6, 9, **12**, 15 | **máximo** |

- Le ganan al Fondo A **13 de 17** variantes.
- Ventaja **mediana**: +0,36%. Producción: **+0,49%**.
- Peor variante: **−0,97%** (media de 3 meses en vez de 6).

**Producción está en el máximo de tres de los cuatro barridos.** Eso no prueba
afinado —los parámetros redondos suelen ser los razonables, y 6 y 12 meses son
convenciones, no números buscados— pero es lo que dejaría un ajuste sobre
resultados, y la ventaja se evapora al moverse: pasar la media de 6 a 3 meses
convierte +0,49% en −0,97%.

**Dicho en una línea:** la ventaja de Horizonte sobre quedarse en el Fondo A, en
la ventana que publica, es de medio punto anual y está en el borde superior de
lo que dan sus vecinos. La ventaja grande es de 2008, y 2008 no está en el
informe.

---

Reproducir: `PYTHONPATH=. python research/horizonte_auditoria/auditoria.py`
(necesita los insumos en el scratchpad; el script dice cuáles).
