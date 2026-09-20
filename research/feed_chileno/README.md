# Búsqueda de un feed de precios chilenos

Registro de la Fase 1. Se anota lo descartado con su evidencia, para que nadie
lo vuelva a intentar sin saber qué pasó.

## Qué se rompió

Desde el **17-07-2026** Yahoo dejó de actualizar el historial de los tickers
`.SN`. 34 de 40 acciones chilenas repiten el mismo cierre desde esa fecha.
Cada descarga trae una sola fila viva —la última— que revierte al valor
congelado en la descarga siguiente.

## Candidatos

### 1. Yahoo por el endpoint `chart` — DESCARTADO

Se probó `query2.finance.yahoo.com/v8/finance/chart/<sym>` con `period1` y
`period2` explícitos, sin pasar por `yfinance`. Devuelve exactamente la misma
serie congelada: ILC 21.450, BCI 62.502 y SQM-B 65.450 repetidos desde julio.
**No es `yfinance`, es el proveedor.** Cambiar de cliente no arregla nada.

### 2. Stooq — DESCARTADO por vía de acceso

`stooq.com/q/d/l/` responde con una página de verificación de navegador que
exige resolver una prueba de trabajo en JavaScript. Falla incluso el control
`aapl.us`, así que no se llegó a evaluar la cobertura chilena. Sortear
detección de bots no es una opción, y tampoco funcionaría en un job desatendido.

### 3. Twelve Data — PENDIENTE, bloqueado en la creación de cuenta

El endpoint de referencia `api.twelvedata.com/stocks?country=Chile` responde
**sin clave** y lista 1.533 instrumentos en XSGO, incluidos ILC, BCI y SQM-B.
La cobertura existe. Pero el plan gratuito se anuncia como "Real-time US
equities and ETFs" más forex y cripto, así que XSGO probablemente sea de pago.
Para confirmarlo hace falta una clave, y para eso una cuenta.

### 4. Alpha Vantage — PENDIENTE, bloqueado en la creación de cuenta

La clave `demo` sólo sirve para los ejemplos de su documentación. Sin clave
propia no se puede ni consultar la cobertura chilena.

### 5. Financial Modeling Prep — PENDIENTE, bloqueado en la creación de cuenta

Capa gratuita de 250 llamadas diarias. Chile aparece en su lista de países,
pero no está confirmado que incluya histórico diario de Santiago.

### 6. Bolsa de Santiago — PENDIENTE, bloqueado en credenciales

`www.bolsadesantiago.com/api/...` está detrás de un captcha de Radware.
`startup.bolsadesantiago.com` no resuelve por DNS desde aquí. La credencial hay
que solicitarla.

### Ya descartado antes

Google Finance y `GOOGLEFINANCE` de Sheets no cubren la Bolsa de Santiago.

## La vara de medir

`src/feed_validation.py` compara un candidato contra el cierre guardado en el
tramo común. Se corre así:

    PYTHONPATH=. python -m research.feed_chileno.validar_candidato <carpeta>

### Lo que mide la referencia de investing.com

Once archivos, del 02-01-2025 al 17-09-2026 (SALFACORP trae desde 2021).
Comparados contra el cierre **crudo** guardado, en 384 días comunes:

| | razón mediana | días exactos | desvío p95 |
|---|---|---|---|
| CHILE, BCI, ENELCHILE, ECL, ILC, LTM, PARAUCO, MALLPLAZA, BSANTANDER, SQM-B | 1,000000 | 90,1% – 97,7% | 0,00% – 1,14% |
| SALFACORP | 0,957988 | 38,3% | 18,24% |

Dos precisiones sobre esto, porque cambian el criterio de aceptación:

**La coincidencia no es exacta todos los días.** La razón *mediana* es
1,000000, y eso es lo que confirma que se trata del mismo instrumento con la
misma convención de cierre. Pero entre un 2% y un 10% de los días difiere, casi
siempre por menos de 1%. Exigir 1,000000 en cada día dejaría fuera a la propia
referencia.

**SALFACORP no calza.** Su archivo viene ajustado por dividendos mientras el
guardado es crudo: la razón mediana se va a 0,958. No sirve para rellenar sin
deshacer antes ese ajuste.

Los umbrales por defecto —mediana en 1, 90% de días exactos, percentil 95 del
desvío bajo 1,2%— salen de medir esta referencia, no de teoría. Revisar cuando
haya un candidato real.
