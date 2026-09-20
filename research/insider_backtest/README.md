# Backtest exploratorio — Beta-Insider (v0.2)

Esto es **investigación paralela**, no metodología oficial. No modifica ni depende de `data/`, `reports/`, `strategy_state.json` ni de las estrategias Sigma-6/Delta-12.

- Metodología completa: ver la propuesta "Beta-Insider" compartida por separado (borrador 0.1) y el docstring de `fetch_and_backtest.py` para los cambios de la v0.2.
- Código: `fetch_and_backtest.py`.
- Universo: `config/universe_us_insider.csv` (30 acciones de EE.UU., vía Trii CDV).
- Se ejecuta automáticamente en GitHub Actions (`.github/workflows/research-insider-backtest.yml`) al tocar cualquier archivo bajo `research/`, o manualmente desde la pestaña Actions ("Run workflow").
- Resultados: `results/` (se commitean automáticamente al terminar la corrida — no requiere ninguna acción manual para leerlos después).

## Qué compara la v0.2 (todo en la misma corrida, mismo universo, mismos costos)

| Serie | Qué es |
| --- | --- |
| Beta-Insider v0.1 | Señal absoluta original (neto insider USD > 0 en 90 días) + SMA200, ahora sobre datos limpios. Casi siempre en caja en mega-caps. |
| Variante A (relativa) | Ranking del universo por sentimiento insider `(compras − ventas) / (compras + ventas)` en 180 días; siempre invertida en el top-8 que esté sobre SMA200. |
| Control Delta-12 US | Réplica de las reglas técnicas de Delta-12 (momentum 12-1 > 0, precio > SMA200, RSI14 ≤ 65, top-8 por momentum) sobre el universo US, sin usar insiders. Omite el filtro de liquidez (no se descarga volumen). |
| Variante B (veto) | Igual que el control, pero excluye tickers con venta neta de insiders ≤ −100 M USD y cero compras en 180 días. Se lee **contra el control**: la diferencia es el aporte marginal del dato de insiders. |
| Benchmark | Igual-ponderado buy & hold del mismo universo. |

## Limpieza de datos (`clean_transactions`)

En orden: duplicados exactos → códigos inconsistentes (P debe ser A, S debe ser D) → filings de 10% owners (columna `RPTOWNER_RELATIONSHIP` de `REPORTINGOWNER.tsv`, leída de forma defensiva) → sanidad de precio contra el cierre **sin ajustar por splits** (`close_raw`, reconstruido con los splits de Yahoo; ratio en [1/2, 2]) → tope de 5.000 M USD por transacción. Los conteos quedan en `results/cleaning_report.json`.

## Archivos de salida (`results/`)

- `RESULTS.md` — tabla comparativa con retorno, CAGR, volatilidad, máximo retroceso, Sharpe, posiciones promedio y meses en caja por serie.
- `summary_metrics.json` — las mismas métricas en JSON.
- `cleaning_report.json` — cuántas filas descartó cada regla de limpieza.
- `nav_<variante>.csv` — NAV diario (base 100) de `v01_absoluta`, `varA_relativa`, `delta12_us_control`, `varB_veto`, `benchmark`. Se mantienen `nav_beta_insider.csv` y `nav_benchmark_equal_weight.csv` por compatibilidad con la v0.1.
- `signals_<variante>.csv` — qué tickers entraron en cada revisión mensual (`signals_by_review.csv` = v0.1).
- `insider_transactions_filtered.csv` — transacciones crudas (Form 4, P/S) filtradas al universo; `insider_transactions_clean.csv` — tras la limpieza.
- `prices_daily.csv` — precios ajustados (`adjusted_close`) y sin ajustar por splits (`close_raw`).

## Limitaciones conocidas

- Usa el dataset **trimestral** de la SEC, no el filing individual en tiempo real — hay rezago de publicación.
- Universo de 30 mega-caps; la evidencia académica consultada sugiere que el efecto de insider buying es más débil en ese segmento que en small/mid caps. La primera corrida lo confirmó: 857 compras vs 23.744 ventas en 10 años.
- GOOGL/GOOG comparten CIK; la actividad de insiders de Alphabet se copia a ambas clases.
- Costo asumido: 0,1% por lado (Trii, acciones EE.UU.), confirmado por el usuario — distinto del 0,1785% que usan Sigma-6/Delta-12 para acciones chilenas.
