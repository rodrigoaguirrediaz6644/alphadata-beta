# Resultado diagnóstico — Bloque Global 01

Corrida reproducible: GitHub Actions `30423909540`, ejecutada el 29 de julio
de 2026 con datos ajustados hasta el 27 de julio de 2026.

## Configuración evaluada

- Diez ETF-país de mercados desarrollados.
- ACWI como benchmark independiente.
- Momentum combinado de 12 y 6 meses.
- Tendencia sobre media de 200 ruedas.
- Rebalanceo mensual y ejecución al cierre de la rueda siguiente.
- Máximo de 12% por ETF.
- Ponderación inversa a volatilidad.
- Costo de 0,1785% sobre el monto transado.
- Efectivo sin rentabilidad.

## Resultado

| Métrica | Bloque 01 | ACWI |
|---|---:|---:|
| Rentabilidad acumulada | 71,09% | 399,09% |
| CAGR | 3,30% | 10,20% |
| Drawdown máximo | -42,10% | -33,53% |
| Calmar | 0,078 | 0,304 |

La exposición media fue 64,39% y la primera inversión ocurrió el 1 de febrero
de 2011, después de completar la historia necesaria para las señales.

El drawdown dominante se extendió desde el 26 de enero de 2018 hasta el 23 de
marzo de 2020. El cierre mensual no protegió el desplome rápido de febrero y
marzo de 2020.

## Decisión

El Bloque 01 queda como control diagnóstico y capa de validación del motor. No
se promueve como estrategia ni se optimizan sus parámetros usando todo el
período. Los siguientes bloques deben aumentar la amplitud del universo antes
de evaluar nuevamente la cartera global completa.
