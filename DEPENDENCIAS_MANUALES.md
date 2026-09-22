# Las dependencias manuales

Qué se rompe si nadie las hace, en cuánto tiempo, y si existe una alternativa
automática. Medido, no estimado.

De las tres que había, **quedan una y media**:

| | estado |
|---|---|
| **MSCI IPSA semanal** | **cerrada.** Publica la canasta igual peso, que sale de precios que el sistema ya baja |
| **Contraste mensual** | **no se cierra**, y la razón es de clase: cubre un defecto que las guardias no pueden ver. Baja a trimestral |
| **Recomendaciones de Credicorp** | **sin consecuencia.** Sigma-6 salió de la asignación; la carga sólo importa si vuelve |

Lo que queda vivo es el contraste, trimestral. La sección 3 se conserva entera
porque la decisión sobre Sigma-6 se puede revisar y entonces la dependencia
vuelve con ella.

---

## 1. El índice semanal: **cerrada**

Producción publica la canasta desde el 22-09-2026. El informe ya no espera
ningún archivo de la Bolsa de Santiago.

**Qué se rompía.** El benchmark del informe. Cada archivo trae cuatro semanas de
solape, así que saltarse una o dos no pierde nada; a partir de la quinta semana
la serie se queda atrás y la línea de comparación deja de avanzar.

**Por qué no hay un reemplazo directo.** Todo instrumento listado en Chile
viaja por el mismo feed `.SN` que sigue congelado. `CFMITNIPSA.SN`, el proxy
que se usaba antes, tiene fecha hasta el 17-09-2026 pero **el 98% de sus
últimas 45 ruedas repite el mismo valor**: está muerto, con fecha fresca. Es
exactamente el defecto que este proyecto vino a terminar y no se puede volver a
él. `^IPSA` está deslistado en el proveedor.

Así que un reemplazo automático tiene que estar **fuera** del feed chileno.

### Lo medido

Contra el MSCI IPSA Gross, 2021-2026:

| candidato | correlación diaria | anualizado | vs MSCI |
|---|---|---|---|
| MSCI IPSA Gross (manual) | — | +18,83% | — |
| **canasta igual peso de las 41 chilenas que el sistema ya baja** | **0,878** | **+16,35%** | −2,5 pp |
| ECH (iShares MSCI Chile) × USDCLP | 0,625 | +14,49% | −4,3 pp |
| FLCH (Franklin FTSE Chile) × USDCLP | 0,193 | +0,02% | serie inservible |

**La canasta gana y no agrega ninguna dependencia**: se construye con los
precios que el sistema ya captura todos los días y que sus guardias ya validan.
No tiene tipo de cambio de ida y vuelta, ni desfase de husos horarios, ni costo
de administración. Y **ya existe a medias**: `benchmark_return` la usa como
respaldo cuando falta el IPSA.

**Su costo es de composición, no de calidad.** La canasta pondera igual y el
MSCI pondera por capitalización, así que son índices distintos. La diferencia
no es sistemática: por año va +21,1 contra +22,1, luego **+19,2 contra +17,8**
y **+10,9 contra +8,3** —dos años por encima—, +54,2 contra +56,2 y +5,8 contra
+8,6.

ECH sí tiene un sesgo sistemático: queda por debajo en cuatro de cinco años y
**4,3 puntos anuales acumulados, en la dirección que halaga a las estrategias.**
Su correlación mensual es alta (0,946) pero la diaria es 0,625, porque cotiza en
Nueva York y el índice se calcula al cierre de Santiago. Descartado por eso.

**Hecho.** La canasta es el benchmark publicado, con su nombre: «Mercado chileno
(canasta igual peso)», no «IPSA». Se ganó autonomía completa; se perdió la
comparación contra el índice exacto, que no es lo mismo que perder la
comparación contra el mercado.

**Y hay que decir para qué lado se movió la vara.** Sobre la reconstrucción
completa el benchmark baja de 261,39 a 235,97 en base 100, o sea unos 2 puntos
anuales **en la dirección que halaga a las estrategias**. Es la misma objeción
que descartó a ECH, y la diferencia es que acá está medida y no es sistemática:
en dos de los cinco años la canasta va por encima del MSCI. Aun así, cualquier
lectura de «le ganamos al mercado» cuenta ahora con una vara 2 puntos más baja,
y eso pesa más que el signo del promedio.

**El benchmark en vivo se recalcula entero en cada corrida, no se encadena.**
Encadenarlo habría empalmado dos índices distintos en la misma columna —MSCI
hasta el 21-09-2026, canasta desde el 22— y un empalme así no se ve roto, se ve
como una serie. Es la forma exacta del defecto de Sigma-6.

---

## 2. El contraste mensual: **no se puede cerrar**

La pregunta era si las guardias ya cubren lo que cubría el archivo. **No lo
cubren, y la diferencia es de clase, no de grado.**

Las guardias detectan **datos que dejan de moverse**:

| guardia | qué ve |
|---|---|
| `ruedas_sin_variacion` | una serie individual congelada |
| `feed_detenido` | el mercado entero quieto en una rueda |
| `adr_contra_local` | el mercado local detenido, con el ADR como testigo |
| `ruedas_faltantes` | una rueda perdida |

Las cuatro miran **variación**. El contraste detecta otra cosa: **un precio que
se mueve con normalidad y está mal de nivel.** Es el caso de SALFACORP, cuya
serie venía ajustada por dividendos en 2021-2024 y habría inyectado un error de
nivel del 18% sin que ninguna guardia dijera nada, porque variaba todos los
días como corresponde.

Y hay una segunda razón, que apareció esta semana: **el contraste entre fuentes
es hoy el mejor instrumento para confirmar dividendos.** Confirmó 101 de 112 y
resultó entre cuatro y diez veces más preciso que el método por precio. Sin el
archivo de la segunda fuente, ese instrumento desaparece.

**Recomendación:** no se cierra. Pero se puede **bajar la frecuencia sin perder
casi nada**: su valor no es detectar rápido —un error de nivel no es urgente,
es persistente— sino detectar. Trimestral cubre lo mismo que mensual a un tercio
del trabajo.

---

## 3. Credicorp: **decidida**, y sin consecuencia mientras siga así

**La decisión se tomó: opción E.** Sigma-6 salió de la asignación el 21-09-2026
y el capital quedó en Delta-12 37,5%, Gamma-6 37,5%, Oro 25%. La estrategia
sigue en el repositorio, con su especificación y su serie reconstruida; lo que
no tiene es plata.

Con eso **la carga manual de Credicorp dejó de tener consecuencia**: si nadie la
hace, no se apaga nada que esté invertido. Vuelve a importar sólo si Sigma-6
vuelve a la asignación.

Lo que sigue es el expediente completo que llevó a esa decisión, que se conserva
porque la condición de reapertura está fijada y el expediente es lo que habría
que volver a leer.

### El planteamiento original

Es **el único insumo del sistema que no se puede obtener solo**. Las otras tres
estrategias son automáticas de punta a punta: Delta-12 y Gamma-6 salen de
precios, el oro no tiene señal.

**Qué se rompe y cuándo.** No hay ruta de captura y nunca la hubo: las 1.108
filas entraron de una vez el 17-07-2026 y una más el 27-07. Ver
`CREDICORP_INSUMO.md`. Sin cargas nuevas:

- **21-10-2026**: la guardia de vigencia dispara. Sigma-6 conserva la cartera y
  deja de abrir.
- **24-11-2026** en adelante: las recomendaciones caducan una a una.
- **Julio de 2027**: la pieza queda en 100% de caja.

### Medido: la prueba nula no distingue

Sigma-6 sin el filtro de corredora, con todo lo demás idéntico:

| tramo | con Credicorp | sin corredora |
|---|---|---|
| 1ª mitad | **+6,84%** | +5,71% |
| 2ª mitad | +28,26% | **+36,41%** |

**El orden se da vuelta**, así que no se distingue. Ver
`research/sigma6_prueba_nula/`.

Lo que sí se puede afirmar: **no hay evidencia de que la recomendación de
corredora agregue retorno por encima del momentum solo**, y la carga de
justificar la única dependencia manual del sistema estaba de su lado.

Y sin el filtro, el solape de Sigma-6 con Delta-12 casi se duplica —de 0,25 a
0,42 de mediana— sin llegar a ser la misma cartera.

### Medido: elegir corredora no es fiable, y no elegir funciona

Con las 33 corredoras y los cortes fijados de antemano, **la correlación de
rangos entre ventanas es +0,47**: hay algo de persistencia, muy lejos de ser
fiable. La mejor de la selección —LarrainVial— cae al 5º puesto en la
evaluación; Credicorp sube del 4º al 1º.

**Consenso-6, que no elige a nadie, queda 2ª en las dos ventanas** y es la
única estable, con cinco veces menos rotación. Ver `research/corredoras/`.

Eso abre una quinta opción que antes no estaba sobre la mesa.

### Y el criterio que de verdad decide: aporte al conjunto

Sigma-6 es una de cuatro piezas, así que lo que importa no es su resultado
individual sino lo que le suma al conjunto. Medido contra el conjunto de tres
piezas en tercios (`research/aporte_marginal/`):

| Sharpe del conjunto | selección | evaluación |
|---|---|---|
| tres piezas, sin cuarta | 1,05 | 1,75 |
| + Sigma-6 actual | **1,09** | 1,98 |
| + Consenso-6 | 1,05 | 1,95 |
| + sin corredora | 0,94 | **2,07** |

**El orden entre mantenerla y quitarla se da vuelta: no se distingue.** Y
ninguna cuarta pieza chilena mejora el retorno del conjunto en la ventana de
selección; lo que aportan es Sharpe, bajando la caída.

**El control de caja vuelve plano** —agregar 25% de caja aporta −0,01 de Sharpe
en las dos ventanas— así que esos aportes son selección y no dilución. Y contra
ese control, **mantener la corredora es positivo en las dos ventanas (+0,05 y
+0,24) y quitarla no (−0,10 y +0,33)**. Es lo único consistente que aparece a
favor de mantenerla.

Dos hechos más, que pesan sobre la opción de mantenerla: **Sigma-6 comparte dos
de sus tres peores caídas con Delta-12** —octubre de 2023 y marzo de 2026— y la
variante sin corredora no comparte ninguna. El argumento a favor de mantener la
corredora ya no puede apoyarse en el aporte al conjunto.

### Y en pesos, sobre $20 millones, el signo se invierte

El Sharpe premia a Sigma-6 por bajar la volatilidad del conjunto, y lo hace
porque **es caja en su mayor parte por construcción**: cuatro posiciones con
tope de 10% son 40% invertido y 60% en caja. El resultado en pesos le cobra esa
misma caja, porque no rinde nada.

Contra el control que saca Sigma-6 y reparte su cuarto entre Delta-12 y
Gamma-6, dejando el oro en 25%:

| | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| con Sigma-6 (25% c/u) | $48.323.631 | +18,50% | −$3.915.943 |
| **sin Sigma-6 (37,5/37,5/25)** | **$52.981.792** | **+20,62%** | −$5.765.292 |

**Mantenerla cuesta $4.658.161 en cinco años**, 2,1 puntos anuales, y lo que
compra es $1,85 millones menos de caída. El control gana en las tres ventanas,
sin darse vuelta. Ver `research/carteras_en_pesos/`.

### Las opciones, sin implementar ni medir

**A. Mantener la carga manual.** Es lo que hay. Cuesta una acción periódica y
deja al sistema con un punto de dependencia humana permanente. La guardia ya
hace que un olvido sea ruidoso en vez de silencioso.

**B. Automatizar la captura.** Requiere una fuente que publique las
recomendaciones de Credicorp de forma consultable. No se ha encontrado, y la
restricción se mantiene: **nada que entre con las credenciales de Rodrigo a la
corredora.**

**C. Reemplazar la señal de corredora por una regla de precio.** Sigma-6 dejaría
de ser «Credicorp más momentum» y pasaría a ser una estrategia de precio sobre
el universo chileno. Deja de depender de nadie. Lo que se pierde es la premisa
de la estrategia: el aporte fundamental de un analista que mira balances y no
sólo cotizaciones. **Sería una estrategia nueva con el nombre viejo**, y eso hay
que decirlo así.

**D. Volver a Consenso-6.** No elige corredora, así que no hereda el problema
de selección, y quedó 2ª en las dos ventanas con cinco veces menos rotación.
**No resuelve la dependencia manual** —sigue necesitando que alguien cargue las
recomendaciones, y ahora de seis fuentes en vez de una— pero sí resuelve la
fragilidad de haber elegido una sola mirando el resultado.

**E. Suspender la pieza y repartir su cuarto entre las otras tres.** El sistema
queda en tres piezas y completamente automático. Es la opción más limpia de
operar y la que más cambia lo que el producto es.

**La decisión no depende de ninguna medición pendiente.** Depende de si esa
carga manual va a existir, y de cuánto vale la premisa fundamental de Sigma-6
frente a la autonomía. Queda para Rodrigo.

**Condición de reapertura ya fijada:** si la guardia de vigencia dispara dos
veces seguidas. Ver `PENDIENTES.md`.
