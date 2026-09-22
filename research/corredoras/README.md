# Estudio de corredoras con los datos completos

La pregunta del protocolo: **¿aporta algo la recomendación de una corredora por
encima de lo que ya aporta el momentum?** Y, si aporta, **¿se puede elegir cuál
sin engañarse?**

## Reglas y cortes, fijados antes de mirar

- **Universo:** sólo acciones locales. Fuera los 406 ADR y las 98 extranjeras,
  porque el efecto cambiario no está incorporado. Quedan **4.668
  recomendaciones de 33 corredoras**, del 08-07-2021 al 15-07-2026.
- **Reglas:** Sigma-6 v2.3.0, las que están corriendo. Recomendación vigente
  `+1`, momentum 12-1 > 0, sobre SMA200, tope 10% por acción, revisión semanal,
  sin tope de tenencia. **Idénticas para todas.**
- **Cortes:** selección 08-07-2021 a 31-12-2023; evaluación 01-01-2024 a
  15-07-2026.
- **Costos:** Trii, 0,1785% con **mínimo $999,99** por operación. El mínimo no
  es neutral —castiga a la variante que se diversifica más— así que el capital
  se declara: **$5.000.000 por pieza**, con sensibilidad a $2.500.000.
- **`available_at`** no existe en el archivo: se usa la fecha de publicación,
  el supuesto optimista. Aplica igual a todas.
- **Precios:** los del repositorio, reparados para 2025-2026, no los del zip.

## La cobertura es mucho mejor de lo que decía la orden

La orden daba 30 tickers de 50 y 4.311 recomendaciones con precio. Con la serie
del repositorio y el alias `CENCOSHOPP → CENCOMALLS`:

**41 tickers de 49, y 4.596 recomendaciones de 4.668: 98,5%.**

| corredora | recomendaciones | con precio | cobertura |
|---|---|---|---|
| Credicorp Capital | 1.143 | 1.113 | **97,4%** |
| JPMorgan | 542 | 542 | 100% |
| BICE | 345 | 341 | 98,8% |
| SANTANDER | 300 | 289 | 96,3% |
| BANCHILE | 273 | 273 | 100% |
| LarrainVial Estudios | 263 | 253 | 96,2% |
| Itaú | 239 | 239 | 100% |
| BCI | 233 | 226 | 97,0% |
| Morgan Stanley | 206 | 206 | 100% |
| Goldman Sachs | 182 | 182 | 100% |
| SCOTIA | 167 | 167 | 100% |
| BTG Pactual | 160 | 160 | 100% |
| MBI | 129 | 129 | 100% |
| Security | 116 | 115 | 99,1% |

El rango va de **96,2% a 100%**, no de 87,6% a 100%. Y **Credicorp deja de ser
la de cobertura más baja**: SANTANDER y LarrainVial están por debajo. La
advertencia de que el hueco de precios subestimaba a Credicorp **ya no aplica**.

Los ocho tickers sin serie: ALMENDRAL, ENELGXCH, NITRATOS, NORTEGRAN,
ORO BLANCO, PAZ, SECURITY, SOCOVESA.

## El resultado, con $5.000.000 por pieza

Retorno anual y peor caída en cada ventana, con el puesto al lado.

| variante | cob | pos | selección 21-23 | # | evaluación 24-26 | # | ops |
|---|---|---|---|---|---|---|---|
| LarrainVial Estudios | 96% | 7,6 | **+10,35%** · −11,3% | **1** | +19,68% · −12,0% | 5 | 296 |
| Consenso-6 (v1.0.0) | — | 29,7 | +7,93% · −21,6% | 2 | +26,20% · −11,5% | 2 | 61 |
| BCI | 97% | 6,4 | +7,45% · −11,9% | 3 | +14,36% · −11,9% | 8 | 292 |
| Credicorp Capital | 97% | 7,8 | +6,08% · −11,9% | 4 | **+27,40%** · −13,3% | **1** | 340 |
| MBI | 100% | 4,0 | +5,18% · −11,3% | 5 | +10,19% · −13,5% | 10 | 223 |
| BICE | 99% | 4,9 | +4,53% · −12,6% | 6 | +16,78% · −10,0% | 7 | 249 |
| Itaú | 100% | 5,2 | +3,81% · −13,9% | 7 | +21,37% · −12,9% | 4 | 194 |
| SANTANDER | 96% | 3,1 | +3,26% · −9,7% | 8 | +6,88% · −9,1% | 13 | 152 |
| Morgan Stanley | 100% | 1,3 | +2,97% · −4,7% | 9 | +5,34% · −4,0% | 14 | 45 |
| Security | 99% | 2,8 | +2,12% · −8,5% | 10 | +9,16% · −6,3% | 11 | 99 |
| BTG Pactual | 100% | 6,0 | +1,38% · −11,7% | 11 | +21,44% · −10,1% | 3 | 210 |
| JPMorgan | 100% | 3,7 | +0,88% · −8,7% | 12 | +12,44% · −16,1% | 9 | 168 |
| SCOTIA | 100% | 2,1 | +0,18% · −8,9% | 13 | +1,22% · −7,2% | 15 | 107 |
| Goldman Sachs | 100% | 1,5 | −0,16% · −4,8% | 14 | +8,37% · −9,7% | 12 | 74 |
| BANCHILE | 100% | 5,9 | −0,73% · −11,9% | 15 | +17,35% · −12,0% | 6 | 277 |

### La estimación honesta

**La mejor de la ventana de selección es LarrainVial, con +10,35%. En la
ventana de evaluación rinde +19,68% y queda en el puesto 5 de 15.**

Ése es el número que corresponde poner en la metodología: **+19,68% anual**, no
el de la ganadora medida sobre su propia ventana.

### Elegir corredora es en buena parte ruido

**Correlación de rangos entre ventanas: +0,468.** Hay algo de persistencia
—no es cero— pero muy lejos de ser fiable. Los dos casos que lo muestran:

- **LarrainVial** va de 1ª a 5ª.
- **Credicorp** va de 4ª a **1ª**. Su +27,40% de la ventana de evaluación es el
  mejor de las quince, y ese número **no estaba disponible en la ventana de
  selección**: quien hubiera elegido con la primera mitad no la habría elegido.
- **BANCHILE** va de última a 6ª; **BTG Pactual**, de 11ª a 3ª.

**La dispersión sí es grande**: de +1,22% a +27,40% anual en la evaluación. No
es que dé lo mismo cuál se use; es que **no se puede saber de antemano cuál va
a servir.** Son dos cosas distintas y conviene no confundirlas.

### Consenso-6, el control que no selecciona a nadie

**Queda 2º en las dos ventanas.** Es la única variante que no cambia de puesto.

| | selección | evaluación |
|---|---|---|
| Consenso-6 | +7,93% · −21,6% | +26,20% · −11,5% |
| Credicorp sola | +6,08% · −11,9% | +27,40% · −13,3% |

Es el resultado más importante del estudio. **Una variante que no elige
corredora rinde como la mejor y es la única estable entre ventanas**, con 61
operaciones contra 340 de Credicorp: cinco veces menos rotación.

Su costo está a la vista y no es menor: **29,7 posiciones promedio** —contra
7,8 de Credicorp— y una peor caída de **−21,6%** en la primera ventana, la
mayor de la tabla. Es una cartera muy diversificada, y bajo el mínimo por
operación eso sería caro si el capital fuera chico. Con $5.000.000 por pieza y
29,7 posiciones, cada una son $168.000 y el mínimo muerde.

La predicción de la orden —«Consenso-6 queda por debajo de Credicorp sola en
retorno, pero con mejor retroceso»— **se cumple a medias**: queda por debajo en
la evaluación por 1,2 puntos, y su retroceso es mejor en la evaluación (−11,5%
contra −13,3%) pero mucho peor en la selección (−21,6% contra −11,9%).

## Sensibilidad: $2.500.000 por pieza

Con la mitad del capital, donde ninguna posición de ocho llega al umbral de
$560.218 y el mínimo muerde más:

**El orden casi no cambia.** La correlación de rangos entre ventanas es +0,479,
prácticamente igual. LarrainVial sigue 1ª en selección y 5ª en evaluación;
Credicorp sigue 1ª en evaluación. Los únicos cambios de puesto son entre
Morgan Stanley y SANTANDER (8º/9º) y entre Itaú y BTG (3º/4º).

Todas pierden entre 0,3 y 1,6 puntos anuales. **Consenso-6 pierde menos de lo
esperado** —de +7,93% a +7,75% y de +26,20% a +25,96%— pese a sus 29,7
posiciones, porque rota cinco veces menos: 61 operaciones contra 296 de
LarrainVial. La ventaja de rotar poco compensa la de concentrar.

**La trampa que la orden advertía existe pero no da vuelta el resultado.**

## Qué contesta esto

**¿Aporta la recomendación de corredora?** La prueba nula anterior no
distinguía. Este estudio agrega que **la dispersión entre corredoras es
grande** —26 puntos anuales entre la mejor y la peor en la evaluación—, así que
la señal no es uniformemente ruido: algunas fuentes hacen diferencia.

**¿Se puede elegir cuál?** Con una correlación de rangos de +0,47, **no de
forma fiable.** Elegir por la ventana de selección habría dado LarrainVial, que
rinde 7,7 puntos anuales menos que Credicorp en la evaluación.

**Y entonces la respuesta útil no es elegir.** Consenso-6 —que no elige— queda
2ª en las dos ventanas, es la única estable, y rota cinco veces menos. Fue
reemplazada en su momento por la variante que selecciona; este estudio dice que
ese cambio **no compró resultado, compró un puesto en una ventana**.

## Lo que este estudio no dice

No dice que Credicorp sea mejor ni peor. Su +27,40% en la evaluación es el
mejor de la tabla y su +6,08% en la selección es un cuarto puesto: **las dos
cosas son la misma corredora medida en dos ventanas**, y ésa es exactamente la
razón por la que el protocolo exige fijar los cortes antes.

Tampoco compara contra el mercado: todos los números son de las variantes entre
sí. Y usa las reglas de v2.3.0 —el filtro de precio incluido— así que mide qué
corredora funciona **dentro del sistema actual**, no cuál tiene mejor señal
cruda. Consenso-6 es la excepción, porque corre con sus propias reglas v1.0.0,
sin filtros de precio; esa diferencia juega a su favor o en su contra según la
ventana y **no está aislada.**
