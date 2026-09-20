# Backtest exploratorio — Beta-Insider

Esto es **investigación paralela**, no metodología oficial. No modifica ni depende de `data/`, `reports/`, `strategy_state.json` ni de las estrategias Sigma-6/Delta-12.

- Metodología completa: ver la propuesta "Beta-Insider" compartida por separado (borrador 0.1).
- Código: `fetch_and_backtest.py`.
- Universo: `config/universe_us_insider.csv` (31 acciones de EE.UU., vía Trii CDV).
- Se ejecuta automáticamente en GitHub Actions (`.github/workflows/research-insider-backtest.yml`) al tocar cualquier archivo bajo `research/`, o manualmente desde la pestaña Actions ("Run workflow").
- Resultados: `results/` (se commitean automáticamente al terminar la corrida — no requiere ninguna acción manual para leerlos después).

## Archivos de salida (`results/`)

- `RESULTS.md` — resumen legible con las métricas principales.
- `summary_metrics.json` — retorno acumulado, CAGR, volatilidad, máximo retroceso de Beta-Insider vs. benchmark igual-ponderado buy & hold del mismo universo.
- `nav_beta_insider.csv` / `nav_benchmark_equal_weight.csv` — series de NAV diario (base 100).
- `signals_by_review.csv` — qué tickers entraron en cada revisión mensual.
- `insider_transactions_filtered.csv` — transacciones de insiders (Form 4, código P/S) ya filtradas al universo, para auditar la señal.
- `prices_daily.csv` — precios ajustados usados en el backtest.

## Limitaciones conocidas (ya documentadas en la propuesta de metodología)

- Usa el dataset **trimestral** de la SEC, no el filing individual en tiempo real — hay rezago de publicación.
- Universo de 31 mega-caps; la evidencia académica consultada sugiere que el efecto de insider buying es más débil en ese segmento que en small/mid caps.
- Costo asumido: 0,1% por lado (Trii, acciones EE.UU.), confirmado por el usuario — distinto del 0,1785% que usan Sigma-6/Delta-12 para acciones chilenas.
