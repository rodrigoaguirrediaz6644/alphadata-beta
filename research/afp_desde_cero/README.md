# Estrategia de fondos AFP, desde cero

Diseño congelado en `DISENO_CONGELADO.md`, en un commit anterior a cualquier
resultado. Horizonte quedó fuera por completo.

---

## La respuesta

**Por el criterio que pediste —máximo retorno— la respuesta es quedarse en el
Fondo A.**

Eligiendo en 2002-2013 la regla con mejor retorno y midiéndola en 2014-2026,
que es el procedimiento fijado de antemano, el resultado es **+10,06% anual
contra +10,01% del Fondo A**. Cinco centésimas de punto. Eso es cero.

**Pero hay una segunda respuesta, y es la que tiene contenido.** Eligiendo por
menor caída en vez de por retorno, la selección **sí transfiere**: la regla
elegida en la primera ventana redujo la peor caída de la segunda de −26,5% a
−17,0%, y cobró 1,12 puntos anuales por hacerlo.

O sea: **no hay una regla que dé más plata, y sí hay una que da menos susto a un
precio conocido.** Cuál de las dos importa es tuya y no del estudio.

---

## 1. La compuerta: qué queda después del 1 de abril de 2027

Esto iba primero por orden del protocolo, y el resultado cambia lo que se puede
prometer.

El Régimen de Inversión de los Fondos Generacionales **se publicó el 1 de
septiembre de 2026** y rige desde el 1 de abril de 2027. Diez fondos, asignados
por año de nacimiento.

| | hoy | desde abril de 2027 |
|---|---|---|
| extremo agresivo | **Fondo A**, 40-80% renta variable | **Etapa 1** (<35 años), hasta ~90-95% en activos de crecimiento |
| extremo conservador | **Fondo E**, hasta 5% renta variable | **Etapa 10** (75+), ~29% en activos de crecimiento |
| ¿se puede elegir? | sí | **obligatorio: no.** Asignado por edad. **Voluntario: sí**, cualquiera de los diez |

**La condición necesaria se cumple:** el ahorro voluntario sigue eligiendo
fondo, así que la estrategia sigue siendo implementable donde importa.

**Pero el refugio se encoge, y mucho.** El extremo conservador pasa de un techo
de 5% en renta variable a cerca de 29% en activos de crecimiento. No son
magnitudes comparables al pie de la letra —«activos de crecimiento» incluye
deuda de mayor riesgo y alternativos, no sólo acciones— pero el orden de
magnitud es inequívoco: **el fondo al que uno se cambia para protegerse va a
tener varias veces más riesgo del que tiene hoy.**

Y la protección es el único producto de esta estrategia. Así que **todo lo que
este estudio mida sobre la capacidad de proteger tiene fecha de vencimiento en
abril de 2027**, y lo que sobrevive es menos de lo que se mide acá. Queda dicho
antes de los números y no después.

Fuentes: [Superintendencia de Pensiones](https://www.spensiones.cl/portal/institucional/594/w3-article-17076.html),
[La Tercera](https://www.latercera.com/pulso/noticia/guia-para-entender-como-funcionaran-los-nuevos-fondos-generacionales-de-las-afp/),
[BioBioChile](https://www.biobiochile.cl/noticias/nacional/chile/2026/09/02/ahora-por-edad-gobierno-publica-como-seran-los-fondos-generacionales-que-reemplazaran-los-multifondos.shtml).

## 2. El rezago, medido de nuevo y contra otra cosa

Medido contra **40 versiones del repositorio fuente** —no del nuestro—,
comparando la fecha de cada commit con la última cuota que traía:

| | |
|---|---|
| rezago de publicación | **2 días corridos en 39 de 40 versiones** (una en 1) |
| máximo | 2 días |

Así que **ejecutar a 1 o 2 días no es posible**: el dato no existe todavía. El
estudio ejecuta a 3 días y reporta 1 y 2 sólo como sensibilidad, no como opción.

**Y el resultado no se da vuelta en ningún lado.** Entre 1 y 10 días de rezago,
ninguna de las doce reglas cambia de signo contra el Fondo A. Por ese lado son
robustas.

### La restricción legal: parcialmente establecida

Los ahorros voluntarios **pueden mantenerse en cualquier tipo de fondo,
independiente de la edad** —lo dice la Superintendencia— y eso es lo que hace
viable la estrategia.

**Lo que no pude establecer con fuente oficial es el límite de traspasos.** Lo
que encontré, de fuente secundaria, es que **los dos primeros cambios del año
son gratuitos y los siguientes pueden tener costo según la AFP**, sin que quede
claro si el ahorro voluntario está exento. **Queda sin resolver**, y no es
menor: la sección 6 muestra que las reglas que mejor protegen superan los dos
cambios anuales en la mayoría de los años. Hay que preguntárselo a Cuprum
directamente.

## 3. Los episodios: el resultado principal

Seis caídas del Fondo A de más de 10% en 24 años. El protocolo esperaba siete;
2018 no llegó al 10% y 2002 queda antes de que la serie tenga historia útil.

| episodio | días al fondo | velocidad | Fondo A | Fondo E |
|---|---:|---|---:|---:|
| 2006-05 a 2006-06 | 35 | rápida | −11,7% | +0,3% |
| **2007-11 a 2009-03** | **488** | lenta | **−44,0%** | +13,1% |
| 2011-01 a 2011-10 | 271 | lenta | −17,4% | +7,9% |
| 2015-11 a 2016-02 | 82 | rápida | −11,0% | +1,1% |
| **2020-02 a 2020-03** | **28** | rápida | **−26,5%** | **−7,8%** |
| 2021-12 a 2023-03 | 442 | lenta | −14,4% | +9,1% |

**El Fondo E no es caja, y 2020 lo demuestra: perdió 7,8%.** En las otras cinco
caídas protegió; en la más rápida, no. Cambiarse a E es cambiar un riesgo por
otro, exactamente como advertía el protocolo.

### La velocidad es el discriminador, y se ve

Qué hizo cada regla desde el máximo previo hasta el fondo:

| regla | 2006 | 2008 | 2011 | 2015 | **2020** | 2022 |
|---|---:|---:|---:|---:|---:|---:|
| Fondo A | −11,7% | −44,0% | −17,4% | −11,0% | **−26,5%** | −14,4% |
| Fondo E | +0,3% | +13,1% | +7,9% | +1,1% | **−7,8%** | +9,1% |
| propia-3m | −5,7% | −3,9% | +0,6% | −1,0% | **−8,5%** | −2,3% |
| propia-6m | −9,6% | −8,6% | +1,4% | −6,0% | **−24,8%** | +6,5% |
| propia-9m | −9,6% | −8,9% | +0,6% | −6,0% | **−24,8%** | +0,4% |
| propia-12m | −9,6% | −8,9% | +0,6% | −6,0% | **−24,8%** | +6,9% |
| mercado-3m | −5,7% | +3,0% | +1,2% | −1,0% | **−8,5%** | −11,2% |
| mercado-6m | −5,7% | −1,9% | +2,8% | −6,0% | **−8,5%** | +0,4% |
| mercado-9m | −9,6% | −1,3% | +0,6% | −6,0% | **−24,8%** | +0,4% |
| mercado-12m | −9,6% | +6,3% | +0,6% | −6,0% | **−24,8%** | −0,7% |
| vol-p70 | −5,7% | +4,6% | −10,1% | −10,5% | −2,8% | +16,4% |
| vol-p80 | −5,7% | +4,6% | −8,2% | −10,5% | **−8,5%** | +16,7% |
| vol-p90 | −9,6% | −9,5% | −8,2% | −10,5% | **−24,8%** | −4,8% |
| vol-p95 | −9,6% | −20,4% | −8,2% | −10,5% | **−24,8%** | −15,2% |

**En 2020, 28 días, las medias de 6, 9 y 12 meses perdieron −24,8% contra −26,5%
del Fondo A: no sirvieron para nada.** Sólo las de 3 meses y los umbrales de
volatilidad más apretados llegaron a tiempo.

Es exactamente lo que el protocolo anticipó y no se arregla con parámetros: una
media larga llega tarde a una caída de tres semanas **por construcción**. Y la
caída rápida no es un caso raro: tres de las seis lo son.

**En 2008, en cambio, casi todo funcionó.** Una caída de 488 días la atrapa
cualquier media. La habilidad que se necesita para 2008 y la que se necesita
para 2020 no son la misma.

## 4. El número honesto: elegir en la primera ventana, medir en la segunda

| regla | selección anual | selección caída | **evaluación anual** | **evaluación caída** |
|---|---:|---:|---:|---:|
| propia-3m | +12,98% | −10,38% | **+10,63%** | **−13,15%** |
| propia-6m | **+13,70%** | −17,22% | +10,06% | −26,48% |
| propia-9m | +13,06% | −17,22% | +9,18% | −26,48% |
| propia-12m | +10,76% | −17,22% | +8,57% | −26,48% |
| mercado-3m | +9,76% | **−9,72%** | +8,89% | −17,01% |
| mercado-6m | +8,27% | −13,00% | +9,49% | −12,68% |
| mercado-9m | +8,94% | −11,72% | +9,40% | −26,48% |
| mercado-12m | +9,00% | −11,72% | +8,95% | −26,48% |
| vol-p70 | +7,63% | −15,15% | **+12,21%** | −11,04% |
| vol-p80 | +9,45% | −13,31% | +11,89% | −13,70% |
| vol-p90 | +7,88% | −20,63% | +10,36% | −26,48% |
| vol-p95 | +8,38% | −25,44% | +9,87% | −26,48% |
| **Fondo A** | +9,94% | −44,00% | **+10,01%** | **−26,48%** |
| Fondo E | +7,54% | −3,23% | +6,17% | −20,81% |

**Eligiendo por retorno:** la mejor de la primera ventana es `propia-6m`
(+13,70% contra +9,94%). En la segunda hace **+10,06% contra +10,01%**. La
ventaja de 3,76 puntos se evaporó a 0,05.

**Eligiendo por menor caída:** la mejor de la primera es `mercado-3m` (−9,72%
contra −44,00%). En la segunda hace **−17,01% contra −26,48%**: protege 9,5
puntos, y cobra 1,12 puntos anuales de retorno.

### Y la trampa, que hay que mirar de frente

Las dos mejores de la ventana de evaluación son `vol-p70` (+12,21%) y `vol-p80`
(+11,89%). **Ninguna de las dos se habría elegido**: en la ventana de selección
hicieron +7,63% y +9,45%, las dos por debajo del Fondo A.

Si alguien mira sólo la columna de evaluación va a concluir que el régimen de
volatilidad funciona. **No es una conclusión, es la definición de mirar el
resultado después.**

### Una observación que no estaba pre-registrada, y va marcada como tal

`propia-3m` es la única que hace las dos cosas: **+10,63% contra +10,01%** y
**−13,15% contra −26,48%**. Fue 3ª por retorno y 2ª por caída en la selección,
así que ninguno de los dos criterios la habría elegido sola.

**No pre-registré un criterio combinado**, y es un hueco de mi propio diseño.
Inventarlo ahora sería elegir después de ver, así que va como observación y no
como resultado. Si se quiere usar, hay que declararlo de antemano y volver a
medir con otro corte, no con éste.

## 5. El costo en calma

62% de los días están fuera de todo episodio. Ahí es donde se paga el seguro:

| regla | anual en calma | contra Fondo A |
|---|---:|---:|
| Fondo A | +9,91% | — |
| propia-9m | +9,43% | **−0,48%** |
| propia-6m | +9,07% | −0,84% |
| propia-12m | +9,05% | −0,86% |
| vol-p95 | +8,66% | −1,25% |
| vol-p90 | +8,50% | −1,41% |
| propia-3m | +8,28% | −1,63% |
| mercado-9m | +8,01% | −1,90% |
| mercado-12m | +7,93% | −1,98% |
| vol-p80 | +7,70% | −2,21% |
| vol-p70 | +7,49% | −2,42% |
| mercado-3m | +7,19% | **−2,72%** |

**Todas cuestan.** Entre medio punto y casi tres puntos anuales. Ése es el
precio del seguro y no hay ninguna que no lo cobre.

## 6. Los cambios de fondo, contra el límite de dos gratis al año

| regla | cambios en 24 años | por año | años con más de 2 |
|---|---:|---:|---:|
| propia-3m | 93 | 3,9 | **20 de 24** |
| mercado-3m | 93 | 3,9 | **17 de 24** |
| mercado-6m | 63 | 2,6 | 11 |
| propia-6m | 49 | 2,0 | 7 |
| vol-p70 | 45 | 1,9 | 6 |
| mercado-9m / 12m | 39 | 1,6 | 5-6 |
| propia-9m / 12m | 35 / 33 | 1,5 | 6 |
| vol-p80 | 33 | 1,4 | 4 |
| vol-p90 | 21 | 0,9 | 3 |
| vol-p95 | 17 | 0,7 | 2 |

**Las dos reglas que mejor protegen son las que más cambian**, y pasan el límite
de dos cambios gratis en 20 y 17 de los 24 años. Ese costo **no está en ninguna
de las cifras de arriba**, porque no está establecido cuánto es ni si aplica al
ahorro voluntario. Es lo primero que hay que preguntar si esto avanza.

## 7. La réplica en otra AFP

Cuprum contra Habitat, ventana de evaluación, ventaja sobre el Fondo A de cada
una:

| regla | Cuprum | Habitat |
|---|---:|---:|
| propia-3m | +0,63% | +0,65% |
| propia-6m | +0,06% | +0,55% |
| mercado-3m | −1,12% | −1,24% |
| vol-p70 | +2,20% | +1,03% |
| vol-p80 | +1,89% | +2,16% |
| vol-p95 | −0,13% | −0,11% |

**El resultado no depende de la administradora.** Once de las doce reglas
conservan el signo y casi la magnitud. La única que se mueve de verdad es
`vol-p70` (+2,20% contra +1,03%), y es justo una de las que no se habría
elegido.

## 8. Lo que el protocolo predijo, y qué pasó

| predicción | resultado |
|---|---|
| «Ninguna de las tres familias le gana al Fondo A en retorno en la ventana de evaluación» | **Correcta en lo que importa.** Cinco de doce le ganan, pero **ninguna de las que el procedimiento habría elegido**: elegir por retorno da +0,05%. |
| «La caída rápida de 2020 se le escapa a todas» | **Parcialmente equivocada.** Se le escapa a las medias de 6, 9 y 12 meses —−24,8% contra −26,5%—, pero las de 3 meses y `vol-p70/p80` la atraparon: −8,5% y −2,8%. |
| «Los latigazos de los años tranquilos se comen lo que ahorren en 2022» | **Correcta como mecanismo, insuficiente como magnitud.** Todas cuestan en calma, entre 0,48 y 2,72 puntos, pero no alcanza a comerse toda la protección. |
| «Al menos una reduce el peor retroceso de forma clara» | **Correcta.** `mercado-3m` elegida de antemano baja la peor caída de −26,5% a −17,0%, y `propia-3m` a −13,2%. |

## 9. El tamaño de muestra, dicho antes de que alguien lea precisión donde no hay

**24 años de datos diarios no son 8.817 observaciones: son seis episodios.**

Elegir la mejor regla en la ventana de selección es elegir sobre **tres** de
ellos —2006, 2008 y 2011—. Y de esos tres, dos son lentos. La ventana de
selección casi no contiene información sobre caídas rápidas, que son la mitad
de las que hay.

Eso acota todo lo de arriba. Ninguna diferencia de menos de un punto anual entre
reglas significa nada con esta muestra, y la diferencia entre la mejor elegida y
el Fondo A por retorno es de **0,05 puntos**.

## 10. Recomendación

**Quedarse en el Fondo A**, si el criterio es máximo retorno. No es un empate a
favor del sistema: es que no hay nada que ganar y sí hay mantención, fuente de
datos, cambios que cuestan y una fecha de vencimiento en abril de 2027.

**La discusión real es la otra**, y no la contesta un estudio. En una AFP no hay
corto, no hay opciones, no hay nada: cambiarse es la única herramienta defensiva
que existe. Una regla que baja la peor caída de −26,5% a −13,2% por 1,6 puntos
anuales puede valer la pena aunque no dé más plata, y puede no valerla. Eso
depende de para qué es esa plata y de cuánto pesa una caída del 26% en el año
equivocado.

**Si se decide avanzar**, lo que corresponde es registrar `propia-3m` —o la que
se elija, declarándolo antes— desde el día uno, **sin recalibrar nada**, con la
señal del Fondo A al lado. Y sabiendo lo que ya está escrito: **ese registro no
dice nada hasta que haya una caída.** Si pasan dos años sin una, sigue vacío, y
eso no es evidencia a favor ni en contra.

**Lo primero que hay que preguntar es el límite de traspasos**, porque
`propia-3m` cambia casi cuatro veces al año y ese costo no está en ninguna
cifra de este documento.

---

Reproducir: `PYTHONPATH=. python research/afp_desde_cero/estudio.py`
