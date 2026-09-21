# Dividendos: qué se puede derivar y qué no

## La decisión

Registro manual, ni ignorar los dividendos ni deducirlos del salto de precio.
Ignorarlos sesga el NAV entre 4% y 8% al año en bancos y utilities chilenas,
siempre hacia abajo. Deducirlos del salto no distingue un reparto de una mala
impresión ni de una noticia. El salto sí sirve como **alarma**: si un
instrumento cae fuerte y no hay dividendo registrado para esa fecha, se marca y
se reporta, sin ajustar nada.

## El atajo para la tabla histórica no funciona como se esperaba

La idea era comparar la serie ajustada por dividendos de investing.com contra
el cierre crudo guardado, localizar dónde cambia el factor, y llenar la tabla
histórica con eso. Medido, **diez de los once archivos de referencia no están
ajustados**: entre 90% y 98% de sus días coinciden exactamente con el cierre
crudo.

| archivo | días en razón 1,0 | razón mínima | carácter |
|---|---|---|---|
| CHILE, BCI, ENELCHILE, ECL, ILC, LTM, PARAUCO, MALLPLAZA, BSANTANDER, SQM-B | 90,1% – 97,7% | 0,926 – 0,979 | crudo |
| SALFACORP | 38,3% | 0,818 | **ajustado** |

Sólo SALFACORP trae la serie ajustada, y es el único archivo con historia desde
2021. En él los escalones sí son dividendos, y se verifican: el 06-05-2024 el
factor pasa de 0,9580 a 1,0000 y la serie cruda cae de 557,00 a 531,79, un
-4,5% que el factor predice.

En los otros diez, los apartamientos de la razón respecto de 1 **no son
dividendos**.

## Lo que sí destapó la comparación

Los diez archivos crudos discrepan de nuestra serie guardada en ventanas de
cinco a siete ruedas, y después vuelven a coincidir. Ejemplo verificado a mano,
Banco de Chile en marzo de 2025:

| fecha | investing.com | nuestro guardado | razón |
|---|---|---|---|
| 14-03-2025 | 129,10 | 129,10 | 1,0000 |
| 17-03-2025 | 121,15 | 130,79 | 0,9263 |
| 21-03-2025 | 123,80 | 133,65 | 0,9263 |
| 24-03-2025 | 125,60 | 125,60 | 1,0000 |

La fuente limpia muestra la caída ex-dividendo el 17-03; nuestra serie no la
muestra, se queda un 8% arriba cinco ruedas y después cae de golpe. **El dato
malo es el nuestro.** Nuestro guardado marca +1,3% el 17-03 cuando el movimiento
real fue -6,2%, y -6,0% el 24-03 cuando el real fue +1,5%.

Aparecen 26 ventanas de este tipo en once instrumentos entre 2025 y 2026. Todo
retorno calculado con un extremo dentro de una de esas ventanas está mal. Es un
problema de datos distinto del congelamiento y del dato fantasma, y anterior a
los dos.

## Qué quedó implementado

`src/dividendos.py` hace dos cosas:

- **`proponer`**: busca escalones en la razón entre una serie ajustada y el
  cierre crudo, y clasifica cada uno. Un escalón sólo se propone como
  `dividendo` si es permanente **y** la serie cruda cae en la fecha ex en la
  magnitud que el factor predice. Si el nivel revierte a los pocos días es
  `bache_transitorio`; si no hay caída que lo respalde es `sin_respaldo`.
  Ninguna propuesta entra sola a la tabla.
- **`alarma_por_salto`**: caídas mayores al umbral sin dividendo registrado
  para esa fecha. No ajusta nada; impide que la tabla manual se quede atrás sin
  que nadie se entere, que es el riesgo real de anotar a mano.

## La prueba nula: el verificador no verificaba

El confirmador busca, en una ventana de hasta nueve ruedas alrededor de la
fecha declarada, el día cuya caída coincide con el monto. Sobre una serie
ruidosa eso encuentra algo casi siempre. Medido: 1.480 fechas **sin dividendo**,
con los montos reales de cada papel y la misma ventana.

| tamaño del dividendo, en tolerancias | n | "confirmados" sin existir |
|---|---|---|
| menor a 0,5 | 529 | **100,0%** |
| 0,5 a 1 | 393 | **99,7%** |
| 1 a 2 | 375 | 74,7% |
| 2 a 4 | 180 | 6,1% |
| mayor a 4 | 3 | 0,0% |

**81,9% de falsos positivos en total**, y de los 134 dividendos de la tabla, 92
caían en las bandas donde el método confirma cualquier cosa.

### Los dos regímenes

- **Confirmada por el precio**: tamaño mayor a 2 tolerancias. Siete
  dividendos, y son justamente los que producían los artefactos visibles.
- **Fecha por convención**: los demás, fechados 5 ruedas antes de la declarada.
  Ese 5 sale de medir el desfase donde sí es verificable —mediana 5, cuartiles
  4 y 5— y mejora sobre el proveedor, que tiene la misma mediana pero disperso
  entre −2 y +9.

No aplicar los pequeños no era opción: suman una mediana de 3,60% por
instrumento en dos años, con máximo de 7,74%.

La columna `origen` de la tabla dice cuál es cuál. Siete verificadas y 127
asumidas es una descripción honesta; "134 confirmadas" no lo era.

## Cuánto importó tener mal esa columna

Se volvieron a correr las selecciones con el ajustado del proveedor y con el
derivado, en la ventana 06-2025 a 09-2026, que es donde la tabla cubre la
ventana completa del momentum 12-1:

| | revisiones | con cartera distinta |
|---|---|---|
| Delta-12 (mensual) | 16 | **7 — 44%** |
| Sigma-6 (semanal) | 68 | **14 — 21%** |

Delta-12 cambia uno o dos nombres en siete de dieciséis revisiones: entra CHILE
y sale ENELCHILE, entra COLBUN y sale AGUAS-A, entran BSANTANDER y LTM y salen
CHILE y ECL. **El defecto no era inocuo.**

### Pero eso no prueba que la columna nueva sea la correcta

Sólo cuatro instrumentos de cuarenta tienen algún dividendo verificado contra
el precio: BSANTANDER, CHILE, QUINENCO y VAPORES. La mayoría de los cambios de
cartera involucra papeles cuyas fechas son **asumidas por convención**:
ENELCHILE, COLBUN, AGUAS-A, ANDINA-B, LTM, ECL, SQM-B, COPEC.

O sea, el 44% mide cuánto depende la cartera de esta columna, no cuánto
mejoró. Lo que sí se sabe: la columna anterior estaba demostrablemente mal en
los siete casos verificables, y la nueva está bien en esos siete. Para el
resto, la nueva está mejor razonada y sigue sin estar verificada.

Lo que cerraría esto es una fuente de dividendos con fecha ex publicada —la
empresa o la bolsa— contra la cual confirmar las 127. Es el camino manual que
el diseño ya contempla.

## Lo que falta

La tabla en sí. La derivación entrega candidatos, no una tabla: de los 58
escalones encontrados en los once archivos, 8 pasan la verificación cruzada, 26
son baches transitorios y 24 quedan sin respaldo. Y los 8 aceptados aparecen
sistemáticamente cinco a siete ruedas después de un bache del mismo
instrumento, lo que hace dudar de la fecha aunque la magnitud cuadre.

Llenar la tabla necesita una fuente de dividendos publicados —la empresa o la
bolsa— contra la cual confirmar fecha y monto. Hasta entonces, el ajustado se
graba igual al crudo y la alarma avisa cuando algo cae sin explicación.

## Nota para el relleno de la ventana 17-07 .. 16-09

En ese tramo los once archivos están en razón 1,0, así que son crudos y sirven
para rellenar sin introducir un desnivel. La advertencia vale para SALFACORP
fuera de ese tramo: antes del 06-05-2024 su archivo está ajustado y usarlo
como crudo inyectaría un error de nivel de hasta 18%.
