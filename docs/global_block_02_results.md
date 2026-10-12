# Resultado diagnóstico — Bloque Global 02

Ejecución reproducible hasta el 28 de julio de 2026. Las cifras incluyen
costos de 0,1785% por monto transado, ejecución al cierre de la rueda siguiente
y deriva natural de los pesos entre rebalanceos.

| Universo | CAGR | Retorno acumulado | Drawdown máximo | Calmar | Exposición media |
|---|---:|---:|---:|---:|---:|
| 10 ETF desarrollados | 3,41% | 74,16% | -42,10% | 0,081 | 64,41% |
| 10 ETF emergentes | 2,29% | 45,53% | -25,00% | 0,092 | 47,36% |
| 20 ETF combinados | 2,52% | 51,12% | -28,66% | 0,088 | 70,93% |
| ACWI | 10,19% | 398,86% | -33,53% | 0,304 | 100,00% |

## Conclusión

El Bloque 02 mejora el control de drawdown respecto del bloque desarrollado,
pero no genera una rentabilidad competitiva. La combinación aumenta la
exposición y reduce el drawdown frente al Bloque 01, aunque su CAGR sigue
quedando muy por debajo de ACWI.

No corresponde añadir más ETF-país manteniendo esta misma configuración. Los
Bloques 01 y 02 quedan como controles diagnósticos. El siguiente experimento
debe aislar si la debilidad está en el ranking transversal, en el filtro de
tendencia o en la asignación inversa a volatilidad, usando validación temporal
y sin escoger parámetros por el resultado total.

## Diagnóstico de componentes

Corrida reproducible `30442040180`, con datos hasta el 28 de julio de 2026.
Cada variante cambia un solo componente sobre el universo combinado de 20 ETF.

| Variante | CAGR | Retorno acumulado | Drawdown máximo | Calmar | Exposición media |
|---|---:|---:|---:|---:|---:|
| Original | 2,51% | 50,78% | -28,66% | 0,088 | 70,93% |
| Igual ponderación | 2,46% | 49,64% | -31,08% | 0,079 | 70,93% |
| Sólo momentum | 3,22% | 69,14% | -37,93% | 0,085 | 73,54% |
| Sólo tendencia | 3,89% | 88,03% | -27,58% | 0,141 | 83,12% |
| Siempre invertida e igual peso | 6,96% | 204,61% | -42,66% | 0,163 | 98,03% |
| ACWI | 10,20% | 399,09% | -33,53% | 0,304 | 100,00% |

La ponderación inversa a volatilidad no explica el rezago: igual ponderación
reduce levemente la rentabilidad y empeora el drawdown. El efectivo explica
parte de la diferencia, pero la cartera siempre invertida todavía queda muy
por debajo de ACWI y asume un drawdown mayor.

El filtro de tendencia aislado domina a los demás controles filtrados, pero
tampoco genera una estrategia competitiva. En 2011-2015 todas las variantes
perdieron dinero mientras ACWI obtuvo 5,43% anualizado; la debilidad, por tanto,
no surge solamente de un episodio reciente.

## Decisión posterior al diagnóstico

No se promoverá ninguna variante de ETF-país ni se ajustarán más parámetros
sobre el período completo. Estos ETF quedan como benchmark operativo y control
de infraestructura. La siguiente incorporación será un bloque pequeño de
acciones estadounidenses con universo histórico fechado, liquidez observada y
selección transversal efectiva, de modo que `max_positions` sea menor que el
número de candidatas.
