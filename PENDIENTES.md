# Pendientes

Este archivo tiene **dos tareas y ninguna discusión abierta**: una recurrente
y una con condición de cierre. Lo
que estaba acá se cerró, y lo que se cerró quedó escrito en su lugar en vez de
apartado para siempre.

La diferencia importa: una tarea recurrente con su periodicidad es parte de la
operación, y un pendiente sin dueño es una discusión que va a empezar de cero
cada vez que alguien la mire.

---

## La tarea recurrente: el contraste trimestral contra investing.com

**Cada trimestre.** Bajar los archivos de referencia de investing.com y
contrastarlos contra el almacén de precios. Los lee `src/referencia_investing.py`
y se dejan en `data/inbox/`.

**Por qué no se puede cerrar, y no es por falta de ganas.** Las guardias del feed
—`ruedas_sin_variacion`, `feed_detenido`, `adr_contra_local`, `ruedas_faltantes`—
miran **variación**. El contraste detecta otra cosa: un precio que se mueve con
normalidad todos los días y **está mal de nivel**. Es el caso de SALFACORP, cuya
serie venía ajustada por dividendos en 2021-2024 y habría inyectado un error de
nivel del 18% sin que ninguna guardia dijera nada.

Y hay una segunda razón: el contraste entre fuentes es hoy **el mejor
instrumento para confirmar dividendos**. Confirmó 101 de 112 y resultó entre
cuatro y diez veces más preciso que el método por precio.

**Por qué trimestral y no mensual.** Su valor no es detectar rápido —un error de
nivel es persistente, no urgente— sino detectar. Trimestral cubre lo mismo a un
tercio del trabajo.

**Condición para cerrarla:** que aparezca una segunda fuente de precios chilenos
que se pueda bajar sola. No hay ninguna hoy: todo lo listado en Chile viaja por
el mismo feed `.SN`, que está congelado desde el 17-07-2026. Ver
`DEPENDENCIAS_MANUALES.md`.

## La tarea de FRED se cerró sola: la fuente ya no está

**FRED no respondía desde los runners de GitHub.** En local devolvía 14.512
observaciones de NASDAQ y VIX; desde Actions fallaba los tres intentos y la
verificación de completitud la rechazaba con 138 días hábiles ausentes.
Costó un informe entero antes de que el paso pasara a `continue-on-error`.

**Se cerró el 23-09-2026 sin resolverla, y esa es la forma correcta de
cerrarla:** Horizonte salió del informe, y FRED era su único consumidor. El
informe del viernes quedó con **una fuente externa menos** — la misma que ya lo
había tumbado una vez.

No hay nada que buscar: la fuente alternativa que faltaba ya no hace falta. Si
alguna vez Horizonte vuelve al informe, la tarea vuelve con ella y está escrita
acá arriba.

---

# Lo que se cerró, y dónde quedó

Nada de esto es un pendiente. Está acá sólo para que nadie lo reabra creyendo
que quedó a medias.

| | dónde quedó |
|---|---|
| **Cuprum, completitud de la descarga** | Ya estaba hecha: `src/horizonte.verificar_completitud` revisa días calendario ausentes, valores nulos y rezago, y **detiene la corrida** si algo falla. Hoy: 8.813 filas de 2002 a 2026, cero problemas. |
| **AESANDES** | Deslistada. El símbolo existe en el proveedor con el nombre «AES Andes S.A.» pero no entrega precios desde el 14-04-2025, y no hay ticker alternativo. Pasó a `estado = deslistado` en `config/tickers.csv`. |
| **MULTIFOODS** | No es una falla: es un símbolo corregido acumulando historia, una rueda por día. La cobertura ahora lo reporta como `ACUMULANDO`. |
| **MALLPLAZA del 03-09-2026** | **Aceptado.** Son $30 corroborados en magnitud y calendario contra la página de relación con inversionistas de Mallplaza, que no publica 2026. Su `origen` en `data/dividendos.csv` lo dice y el panel ya no lo cuenta. |
| **La sección Horizonte** | Reescrita en el mismo lenguaje que el resto: qué se hizo con la plata y cuánto quedó de un millón, en vez de CAGR y volatilidad. |
| **Sigma-6** | Salió de la asignación el 22-09-2026. Código y series se conservan. Se reabriría con una señal de corredora que aporte, medida con el protocolo de `ESTRATEGIAS_ALPHADATA_v2.md`. |
| **La caja en un money market** | Parqueado: los $3.000.000 que motivaban la discusión eran de Sigma-6. Se reabre si la caja sube bastante por encima de lo que deja el redondeo; lo ya decidido sigue valiendo. |
| **El tope de concentración del 25%** | Decidido y no se reabre por resultado: cuesta 1,16 puntos anuales en Gamma-6 y compra 2 puntos de peor caída, y eso se aceptó al ponerlo. Ver `POLITICA_REBALANCEO.md`. |
| **Las nueve fechas ex que se apartan dos o tres ruedas** | Cerrado. El desfase está censurado en cero y la distribución 58/34/8/1 es la forma de un instrumento con resolución de una rueda, no de dos poblaciones. |
| **La razón del CDV** | Confirmada uno a uno en doce nombres, entre 1,0001 y 1,0059. Ver `research/spread_cambio/`. |
| **El premio del CDV** | Medido: +0,047% ± 0,078% en 2026, que no se distingue de cero. No entra al modelo de costo porque un desvío de nivel no es un cargo por lado. Vigilado en el panel de salud con banda de ±1%. |
| **El símbolo del CDV de Exxon** | No se encontró y queda **vacío en vez de adivinado**. No hace falta buscarlo: la puerta de símbolos impide operarlo y Gamma-6 salta al siguiente elegible si XOM entra al top 6. |
| **`reconstruccion_historica.csv` con diff de ruido** | Molestia conocida, no defecto: 1.027 líneas de diff con diferencia relativa máxima 1,3e-15. Se arregla redondeando la salida, y no antes de que alguien lo necesite. |
| **El paso de conversión de pesos a dólares** | En suspenso a propósito, esperando que Rodrigo confirme si es obligatorio u opcional. La primera compra se pagó en pesos con saldo en dólares de $0,00 y el cambio implícito difiere 0,11% del de la pantalla. |

## Y el panel de salud quedó sin nada apartado

`src.salud.CONOCIDOS` está **vacío**. El mecanismo se conserva porque va a
volver a hacer falta, junto con la prueba que exige que todo lo que se aparte
tenga su entrada escrita acá. Pero hoy no hay ninguna alarma suprimida, que es
la única forma de que una alarma signifique algo.
