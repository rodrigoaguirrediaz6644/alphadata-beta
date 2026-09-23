# El dólar se justifica por lo que protege, no por lo que rinde

Diseño congelado en `HIPOTESIS.md`, en un commit anterior a cualquier resultado.
Investigación pura: no toca `data/`, `reports/`, el pipeline ni el informe.

**Ésta es la única afirmación que el proyecto puede sostener sobre el dólar, y
va primero porque dentro de un año la tabla se va a leer sola.**

La tabla dice +9,06% anual con dólar contra +7,01% sin dólar, y cualquiera va a
concluir que el dólar gana plata. **No está demostrado que gane plata.** Esos
+2,05 puntos son, en el fondo, «el peso se depreció de 500 a 970 en diecinueve
años»: un movimiento direccional que pudo haber sido al revés, no un mecanismo
repetible.

**Lo que sí está demostrado es que amortigua:** 3,56 puntos en los episodios,
sobre trece eventos distintos y separados en el tiempo. *Eso* es un mecanismo.

| | de dónde viene | ¿se repite? |
|---|---|---|
| **el retorno** (+2,05 pts anuales) | una tendencia del peso en una ventana | **no se sabe** |
| **la protección** (3,56 pts en episodios) | trece eventos distintos | **sí** |

Los dos criterios pre-registrados se cumplen: el colchón es real. Y la
predicción que yo me había jugado en contra falló por 5,25 puntos.

---

## Primero: la regla que congelé estaba rota

La escribí pensando en las AFP, donde el Fondo A recupera máximos entre crisis.
**La bolsa chilena estuvo bajo su máximo de 2010 durante diez años seguidos**,
así que «tramo contiguo bajo el máximo móvil» produjo esto:

| episodio | días |
|---|---:|
| 2007-12-07 a 2008-10-10 | 308 |
| **2010-11-04 a 2020-03-18** | **3.422** |
| 2026-01-27 a 2026-06-05 | 129 |

Un episodio de 3.422 días junta 2011, 2015-16, 2019 y 2020 en uno solo.

**El defecto se ve sin mirar el resultado** —un episodio de nueve años no es un
episodio— así que reparé el instrumento y lo dejé escrito: el umbral de 15% no
se toca, y el episodio ahora se cierra cuando la serie recupera la mitad de lo
caído. Las dos reglas quedan en el código.

## Los 20 episodios

ECH × USDCLP como bolsa chilena en pesos, 2007-11-21 a 2026-09-23. Cartera de
37,5% Chile, 37,5% global y 25% oro, rebalanceo diario.

| episodio | días | Chile | USD/CLP | con dólar | sin dólar | beneficio |
|---|---:|---:|---:|---:|---:|---:|
| 2008-04 a 2008-09 | 161 | −21,66% | +16,01% | −8,45% | −16,42% | **+7,97%** |
| 2008-09 a 2008-10 | 10 | −29,95% | +9,14% | −8,78% | −16,38% | **+7,60%** |
| 2011-08 a 2011-09 | 23 | −17,97% | +5,38% | −8,71% | −11,64% | +2,92% |
| 2013-02 a 2016-01 | 1.066 | −32,78% | +53,53% | +6,51% | −18,35% | **+24,86%** |
| 2018-01 a 2018-09 | 216 | −15,61% | +12,60% | −1,51% | −8,79% | +7,28% |
| **2019-10 a 2019-11** | **26** | **−15,55%** | **+6,29%** | **−1,13%** | **−4,94%** | **+3,81%** |
| 2019-11 a 2020-03 | 124 | −43,41% | +5,53% | −20,80% | −23,71% | +2,91% |
| 2021-03 a 2021-10 | 211 | −23,61% | +12,02% | +3,15% | −4,18% | +7,33% |
| 2022-09 a 2022-10 | 42 | −18,25% | +4,57% | −5,95% | −8,47% | +2,51% |
| 2026-01 a 2026-03 | 52 | −15,20% | +5,54% | −7,43% | −10,11% | +2,68% |

*(Los 10 restantes, con beneficio negativo o nulo, están en `episodios.csv`.)*

### El veredicto contra el criterio escrito antes

| | |
|---|---|
| «el peso sube en al menos 5 de los episodios» | **13 de 20. CUMPLE** |
| «el beneficio mediano es de al menos 2 puntos» | **+2,60%. CUMPLE** |

**El colchón cambiario existe.** Y **octubre de 2019 lo muestra solo**, que era
el caso que más informaba: estrés chileno puro, sin crisis global que lo
acompañe. Chile cayó 15,55%, el peso se debilitó 6,29% y la cartera con dólar
cayó 1,13% contra 4,94%.

### Pero no es universal, y eso también va

**En 7 de los 20 episodios tener el dólar fue peor.** Son aquellos donde el peso
se fortaleció mientras la bolsa chilena caía —2010-11, 2011-05, 2012-04,
2020-07—. El mecanismo es real y falla un tercio de las veces.

## Mi predicción, y cómo se cayó

Escribí antes de medir que **la cartera con dólar igual tendría peor caída
máxima sobre la ventana completa**, razonando que el dólar agrega riesgo fuera
de los episodios.

| | anual | peor caída | volatilidad |
|---|---:|---:|---:|
| **con el dólar** | +9,06% | **−26,81%** | 22,59% |
| **sin el dólar** | +7,01% | **−32,06%** | 17,27% |
| el dólar solo | +3,56% | −34,41% | 16,61% |

**Falso por 5,25 puntos.** El dólar **reduce** la caída máxima.

Lo que sí acerté es la mitad del razonamiento, y por eso conviene separarlo:

| | en episodios | fuera de ellos |
|---|---:|---:|
| con el dólar | −7,63% | +17,79% |
| sin el dólar | −11,19% | +20,08% |
| días | 2.019 | 2.680 |

**Amortigua 3,56 puntos en los episodios y cuesta 2,29 fuera de ellos.** Y
**sube la volatilidad diaria mientras baja la caída profunda**, que es
exactamente el perfil de un seguro: se paga todos los días y se cobra pocas
veces.

## Qué corrige de lo que dije antes

En `research/exposicion_dolar/` concluí, sobre 2021-2026, que **«el 62,5% no es
un seguro, es una apuesta direccional al dólar»**. Esa frase estaba medida sobre
una ventana sin una caída chilena de las que importan, y **sobre 19 años no se
sostiene**: el dólar se comporta como seguro contra caídas profundas.

Lo que sí se sostiene de aquello es que **cuesta**: 2,29 puntos anuales fuera de
los episodios y 5 puntos más de volatilidad diaria.

**La formulación correcta para Rodrigo es la de las dos cosas juntas**, que es
como se decide todo lo demás en este proyecto: el 62,5% en dólares amortiguó
3,56 puntos en las caídas chilenas de diecinueve años y costó 2,29 puntos
anuales el resto del tiempo, con más vaivén diario. No es gratis y no es
inútil; es un intercambio con las dos cifras a la vista.

## Las dos advertencias que van con esto

**El retorno favorece al dólar por la ventana.** El peso se depreció de ~500 a
~970 en diecinueve años, o sea +3,56% anual del dólar solo. Esa parte del
resultado **sí depende de la ventana**; la de la caída máxima depende mucho
menos, porque viene de episodios repetidos y no de una tendencia.

**La bolsa chilena es ECH y no el IPSA**, porque `^IPSA` no existe en el
proveedor y las acciones chilenas del almacén empiezan en 2015. Es un ETF con
diferencias de seguimiento, y el episodio de 2008 arranca con la serie ya
empezada —el máximo real fue en octubre de 2007 y ECH parte un mes después—, así
que esa caída sale subestimada.

---

Reproducir: `PYTHONPATH=. python research/colchon_cambiario/estudio.py`

## Verificación 1: los siete fracasos **no** son los episodios chicos

Era la pregunta correcta y la respuesta es la incómoda. Ordenados de la caída
más profunda a la más leve:

| # | episodio | cae Chile | USD/CLP | beneficio |
|---:|---|---:|---:|---:|
| 1 | 2019-11 a 2020-03 | −43,41% | +5,53% | +2,91% |
| 2 | 2013-02 a 2016-01 | −32,78% | +53,53% | +24,86% |
| 3 | 2008-09 a 2008-10 | −29,95% | +9,14% | +7,60% |
| **4** | **2011-05 a 2011-08** | **−28,45%** | **−4,24%** | **−2,14%** |
| **5** | **2007-12 a 2008-01** | **−24,67%** | **−5,79%** | **−1,89%** |
| 6 | 2021-03 a 2021-10 | −23,61% | +12,02% | +7,33% |

| | beneficio mediano | fracasos |
|---|---:|---:|
| los 10 más profundos | +2,26% | **3 de 10** |
| los 10 más leves | +2,60% | **4 de 10** |

**Están repartidos.** Tres de los diez más profundos fallaron, incluidos el
cuarto y el quinto peor. El beneficio mediano es prácticamente igual en los dos
grupos.

**Entonces el resultado no es más fuerte que «13 de 20»: es exactamente eso.**
El seguro no discrimina entre caídas grandes y chicas — falla un tercio de las
veces en las dos.

Y no se salió a buscar qué distingue a los siete. Veinte episodios con siete
fracasos no sostienen una sub-regla, y buscarla es como se fabrica un backtest
bonito.

## Verificación 2: ECH es un proxy pobre del IPSA — y eso jugaba **en contra**

Era la preocupación metodológica correcta, y el proxy sale mal parado:

| | |
|---|---|
| correlación de retornos diarios | **+0,634** |
| error de seguimiento anualizado | **24,03%** |
| en episodios, correlación mediana | +0,718 |
| en episodios, error de seguimiento mediano | 20,6% |

**ECH × FX no es la bolsa chilena en pesos: es un primo lejano.** Y exagera las
caídas — en 10 de 11 episodios cae más que el IPSA, con una diferencia mediana
de **−2,66%**.

### Pero el veredicto no sólo sobrevive: mejora

Misma regla, mismo umbral, misma ventana (2015-2026, 2.779 días), cambiando sólo
la serie chilena:

| bolsa chilena | episodios | peso sube | benef. mediano | caída con | caída sin |
|---|---:|---:|---:|---:|---:|
| ECH × FX | 11 | 9 de 11 | +2,92% | −26,74% | −29,41% |
| **IPSA** | **5** | **5 de 5** | **+9,30%** | **−25,03%** | **−28,57%** |

**Con el IPSA el colchón aparece en 5 de 5 episodios y el beneficio mediano
triplica.** La contaminación que temías existe y es grande, pero empujaba en
contra del resultado, no a favor: ECH inventa episodios que el IPSA no tiene
—once contra cinco— y son justamente los sustos menores donde el colchón falla.

**Lo que hay que decir con esto:** los números de los veinte episodios están
medidos sobre una serie que no es el IPSA, y la mitad de los fracasos
probablemente sean episodios que no existieron. **No los corrijo** —eso exigiría
rehacer todo sobre una serie que no llega a 2008— pero la dirección del sesgo
está medida y es ésta.

### Lo que no se pudo verificar

El IPSA del proyecto **empieza en 2015 y queda congelado el 17-07-2026**, así
que la comparación cubre 11 de los 20 episodios. **Los dos fracasos más
profundos —2011 y 2007-08— quedan fuera y no se pueden re-medir con el IPSA.**
Conseguir una serie del IPSA que llegue a 2007 cambiaría eso; con lo que hay en
el repositorio, no.
