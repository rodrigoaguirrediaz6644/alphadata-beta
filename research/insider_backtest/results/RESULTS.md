# Resultado del backtest exploratorio Beta-Insider (v0.2)

Generado automáticamente. Periodo: 2016-06-01 a 2026-09-18. Universo: 30 acciones US. Costo: 0.1% por lado.

| Serie | Retorno acumulado | CAGR | Volatilidad anual | Máximo retroceso | Sharpe (CAGR/vol) | Posiciones promedio | Meses en caja |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Beta-Insider v0.1 (neto > 0, SMA200; datos limpios) | 32.0% | 2.7% | 4.3% | -9.8% | 0.63 | 0.70 | 65/123 |
| Variante A: ranking relativo insider + SMA200 (siempre invertida) | 343.8% | 15.6% | 18.4% | -34.6% | 0.85 | 7.92 | 0/123 |
| Control: réplica Delta-12 sobre universo US (sin veto) | 407.6% | 17.1% | 20.1% | -31.8% | 0.85 | 7.65 | 1/123 |
| Variante B: réplica Delta-12 + veto por venta masiva de insiders | 385.8% | 16.6% | 19.0% | -29.7% | 0.87 | 7.46 | 1/123 |
| Benchmark igual-ponderado (buy & hold) | 1008.2% | 26.3% | 23.7% | -32.5% | 1.11 | — | — |

## Limpieza de transacciones

Entrada: 24601 filas. Descartadas por: duplicados 176, códigos inconsistentes 7, 10% owners 0, precio fuera de rango 46, valor > 5,000,000,000 USD 2. Salida: 24370 filas (`insider_transactions_clean.csv`).

## Cómo leer la comparación

- La v0.1 y la Variante A usan solo información de insiders + SMA200. La Variante A siempre está invertida, así que su exposición es comparable al benchmark.
- La Variante B solo se puede juzgar contra su control (réplica Delta-12 sin veto): la diferencia entre ambas es el efecto marginal del dato de insiders.
- Ventanas: v0.1 90 días; A/B 180 días. Veto B: venta neta <= -100,000,000 USD sin compras.
- La réplica Delta-12 omite el filtro de liquidez (no se descarga volumen; irrelevante en mega-caps).

Ver `signals_<variante>.csv` para qué tickers entraron en cada revisión mensual.

**Nota:** dataset trimestral de la SEC (rezago de publicación) y universo fijo de mega-caps; ver limitaciones en la propuesta de metodología.