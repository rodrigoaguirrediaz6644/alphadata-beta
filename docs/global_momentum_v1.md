# Cartera Global Momentum V1

La estrategia selecciona dinámicamente acciones con tendencia y momentum
positivos en hasta treinta mercados. Todas las señales se calculan en moneda
base y exclusivamente con información disponible en la fecha de decisión.

## Reglas iniciales

- Rebalanceo mensual en la última rueda disponible.
- Momentum combinado de 12 y 6 meses.
- Precio sobre media móvil de 200 ruedas.
- Liquidez mínima equivalente a USD 1 millón diarios.
- Ranking común para todos los mercados.
- Ponderación inicial inversa a la volatilidad.
- Máximo 4% por acción, 12% por país y 25% por sector.
- Hasta 30 posiciones; la capacidad no asignada permanece en efectivo.

## Datos obligatorios

El backtest productivo debe aportar precios ajustados, divisas, liquidez,
país, sector y membresía histórica del universo por fecha. No se permite usar
la lista actual de acciones como si hubiese estado disponible en todo el
pasado. Las acciones deslistadas deben permanecer en la historia.

## Estado

Esta versión implementa el motor de selección y control de concentración.
Todavía no declara rentabilidad esperada: antes de promoverla se debe construir
el universo histórico, ejecutar un backtest walk-forward con costos y comparar
contra MSCI ACWI, una cartera global equiponderada y momentum global simple.

## Incorporación por bloques

El universo se incorporará y validará de forma incremental. El Bloque 1,
`GLOBAL_ETF_DEVELOPED_01`, contiene diez ETF-país líquidos cotizados en USD:
Estados Unidos, Canadá, Reino Unido, Alemania, Francia, Suiza, Suecia, Japón,
Australia y Singapur. Su objetivo es validar el backtest económico, los costos,
la ejecución en la rueda siguiente y la comparación con ACWI antes de añadir
universos históricos de acciones.

Este bloque es diagnóstico y no implica que los ETF sustituyan la selección
final de acciones. Los bloques posteriores incorporarán acciones con membresía,
liquidez y deslistados fechados por mercado.
