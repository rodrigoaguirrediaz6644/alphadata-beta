# Inventario de acciones elegibles — Perú y Colombia

Estado inicial al 28 de julio de 2026. Este inventario prepara la investigación y los backtests; no activa descargas productivas ni incorpora todavía estrategias al informe.

## Principios

1. La pertenencia a un índice es condición de observación, no elegibilidad automática.
2. Cada valor debe superar cobertura histórica, negociación, liquidez monetaria y calidad del retorno total.
3. Acciones ordinarias y preferenciales del mismo emisor se tratan como una sola exposición económica.
4. No se rellenan precios ni volúmenes faltantes para simular liquidez.
5. Los símbolos de proveedor son candidatos hasta que una prueba automática confirme su cobertura.
6. Una serie internacional o ADR puede aportar una señal, pero no demuestra liquidez ejecutable en BVL.
7. La liquidez se compara únicamente dentro de la misma plaza y moneda de cotización.

## Referencias oficiales

- Perú: MSCI nuam Peru Select Capped 15%, publicado por BVL. La BVL informó 18 compañías representativas en marzo de 2026.
- Colombia: MSCI COLCAP. MSCI reportó 22 valores al 30 de junio de 2026 y publica sus diez mayores posiciones.
- Colombia operable: iShares MSCI COLCAP se utiliza sólo como contraste de composición y posible benchmark, no como acción elegible.

## Estados

- `candidato_liquido`: existe evidencia inicial de cotización líquida local o internacional.
- `candidato`: pasa a prueba automática de datos y liquidez.
- `condicionado`: requiere confirmación de negociación, clase, historia o proveedor.
- `reserva`: sólo entra si supera filtros estrictos.
- `benchmark_operable`: vehículo de comparación, no acción seleccionable.
- `PROXY_SENAL`: serie internacional utilizable para investigación de señal, no para medir liquidez local.
- `PROXY_SIN_DATOS`: proxy declarado cuya descarga no cumple calidad técnica.

## Filtros propuestos para la siguiente etapa

Los umbrales definitivos se fijarán después de medir la distribución real de ambos mercados:

- al menos 3 años de precios diarios ajustados, idealmente 5;
- cobertura mínima de 95% de ruedas en la ventana de señal;
- porcentaje máximo de días sin transacción;
- mediana de valor negociado diario y percentil de liquidez por país;
- precio no obsoleto al rebalanceo;
- historial de dividendos y splits conciliado;
- máximo una clase por emisor económico y límites adicionales por grupo económico;
- trazabilidad de altas y bajas del índice para evitar sesgo de supervivencia.

## Fuentes

- https://www.bvl.com.pe/en/market/msci-nuam-peru-select-capped-15-index
- https://www.bvl.com.pe/bvlupdate/indice-msci-peru-select-dame-luz-030326
- https://www.msci.com/indexes/index/737809/msci-colcap-index
- https://www.bvc.com.co/msci-colcap
- https://www.blackrock.com/co/productos/251708/ishares-fondo-burstil-ishares-colcap-fund

## Limitación conocida

Las listas completas actuales no se exponen de forma uniforme en páginas estáticas. Los registros marcados `candidato_por_verificar` son un universo de investigación, no una afirmación de pertenencia vigente. La siguiente tarea debe descargar o reconstruir la composición oficial por fecha y validar cada símbolo antes de habilitarlo.

## Medición automática

La rama incluye `src/evaluate_regional_universe.py`, que descarga cada símbolo de manera independiente y genera:

- `data/regional_universe_coverage.csv`: métricas y decisión por instrumento;
- `data/regional_universe_summary.csv`: conteo por país y estado medido.

La decisión medida usa inicialmente tres años de historia, 95% de cobertura del calendario observado del país, 95% de precios ajustados válidos, dato no más antiguo que diez días, negociación en 80% de las ruedas y liquidez por encima del percentil 40 del país. Estos umbrales son criterios de investigación y deberán revisarse después de observar la distribución real; no activan estrategias ni tickers productivos.

El flujo manual `Evaluar universo Perú y Colombia` ejecuta las pruebas, mide los símbolos y publica ambos CSV como artefactos durante 30 días. En pull requests sólo ejecuta las pruebas unitarias para que una falla temporal del proveedor no bloquee cambios de código.

## Depuración de símbolos y plazas

La medición distingue ahora tres conceptos que antes estaban mezclados:

- `local_ticker`: nemónico del instrumento en su bolsa;
- `data_symbol_candidate`: símbolo usado por el proveedor de precios;
- `data_role`: indica si la serie mide precio y liquidez local, es sólo un proxy de señal o es un benchmark.

BAP, SCCO, BVN e IFS se mantienen como instrumentos observados de Perú, pero las series descargadas con esos símbolos corresponden a cotizaciones estadounidenses. Quedan clasificadas como `proxy_senal_no_liquidez_local`: no pueden elevar el percentil de liquidez de las acciones BVL ni ser declaradas ejecutables localmente.

La preferencial de Grupo Sura se corrigió de `PFSURA.CL` a `PFGRUPSURA.CL`. El nemónico local se normalizó a `PFGRUPSURA`.

## Pertenencia histórica y sesgo de supervivencia

El inventario actual sigue siendo una fotografía de investigación. Antes de cualquier backtest definitivo debe existir una tabla de membresía por fecha con, al menos, índice, instrumento, fecha efectiva de entrada, fecha efectiva de salida, fuente y fecha de observación. Si una fecha de entrada o salida no está demostrada, se conserva como desconocida y el instrumento no puede asumirse constituyente para todo el pasado.

Los boletines históricos S&P/BVL pueden utilizarse como puente para reconstruir el universo peruano anterior a nuam, pero no equivalen automáticamente al MSCI nuam Peru Select Capped 15%. En Colombia, cada revisión trimestral del MSCI COLCAP debe almacenarse como una observación separada. Esta regla bloquea el uso de la lista actual sobre toda la historia y evita sesgo de supervivencia.

## Pendiente de datos

Yahoo no es una fuente suficiente para conciliar dividendos locales ni membresía histórica. Los eventos corporativos deben contrastarse con las bolsas o emisores antes de calcular retorno total. Hasta entonces, `dividend_events = 0` significa “no observado por el proveedor”, no “la empresa no pagó dividendos”.

## Resultado medido del universo ampliado

La corrida 30397222230 evaluó los 50 registros el 28 de julio de 2026. Resultado bruto: Perú 9 elegibles, 5 condicionados por liquidez, 5 no elegibles y 4 proxies de señal; Colombia 13 elegibles, 10 condicionados, 3 no elegibles y 1 benchmark.

Resultado de los diez candidatos añadidos:

| País | Instrumento | Resultado | Decisión de investigación |
|---|---|---|---|
| Perú | Backus B | Sin datos | Reserva; buscar símbolo o fuente alternativa |
| Perú | Backus inversión | Condicionado por liquidez | Mantener como reserva; elegir una sola clase Backus |
| Perú | Minera Poderosa | Sin datos | No excluir financieramente; buscar fuente alternativa |
| Perú | Orygen | Sin datos | Reconstruir continuidad con Enel Generación Perú |
| Perú | Aenza | Sin datos | Reserva; buscar fuente alternativa |
| Colombia | Éxito | Elegible técnico | Candidato inmediato, sujeto a membresía histórica |
| Colombia | PEI | No elegible | Historia disponible menor a tres años y vehículo no ordinario |
| Colombia | Grupo Bolívar | Condicionado por liquidez | Reserva |
| Colombia | Grupo Aval ordinaria | Condicionado por liquidez | Reserva; preferir una sola exposición del grupo |
| Colombia | Davivienda Group preferencial | No elegible | Historia posterior a reorganización insuficiente; conciliar con PFDAVVNDA |

La elegibilidad técnica no equivale todavía a pertenencia histórica demostrada. Para backtests se aplicará máximo una clase por emisor y límites por grupo económico. En particular, se elegirá una sola clase de Cibest, Grupo Sura, Grupo Argos, Corficolombiana, Grupo Aval y Backus.


## Reconstrucción histórica inicial de Colombia

La página oficial de la BVC publica canastas históricas discriminadas por año. Cuando el archivo oficial no puede descargarse automáticamente, se conserva una observación parcial respaldada por una fuente de mercado que identifica expresamente la canasta BVC; no se completa la lista por inferencia.

Se registraron snapshots parciales para 2022-12-01, 2023-12-01 y 2025-11-26. Todos mantienen vacíos `effective_from` y `effective_to`: prueban presencia en una fecha, no continuidad entre fechas.

Los cambios explícitos se almacenan por separado en `config/index_membership_events.csv`:

- Éxito: entrada efectiva en diciembre de 2023.
- Éxito: nueva entrada informada en noviembre de 2025; esta segunda entrada demuestra que no puede asumirse continuidad desde 2023.
- ETB y Canacol Energy: salida informada en noviembre de 2025.

Los nemónicos históricos `BCOLOMBIA` y `PFBCOLOM` se preservan en los snapshots anteriores a la reorganización de Grupo Cibest. No se sustituyen retroactivamente por `CIBEST` o `PFCIBEST`, porque hacerlo mezclaría identidades de cotización y eventos corporativos.

Fuentes de esta etapa:

- BVC, página de canasta histórica MSCI COLCAP: https://www.bvc.com.co/indices/msci%20colcap
- Rebalanceo de diciembre de 2022 basado en la canasta BVC: https://www.accivalores.com/otros-informes/6824-bvc-publica-canasta-proforma-del-indice-msci-colcap/
- Canasta de diciembre de 2023: https://www.larepublica.co/finanzas/a-pesar-de-la-opa-grupo-exito-ingresa-a-la-canasta-proforma-del-indice-msci-colcap-3754047
- Canasta pro forma de noviembre de 2025: https://www.accivalores.com/wp-content/uploads/Rebalanceo-COLCAP-Nov-2025-13.11.2025.pdf

La reconstrucción completa por trimestre sigue pendiente de recuperar los archivos oficiales faltantes. Hasta entonces, estos snapshots pueden filtrar candidatos por presencia demostrada, pero no habilitan un backtest libre de sesgo por sí solos.


## Evidencia colombiana de 2024

La reconstrucción añade dos puntos verificables sin tratar las fuentes parciales como canastas completas:

- El ingreso de PEI fue anunciado en la canasta pro forma de mayo y entró en vigor el lunes 3 de junio de 2024, con una ponderación publicada de 2,9%. Se registra como evento explícito ADD.
- La canasta pro forma de agosto de 2024 no informó entradas ni salidas. La fuente identifica como mayores ponderaciones a PFBCOLOM, ECOPETROL y BCOLOMBIA, y como menores a CNEC, PFCORFICOL y ETB. Sólo esas seis observaciones se almacenan para el 30 de agosto de 2024.

Fuentes:

- https://www.larepublica.co/finanzas/pei-es-el-nuevo-emisor-en-la-lista-proforma-del-msci-colcap-para-el-rebalanceo-de-mayo-3865619
- https://accivalores.com/media/attachments/2024/08/21/canasta-proforma-rebalanceo-colcap-agosto-2024.pdf

La ausencia de cambios informada en agosto demuestra continuidad de la composición inmediatamente anterior, pero no completa por sí sola los nombres ausentes en la fuente ni autoriza a reconstruir períodos anteriores o posteriores por inferencia.
