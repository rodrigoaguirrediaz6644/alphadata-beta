# Cómo cargar recomendaciones nuevas

Sigma-6 sólo compra lo que sus recomendaciones sostienen, y la única forma de
que entren es dejar un CSV en `data/inbox/`. No hay descarga, ni API, ni
lectura de correo. Ver `CREDICORP_INSUMO.md`.

`src/ingest_recommendations.py` consolida lo que encuentre ahí, lo archiva y no
borra el historial. Corre como paso del workflow.

## Las dos fechas, que es lo que más importa

| columna | qué es |
|---|---|
| `published_at` | el día en que la corredora publicó el informe |
| `available_at` | **el día en que ese informe estuvo disponible para usarlo** |

**La estrategia filtra por `available_at`, no por `published_at`.** Es la
diferencia entre una simulación honesta y una que mira hacia adelante: un
informe publicado el martes que llegó el jueves no se pudo usar el miércoles, y
fecharlo el martes haría que el modelo comprara con información que todavía no
tenía.

**Si `available_at` va vacía, se toma la de publicación.** Es el supuesto
optimista —disponible el mismo día— así que conviene llenarla cuando se sepa
que hubo demora. Una `available_at` anterior a `published_at` se rechaza.

## Las columnas

Las diez tienen que estar presentes, aunque algunas vayan vacías. Si falta
alguna, la corrida se detiene con el nombre de la que falta.

```
published_at,available_at,broker,ticker,recommendation,target_price_min,target_price_max,currency,source_url,notes
```

- `broker`: hoy sólo se reconoce **Credicorp Capital**. Otra corredora, o mal
  escrita, y la fila se rechaza.
- `ticker`: el símbolo AlphaData, igual que en `config/tickers.csv`.
- `recommendation`: el texto de la corredora. Ver el vocabulario más abajo.
- `target_price_min`, `target_price_max`, `currency`, `source_url`, `notes`
  pueden ir vacías; no entran en ninguna decisión.

## El vocabulario que reconoce

No hay que traducir nada: se escribe lo que dice el informe.

| se lee como | textos aceptados |
|---|---|
| **compra** (+1) | `compra`, `comprar`, `outperform`, `sobreponderar`, `superior al mercado` |
| neutral (0) | `mantener`, `neutral`, `igual al mercado`, `market perform` |
| venta (−1) | `vender`, `venta`, `underperform`, `subponderar`, `inferior al mercado` |

No distingue mayúsculas, tildes ni espacios de más. **Sólo el +1 compra**: con
neutral o venta, Sigma-6 no abre y suelta lo que tenga.

Cualquier otro texto se rechaza con «recomendación sin acción reconocida». Si
aparece uno nuevo, se agrega a `SIGNALS` en `src/strategy_engine.py`; no se
reescribe el archivo de entrada para acomodarlo.

## Un ticker fuera del catálogo se descarta

Si el símbolo no está en `config/tickers.csv`, la fila se rechaza con «ticker
fuera del catálogo» y queda en `data/recommendations_errors.csv`. **Se
descarta en silencio salvo por ese archivo**, así que hay que mirarlo.

Es exactamente lo que estuvo perdiendo **veintidós señales de CENCOSHOPP**:
Cencosud Shopping se renombró Cenco Malls y el archivo seguía trayendo el
nombre viejo. Se arregló con un alias, no cambiando el histórico:

```python
ALIAS_TICKERS = {"CENCOSHOPP": "CENCOMALLS"}
```

Cuando una empresa se renombre, el alias es el camino. Las ocho filas que hoy
siguen rechazadas son de **AESANDES**, entre 2021 y 2022, y no están en el
catálogo: quedan fuera a propósito.

## Después de cargar

Una recomendación de compra vale **365 días** desde su `available_at`. Pasado
ese plazo la posición se suelta, salvo que la guardia de vigencia esté activa.

Y la guardia: **si la recomendación más reciente pasa de 90 días, Sigma-6
conserva la cartera, no abre nada y no vende**, y el informe lo dice. Con la
última carga del 22-07-2026, dispara el **21-10-2026**.

El informe lista en cada corrida qué nombres necesitan recomendación nueva y
antes de cuándo.

## Cuándo se vuelve a abrir la decisión sobre Sigma-6

Anotado de antemano para que no se decida por cansancio: **si la guardia de
vigencia dispara dos veces seguidas.** No es un reproche a nadie; es que ese
momento conviene tenerlo definido antes de llegar a él.
