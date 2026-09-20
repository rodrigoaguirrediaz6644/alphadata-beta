# Gamma-6 US — metodología (borrador 0.2)

Estado: **investigación paralela, no oficial**. No forma parte de `strategies.v2.json` ni de las estrategias Sigma-6 / Delta-12. Se evalúa en `research/momentum_us/` con su propio pipeline y no toca `data/`, `reports/` ni `strategy_state.json`.

Fecha del borrador: 20 de septiembre de 2026 (0.2: tras el estudio de mejoras de la sección 12, se adopta la variante concentrada de 6 posiciones con pesos 2/1/1; la Gamma-8 original queda como referencia).

## 1. Origen y hipótesis

Gamma-6 US nace de dos conclusiones del trabajo previo sobre acciones de EE.UU. (informe "Qué funciona y qué no en mega-caps de EE.UU."):

- El dato de transacciones de insiders (Beta-Insider) no aporta en este universo, y las reglas de Delta-12 trasladadas tal cual a acciones US empatan con la cartera igual-ponderada rebalanceada (17% CAGR): su filtro RSI ≤ 65 y el tope del 15% sacan o diluyen a los líderes en los años buenos.
- Lo que sí aporta, de forma consistente en las dos mitades del periodo 2014-2026 y también sin NVDA, es la **selección cross-sectional por momentum de horizonte corto e intermedio**. Cualquier filtro de régimen sobre el índice (SMA200, amplitud) restó 5-6 puntos de CAGR sin reducir el retroceso máximo.

La hipótesis es la del premio de momentum documentado por AQR para large caps (6,8% anual en 1927-2013, significativo): las acciones que lo han hecho mejor en los últimos 3 a 12 meses tienden a seguir haciéndolo mejor que sus pares durante el mes siguiente. Se usa un compuesto de tres horizontes para no depender de uno solo, que es donde el 12-1 clásico falla en este universo (sin NVDA pierde toda su ventaja).

## 2. Universo

Las 30 acciones de EE.UU. disponibles vía Trii como CDV, listadas en `config/universe_us.csv` (misma lista que el universo Beta-Insider, ya depurada: sin `CCL` por ambigüedad y sin `X` por deslistamiento). Los precios son los de la acción original en EE.UU. (Yahoo Finance, cierre ajustado por dividendos y splits); el CDV replica ese precio 1:1.

Una acción es elegible en una revisión si tiene al menos **252 sesiones** de historia de precios válidos.

## 3. Señal

Al cierre de la última sesión bursátil de cada mes (`t`), para cada acción elegible:

- `r3  = P[t] / P[t-63] - 1` — rentabilidad de 3 meses, sin saltar el último mes.
- `r6  = P[t-21] / P[t-126] - 1` — rentabilidad 6-1 (seis meses, saltando el último).
- `r12 = P[t-21] / P[t-252] - 1` — rentabilidad 12-1 (la misma que usa Delta-12).

Cada componente se estandariza entre las acciones elegibles (z-score cross-sectional) y el **score** es el promedio ponderado de los tres z-scores con pesos **2/1/1** (`score = (2·z3 + z6 + z12) / 4`): el horizonte de 3 meses es el que más aporta en este universo (sección 12). El horizonte de 3 meses no salta el último mes porque en este universo la reversión de corto plazo no aparece (la regla "8 peores del mes" rinde 13% con Sharpe 0,59).

No se usa RSI, ni volumen, ni ningún filtro sobre el índice.

## 4. Entrada y selección

En cada revisión mensual son elegibles las acciones con historia suficiente **y precio de cierre por encima de su propia SMA200** (filtro de tendencia por acción; no hay filtro sobre el índice). Se compran las **6 elegibles con mayor score**. Se sale de cualquier acción que deje de estar entre esas 6. No hay condición de score mínimo: mientras haya al menos 6 elegibles la estrategia está 100% invertida (la EW rebalanceada, su vara de comparación, también lo está); si hay menos de 6, el resto queda en caja.

La ejecución simulada ocurre en la sesión siguiente a la revisión, con el cierre ajustado de esa sesión.

## 5. Tamaño

Igual ponderación: **16,7% por acción**, 6 posiciones, 100% invertido. Sin ventas cortas ni apalancamiento. Sin límite sectorial (el universo es de 30 nombres y el tope de Delta-12 demostró costar retorno sin reducir riesgo aquí).

## 6. Costos

**0,1% por lado** (spread de Trii para acciones de EE.UU., confirmado), aplicado sobre el turnover efectivo con la misma fórmula que Delta-12: `costo = 0,5 × (Σ|Δpeso| + |Δcaja|) × 0,1%`. El pipeline reporta además el resultado a 0,3% por lado como estrés; la estrategia cambia ~2 posiciones por mes, así que triplicar el costo resta menos de 1 punto de CAGR.

## 7. Variantes que el pipeline reporta junto a la principal

- **Gamma-8 base (referencia):** la versión original menos concentrada: 8 posiciones, pesos 1/1/1, mismo filtro de tendencia. Rinde 22,9% con Sharpe 1,13; sin NVDA es idéntica en Sharpe a Gamma-6 (0,97). Se mantiene para medir cuánto de la ventaja de Gamma-6 viene de la concentración.
- **Gamma-8 ajustada por volatilidad:** score dividido por la volatilidad de 6 meses (idea de Clenow). Algo menos de retorno, mismo retroceso.
- **Benchmark justo:** las 30 igual ponderadas, rebalanceadas cada mes.
- **Candidata simple:** igual ponderada solo entre las acciones sobre su SMA200, 100% invertida. Un solo parámetro, Sharpe algo mejor que la EW.
- **Referencia:** buy & hold sin rebalancear. Se muestra porque era el "benchmark" anterior, pero está dominada por NVDA (75% de la cartera al final) y no es una vara justa para una estrategia mensual.

## 8. Resultados de diseño (2014-06 a 2026-09, dentro de muestra)

| Serie | CAGR | Vol | MDD | Sharpe |
|---|---:|---:|---:|---:|
| **Gamma-6 US** | **27,7%** | **21,8%** | **-31%** | **1,27** |
| Gamma-8 base (referencia) | 22,9% | 20,3% | -32% | 1,13 |
| EW rebalanceada mensual | 17,1% | 17,6% | -34% | 0,97 |

Robustez de Gamma-6: primera mitad 28,0% vs 16,6% (EW); segunda mitad 28,3% vs 17,6%; sin NVDA 19,6% vs 15,4% (Sharpe 0,97 vs 0,89). Su retorno extra sobre Gamma-8 (5 puntos) proviene de concentrarse más en los líderes: sin NVDA ambas tienen el mismo Sharpe. Se eligió a sabiendas, como estrategia de mayor retorno dentro de un conjunto de varias (acciones chilenas, ETF, fondos, commodities/índices), no como la de menor riesgo. Estos números son **dentro de muestra**: la regla se eligió mirando este periodo entre unas veinte alternativas, así que el margen real esperado es menor.

## 9. Criterio de éxito fuera de muestra (fijado de antemano)

El pipeline registra desde el **1 de octubre de 2026** el NAV de Gamma-6 US, de la Gamma-8 base y de la EW rebalanceada con las mismas reglas, sin recalibrar nada, y la cartera objetivo de cada revisión en `results/paper_trading_log.csv`. Se considerará candidata a estrategia oficial solo si, tras **12 meses**, Gamma-6 US supera a la EW rebalanceada en Sharpe y su retroceso máximo no es peor en más de 5 puntos. Si no lo consigue, se descarta sin ajustar parámetros para "arreglarla".

## 10. Riesgos y limitaciones

- **Sobreajuste:** ~20 reglas probadas en un solo periodo de 12 años. La robustez en dos mitades y sin NVDA reduce, no elimina, la sospecha. De ahí el criterio de la sección 9.
- **Concentración del periodo:** 2014-2026 en mega-caps US estuvo dominado por un puñado de nombres; un periodo de liderazgo rotativo o de mercado lateral puede castigar al momentum (los "momentum crashes" de 2009 no están en la muestra).
- **Sin protección de cola:** ninguna variante evita retrocesos del 30-34% (2020, 2022). El timing del índice no funcionó en este periodo, pero eso no garantiza que no haga falta en otro.
- **Concentración:** 6 posiciones de 16,7% cada una; una sola acción que caiga 30% en un mes le cuesta 5 puntos a la cartera. Es el precio explícito del retorno extra frente a Gamma-8.
- **Universo pequeño:** 6 posiciones sobre 30 nombres es el 20% del universo; la selección es menos exigente que en un índice amplio y el resultado depende de que Trii mantenga esos 30 CDV.
- **Costos y liquidez del CDV:** se asume que el CDV replica el precio US 1:1 y que el spread de 0,1% se mantiene; no se modela el tipo de cambio ni diferencias de horario.
- **Rezago de precios:** la señal usa el cierre US del último día hábil del mes; la ejecución en el CDV al día siguiente puede diferir del cierre ajustado de Yahoo.

## 11. Pipeline

- Código: `research/momentum_us/backtest.py` (señal y orquestación) y `research/common/engine.py` (motor de backtest reutilizable).
- Tests: `tests/test_momentum_us.py` (funciones puras, sin red).
- Workflow: `.github/workflows/research-momentum-us.yml` — corre al cambiar el código o el universo, el día 1 de cada mes (seguimiento fuera de muestra) y a demanda. Commitea `research/momentum_us/results/` para poder leer los resultados sin recalcular.
- Salidas: `RESULTS.md` (tablas completas, mitades, sin NVDA, estrés de costos, retorno anual, seguimiento fuera de muestra, cartera objetivo vigente), `summary_metrics.json`, `yearly_returns.csv`, `nav_<serie>.csv`, `signals_<serie>.csv`, `current_target_portfolio.csv`, `paper_trading_log.csv`, `prices_daily.csv`.

## 12. Estudio de mejoras (20 de septiembre de 2026)

Se probaron 27 variantes técnicas y macro sobre la base de entonces (Gamma-8 + tendencia), cada una en cuatro cortes: periodo completo, 2014-2019, 2020-2026 y sin NVDA. Solo cuenta como mejora lo que gana en Sharpe en los cuatro cortes.

| Familia | Qué se probó | Resultado |
|---|---|---|
| Concentración | 5, 6, 10, 12 posiciones | 5-6 posiciones sube el CAGR a 27% y el Sharpe a 1,16-1,23 con NVDA; sin NVDA no mejora (0,86-0,89 vs 0,97). Es apuesta a que persista un líder dominante. |
| Ponderación | inversa a la volatilidad; proporcional al score | Score-ponderada da 38% CAGR pero sin NVDA cae a Sharpe 0,79: es solo concentración en NVDA. Descartada. Inversa a la vol: sin efecto. |
| Horizontes | solo 3/6, solo 6/12, pesos 2/1/1, + máximo 52 s, + reversión 1 mes | 2/1/1 y solo 3/6 mejoran marginalmente (Sharpe 1,18-1,19 vs 1,13) y no pierden sin NVDA. 6/12 es peor: el horizonte corto es el que aporta en este universo. |
| Rotación | revisión semanal y quincenal; histéresis (salir solo al caer del top 12) | Todas peores; sin NVDA claramente peores (Sharpe 0,71). La revisión mensual es la correcta. |
| Stops | trailing stop intramensual 10/15/20% | Peores en retorno y Sharpe; solo el 10% reduce el retroceso (-24%) a costa de 7 puntos de CAGR. |
| Control de volatilidad | exposición = 15% o 20% / vol realizada del índice EW | Reduce el retroceso máximo a -25/-27% con Sharpe igual (1,11). Cambia el perfil de riesgo, no la eficiencia. |
| Macro: VIX | VIX > 30 (o > 25) → 50% de exposición; VIX > 30 → caja | 50% con VIX > 30 baja el retroceso a -26% con Sharpe igual; salir a caja es peor (Sharpe 0,98). Coherente con la evidencia: el VIX alto es señal de rebote, no de salida. |
| Macro: Nasdaq | Nasdaq > SMA200 si no caja / 50% | Peor en todos los cortes. Igual que con el índice EW: el timing de mercado resta aquí. |

Conclusiones: (1) la base está cerca de su configuración eficiente; nada la supera de forma robusta en los cuatro cortes; (2) el retorno se puede subir concentrando, aceptando que la ventaja depende de que haya líderes persistentes — es la opción adoptada en la 0.2 (Gamma-6 US); (3) el retroceso se puede bajar unos 6-8 puntos con control de volatilidad o media exposición con VIX > 30, sin perder Sharpe, si en algún momento se prefiere ese perfil; (4) no había datos de tasas, curva o inflación en el entorno para probar filtros macro fundamentales; la literatura (Springer 2013, AQR) indica que el momentum rinde más en contracciones y actúa como cobertura, lo que no justifica filtros macro de salida.
