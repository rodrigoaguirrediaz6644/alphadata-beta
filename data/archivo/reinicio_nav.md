# Reinicio del seguimiento en vivo — 21-09-2026

## Qué se archivó

| archivo | filas | desde | hasta |
|---|---|---|---|
| `strategy_nav_incidente_2026.csv` | 16 | 16-07-2026 | 18-09-2026 |
| `strategy_state_incidente_2026.json` | — | — | 2026-09-18 |

Últimos valores que llegó a publicar esa serie:
- Sigma-6: 111.21
- Delta-12: 130.21
- Gamma-6: 99.90
- Oro: 99.90
- IPSA TR: 212.56

Ninguno es real. El NAV nació el 16-07-2026, un día después de que el feed
chileno se congelara, y nunca tuvo una jornada de valorización con precios
vivos.

## Desde cuándo corre la serie nueva

**17-09-2026**, con las cuatro piezas en 100 en esa misma fecha.

## Qué se limpió del estado

sigma_entries, delta_entries, gamma_entries, oro_entries, sigma_portfolio, delta_portfolio, gamma_portfolio, oro_portfolio, delta_last_period, gamma_last_period, entry_dates_version, valuation_date, nav, ingestion, last_run_utc.

Ninguna cartera, fecha de entrada ni NAV del periodo contaminado sobrevive: las
carteras de esas semanas tampoco son las que las reglas habrían elegido con
datos reales, así que heredarlas sería arrastrar el mismo problema.

## La separación

`historical_model_nav.csv` pasa a llamarse `reconstruccion_historica.csv`. No
se archiva porque sigue siendo válida como backtest; lo que cambia es que su
nombre diga lo que es. El gráfico deja de encadenarla con el seguimiento en
vivo: son dos series distintas en dos archivos distintos y se dibujan por
separado.
