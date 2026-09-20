# AlphaData Automation 2.0

Automatiza las estrategias oficiales Sigma-6, Delta-12 y Gamma-6, y publica además el resultado del conjunto (un tercio en cada una). La única entrada manual es un CSV con nuevas recomendaciones de Credicorp Capital.

## Flujo automático

1. Colocar uno o más CSV en `data/inbox/` usando `templates/recomendaciones_credicorp.csv`.
2. Ejecutar `python alphadata.py run` o iniciar la acción de GitHub.
3. El sistema consolida y archiva las recomendaciones, descarga precios y benchmark, valida cobertura, calcula carteras y costos, actualiza el estado y redacta informes HTML/Markdown.

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python alphadata.py test
PYTHONPATH=. python alphadata.py run
```

Si ya existen precios descargados:

```bash
PYTHONPATH=. python alphadata.py run --offline
```

## Salidas

- `reports/latest_report.html` y `reports/latest_report.md`
- `data/portfolio_sigma6.csv` y `data/portfolio_delta12.csv`
- `data/movements_*.csv` y `data/audit_*.csv`
- `data/strategy_nav.csv` y `data/strategy_state.json`
- `data/recommendations_history.csv`, errores y cobertura

## Fuentes automáticas

Los precios se descargan mediante Yahoo Finance usando el catálogo `config/tickers.csv`. El benchmark `IPSA_TR` usa `CFMITNIPSA.SN`: el cierre ajustado del ETF vinculado al IPSA se emplea como proxy invertible de retorno total desde que Yahoo dejó congelado `^IPSA` tras el cambio de administrador del índice a MSCI. No se presenta como el nivel oficial del índice. Cada corrida conserva la fuente y la cobertura. Si Yahoo entrega un lote parcial, los símbolos ausentes se reintentan individualmente y, si continúan ausentes, se conserva su última serie validada con la marca `CACHE_VALIDADA` en `data/coverage_report.csv`. El benchmark solo se acepta si tiene historia suficiente y no supera tres días hábiles de rezago respecto del mercado local; de lo contrario la corrida se detiene.

## Costos

Ambas estrategias aplican 0,1785% al monto transado, correspondiente a Trii/Racional (0,15% más IVA). La tarifa mínima de $1.990 sólo puede incorporarse cuando se define capital y tamaño de cada orden.

## Incorporar estrategias futuras

1. Crear una función en `src/strategies/` o un módulo equivalente que devuelva `portfolio` y `audit`.
2. Registrar `modulo:funcion` en `config/runtime.v2.json`.
3. Agregar el código a `enabled_strategies`.
4. Añadir pruebas de señales, fechas, pesos, costos y ausencia de información futura.

La metodología 2.0.0 está separada de la configuración de ejecución para que las versiones históricas no se reescriban.
