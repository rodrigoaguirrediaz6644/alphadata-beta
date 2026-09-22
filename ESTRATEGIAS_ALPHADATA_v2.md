# Estrategias oficiales de AlphaData

Versión de metodología: **2.3.0**  
Vigencia: **25 de septiembre de 2026**  
Estado: **paper trading; no publicadas como recomendación de inversión**

La configuración operativa oficial es `strategies.v2.json`. Las estrategias
oficiales son **Delta-12**, **Gamma-6** (incorporada en la metodología 2.2.0) y
**Oro** (incorporada en la metodología 2.3.0). **Sigma-6 salió de la asignación
el 22-09-2026**; ver la sección final, que explica qué se midió y por qué.

Esta versión no modifica retroactivamente la metodología 1.0.0: la antigua
Sigma-6 pasa a llamarse **Consenso-6** y queda como estrategia histórica no
oficial.

## 1. Delta-12

Delta-12 es una estrategia mensual independiente de las corredoras que busca tendencias persistentes mediante precio, momentum y liquidez.

### Indicadores y elegibilidad

Una acción es elegible sólo si:

1. `Momentum12-1 = PrecioAjustado[t-21] / PrecioAjustado[t-252] - 1 > 0`.
2. El precio ajustado está estrictamente sobre la SMA de 200 sesiones.
3. Cuenta con al menos 252 sesiones de historia y 200 observaciones para la SMA.
4. **`RSI14 <= 65`.** El RSI de 14 sesiones se calcula sobre el cierre
   ajustado con suavizado exponencial (`alpha = 1/14`) y al menos 14
   observaciones; sin datos suficientes se toma 100, que excluye.
5. No pertenece al 20% menos líquido.
6. La liquidez corresponde a la mediana de `PrecioAjustado × Volumen` durante 60 sesiones, con al menos 30 observaciones.
7. Los datos requeridos son completos y no están vencidos.

> **El RSI es también condición de permanencia, y es la única regla del sistema
> que vende un ganador por serlo.** Una posición que se pone demasiado caliente
> se suelta en la revisión siguiente aunque el momentum siga positivo y el
> precio siga sobre la SMA200. Está en el código desde `274de5c` (27-07-2026) y
> faltaba en este documento.

### Entrada y tamaño

- Evaluación al cierre de la última sesión bursátil del mes.
- Ordenar las acciones elegibles por momentum descendente; ticker ascendente resuelve empates.
- Seleccionar como máximo ocho.
- Ponderar en partes iguales con máximo 15% por acción.
- Mantener en caja el capital no asignable.
- Ejecutar a la apertura de la primera sesión bursátil del mes siguiente.
- No se permiten ventas cortas ni apalancamiento.

### Salida

Se vende en la siguiente revisión mensual si ocurre cualquiera de estos eventos:

- Sale del top 8.
- `Momentum12-1 <= 0`.
- `PrecioAjustado <= SMA200`.
- **`RSI14 > 65`.**
- Cae bajo el percentil 20 de liquidez.
- Presenta datos inválidos o vencidos.

No existen stops intrames ni decisiones por noticias.

### Costos

Delta-12 utiliza el mismo modelo Trii/Racional de Sigma-6: 0,1785% sobre el monto transado y tarifa mínima de $1.990 cuando corresponda. Los backtests sin capital definido no incluyen la tarifa mínima.

## 2. Gamma-6

Gamma-6 es una estrategia mensual sobre acciones de Estados Unidos accesibles en Chile como CDV. No usa recomendaciones de corredoras ni datos fundamentales: selecciona por fuerza relativa de precio dentro del propio universo.

### Universo

Las 30 acciones estadounidenses listadas en `config/tickers.csv` con tipo `accion_us`, todas disponibles como CDV en la plataforma local. Se exige un mínimo de 252 sesiones de historia de precios ajustados válidos.

### Indicadores

Con el cierre ajustado en dólares de la última sesión del mes (`t`):

- `Retorno3m = PrecioAjustado[t] / PrecioAjustado[t-63] - 1`
- `Retorno6-1 = PrecioAjustado[t-21] / PrecioAjustado[t-126] - 1`
- `Retorno12-1 = PrecioAjustado[t-21] / PrecioAjustado[t-252] - 1`
- `SMA200 = promedio(PrecioAjustado[t-199:t])`

Cada retorno se estandariza entre las acciones elegibles (z-score transversal) y el puntaje es `(2·z(Retorno3m) + z(Retorno6-1) + z(Retorno12-1)) / 4`. El horizonte de tres meses pesa el doble.

### Qué pasa con un nombre que no se puede operar

**Salta al siguiente elegible.** La intención de Gamma-6 es tener los seis
mejores **que se puedan comprar**; dejar el cupo en caja cambiaría en silencio
la exposición de la estrategia a algo que nadie midió.

El filtro que decide qué es operable es la **puerta de símbolos**
(`src/cdv.py`): un nombre estadounidense sólo es elegible si su CDV tiene
símbolo verificado. La regla en el código es una sola —sin símbolo, no
elegible— y cubre los dos casos: el que nunca tuvo CDV en el proveedor, como
XOM, y el que la puerta rechace, porque la corrida le borra el símbolo antes de
rankear. En la auditoría queda con `reason = "sin CDV operable"` y su score
intacto, así que se ve que quedó fuera por no poder comprarse y no por rankear
mal.

**El oro no tiene esta salida**, y es a propósito: es una posición única. Si
IAUCL dejara de ser operable, la pieza no tiene siguiente a quien ascender y
eso es una decisión, no una regla automática.

### Entrada

Una acción entra cuando se cumplen simultáneamente:

1. Tiene al menos 252 sesiones de historia válida.
2. Su cierre ajustado supera su SMA200.
3. Queda entre las seis de mayor puntaje.

El cálculo se realiza al cierre de la última sesión bursátil del mes y la ejecución simulada ocurre en la sesión siguiente. No se aplica ningún filtro sobre el índice ni sobre el estado general del mercado.

### Tamaño

- Ponderación igual entre las seis posiciones: 16,67% cada una.
- Si hay menos de seis elegibles, el capital no asignado queda en caja.
- No se permiten ventas cortas ni apalancamiento.

### Salida

Se vende en la sesión siguiente a la revisión mensual cuando la acción deja de estar entre las seis de mayor puntaje, cuando su cierre cae bajo la SMA200 o cuando sus precios son inválidos o están vencidos. No se aplican stop-loss intramensuales ni decisiones discrecionales por noticias.

### Moneda y costos

Los indicadores se calculan sobre el precio en dólares: el tipo de cambio es un factor común y no altera el orden entre acciones. La valorización, el NAV y los resultados publicados están en pesos, convertidos con el tipo de cambio diario `USDCLP`, de modo que incluyen el efecto cambiario que enfrenta un inversionista local. El costo aplicado es 0,1% por lado, el spread que cobra la plataforma en acciones de Estados Unidos, sobre la misma fórmula de rotación que las demás estrategias.

### Origen y validación pendiente

Gamma-6 proviene del estudio comparativo documentado en `research/momentum_us/`, donde se contrastaron veinte reglas alternativas en dos submuestras y excluyendo la acción de mayor crecimiento del periodo. Su resultado previo a la puesta en marcha es una reconstrucción retrospectiva. La validación prospectiva se evalúa contra la cartera igual ponderada del mismo universo.

## 3. Oro

Oro es la única pieza del conjunto que no selecciona nada. Es una posición permanente en el ETF **IAU** (iShares Gold Trust), accesible en Chile como CDV, y su función no es rendir más que las otras: es sostener la cartera cuando las otras caen.

### Universo

Un solo instrumento, IAU, registrado en `config/tickers.csv` con tipo `etf_us`. El tipo importa: Gamma-6 filtra por `accion_us`, de modo que el oro no compite nunca por un lugar en esa cartera. Se exige al menos 60 sesiones de historia válida antes de abrir.

### Regla

No hay indicadores, ranking ni filtro de tendencia. La posición se mantiene al 100% de la pieza, lo que equivale a un 25% del conjunto con las cuatro estrategias vigentes. Se revisa mensualmente junto con las demás, pero la revisión sólo puede cerrarla si los datos dejan de ser confiables: no se vende por precio ni por tendencia.

Esa decisión está medida, no supuesta. Filtrar el oro por su propia tendencia destruye valor: en veinte años el retorno anual cae de 14,8% a 9,5% y la peor caída empeora en vez de mejorar. El oro protege precisamente en los momentos en que un filtro de tendencia ya lo habría vendido.

### Por qué está en la cartera

En el estudio de `research/etf_multiactivo/` el oro fue el único instrumento del universo analizado que terminó positivo en las seis grandes caídas desde 2008 (+52,2%, +23,6%, +18,7%, +12,4%, +4,3% y +1,1% en pesos). Probado como 25% contra el resto de la cartera, el Sharpe sube de 2,28 a 2,60 y la peor caída se reduce a la mitad, de -10,6% a -5,5%. La contrapartida es real y esperada: el conjunto reconstruido rinde algo menos con oro (334,0 contra 348,3 en base 100 desde julio de 2021) a cambio de caer bastante menos.

### Moneda, costos y fecha de apertura

La valorización es en pesos, convertida con el tipo de cambio diario `USDCLP` saneado por `sanear_fx`, de modo que el resultado publicado incluye el efecto cambiario que enfrenta un inversionista local. El costo es 0,1% por lado, pagado esencialmente una sola vez al abrir, porque la rotación esperada es nula. La fecha de apertura registrada es la fecha en que la posición entra en seguimiento oficial, nunca la primera fecha disponible del instrumento: fechar la compra en el nacimiento del ETF inventaría una rentabilidad que nadie obtuvo.

## 4. Conjunto AlphaData

El informe publica además el resultado de repartir el capital entre las tres
estrategias oficiales: **Delta-12 37,5%, Gamma-6 37,5% y Oro 25%**, o
$7.500.000, $7.500.000 y $5.000.000 sobre un capital de referencia de $20
millones. Se reequilibra al cierre de cada mes y dentro del mes los pesos se
dejan correr. Mientras una estrategia no tenga historial disponible, el
conjunto reparte entre las que sí lo tienen en esa fecha.

El reparto vive en `config/runtime.v2.json`, bajo `capital.reparto`, y no está
escrito a mano en ninguna parte del código.

### El criterio para admitir o retirar una pieza

**Una estrategia no tiene que ser buena por sí sola. Tiene que aportar al
conjunto.** Una que rinde 50% con 50% de caída propia es buena pieza si al
conjunto le suma 10 puntos de retorno y sólo 3 de caída máxima.

Y el corolario, que es la razón por la que el oro se queda: **una pieza se
juzga por lo que le hace al retorno del conjunto Y por lo que le hace a la
caída del conjunto.** Rendir menos que las otras no es motivo de salida si su
función es amortiguar. El oro rinde cerca de 7% anual contra 24% de las otras
dos y eso, por sí solo, no dice nada sobre si debe estar.

**Sin el corolario, el test de aporte marginal poda la cartera hasta dejar una
sola pieza**, porque cualquier pieza que rinda menos que el promedio baja el
retorno del conjunto. La pregunta correcta no es «¿rinde menos?» sino «¿qué
queda si la saco?».

**Sigma-6 salió porque no amortiguaba, no porque rindiera menos.** Compartía
dos de sus tres peores caídas con Delta-12 —octubre de 2023 y marzo de 2026—,
o sea que su caída llegaba justo cuando el conjunto ya estaba cayendo. El
control que reparte su cuarto entre las otras ganó las tres ventanas y mantener
la pieza costaba $4.658.161 sobre $20 millones en cinco años. Ver
`research/carteras_en_pesos/` y `research/aporte_marginal/`.

El protocolo se fija **antes de mirar**: aporte marginal al conjunto, en pesos y
en peor caída, en las dos ventanas, contra el control que reparte su parte entre
las piezas que quedan. Eso vale tanto para retirar como para admitir.

## 5. Consenso-6 (histórica, no oficial)

Consenso-6 es el nuevo nombre de la antigua Sigma-6 versión 1.0.0. Utilizaba la suma de señales vigentes de Credicorp, BICE, Itaú, BTG Pactual, MBI y LarrainVial Estudios. Desde la versión 2.0.0 queda registrada como **estrategia histórica no oficial**. Su configuración permanece íntegra en `strategies.v1.json` y su historial no debe reescribirse.


## Sigma-6: qué fue, qué se midió y por qué salió

Sigma-6 combinaba la recomendación vigente de Credicorp Capital con
confirmación de momentum 12-1 y, desde el 21-09-2026, SMA200. **Salió de la
asignación el 22-09-2026.** Su especificación completa queda en
`data/archivo/sigma6_metodologia_v2.3.0.md`, su código en
`src/strategy_engine.py` y sus series en `data/`. Nada de eso se borra: si
alguna vez vuelve una señal de corredora que aporte, la maquinaria está.

**Qué se midió**, en ese orden:

1. **Prueba nula.** Sigma-6 sin el filtro de corredora, con todo lo demás
   idéntico. El orden se da vuelta entre submuestras: **no se distingue**.
2. **Catorce corredoras, con los cortes fijados de antemano.** La correlación
   de rangos entre ventanas es **+0,47**: elegir corredora no se puede
   anticipar. La mejor de la ventana de selección —LarrainVial— cae al quinto
   puesto en la de evaluación. La estimación honesta de esa selección es
   **+19,68% anual**, no el resultado de la ganadora sobre su propia ventana.
3. **Aporte al conjunto**, que es el criterio correcto para una pieza de
   cuatro. Contra un control de caja, mantener la corredora aportaba Sharpe de
   forma consistente (+0,05 y +0,24).
4. **El mismo cálculo en pesos**, sobre $20 millones, que es lo que decide.

**Por qué salió.** Contra el control que reparte su cuarto entre Delta-12 y
Gamma-6 dejando el oro en 25%:

| | los $20M quedan en | anual | peor caída |
|---|---|---|---|
| con Sigma-6, cuatro al 25% | $48.685.107 | +18,67% | −$3.940.468 |
| **sin Sigma-6, 37,5/37,5/25** | **$53.566.005** | **+20,88%** | −$5.784.514 |

**Mantenerla costaba $4.880.898 en cinco años** —2,2 puntos anuales— y lo que
compraba era $1,84 millones menos de caída. **El control ganó las tres ventanas
sin darse vuelta**, que es más de lo que consiguió cualquier otra comparación
de este proyecto.

La divergencia con el Sharpe tiene explicación y conviene dejarla escrita:
Sigma-6 era caja en su mayor parte por construcción —cuatro posiciones con tope
de 10% son 60% en caja— así que bajaba la volatilidad del conjunto y el Sharpe
la premiaba por eso, mientras el resultado en pesos le cobraba esa misma caja
porque no rinde nada.

**Y sale además el único insumo que el sistema no podía obtener solo.** Las
tres piezas que quedan corren únicamente con precios: el sistema queda
automático de punta a punta. La guardia de vigencia de las recomendaciones
sigue existiendo en el código y deja de ser un riesgo operativo, porque que
caduquen ya no apaga nada.

Detalle de cada medición en `research/sigma6_prueba_nula/`,
`research/corredoras/`, `research/aporte_marginal/` y
`research/carteras_en_pesos/`.

## Controles comunes

Cada corrida debe guardar fecha y hora de corte, versión, archivos recibidos, errores, exclusiones, indicadores, señales, cartera anterior, cartera nueva, entradas, salidas, permanencias, pesos, caja, rotación, costos y benchmark. Ningún cálculo puede utilizar información conocida después de la fecha de señal.

La referencia conceptual es el IPSA con dividendos. Desde septiembre de 2026,
la serie operativa `IPSA_TR` utiliza el cierre ajustado de `CFMITNIPSA.SN`
como **proxy invertible de retorno total**. No se presenta como el nivel oficial
del índice: Yahoo dejó congelado `^IPSA` el 17 de julio de 2026 y el IPSA pasó
de S&P a MSCI el 1 de septiembre. El cambio de proveedor no reescribe el NAV
histórico; las variaciones nuevas se encadenan desde el valor acumulado vigente.

## Pendientes antes de comercializar

- Reconstruir el universo histórico sin sesgo de supervivencia.
- Incorporar límites sectoriales con un mapa histórico confiable.
- Incorporar deslizamiento dependiente del volumen.
- Definir de forma verificable cuándo aplica la tarifa mínima de $1.990.
- Completar validación prospectiva de seis a doce meses.
- Realizar revisión legal del lenguaje comercial y las advertencias.
