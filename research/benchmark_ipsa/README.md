# El benchmark real: MSCI IPSA Gross

## Por qué se reemplaza el anterior

`IPSA_TR` venía del ETF proxy `CFMITNIPSA.SN`, que tiene dos problemas y ninguno
tiene arreglo: un salto de 100 a 212,56 el 17-07-2026 por el cambio de símbolo,
y desde ese mismo día está congelado, porque es un ticker `.SN` y cayó con el
resto del feed chileno. El informe terminaba suprimiendo la comparación.

La fuente nueva es el índice **MSCI IPSA Gross** (`MMXIPSAGC`), con dividendos
reinvertidos. Se usa la variante Gross y no la Price porque el NAV de las
estrategias se calcula con precios ajustados: comparar un NAV con dividendos
contra un índice sin ellos subestima al mercado todos los años.

## La comparación, con los dos cortes alineados

Ventana 08-07-2021 .. 15-07-2026, que es exactamente la de
`data/historical_model_nav.csv`, todo en base 100 a la primera fecha:

| serie | base 100 | anual | peor caída | vs mercado |
|---|---|---|---|---|
| Delta-12 | 365,7 | 29,5% | -13,9% | +104,3 |
| Sigma-6 | 355,4 | 28,7% | -17,3% | +94,0 |
| **Conjunto AlphaData** | **334,0** | **27,2%** | **-8,9%** | **+72,6** |
| Gamma-6 | 292,3 | 23,8% | -26,4% | +30,9 |
| Oro | 274,6 | 22,3% | -23,5% | +13,2 |
| MSCI IPSA Gross | 261,4 | 21,1% | -15,9% | — |

Reproducible con:

    PYTHONPATH=. python -m research.benchmark_ipsa.comparar <archivo del índice>

## Cuidado con la fecha de anclaje

El índice vale 4.188,16 el 08-07-2021 y 4.247,83 el 09-07: subió 1,42% ese día.
Anclar en el 09 en vez del 08 baja al mercado de 261,4 a 257,7 en base 100, sin
tocar el lado de las estrategias. Son 3,7 puntos regalados a favor de la casa.

La base correcta es el **08-07-2021**, que es la primera fila del NAV
reconstruido, donde todas las series valen 100.

## Qué dice el número

El conjunto rinde 27,2% anual contra 21,1% del mercado: **6,1 puntos al año**.
Es bastante menos de lo que sugería el gráfico con el benchmark roto, pero es
real y, sobre todo, lo consigue con **la mitad de la peor caída**: -8,9% contra
-15,9%. Esa es la parte que vale, y es el oro haciendo lo que se compró que
hiciera.

Las dos estrategias chilenas baten al mercado por más margen que el conjunto,
pero con caídas mayores. Quien mire sólo el retorno va a preguntar por qué no
se concentra todo en Delta-12; la respuesta está en la columna de al lado.

## Advertencia sobre estos números

Son reconstrucción retrospectiva, no ejecución. Se aplican las reglas hacia
atrás sobre el universo actual, así que arrastran sesgo de supervivencia: las
empresas que salieron de bolsa en el periodo no están en el universo. El número
de mercado no tiene ese problema; el de las estrategias sí. La comparación es
la mejor disponible, no una medición limpia.

## Mantención

La Bolsa de Santiago publica "MSCI IPSA S" —la S es la Gross; la N es sin
dividendos— en ventanas de 20 ruedas que no se pueden ampliar. Con una descarga
semanal siempre hay cuatro semanas de solape, así que no se pierde ningún día
aunque se salte una o dos, y el almacén de sólo agregar ignora lo repetido.

Validado contra esa fuente en las 20 ruedas que se superponen: razón mediana
0,99999965 y diferencia máxima 0,0008%, que es el redondeo a dos decimales de
investing.com. Son la misma serie.

**Revisado, y no se puede automatizar.** Al abrir
`bolsadesantiago.com/indices_rv_indices` desde un navegador limpio, el sitio
redirige a una página de captcha de Radware con el mensaje "ANOMALY DETECTED" y
pide resolverlo para dar acceso. Encima corre una segunda capa de detección de
F5. No se llegó a ver la petición de descarga porque no se llega a la página, y
resolver un captcha no es una opción: ni se hace, ni funcionaría en un runner
desatendido, que es precisamente lo que esas defensas están para bloquear.

Queda como **descarga manual semanal**. No bloquea nada: cada archivo trae 20
ruedas, así que hay cuatro semanas de solape y se puede saltar una o dos sin
perder días. El almacén de sólo agregar ignora lo repetido.
