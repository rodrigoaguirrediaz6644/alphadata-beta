# Candidatos de ETF para una cuarta estrategia

Generado automáticamente. Universo: 56 instrumentos; con datos utilizables: 56.
Todo está medido **en pesos**: los precios en dólares se convierten con el tipo de cambio diario, porque la correlación que importa es la que enfrenta un inversionista local.

## Los que más diversifican

Correlación de retornos mensuales contra cada estrategia. Mientras más baja, más aporta al conjunto.

| ETF | Qué es | Categoría | Corr. conjunto | Sigma-6 | Delta-12 | Gamma-6 | Retorno anual | Peor caída | Meses |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FXI | iShares China Large-Cap | pais | +0.03 | -0.01 | -0.04 | +0.09 | 4.7% | -99.4% | 60 |
| MCHI | iShares MSCI China | pais | +0.05 | -0.00 | -0.05 | +0.14 | 6.4% | -99.4% | 60 |
| IAU | iShares Gold Trust | commodity | +0.07 | -0.04 | -0.06 | +0.21 | 16.0% | -99.4% | 60 |
| EWH | iShares MSCI Hong Kong | pais | +0.10 | -0.01 | +0.02 | +0.18 | 8.3% | -99.3% | 60 |
| INDA | iShares MSCI India | pais | +0.11 | -0.13 | -0.16 | +0.42 | 9.3% | -99.4% | 60 |
| HYG | iShares iBoxx High Yield Corporate Bond | bono_corporativo | +0.12 | -0.24 | -0.27 | +0.63 | 8.5% | -99.3% | 60 |
| LQD | iShares iBoxx Investment Grade Corporate Bond | bono_corporativo | +0.14 | -0.22 | -0.26 | +0.62 | 6.5% | -99.3% | 60 |
| TLT | iShares 20+ Year Treasury Bond | bono_soberano | +0.14 | -0.15 | -0.20 | +0.54 | 2.9% | -99.4% | 60 |
| IYE | iShares U.S. Energy | sector_us | +0.16 | -0.07 | +0.02 | +0.32 | 11.3% | -99.3% | 60 |
| IYK | iShares U.S. Consumer Staples | sector_us | +0.19 | -0.09 | -0.07 | +0.48 | 13.3% | -99.3% | 60 |
| CFIETFCD | ETF local — mandato por confirmar | local_por_confirmar | +0.20 | +0.25 | +0.15 | +0.06 | 4.9% | -1.5% | 60 |
| EMB | iShares J.P. Morgan USD Emerging Markets Bond | bono_emergente | +0.22 | -0.15 | -0.20 | +0.67 | 7.6% | -99.3% | 60 |
| CFIETFCC | ETF local — mandato por confirmar | local_por_confirmar | +0.23 | +0.17 | +0.27 | +0.08 | 6.3% | -10.5% | 60 |
| IDU | iShares U.S. Utilities | sector_us | +0.25 | -0.14 | -0.05 | +0.60 | 12.2% | -99.3% | 60 |
| IYZ | iShares U.S. Telecommunications | sector_us | +0.26 | -0.07 | -0.02 | +0.56 | 9.8% | -99.2% | 60 |

## Los redundantes

Replican lo que el conjunto ya tiene; agregarlos sube el riesgo sin diversificar.

| ETF | Qué es | Corr. conjunto | Retorno anual |
| --- | --- | ---: | ---: |

## Resumen por categoría

| Categoría | Instrumentos | Corr. conjunto (mediana) | Retorno anual (mediana) |
| --- | ---: | ---: | ---: |
| bono_corporativo | 2 | +0.13 | 7.5% |
| bono_emergente | 1 | +0.22 | 7.6% |
| bono_soberano | 1 | +0.14 | 2.9% |
| commodity | 1 | +0.07 | 16.0% |
| cripto | 1 | +0.39 | 24.7% |
| estilo | 3 | +0.39 | 16.5% |
| indice_amplio | 2 | +0.44 | 16.9% |
| local_por_confirmar | 8 | +0.35 | 6.9% |
| pais | 17 | +0.37 | 10.6% |
| region | 5 | +0.36 | 11.3% |
| sector_us | 14 | +0.34 | 13.6% |
| tematico | 1 | +0.36 | 11.3% |

## Qué daría una rotación sobre este universo

Referencia, no propuesta: la misma señal de Gamma-6 (momentum compuesto 3/6/12) aplicada a los ETF, para ver qué hay acá.

| Variante | Retorno anual | Volatilidad | Peor caída | Sharpe | Posiciones |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top 5 con filtro de tendencia | 0.0% | 0.0% | 0.0% | — | 0.0 |
| Top 5 sin filtro | 13.0% | 4014.1% | -99.3% | +0.00 | 4.7 |

## Cómo leer esto

- La correlación se mide sobre la ventana común con el seguimiento de las estrategias, que parte en julio de 2021. Son pocos años: sirve para descartar lo obviamente redundante, no para afinar.
- Un ETF con correlación baja **no** es por sí solo una buena estrategia; puede ser simplemente un activo malo que se mueve distinto. Hay que mirar juntas las dos columnas: correlación y retorno.
- `candidatos.csv` trae la tabla completa con los 56, la correlación semanal y las métricas por instrumento.
- Los ETF locales aparecen sólo si Yahoo tiene su símbolo; su mandato está por confirmar y hay que verificarlo antes de usarlos.
