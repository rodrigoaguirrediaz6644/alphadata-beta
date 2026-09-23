# El tope, la banda en las siete AFP, y la ley que sí importa

Criterio de la réplica congelado en `HIPOTESIS.md`, en un commit anterior a
cualquier resultado. No toca `data/`, `reports/`, el pipeline ni el informe.

**Lo primero, porque cambia el orden de todo lo demás:** el tope de dos
traspasos no aplica, nunca aplicó, y la pregunta se volvió irrelevante — pero
por una razón peor que la que buscábamos. Ver el punto 3.

---

## 1. Reconciliado: los 23 puntos son 2008, y mi tabla tenía un defecto

Mi implementación del tope coincide con la tuya en las tres cosas que
preguntaste:

| | mi implementación |
|---|---|
| al agotar los traspasos | **queda pegada en el fondo actual**, no vuelve a ninguno por defecto |
| contador | **año calendario**, no móvil |
| regla evaluada | **la misma** con tope y sin tope; sólo cambia si el cambio se ejecuta |
| posición inicial | Fondo A |
| refugio | **Fondo E** (tú usas D) |

No está ahí la diferencia. **Está en la ventana.**

| desde | tope | anual | peor caída | cam/año | Fondo A | caída A | la caída va de |
|---|---|---:|---:|---:|---:|---:|---|
| 2004-01-07 | sin | +10,70% | −10,82% | 18,0 | +9,40% | −42,71% | 2022-07 a 2022-10 |
| 2004-01-07 | **2/año** | +9,77% | **−40,43%** | 2,0 | +9,40% | −42,71% | **2008-06 a 2009-03** |
| 2010-01-01 | sin | +9,21% | −10,82% | 18,1 | +9,07% | −26,06% | 2022-07 a 2022-10 |
| 2010-01-01 | **2/año** | +9,44% | **−17,24%** | 2,1 | +9,07% | −26,06% | 2011-04 a 2011-10 |
| 2014-01-01 | **2/año** | +10,48% | −13,93% | 2,1 | +10,00% | −26,06% | 2021-12 a 2022-03 |

**Mi −40,43% reproduce exacto, y sobre tu ventana da −17,24% contra tu −16,95%:
0,3 puntos de diferencia.** No hay desacuerdo de implementación. Mi ventana
arranca en 2004 y la tuya no ve el máximo de 2008; **ésa es toda la brecha.**

La caída con tope ocurre **entre junio de 2008 y marzo de 2009**. La regla sin
tope quería seis cambios ese año; con dos se gastan temprano y la posición se
queda en Fondo A durante el desplome entero.

### Mi defecto, que es peor que el número

En aquella tabla las filas de las reglas corrían desde **2004** y las filas de
«comprar A y no mirar» desde **2010**. Puse −40,43% al lado de un −26,06% que
venía de otra ventana. **Sobre la ventana de las reglas el Fondo A cae
−42,71%**, así que la frase «prácticamente la caída completa del Fondo A» era
correcta y el número que la respaldaba no. Comparación ilegible por mi culpa.

### Lo que cambia la conclusión

**El tope no cobra un peaje fijo. Su costo es binario según si la ventana
contiene un derrumbe lento de doce meses.**

- Sin 2008: cuesta 1 a 3 puntos de caída. Es tu resultado y es correcto.
- Con 2008: la protección desaparece. Es el mío y también es correcto.

Ninguno de los dos números describe «el efecto del tope». Los dos describen
**cuántos episodios lentos vio la ventana**, que es exactamente el problema de
fondo de toda esta línea: hay cuatro o cinco crisis en veintitrés años.

## 2. La banda replica en las siete AFP — y no llega a mi propio umbral

Media de 126 días hábiles, rezago de 5 días hábiles, banda fija en 2,0%
—**no se re-eligió por AFP**—, señal sobre el valor cuota del Fondo A de cada
una, refugio Fondo E.

### En ventana común, la dispersión es de un punto

| AFP | anual | caída | cam/año | Fondo A | caída A | ventaja |
|---|---:|---:|---:|---:|---:|---:|
| capital | +9,70% | −19,43% | 1,7 | +8,60% | −26,66% | +7,22% |
| cuprum | +9,81% | −19,02% | 1,6 | +8,70% | −26,48% | +7,46% |
| habitat | +9,81% | −18,67% | 1,6 | +8,70% | −26,06% | +7,39% |
| modelo | +9,24% | −19,80% | 1,7 | +8,55% | −27,64% | +7,84% |
| planvital | +9,30% | −19,33% | 1,7 | +8,56% | −26,62% | +7,29% |
| provida | +9,44% | −19,91% | 1,7 | +8,53% | −26,69% | +6,78% |

*(desde 2011-04-01, la ventana común a seis; Uno arranca en 2019 y va aparte)*

**Rango de la ventaja entre AFP: 1,1 puntos contra un efecto de 7,3.** Eso es
lo más fuerte que salió: **no es el artefacto de una serie.** El mismo mecanismo,
el mismo tamaño, en seis administradoras distintas.

Sobre las siete en la ventana corta (2020-05 en adelante) la ventaja es +2,80%
a +4,28%, rango 1,5 puntos. Uno incluido, y se comporta como las demás.

### La meseta está, y 2,0% cae adentro en las siete

Peor caída por banda:

| AFP | 0,0% | 0,5% | 1,0% | 1,5% | **2,0%** | 2,5% | 3,0% | **3,5%** | 5,0% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| capital | −18,89% | −17,90% | −19,43% | −19,43% | **−19,43%** | −19,43% | −19,43% | −19,43% | −24,86% |
| cuprum | −18,16% | −17,42% | −19,02% | −19,02% | **−19,02%** | −19,02% | −19,02% | **−21,80%** | −24,36% |
| habitat | −17,91% | −17,14% | −18,67% | −18,67% | **−18,67%** | −18,67% | −18,67% | **−22,18%** | −23,93% |
| modelo | −19,85% | −15,87% | −14,87% | −19,80% | **−19,80%** | −19,80% | −19,80% | −19,80% | −19,80% |
| planvital | −18,57% | −17,76% | −19,33% | −19,33% | **−19,33%** | −19,33% | −19,33% | −19,91% | −24,73% |
| provida | −18,97% | −18,29% | −19,91% | −19,91% | **−19,91%** | −19,91% | −20,99% | −20,99% | −25,13% |

Y la rotación cae de **~7,5 a ~1,5 cambios al año** en las siete, igual de
parejo. **Confirmás el mecanismo: la banda compra rotación baja casi gratis.**

### Pero falla la condición que yo mismo escribí

Pre-registré: la banda de 2,0% deja la caída **al menos 8 puntos** mejor que el
Fondo A de cada AFP.

**0 de 6 lo cumplen.** El rango es +6,78% a +7,84%. Falla por poco y falla
parejo — que es la peor forma de fallar, porque no es ruido.

Las otras tres condiciones se cumplen: el retorno queda arriba del Fondo A en
las seis (+0,69% a +1,11%), la dispersión es de un punto, y 2,0% cae dentro de
la meseta en todas.

**Entonces: el mecanismo es real y replica; la magnitud que yo exigí no está.**

### Y queda una diferencia de convención sin explicar

Tú mides −15,30% de caída; yo −19% con refugio E y **−21,8% con refugio D**.
Probé el refugio porque era la diferencia obvia, y **empeora en vez de
acercarse**:

| AFP | refugio E | refugio D | E solo | D solo |
|---|---:|---:|---:|---:|
| cuprum | −19,02% | −21,83% | −20,81% | −16,17% |
| habitat | −18,67% | −21,41% | −21,18% | −16,23% |
| provida | −19,91% | −22,25% | −23,87% | −18,31% |

**El Fondo D es más seguro que el E por su cuenta —−16,2% contra −20,8%— y sin
embargo hace peor a la estrategia.** No tengo explicación para eso y no la voy
a inventar. Lo dejo anotado como lo que es: una discrepancia abierta entre tu
medición y la mía que el refugio no cierra.

### El tope sobre la banda: el mismo patrón de 2008

| AFP | sin tope | con tope 2/año | ¿ve el máximo de 2008? |
|---|---:|---:|---|
| cuprum | −19,02% | **−41,62%** | sí |
| habitat | −18,67% | **−41,78%** | sí |
| planvital | −19,33% | **−39,09%** | sí |
| provida | −19,91% | **−43,48%** | sí |
| capital | −19,43% | −20,17% | no |
| modelo | −19,80% | −20,23% | no |
| uno | −26,51% | −26,51% | no |

**La línea divisoria es exactamente 2008.** Confirma el punto 1 desde otro lado
y sobre otra regla.

Años que pasan de dos cambios con banda de 2,0%: **4 a 5 de 25** en las de
historia larga, peor caso 2022 con cinco. Menos que tus 8 de 24, misma
dirección: el tope mordería en los años agitados.

## 3. La ley: el tope está muerto, y lo que viene es peor

### El proyecto

**Boletín 13.959-13**, ingresado por el Ejecutivo en diciembre de 2020 con
urgencia. **Rechazado en la idea de legislar por la Cámara de Diputados el 28 de
abril de 2021: 49 a favor, 75 en contra, 4 abstenciones.** Rechazada la idea de
legislar, no podía volver a tratarse hasta un año después; el Gobierno podía
insistir por el artículo 68 de la Constitución. **No encontré registro de que
haya insistido ni de tramitación posterior**, y el gobierno que lo patrocinó
dejó el cargo en marzo de 2022. Cinco años y medio sin movimiento.

### Tu pregunta: ¿aplicaba al ahorro voluntario?

**Quedó sin respuesta directa y dejó de importar**, porque el régimen entero
cambia antes de que la pregunta pueda volver a plantearse.

### Lo que sí rige, y es lo que hay que mirar

**Ley 21.735. Desde el 1 de abril de 2027 los multifondos A, B, C, D y E dejan
de existir.** Los reemplazan **diez Fondos Generacionales**: un Fondo Inicial
hasta los 35 años, ocho Fondos Intermedios en tramos de cinco años, y un Fondo
de Consolidación sobre los 75. El límite de activos de crecimiento parte en 95%
y baja con la edad.

| | ahorro obligatorio | ahorro voluntario (Cuenta 2, APV) |
|---|---|---|
| elección de fondo | **ninguna**: asignado por año de nacimiento | **libre**, cualquier Fondo Generacional |
| cambio de fondo | **imposible**, se mueve solo con la edad | **«cuando lo estimen pertinente»** |
| tope de traspasos | — | **ninguno en el Régimen de Inversión publicado** |

**Entonces la respuesta a tu punto 3 es: el tope no aplica a la Cuenta 2, y no
aplica a nada, porque el proyecto murió y el sistema que regulaba se acaba.**

### Pero el reemplazo le pega más fuerte que el tope

**En dieciocho meses desaparece el par Fondo A / Fondo E sobre el que está
construido todo esto.** No es una restricción de frecuencia: es que los dos
instrumentos dejan de existir.

Lo que queda por resolver, y es concreto:

1. **Qué par reemplaza a A y E.** Fondo Inicial contra Fondo de Consolidación es
   lo obvio, pero no son A y E: hay que ver los límites por fondo del Régimen de
   Inversión emitido en septiembre de 2026.
2. **No hay serie histórica de los Fondos Generacionales.** No se puede
   backtestear nada sobre ellos hasta que existan. Lo más cerca es reconstruir
   una réplica sintética desde los límites del régimen, que es lo que ya se hizo
   en `research/afp_administracion/` para otra cosa.
3. **El rezago de ejecución puede cambiar**, y todo este trabajo mostró que el
   resultado se da vuelta entre 6 y 8 días.

**Eso reordena la prioridad.** Nos preocupaba un proyecto de ley rechazado hace
cinco años mientras una ley vigente borra los dos instrumentos en abril de 2027.

## Lo que no hace este estudio

No propone regla nueva, no ajusta ningún parámetro, no agrega características ni
ventanas, y no implementa nada. La banda de 2,0% y la media de 126 vienen fijas
de tu medición y no se re-eligieron.

---

Reproducir: `PYTHONPATH=. python research/afp_tope_y_banda/estudio.py`

Series de las siete AFP desde
[collabmarket/data_afp](https://github.com/collabmarket/data_afp) (valor cuota
de la Superintendencia).

Fuentes de los hechos normativos:
[DF — el proyecto de diciembre de 2020](https://www.df.cl/mercados/pensiones/gobierno-ingresa-proyecto-que-limita-el-cambio-de-fondos-en-las-afp) ·
[El Mostrador — la Cámara lo rechaza, 28-04-2021](https://www.elmostrador.cl/dia/2021/04/28/diputados-rechazan-proyecto-que-limita-los-traspasos-entre-fondos-de-pensiones-gobierno-debera-insistir-en-el-senado/) ·
[Superintendencia de Pensiones — Régimen de Inversión de los Fondos Generacionales](https://www.spensiones.cl/portal/institucional/594/w3-article-17131.html) ·
[DF — elección de fondo del ahorro voluntario](https://www.df.cl/mercados/pensiones/como-funcionara-la-eleccion-de-fondos-de-ahorro-voluntario-con-la-reforma) ·
[T13 — qué no se podrá hacer con los fondos generacionales](https://www.t13.cl/noticia/te-puede-servir/fin-multifondos-b-c-d-e-no-se-puede-hacer-nuevo-sistema-fondos-generacionales-2-9-2026)
