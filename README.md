# AlphaData — automatización de precios (piloto)

Este módulo descarga precios históricos semanales para una muestra de instrumentos de AlphaData.

## Alcance del piloto

- Fuente: Yahoo Finance mediante `yfinance`.
- Descarga diaria y consolidación interna al cierre semanal de cada viernes.
- Rentabilidad calculada con cierre ajustado por dividendos y eventos corporativos; cierre normal conservado para reportes.
- Mercado local: sufijo `.SN`.
- Benchmark: `^IPSA`.
- Frecuencia automática: cada sábado.
- Salida: `data/prices_weekly.csv` y `data/coverage_report.csv`.
- Backtest: consenso semanal sin anticipación, cartera máxima de dos acciones y costos de rotación.

Los parámetros de estrategia están en `config/strategy.json`. Las salidas del piloto son `data/signals_weekly.csv`, `data/backtest_weekly.csv` y `data/backtest_summary.csv`.

El piloto no genera recomendaciones de inversión ni modifica la cartera oficial. Primero verifica cobertura, moneda, fechas y continuidad de precios.

Las acciones locales son obligatorias. El benchmark es opcional durante el piloto: si Yahoo no entrega su historial, se registra la advertencia sin bloquear los precios de la cartera.

## Ejecución local

```bash
python -m pip install -r requirements.txt
python src/fetch_prices.py
```

## Próxima integración

Cuando la cobertura sea aprobada, el proceso escribirá los precios validados en Google Sheets usando una cuenta de servicio guardada como secreto de GitHub.
