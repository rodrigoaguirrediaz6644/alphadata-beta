# La perilla que nos separaba, los pares en las siete, y 2027 medido

Investigación pura: no toca `data/`, `reports/`, el pipeline ni el informe.
Nada sobre el tope ni sobre el boletín 13.959-13.

**Los tres resultados, arriba:**

1. **La discrepancia es una sola perilla y no es el refugio ni el rezago:** tus
   «126 días» son corridos, los míos eran hábiles. Y al aislarla aparece algo
   que nos corrige a los dos: **el precipicio está entre 100 y 110 días
   hábiles**, no en 150. La meseta que mediste es real pero termina antes de lo
   que parecía.
2. **Tu tabla de pares replica en las siete AFP.** A→C da entre +17,49 y +21,83
   puntos de ventaja; tu +20,76 cae adentro.
3. **2027 no mata la estrategia, pero tu «dos tercios del beneficio» está
   medido con la vara equivocada.** La ventaja *sube* a +29,66 puntos; la
   protección en términos absolutos **empeora de −11,72% a −21,98%, casi el
   doble de caída.** La ventaja crece porque el lado agresivo empeora más, no
   porque el refugio funcione.

---

## 1. La perilla: «126 días» significaba dos cosas

Mi `histeresis()` es literalmente tu especificación —salida cuando
`precio/media−1 < −0,02`, vuelta sobre `+0,02`, se mantiene entre medio,
posición desplazada, sin costo, sin tope—. No estaba ahí.

Cuprum, banda 2%, refugio D, desde 2011-04-01. Tu número: **−15,56%**.

| grilla | la media es | rezago | caída | cam/año |
|---|---|---|---:|---:|
| corridos | 126 filas = 126 corridos ≈ 90 hábiles | 5 corridos | **−15,56%** | 2,3 |
| corridos | 126 filas = 126 corridos ≈ 90 hábiles | 7 corridos = 5 hábiles | **−15,56%** | 2,3 |
| hábiles | 90 filas = 90 hábiles ≈ 126 corridos | 5 hábiles | **−15,56%** | 2,2 |
| hábiles | 126 filas = 126 hábiles ≈ 176 corridos | 5 hábiles | **−21,83%** | 1,6 |
| corridos | 176 filas = 176 corridos = 126 hábiles | 7 corridos = 5 hábiles | **−21,83%** | 1,6 |

**El rezago no mueve nada** —5 o 7 filas dan idéntico—. La media sí. Tu ventana
efectiva son ~90 días de cotización; la mía eran 126.

### Y eso destapa algo que nos corrige a los dos

Peor caída por largo de media, en **días hábiles efectivos**:

| | 45 | 63 | 90 | 100 | **110** | 126 | 150 |
|---|---:|---:|---:|---:|---:|---:|---:|
| refugio D | −15,18% | −15,29% | −15,56% | −15,56% | **−21,83%** | −21,83% | −21,83% |
| refugio E | −14,39% | −12,28% | −10,32% | −11,20% | **−19,02%** | −19,02% | −19,02% |

**El salto está entre 100 y 110 días hábiles.** Tu barrido de 63/100/126
corridos son 45/71/90 hábiles: **los tres caen antes del salto**, por eso
pareció meseta plana. Y tu «150 en adelante cae al precipicio» es correcto —150
corridos son 107 hábiles, justo pasando el borde.

Entonces la robustez al largo de la media es **más estrecha de lo que los dos
reportamos**: la región buena va de ~45 a ~100 días hábiles y se cae seis puntos
al cruzarla. Mi 126 hábiles estaba 26 días al otro lado del borde; por eso mi
número era peor, y no porque midiera mal.

**Nota para cualquier cosa que se escriba después: el largo de la media hay que
declararlo en días de cotización, no en «días».**

## 2. Los cinco pares en las siete AFP

Banda 2%, media 126 corridos, rezago 7 corridos (= 5 hábiles), ventana
2004-2019, señal sobre el nivel del fondo agresivo. **Ventaja en caída:**

| par | capital | cuprum | habitat | modelo | planvital | provida | mediana |
|---|---:|---:|---:|---:|---:|---:|---:|
| A→E | +29,63% | +32,28% | +30,69% | *+7,44%* | +30,63% | +32,20% | **+30,66%** |
| A→D | +23,81% | +28,53% | +29,80% | *+7,04%* | +28,56% | +30,28% | **+28,55%** |
| **A→C** | +17,49% | +21,11% | +21,48% | *+5,81%* | +21,03% | +21,83% | **+21,07%** |
| B→D | +16,08% | +18,18% | +18,81% | *−0,32%* | +17,78% | +19,40% | **+17,98%** |
| B→C | +9,44% | +10,89% | +11,21% | *+0,58%* | +10,42% | +11,05% | **+10,66%** |

*Uno no tiene historia en la ventana. Modelo va en cursiva porque arranca en
septiembre de 2010 y **no ve 2008**: es la misma asimetría de ventana de
siempre, no una AFP distinta.*

**Tu +20,76 de A→C replica: la mediana es +21,07 y las cinco AFP con 2008 caen
entre +17,49 y +21,83.** Excluyendo Modelo el rango es de 4,3 puntos. La
escala ordenada por lo defensivo del refugio también replica, pareja en las
siete.

## 3. El par de 2027

Réplica sintética desde los límites: se resuelve la mezcla de Fondo A y Fondo E
que iguala el porcentaje de activos de crecimiento, usando los máximos de renta
variable del DL 3.500 (80% y 5%) como ancla pública.

**Antes que nada, un dato que sale de la propia construcción:** el Fondo Inicial
al 95% pide **w = 1,20 en Fondo A**. Es decir, **el fondo más joven de 2027 no
se puede representar con ningún multifondo actual: es más agresivo que el
Fondo A.** Su caída sintética 2004-2019 es **−51,65% contra −44,00% del Fondo
A**. Tenías razón en que el lado agresivo estaba subestimado.

### Tu diagnóstico replica casi exacto

| fondo | corr con A (tú) | corr con A (yo) | vol anual | caída propia |
|---|---:|---:|---:|---:|
| C | +0,940 | **+0,936** | 4,80% | −16,90% |
| D | +0,809 | **+0,715** | 3,22% | −8,52% |
| E | +0,136 | **+0,093** | 2,68% | −11,13% |

**La correlación es lo que manda y eso queda confirmado.** (Tu métrica de
«sigue cayendo» no la reproduzco: a mí las medianas dan todas positivas, entre
+1,19% y +1,70%. No sé de dónde viene la diferencia y no la voy a explicar sin
medirla; la conclusión sobre correlación no depende de ella.)

### Y el fondo de Consolidación es un refugio mediocre

| Consolidación | w en Fondo A | **corr con Inicial** | vol anual | caída propia |
|---:|---:|---:|---:|---:|
| 20% | 0,20 | 0,681 | 3,04% | −8,83% |
| 25% | 0,27 | 0,794 | 3,42% | −11,56% |
| **29%** | 0,32 | **0,855** | 3,78% | −14,03% |
| 35% | 0,40 | 0,914 | 4,39% | −17,65% |
| 40% | 0,47 | 0,944 | 4,94% | −20,71% |

**Al 29%, la correlación con el fondo agresivo es 0,855** — entre el Fondo D
(0,715) y el Fondo C (0,936), y a un mundo de distancia del Fondo E (0,093).
Por tu propio criterio, **el refugio de 2027 no está descorrelacionado**.

### Lo que eso le hace a la estrategia

| par | estrategia | agresivo | ventaja | cam/año |
|---|---:|---:|---:|---:|
| A→E (hoy) | +11,18% / **−11,72%** | +8,79% / −44,00% | +32,28% | 2,1 |
| A→D | +10,50% / −15,47% | +8,79% / −44,00% | +28,53% | 2,1 |
| A→C | +10,21% / −22,89% | +8,79% / −44,00% | +21,11% | 2,1 |
| Inicial→Consol 20% | +11,11% / −17,06% | +8,93% / −51,65% | +34,59% | 2,6 |
| **Inicial→Consol 29%** | +10,88% / **−21,98%** | +8,93% / −51,65% | **+29,66%** | 2,6 |
| Inicial→Consol 40% | +10,58% / −27,66% | +8,93% / −51,65% | +23,98% | 2,6 |

**Acá está la corrección a tu punto 1.** Medido como *ventaja sobre el fondo
agresivo*, 2027 no pierde nada: +29,66 puntos contra +32,28 de hoy, o sea 92%
del beneficio, no dos tercios. **Pero eso es un espejismo de la vara.** La
ventaja se mantiene porque el fondo agresivo empeora —de −44,00% a −51,65%—, no
porque el refugio proteja.

**Lo que hay que mirar es la caída propia de la estrategia: pasa de −11,72% a
−21,98%. Casi el doble.** Y tú mismo escribiste que la protección es el único
producto de esta estrategia.

Dicho derecho: **en abril de 2027 la estrategia sigue existiendo y sigue
ganándole al fondo agresivo, pero deja de ser una estrategia de protección.**
Con −21,98% de caída peor está más cerca de la mezcla fija que de lo que hace
hoy con el Fondo E.

### Dos salvedades, y una donde no te acompaño

**La mezcla A/E es una aproximación lineal.** Si el fondo de Consolidación real
diversifica con algo que el Fondo E no tiene —deuda local larga indexada a UF,
alternativos ilíquidos que no se marcan a mercado— su correlación va a ser otra.
**Ése es exactamente el número que hay que pedir**, y ahora sabemos qué pedir:
la correlación de la cartera de referencia del fondo de Consolidación con la del
Fondo Inicial, no su volatilidad ni su porcentaje de renta variable.

**El 29% no lo pude verificar.** La Superintendencia confirma el 95% del fondo
más joven; el ~29% de Consolidación viene de tu orden y no lo encontré en la
fuente. Por eso está barrido de 20% a 40%: la conclusión no cuelga de ese
número, porque en todo el rango la correlación va de 0,68 a 0,94 y nunca se
acerca a la del Fondo E.

**Y donde no te acompaño:** dijiste que en 2011-2026 el orden se da vuelta y D
es mejor refugio que E. **En mis series no se da vuelta en ninguna ventana.**

| ventana | corr D-A | corr E-A | caída con D | caída con E | mejor |
|---|---:|---:|---:|---:|---|
| 2004-01 a 2019-12 | 0,715 | 0,093 | −15,47% | **−11,72%** | E |
| 2011-04 a 2026-09 | 0,465 | 0,092 | −15,56% | **−10,44%** | E |
| 2020-01 a 2026-09 | 0,433 | 0,124 | −15,56% | **−10,44%** | E |

El Fondo E gana en las tres, y por 4 a 5 puntos. Puede que midas sobre el
índice del sistema o con otra ventana; con estas series, **E domina a D como
refugio y no hay tal cosa de que dependa del tipo de crisis.** Si tenés la
corrida que muestra lo contrario, ésa es la que hay que cruzar.

## 4. Sobre el umbral de 8 puntos

Tenés razón en el orden: primero la especificación, después el umbral. Ya
resuelta la especificación, con media dentro de la región buena (~90 hábiles) y
refugio E, la caída es **−10,32%** contra **−26,48%** del Fondo A: **+16,2
puntos.** Pasa el umbral con holgura.

**Pero lo digo con la etiqueta puesta:** el largo de la media quedó elegido
después de ver que 126 hábiles caía del otro lado del precipicio. Eso es
selección posterior, igual que la banda. **No lo cuento como que el umbral se
cumplió; lo cuento como que el umbral no se puede aplicar todavía, porque el
parámetro que decide está a diez días hábiles de un salto de seis puntos.**

Lo que sí vale sin etiqueta es lo de siempre: **dispersión de 1,1 a 4,3 puntos
entre AFP contra un efecto de 21 a 30.** El mecanismo no es de una serie.

## Lo que no hace este estudio

No propone regla nueva, no implementa nada, y no ajusta la banda ni el rezago.
El largo de la media se barre para mostrar dónde está el borde, no para elegir
el punto.

---

Reproducir: `PYTHONPATH=. python research/afp_2027/estudio.py`

Series en `research/afp_tope_y_banda/vc_*.csv`.

Fuentes normativas:
[Superintendencia de Pensiones — Régimen de Inversión de los Fondos Generacionales](https://www.spensiones.cl/portal/institucional/594/w3-article-17131.html) ·
[Superintendencia de Pensiones — propuesta en consulta](https://www.spensiones.cl/portal/institucional/594/w3-article-17076.html)
