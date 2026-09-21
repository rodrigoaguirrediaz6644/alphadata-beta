# De dónde salen las recomendaciones de Credicorp

La pregunta llevaba tres rondas: **¿Credicorp publica menos, o se está
capturando menos de lo que publica?** Se contesta sin salir del repositorio, y
la respuesta es una tercera que no estaba en el menú.

## No hay ninguna ruta de captura, y nunca la hubo

`src/ingest_recommendations.py` consolida los CSV que aparezcan en
`data/inbox/`. Eso es todo. **No hay descarga, ni API, ni lectura de correo, ni
scraping.** El único mecanismo es que alguien deje un archivo ahí.

Hoy `data/inbox/` está vacío.

## Las 1.108 filas entraron de una vez

| | |
|---|---|
| `source_url` con contenido | **0 de 1.108** |
| `notes` = «Histórico validado, página N» | **1.107 de 1.108**, del 08-07-2021 al 09-07-2026 |
| `notes` = «captura aportada por Rodrigo» | **1**, del 22-07-2026 |

Y el historial del archivo lo confirma:

| commit | fecha | filas |
|---|---|---|
| `06553d6` | 16-07-2026 | 0 |
| `6c16f61` | 17-07-2026 | **1.108** |
| `7137cc4` | 27-07-2026 | 1.109 |

**Todo el insumo de Sigma-6 se cargó el 17-07-2026 en una sola operación**: la
transcripción página por página de un documento histórico que cubre cinco años.
Diez días después se agregó una fila a mano. Desde entonces, nada.

## Lo que eso cambia

La caída del flujo que medimos —de 17-19 filas mensuales en 2025 a 4-8 en
2026— **no es una ruta de captura que se rompió.** Es cómo termina el documento
que se transcribió: dentro de la misma carga, 2022 trae 290 filas y 2026 sólo
69 en siete meses.

Así que la pregunta original estaba mal planteada por nuestra parte. No hay que
averiguar si Credicorp publica menos ni reparar una captura: **no existe nada
que reparar.** Lo que hay que decidir es si alguien va a seguir dejando los
archivos en `data/inbox/`, y con qué frecuencia.

## Lo que sigue de acá

Sigma-6 se queda sin nombres por aritmética: las recomendaciones vigentes
caducan a los 365 días y la última disponible es del **22-07-2026**. Sin
cargas nuevas, VAPORES cae el 24-11-2026, CENCOMALLS el 22-04-2027, BCI y
PARAUCO el 01-07-2027 y LTM el 09-07-2027. **En julio de 2027 la pieza queda
en 100% de caja.**

Eso no es un defecto del sistema ni del mercado: es el insumo, que depende de
una acción manual que no ha vuelto a ocurrir en dos meses.

La decisión que sigue —arreglar el insumo, suspender la pieza y repartir su
cuarto entre las otras tres, o aceptar la caja— ya no depende de ninguna
medición pendiente. Depende de si esa carga manual va a existir.

## Lo que se hizo con esto

Sigma-6 se queda. No hay nada que reparar ni fuente que buscar; lo que faltaba
era volver sostenible esa decisión, y son tres cosas:

1. **La guardia de vigencia.** Si la recomendación más reciente pasa de 90
   días, Sigma-6 conserva la cartera, no abre nada y no vende, y el informe lo
   dice. Un mes saltado deja de ser silencioso. Con la última carga del
   22-07-2026, dispara el **21-10-2026**.
2. **El informe avisa por nombre.** Dice qué necesita recomendación nueva y
   antes de cuándo, así que el compromiso lo sostiene el sistema y no la
   memoria de nadie.
3. **El procedimiento está escrito**, en `GUIA_INBOX_RECOMENDACIONES.md`,
   empezando por lo único que de verdad se puede hacer mal: qué significa cada
   una de las dos fechas.

Y queda definido de antemano cuándo se vuelve a abrir la pregunta: **si la
guardia dispara dos veces seguidas.**
