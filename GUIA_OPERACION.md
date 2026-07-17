# Guía de operación

## Lo único que debe hacer el usuario

Copiar las nuevas recomendaciones de Credicorp a un CSV basado en `templates/recomendaciones_credicorp.csv` y subirlo a `data/inbox/`. Puede subir varios archivos; el sistema elimina duplicados y conserva el historial.

Campos obligatorios: `published_at`, `available_at`, `broker`, `ticker` y `recommendation`. Los demás campos deben conservarse aunque queden vacíos. `broker` debe ser Credicorp Capital. Las recomendaciones admitidas son Comprar, Sobreponderar, Outperform, Superior al mercado, Mantener, Neutral, Vender, Subponderar, Underperform e Inferior al mercado.

## Ejecución manual

```bash
PYTHONPATH=. python alphadata.py run
```

## Ejecución programada

`.github/workflows/update-prices.yml` corre de lunes a viernes, descarga datos, calcula, redacta, guarda artefactos y opcionalmente envía el informe por correo. También permite ejecución manual.

## Controles

Una corrida se detiene si hay menos de 20 acciones locales con historia suficiente o si falta el benchmark. Las recomendaciones inválidas quedan en `data/recommendations_errors.csv`; nunca se usan silenciosamente. Cada corrida conserva carteras, movimientos, auditoría, NAV, fecha de corte, versión y estado.

## Correo opcional

Configure los secretos `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` y `REPORT_RECIPIENTS`. Sin ellos, el informe se genera igualmente.
