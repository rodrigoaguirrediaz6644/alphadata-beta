# Candidatos ETF — análisis de correlación

Investigación paralela, **no** metodología oficial. Sólo lee `data/market_prices_daily.csv` (tipo de cambio) y `data/historical_model_nav.csv` (series de las estrategias); escribe únicamente en `results/`.

Responde una pregunta concreta: de los 56 ETF disponibles en Trii, **cuáles sirven para una cuarta estrategia que no repita lo que ya hacen Sigma-6, Delta-12 y Gamma-6**.

- Universo: `config/universe_etf.csv`. Los 48 ETF de EE.UU. se piden a Yahoo por su símbolo original (el CDV local replica ese precio; la terminación `CL` es sólo nomenclatura de Trii). Los 8 ETF locales se piden con sufijo `.SN` y su mandato está por confirmar.
- Código: `analisis.py`. Tests sin red: `tests/test_etf_multiactivo.py`.
- Workflow: `.github/workflows/research-etf.yml` (a demanda y al tocar estos archivos).

Todo se mide **en pesos**: los precios en dólares se convierten con el tipo de cambio diario, porque la correlación que importa es la que enfrenta un inversionista local.

## Salidas (`results/`)

- `RESULTS.md` — los que más diversifican, los redundantes, resumen por categoría y, como referencia, qué daría una rotación de momentum sobre este universo.
- `candidatos.csv` — los 56 con correlación contra cada estrategia, retorno, peor caída e historia disponible.
- `correlacion_mensual.csv` / `correlacion_semanal.csv`, `precios_clp.csv`, `prices_daily.csv`, `nav_rotacion_*.csv`, `signals_rotacion_*.csv`, `summary.json`.

## Advertencia

La correlación se mide sobre la ventana común con el seguimiento de las estrategias, que parte en julio de 2021: son pocos años. Sirve para descartar lo obviamente redundante, no para afinar. Y correlación baja no equivale a buen activo: hay que leerla junto al retorno.
