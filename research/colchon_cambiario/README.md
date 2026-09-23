# El colchón existe. Y mi predicción se cayó.

Diseño congelado en `HIPOTESIS.md`, en un commit anterior a cualquier resultado.
Investigación pura: no toca `data/`, `reports/`, el pipeline ni el informe.

**Los dos criterios pre-registrados se cumplen: el colchón cambiario es real.**
Y la predicción que yo me había jugado en contra falló por 5,25 puntos.

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
