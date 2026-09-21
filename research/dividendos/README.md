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
