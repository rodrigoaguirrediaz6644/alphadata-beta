# AlphaData Automation 2.0

Automatiza las estrategias oficiales Sigma-6, Delta-12, Gamma-6 y Oro, y publica además el resultado del conjunto (un cuarto en cada una). La única entrada manual es un CSV con nuevas recomendaciones de Credicorp Capital.

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

Las tres piezas aplican **0,15% de comisión más 19% de IVA = 0,1785%**, con
mínimo de **$999,99** por operación, y la misma tarifa para acción chilena y
para CDV. Los tres parámetros están medidos sobre órdenes reales de Trii, no
supuestos; la orden ejecutada 11157665580442 los confirma al peso. Viven en
`config/runtime.v2.json` y en ninguna otra parte: ver `UN_VALOR_UNA_CASA.md`.

*(Este archivo decía «0,15% más IVA» desde el principio, mientras el código
llevaba la constante pelada y un mínimo de $1.990 que era un supuesto. La
descomposición correcta estaba escrita y nadie la estaba leyendo: es el mismo
defecto de la norma, con la copia buena en la documentación y la mala en el
código.)*

## Incorporar estrategias futuras

**El criterio primero no es técnico:** una estrategia no tiene que ser buena por
sí sola, tiene que **aportar al conjunto**, y se juzga por lo que le hace al
retorno del conjunto *y* por lo que le hace a su peor caída. Rendir menos que
las otras no es motivo de salida si su función es amortiguar. Ver
`ESTRATEGIAS_ALPHADATA_v2.md`, sección 4.

1. Crear una función en `src/strategies/` o un módulo equivalente que devuelva `portfolio` y `audit`.
2. Registrar `modulo:funcion` en `config/runtime.v2.json`.
3. Agregar el código a `enabled_strategies`.
4. Añadir pruebas de señales, fechas, pesos, costos y ausencia de información futura.

La metodología 2.0.0 está separada de la configuración de ejecución para que las versiones históricas no se reescriban.
