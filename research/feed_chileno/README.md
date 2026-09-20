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

### 3. Twelve Data — DESCARTADO, XSGO es de pago

El catálogo existe: `api.twelvedata.com/stocks?country=Chile` responde **sin
clave** y lista 1.533 instrumentos en XSGO, con los símbolos `ILC`, `BCI`,
`CHILE` y `SQM.B` —con punto, no con guion— entre ellos.

Probado con una clave del plan gratuito (Basic), la respuesta para cada uno de
esos símbolos, tanto en `/time_series` como en `/eod`, es:

> This symbol is available starting with the Pro or Venture plan.

El control funciona: AAPL en NASDAQ devuelve la serie diaria sin problema, y
los ADR `LTM` y `SQM` en NYSE también. **La limitación es del plan, no del
símbolo ni del formato.** El plan Pro cuesta USD 229 al mes, fuera del
alcance acordado de no pagar por datos.

Queda una utilidad lateral: el plan gratuito sí cubre los instrumentos
estadounidenses del universo, así que sirve como segunda fuente para la
guardia de contraste del lado de Gamma-6 y del oro. No resuelve lo chileno.

Una nota operativa para quien lo retome: el plan gratuito corta a 8 créditos
por minuto. Consultar cuarenta instrumentos exige espaciar las llamadas aunque
se pague.

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

Once archivos. Diez van del 02-01-2025 al 17-09-2026; SALFACORP trae desde 2021.
Comparados contra el cierre **crudo** guardado, en la ventana común
02-01-2025 .. 17-07-2026, 384 días:

| | razón mediana | días exactos | desvío p95 |
|---|---|---|---|
| los once | 1,000000 | 90,1% – 97,7% | 0,00% – 1,14% |

Aprueban 11 de 11. Dos precisiones, porque cambian el criterio de aceptación:

**La coincidencia no es exacta todos los días.** La razón *mediana* es
1,000000, y eso es lo que confirma que se trata del mismo instrumento con la
misma convención de cierre. Pero entre un 2% y un 10% de los días difiere, casi
siempre por menos de 1%. Exigir 1,000000 en cada día dejaría fuera a la propia
referencia.

**La ventana hay que fijarla.** Una serie ajustada por dividendos se separa del
cierre crudo en escalones que se acumulan hacia atrás: mientras más historia,
más se aleja la razón mediana de 1. SALFACORP medido sobre 2021-2026 da
0,957988 y parece no servir; acotado al 01-2025 como los otros diez da
1,000000 con 96,61% de días exactos. Es el mismo archivo. Sin ventana común,
los candidatos quedan ordenados por cuánta historia traen y no por calidad.

Los umbrales por defecto —mediana en 1, 90% de días exactos, percentil 95 del
desvío bajo 1,2%— salen de medir esta referencia, no de teoría. Revisar cuando
haya un candidato real.

## Lo que queda pendiente

- Derivar el cierre ajustado desde el crudo más una tabla de acciones
  corporativas. Hoy el almacén conserva el crudo intacto y deja rastro del
  factor cuando el ajustado cambia, pero sigue tomando el ajustado del
  proveedor en vez de calcularlo.
- Suprimir la fila de NAV por estrategia cuando una de sus posiciones está
  detenida. Hoy la corrida aborta antes, en `fetch_prices`, así que no llega a
  escribirse ninguna fila; falta el caso de una detención que afecte sólo a una
  estrategia.
- La guardia de contraste está escrita y probada, pero no tiene una segunda
  fuente que contrastar hasta que haya proveedor.
