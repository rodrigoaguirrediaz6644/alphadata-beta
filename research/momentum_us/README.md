# Gamma-6 US — backtest exploratorio y seguimiento

Este módulo es el **banco de pruebas** de Gamma-6: aquí se diseñó y aquí se comparan variantes. Desde la metodología 2.2.0, la versión oficial de la estrategia vive en `src/strategy_engine.py::gamma6`, se calcula en la corrida semanal y se publica en el informe. Si se cambia una regla, debe cambiarse en ambos lados o la comparación deja de ser válida.

Nada de lo que está aquí escribe en `data/`, `reports/` ni `strategy_state.json`.

- Metodología: `METODOLOGIA_GAMMA6_US.md` (en esta carpeta).
- Código: `backtest.py` (señal y orquestación); motor común en `research/common/engine.py`.
- Universo: `config/universe_us.csv` (30 acciones US vía Trii CDV).
- Tests sin red: `tests/test_momentum_us.py`.
- Workflow: `.github/workflows/research-momentum-us.yml`. Corre al tocar `research/momentum_us/`, `research/common/` o el universo; el día 1 de cada mes; y a demanda ("Run workflow"). Commitea `results/` automáticamente.

## Qué hay en `results/`

- `RESULTS.md` — tablas: periodo completo, dos mitades, sin NVDA, estrés de costos (0,3%), retorno por año, seguimiento fuera de muestra desde 2026-10-01 (cuando haya datos) y cartera objetivo vigente.
- `summary_metrics.json`, `yearly_returns.csv` — lo mismo en datos.
- `nav_<serie>.csv`, `signals_<serie>.csv` — NAV diario y cartera de cada revisión. Series: `gamma6`, `gamma8_base`, `gamma8_vol`, `ew_rebalanced`, `ew_trend`, `buy_hold`.
- `oos_nav_<serie>.csv` — NAV desde la fecha de lanzamiento del seguimiento (solo tras 2026-10-01).
- `current_target_portfolio.csv` — ranking completo con score, componentes y peso objetivo al último cierre.
- `paper_trading_log.csv` — bitácora: qué cartera objetivo produjo cada corrida (una fila por fecha de revisión).
- `prices_daily.csv` — precios ajustados usados.

## Cómo leerlo

La comparación que importa es **Gamma-6 US vs "Benchmark: EW rebalanceada mensual"**. El buy & hold sin rebalancear se muestra solo como referencia: está dominado por NVDA. El criterio de éxito fuera de muestra está fijado en la metodología (sección 9) y no se cambia mirando los resultados.
