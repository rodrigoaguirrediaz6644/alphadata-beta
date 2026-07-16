# AlphaData — automatización de precios (piloto)

Este módulo descarga precios históricos semanales para una muestra de instrumentos de AlphaData.

## Alcance del piloto

- Fuente: Yahoo Finance mediante `yfinance`.
- Mercado local: sufijo `.SN`.
- Benchmark: `^IPSA`.
- Frecuencia automática: cada sábado.
- Salida: `data/prices_weekly.csv` y `data/coverage_report.csv`.

El piloto no genera recomendaciones de inversión ni modifica la cartera oficial. Primero verifica cobertura, moneda, fechas y continuidad de precios.

## Ejecución local

```bash
python -m pip install -r requirements.txt
python src/fetch_prices.py
```

## Próxima integración

Cuando la cobertura sea aprobada, el proceso escribirá los precios validados en Google Sheets usando una cuenta de servicio guardada como secreto de GitHub.

