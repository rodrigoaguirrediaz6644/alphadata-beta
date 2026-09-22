# Estrategia de administración A↔E — el intento serio

Diseño congelado en `DISENO_CONGELADO.md`, en un commit anterior a cualquier
resultado.

---

## La respuesta, en orden

**1. La réplica sintética falló, y con ella la mitad del plan.** Error de
seguimiento de **8,0% anual** contra una ventaja buscada de 0,5 a 1,6 puntos.
No puede sustituir al fondo, así que tampoco puede extender la historia — que
era el argumento central.

**2. La arquitectura sí se pudo probar sin ella**, sobre los fondos reales. Y
por el criterio pre-registrado **transfiere en retroceso**: la regla elegida en
2004-2013 bajó la peor caída de 2014-2026 de −19,60% a **−13,99%**, con el
retorno plano (+0,18%, que es ruido).

**3. Pero el diagnóstico por pieza dice que esa transferencia no se ganó.** Cada
mecanismo funciona en exactamente una ventana y **se intercambian**: el lento
fue la estrella de la selección y dio **cero** protección en la evaluación; el
rápido fue lo peor de la selección e hizo **todo** el trabajo en la evaluación.
La regla elegida transfirió porque llevaba al rápido de pasajero.

**4. El colchón cambiario no aporta nada medible.** −0,12% de retorno y 0,00 de
mejora en la caída.

---

## 1. Por qué la réplica no sirve

Pesos ajustados sobre 2002-2013 por mínimos cuadrados no negativos:

| | |
|---|---|
| renta variable extranjera | 47% |
| **renta variable local** | **50%** |
| renta fija | 3% |

**El primer síntoma son los pesos.** El Fondo A tiene del orden de 15% en
acciones chilenas, no 50%. El ajuste carga el componente local porque es lo que
mejor absorbe lo que los otros no explican, y eso ya dice que faltan
componentes.

| | |
|---|---|
| correlación mensual con el Fondo A real | **0,751** |
| varianza sin explicar | **44%** |
| error de seguimiento | 2,32% al mes = **8,0% anual** |
| volatilidad del propio Fondo A | 3,48% al mes |

**Y el número que decide: el desacuerdo de señal.** Con la media de 6 meses, la
señal calculada sobre la réplica difiere de la calculada sobre el fondo real en
**15% de los meses** —12% con 9 meses, 10% con 12—. Uno de cada siete meses la
réplica dice salir cuando el fondo dice quedarse, o al revés.

**No es un problema de los promedios mensuales.** Se probaron tres
construcciones —todo promedio mensual, fin de mes para mundo y dólar con el
Fondo E real como renta fija, y todo fin de mes con ECH como bolsa local— y las
tres caen en el mismo lugar: correlación 0,73-0,84 y error de 1,4-1,9% al mes.
El techo es de la arquitectura de tres componentes, no de la frecuencia.

**Tampoco lo arregla abrir la moneda.** Con el tipo de cambio como cuarto
componente la calibración mejora a 0,859 y **la verificación empeora a 0,681**:
ajusta la ventana de calibración y no transfiere. Y devuelve una exposición
cambiaria implícita de **0%**, o sea una cobertura del 100%, que es imposible
para un fondo con la mayoría de sus activos afuera.

### Lo que se cae con la réplica

De los cuatro beneficios que la justificaban, **tres se caen**: quitar el rezago
de la señal, abrir la caja negra de la moneda, y comprar décadas de historia.

**El cuarto sobrevive y no necesitaba réplica**: el remapeo de 2027 se modela
como 29% del Fondo A real más 71% del Fondo E, sin sintético de por medio.

### Y el desvío del diseño, dicho y no disimulado

El diseño congelado fijaba **selección 1996-2002** sobre la réplica. Esa ventana
no existe. El estudio cae a **selección 2004-2013 / evaluación 2014-2026**, que
es la ventana que el estudio anterior ya miró. **Está contaminada**, y la
validación de verdad sigue siendo hacia adelante.

## 2. Lo que sí transfirió

Criterio pre-registrado: mayor `CAGR / |peor caída|` entre las que no pierdan
más de 1 punto anual contra el Fondo A.

| criterio de selección | elige | evaluación: retorno | evaluación: peor caída |
|---|---|---|---|
| sólo retorno | L6-R4 | +10,15% (**+0,18%**) | −13,99% (**+5,61 pp**) |
| sólo caída | L9-R4 | +9,50% (−0,48%) | −13,99% (+5,61 pp) |
| **combinado (pre-registrado)** | **L6-R4** | **+10,15% (+0,18%)** | **−13,99% (+5,61 pp)** |

Fondo A en la evaluación: **+9,98%** anual, peor caída **−19,60%**.

Diez de dieciocho configuraciones ganan en retorno y doce mejoran la caída.

**Eso confirma tu predicción casi al pie de la letra:** gana en retroceso de
forma clara y queda pareja en retorno. Dos décimas de punto de retorno no son
una ventaja, son ruido.

### En los episodios

| episodio | meses | velocidad | Fondo A | Fondo E | elegida |
|---|---:|---|---:|---:|---:|
| 2007-11 a 2009-02 | 15 | lenta | −41,83% | +13,38% | **−23,40%** |
| 2011-05 a 2011-09 | 4 | media | −13,56% | +4,03% | **+1,22%** |
| 2020-02 a 2020-03 | 1 | **rápida** | −19,60% | **−4,12%** | **−12,66%** |
| 2022-01 a 2023-03 | 14 | lenta | −13,37% | +22,98% | **−0,60%** |

Protege en las cuatro, y en las dos lentas protege casi por completo. **Y el
Fondo E volvió a no ser refugio en la rápida:** perdió 4,12%.

## 3. Y por qué hay que desconfiar de eso

Las piezas solas, en las dos ventanas:

| pieza | selección: anual | selección: caída | evaluación: anual | evaluación: caída |
|---|---:|---:|---:|---:|
| **solo lento 6** | **+12,26%** | **−14,89%** | +10,06% | **−19,60%** |
| solo lento 9 | +11,81% | −15,58% | +8,76% | −19,60% |
| solo lento 12 | +10,48% | −15,58% | +8,32% | −19,60% |
| solo rápido 4 | +7,99% | −39,83% | +10,13% | **−8,79%** |
| **solo rápido 6** | **+7,26%** | **−39,83%** | **+11,67%** | **−8,88%** |
| solo rápido 8 | +7,37% | −42,68% | +10,02% | −22,06% |
| solo colchón | +7,64% | −44,09% | +9,86% | −19,60% |
| **Fondo A** | +8,26% | −41,83% | +9,98% | −19,60% |

**Léelo en diagonal y se ve solo.**

**El mecanismo lento fue lo mejor de la selección** —+12,26% con −14,89% de
caída contra −41,83% del fondo— y en la evaluación su peor caída es
**−19,60%: exactamente la del Fondo A. Protección cero.**

**El mecanismo rápido fue lo peor de la selección** —perdía contra el fondo en
retorno *y* en caída— y en la evaluación hace **+11,67% con −8,88%**, mejor que
el fondo en las dos cosas y mejor que la combinación que el criterio eligió.

**Nadie habría elegido el rápido mirando la ventana de selección.** Entró a la
regla ganadora porque las 18 configuraciones lo llevan bundleado con el lento.
La transferencia no la produjo el criterio: la produjo el empaquetado.

Y hay una explicación, no es sólo azar: la ventana de selección contiene **una
caída lenta grande (2008) y una media (2011)**, y ninguna rápida. La evaluación
contiene la única rápida de los veintidós años. **Cada ventana premió al
mecanismo que le tocaba**, y con dos ventanas y cuatro episodios eso es lo
esperable.

### Otras dos cosas que no aguantan

**El colchón cambiario no aporta.** −0,12% de retorno y ninguna mejora de caída.
Era la predicción con mecanismo económico detrás y no aparece en los números.
Puede ser que el efecto exista y sea demasiado chico para verse con cuatro
episodios; lo que no se puede decir es que aporte.

**La ventaja de retorno se da vuelta dentro del rango de rezago.** Con la señal
aplicada un mes después da +10,15%; con dos meses, **+9,40%, por debajo del
Fondo A**; con tres, +11,27%. Un rango de 1,9 puntos que no es monótono es
ruido, y confirma que el +0,18% no es nada.

## 4. Los dos mundos

| | refugio Fondo E (hoy) | refugio Etapa 10 (2027) |
|---|---:|---:|
| retorno de la elegida | +10,15% | +10,13% |
| ventaja de retorno | +0,18% | +0,15% |
| peor caída de la elegida | −13,99% | −15,59% |
| **mejora de la caída** | **+5,61 pp** | **+4,01 pp** |

**La dilución de 2027 se come casi un tercio de la protección**, que es el único
producto de esto. Y es el mundo que va a estar vigente cuando opere de verdad.

## 5. El veredicto contra la condición de cierre

La condición era: **si no transfiere entre ventanas, no hay estrategia y se
cierra el tema.**

**En retorno: no transfiere, y el tema se cierra.** La mejor de la selección
gana dos décimas en la evaluación, que se dan vuelta con un mes más de rezago.
No hay ventaja de retorno y no la va a haber con más indicadores.

**En retroceso: transfirió, pero no de una forma en la que se pueda confiar.**
La mejora es real y grande —de 5,6 puntos, y protege en los cuatro episodios—
pero viene de un mecanismo que la ventana de selección rechazaba, y el
diagnóstico dice que cada ventana premia al mecanismo que le tocó. **Con cuatro
episodios eso no se puede distinguir de suerte.**

### Entonces

**No hay una tercera vuelta con más indicadores**, como quedó acordado. Lo que
sí hay, si te interesa la protección y no el retorno, es una hipótesis concreta
y barata de registrar: **un cortacircuitos rápido** —fuera cuando la renta
variable global en pesos cae más de 4-6% en un mes, adentro cuando el mes vuelve
a ser positivo— que en la evaluación cortó la peor caída a menos de la mitad y
no cobró retorno.

Registrarlo desde el día uno, sin recalibrar, con la señal del Fondo A al lado.
**Y sabiendo lo que ya está escrito: ese registro no dice nada hasta que haya
una caída.** Si pasan dos años sin una, sigue vacío.

Lo que **no** corresponde es implementarlo como estrategia sobre la base de este
backtest. La ventana que lo respalda es la que el estudio anterior ya miró, y la
otra ventana lo rechaza.

---

Reproducir: `PYTHONPATH=. python research/afp_administracion/estudio.py`
