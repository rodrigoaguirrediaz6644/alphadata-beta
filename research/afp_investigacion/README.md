# Fondos AFP: qué los compone, qué los mueve, y qué hacer con eso

Investigación en fuentes normativas y literatura técnica, con todo lo afirmado
verificado contra datos. No toca producción ni el informe.

Los dos estudios anteriores buscaron una **regla de cambio** y no la
encontraron. Éste empieza por otro lado: por qué está hecho el fondo y qué lo
mueve. Y de ahí sale una estrategia distinta, que no es de tiempo.

---

## La respuesta corta

**El Fondo A ya trae su propia defensa adentro, y cambiarse de fondo la
entrega.** Su exposición cambiaria sin cubrir tiene correlación **−0,44** con la
bolsa global: cuando el mundo cae, el dólar sube y amortigua. Medido: en los 23
meses en que la bolsa global cayó más de 5%, **el Fondo A cayó sólo el 55% de
lo que cayó la bolsa**.

**Lo que decide el resultado no es cuándo cambiarse, es en qué mezcla estar.**
Pasar de 100% en A a 40% en A y 60% en E sube el Calmar de **0,22 a 0,54**:
cuesta 1,2 puntos de retorno anual y corta la peor caída de **−41,8% a −15,0%**.
Ninguna regla de tiempo que probamos se acercó a eso.

**Y la estrategia que sale no exige mirar el mercado nunca.**

---

## 1. Qué compone cada fondo

### Los límites legales

| fondo | renta variable |
|---|---|
| A | 40% a 80% |
| B | 25% a 60% |
| C | 15% a 40% |
| D | 5% a 20% |
| E | **hasta 5%** |

### La composición efectiva del Fondo A

| | |
|---|---|
| renta variable **extranjera** | **65%** |
| renta variable local (Chile) | 15% |
| renta fija extranjera | 18% |
| renta fija local | 2% |

**Dos tercios del Fondo A están afuera de Chile.** Eso es lo que explica casi
todo lo que sigue.

### La cobertura cambiaria, que es la pieza que nadie mira

La normativa —límite **A03** del Régimen de Inversión— fija cuánto de la
inversión en moneda extranjera puede quedar **sin cubrir**, con un techo de
**50%**. La literatura académica que midió las carteras reales entre 2010 y 2014
encontró exposición sin cubrir en torno al 28% ponderado, con el Fondo A en el
extremo alto del menú.

**Esto se confirmó solo en los datos.** Al construir la réplica del Fondo A con
la composición publicada y dejar libre un único parámetro —cuánto de la
exposición extranjera va sin cubrir— el ajuste cae exactamente en **50%**, que
es el límite regulatorio. No se buscó: salió.

## 2. Qué mueve al Fondo A

Regresión de los retornos mensuales del Fondo A de Cuprum sobre factores,
2004-2026, 272 meses:

| factor | beta | t | aporte a la varianza |
|---|---:|---:|---:|
| bolsa mundial desarrollada | 0,419 | 9,8 | **50%** |
| bolsa emergente | 0,226 | 6,8 | **35%** |
| **dólar/peso** | **0,381** | **11,4** | **−5%** |
| bolsa chilena | 0,269 | 8,9 | 19% |
| renta fija (Fondo E) | 0,065 | 1,0 | 0% |

**R² = 0,753.** Volatilidad del Fondo A: 12,2% anual. Residuo sin explicar: 6,1%
anual.

Tres cosas que esta tabla dice y que conviene leer despacio:

**Las betas suman lo que dice la composición.** 0,419 + 0,226 = 0,645 de bolsa
extranjera, contra el 65% publicado. La beta al dólar, 0,381, es 65% × 59% sin
cubrir, muy cerca del 50% regulatorio. **El modelo no se ajustó a estos
números: se construyó con la composición y coincidió.**

**Los emergentes son un tercio del riesgo.** Es el componente que el estudio
anterior no tenía, y por eso su réplica cargaba 50% en acciones chilenas —
estaba usando Chile como sustituto de los emergentes. Con emergentes adentro, el
error de seguimiento baja de 8,0% a 6,3% anual y la correlación sube de 0,751 a
0,857.

**El dólar aporta varianza NEGATIVA.** No es un error de signo. Su correlación
con la bolsa global es −0,44, así que sus términos de covarianza restan. **La
exposición cambiaria reduce el riesgo del fondo en vez de aumentarlo.**

## 3. El colchón cambiario, medido

| | |
|---|---|
| meses con bolsa global en baja | 104 de 272 |
| dólar en esos meses | **+1,59%** |
| dólar en los demás | −0,58% |
| correlación dólar / bolsa global | **−0,44** |

En las **23 caídas fuertes** (bolsa global bajo −5%):

| | |
|---|---|
| bolsa global | −8,80% |
| dólar | **+4,26%** |
| **Fondo A** | **−4,87%** |

**El Fondo A cae el 55% de lo que cae la bolsa mundial.** Ésa es la razón por la
que sus retrocesos en pesos son menores de lo que uno esperaría de un fondo con
80% en renta variable, y es una protección que **ya está pagada y no hay que
acertarle a nada para tenerla**.

### Y la hipótesis de que el peligro es que el colchón falle

Se probó directamente, separando las caídas fuertes según si el dólar subió:

| | meses | Fondo A |
|---|---:|---:|
| caídas **con** colchón (dólar sube) | 18 | −5,06% |
| caídas **sin** colchón (dólar baja) | 5 | **−4,21%** |

**Al fondo le fue mejor cuando el colchón falló.** Con cinco casos no es
concluyente, pero no respalda la hipótesis — y es coherente con que la señal de
colchón que se probó en el estudio anterior no aportara nada (−0,12% de retorno,
cero de mejora en la caída).

La explicación probable: cuando la bolsa cae y el peso **no** se deprecia, suele
ser porque la caída es leve o local, no global.

## 4. Por qué el timing no funciona, con evidencia de afuera

**La Superintendencia de Pensiones midió que el 79,5% de los afiliados que se
cambiaron de fondo obtuvieron peor resultado que si se hubieran quedado**, y
78,2% peor que la estrategia por defecto.

Y hay un efecto de segundo orden documentado: los traspasos masivos obligan a
las AFP a mover carteras, y esos movimientos generan diferencias del orden de
**1% en los precios de los instrumentos del mercado chileno**. El que se cambia
tarde paga el movimiento del que se cambió temprano.

Eso coincide con lo que encontramos por nuestra cuenta:

- **Estudio 1** (doce reglas simples): eligiendo por retorno en 2002-2013 y
  midiendo en 2014-2026, la ventaja es **+0,05 puntos**. Cero.
- **Estudio 2** (dos velocidades, exposición graduada, colchón): transfirió en
  retroceso, pero el diagnóstico mostró que **cada mecanismo funciona en una
  sola ventana y se intercambian**. El que hizo el trabajo era el que la ventana
  de selección rechazaba.

**Tres fuentes independientes apuntan al mismo lugar.**

## 5. Lo que nadie mira: el Fondo E no es lo que parece

| fondo | anual | volatilidad | peor caída | Calmar | cuándo la peor |
|---|---:|---:|---:|---:|---|
| A | +9,27% | 12,2% | −41,83% | 0,22 | 2009-02 |
| B | +8,86% | 9,2% | −28,91% | 0,31 | 2008-10 |
| C | +8,28% | 6,7% | −15,29% | 0,54 | 2008-10 |
| **D** | +7,43% | 5,8% | **−11,15%** | **0,67** | **2021-10** |
| **E** | +6,88% | 5,7% | **−14,61%** | 0,47 | **2021-10** |

**El Fondo E rinde menos que el D y cae más.** Y los dos tocan su peor caída en
**octubre de 2021**, que no fue una crisis de bolsa sino el shock global de
tasas. **El Fondo E es renta fija larga, no es caja**, y tiene su propio riesgo
de cola que no se parece en nada al de la bolsa.

### Pero no está dominado como cobertura

A igual caída máxima objetivo, mezclado con A, los dos refugios dan lo mismo:

| caída máxima | con Fondo E | con Fondo D |
|---|---|---|
| −15% | +8,05% (40% en A) | +8,00% (25% en A) |
| −20% | +8,33% (51% en A) | +8,26% (38% en A) |
| −25% | +8,56% (61% en A) | +8,53% (52% en A) |

**E rinde menos pero cubre mejor, así que se necesita menos.** La elección no es
cuál rinde más: es **contra qué te quieres cubrir**.

| episodio | Fondo A | Fondo D | Fondo E |
|---|---:|---:|---:|
| 2008, bolsa | −41,83% | −0,94% | **+13,38%** |
| 2020, bolsa | −19,60% | −10,16% | **−4,12%** |
| 2022, bolsa | −13,37% | +14,65% | **+22,98%** |
| **2021, tasas** | +15,79% | **−8,69%** | **−12,97%** |

**E es el mejor refugio contra caídas de bolsa y el peor contra shocks de
tasas.** D es al revés. Y en 2020 ninguno de los dos protegió de verdad.

## 6. La estrategia

### Mezcla fija por tolerancia a la caída, reequilibrada una vez al año

No hay señal que mirar, no hay pronóstico que acertar, y no hay nada que hacer
entre una revisión y la siguiente.

**Paso 1 — elegir un punto de la frontera.** Repartiendo el saldo entre Fondo A
y Fondo E, que la ley permite (se puede estar en dos fondos a la vez):

| % en A | anual | volatilidad | peor caída | Calmar | 2002-13 | 2014-26 |
|---:|---:|---:|---:|---:|---:|---:|
| **100%** | **+9,27%** | 12,2% | **−41,83%** | 0,22 | +8,26% | +10,07% |
| 80% | +8,94% | 10,0% | −32,95% | 0,27 | +8,29% | +9,45% |
| 60% | +8,53% | 7,9% | −24,09% | 0,35 | +8,24% | +8,77% |
| **40%** | **+8,05%** | 6,2% | **−14,96%** | 0,54 | +8,08% | +8,03% |
| 30% | +7,79% | 5,7% | −10,82% | 0,72 | +7,98% | +7,64% |
| 20% | +7,50% | 5,4% | −10,16% | **0,74** | +7,84% | +7,24% |
| 0% | +6,88% | 5,7% | −14,61% | 0,47 | +7,52% | +6,38% |

**Lo que compra cada escalón está a la vista.** De 100% a 40% en A se entregan
1,2 puntos anuales y se corta la peor caída de −41,8% a −15,0%. De 40% a 20% se
entregan 0,55 puntos más y se gana apenas 4,8 puntos de caída: **ahí el trato
empieza a empeorar.**

**No hay que afinar el punto.** El óptimo por Calmar es 20% en A sobre todo el
período, pero por ventana fue 0% en 2002-2013 y 30% en 2014-2026. **Cualquier
cosa entre 20% y 40% es la misma decisión**, y pretender más precisión es
inventarla.

**Paso 2 — reequilibrar una vez al año, en fecha fija.** No mensual: sale mejor
anual.

| frecuencia (mezcla 30/70) | anual | peor caída | Calmar |
|---|---:|---:|---:|
| mensual | +7,73% | −10,82% | 0,71 |
| trimestral | +7,75% | −10,63% | 0,73 |
| **anual** | **+7,84%** | **−9,16%** | **0,86** |

El reequilibrio es la única parte activa, y es **contraria al instinto**: compra
A cuando cayó y lo vende cuando subió. No necesita pronóstico y aporta 0,13-0,16
puntos anuales más 1-2 puntos menos de caída, gratis dado que los cambios no
cuestan.

**Paso 3 — no mirar el mercado.** La mezcla se revisa cuando cambia el horizonte
o la tolerancia, **nunca por resultados**. Un cambio motivado por lo que hizo el
mercado es exactamente el comportamiento que llevó al 79,5% a rendir peor.

### Qué recomiendo

**Si el criterio es máximo retorno, la respuesta es 100% en A** y no hay nada más
que hacer. Es lo que dice el dato y es gratis.

**Si la caída del 41,8% de 2008 es intolerable**, el punto sensato es **40% A /
60% E**: cuesta 1,2 puntos anuales y deja la peor caída histórica en −15,0%.

Lo que **no** recomiendo es el punto de máximo Calmar (20% en A). Optimiza un
cociente, no una decisión: entrega 1,8 puntos anuales por una mejora de caída
que ya estaba casi toda conseguida en 40%.

### Y el cortacircuitos, si insistes en algo activo

Del estudio anterior queda una hipótesis medida pero no validada: salir cuando
la renta variable global en pesos cae más de 4-6% en un mes, volver cuando el
mes es positivo. En la ventana de evaluación cortó la peor caída a menos de la
mitad sin cobrar retorno. **Pero la otra ventana lo rechazaba**, así que sólo
corresponde registrarlo hacia adelante, no implementarlo.

**Y no se mezcla con la mezcla fija**: si se hacen las dos cosas a la vez no se
va a poder saber cuál funcionó.

## 7. Qué cambia el 1 de abril de 2027

Los cinco multifondos se reemplazan por diez fondos generacionales. En el ahorro
**obligatorio** uno queda asignado por edad; en el **voluntario** se puede elegir
cualquiera de los diez.

El extremo conservador —Etapa 10— trae **~29% de activos de crecimiento**, que
es casi exactamente el Fondo C de hoy (27,5% de renta variable de referencia).

| % en A | con Fondo E (hoy) | | con Etapa 10 ≈ C (2027) | |
|---:|---:|---:|---:|---:|
| | anual | caída | anual | caída |
| 100% | +9,27% | −41,83% | +9,27% | −41,83% |
| 60% | +8,53% | −24,09% | +8,94% | −31,51% |
| 40% | +8,05% | −14,96% | +8,74% | −26,28% |
| 20% | +7,50% | −10,16% | +8,52% | −20,92% |
| 0% | +6,88% | −14,61% | +8,28% | −15,29% |

**El piso de protección sube de −10,2% a −15,3%.** Después de 2027 no se puede
bajar de ahí: el refugio más conservador del menú nuevo ya trae casi un tercio
en activos de crecimiento.

A cambio rinde más: **+8,28% contra +6,88%**. La frontera entera se desplaza a
más retorno y menos protección.

**La consecuencia práctica:** si la protección importa, **conviene fijar la
mezcla ahora y no después**, porque el instrumento que la da desaparece. Y si lo
que importa es el retorno, 2027 es una mejora.

## 8. Lo que no hay que hacer

**No usar la réplica sintética para operar.** Aun con la composición correcta y
emergentes incluidos, su error de seguimiento es **6,3% anual** contra una
ventaja buscada de 0,5 a 1,6 puntos. Sirve para entender el fondo — y sirvió—
pero no para generar señales.

**No buscar una tercera regla de tiempo.** Tres fuentes independientes dicen lo
mismo y la condición de cierre ya estaba acordada.

**No confundir el Fondo E con caja.** Perdió 14,61% en 2021 sin que hubiera
crisis de bolsa.

---

### Réplica en otra AFP

| fondo | Cuprum anual | Habitat anual | Cuprum caída | Habitat caída |
|---|---:|---:|---:|---:|
| A | +9,27% | +9,43% | −41,83% | −40,48% |
| C | +8,28% | +8,53% | −15,29% | −13,95% |
| D | +7,43% | +7,74% | −11,15% | −11,19% |
| E | +6,88% | +7,18% | −14,61% | −14,90% |

Nada de lo anterior depende de la administradora.

### Fuentes

- [Superintendencia de Pensiones — Régimen de Inversión de Fondos Generacionales](https://www.spensiones.cl/portal/institucional/594/w3-article-17131.html)
- [Superintendencia de Pensiones — Fondos de pensiones y multifondos](https://www.spensiones.cl/portal/institucional/594/w3-propertyvalue-9909.html)
- [Compendio de Pensiones — Operaciones con instrumentos derivados](https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3099.html)
- [Fintualist — la cobertura cambiaria obligatoria y el límite A03](https://fintualist.com/chile/alpha/que-es-la-cobertura-cambiaria-obligatoria-y-por-que-los-fondos-de-pensiones-deberian-abandonarla/)
- [Riesgo cambiario: ¿cubrirse o no? El caso de los multifondos de pensiones en Chile](https://www.redalyc.org/jatsRepo/818/81860976005/html/index.html)
- [Cristi, M. — *Felices y Forrados: efectividad de los cambios de fondo*, U. de Chile](https://repositorio.uchile.cl/handle/2250/149952)
- [Asociación de AFP — Multifondos y límites de inversión](https://www.aafp.cl/temas-previsionales/multifondos/)
- [La Tercera — guía de los fondos generacionales](https://www.latercera.com/pulso/noticia/guia-para-entender-como-funcionaran-los-nuevos-fondos-generacionales-de-las-afp/)

Reproducir: `PYTHONPATH=. python research/afp_investigacion/estudio.py`
