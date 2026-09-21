# Estrategias oficiales de AlphaData

Versión de metodología: **2.3.0**  
Vigencia: **25 de septiembre de 2026**  
Estado: **paper trading; no publicadas como recomendación de inversión**

La configuración operativa oficial es `strategies.v2.json`. Esta versión no modifica retroactivamente la metodología 1.0.0: la antigua Sigma-6 pasa a llamarse **Consenso-6** y queda como estrategia histórica no oficial. Las estrategias oficiales desde esta versión son **Sigma-6**, **Delta-12**, **Gamma-6** (incorporada en la metodología 2.2.0) y **Oro** (incorporada en la metodología 2.3.0).

## 1. Sigma-6

Sigma-6 es la estrategia anteriormente evaluada como Credicorp Momentum. Combina la recomendación fundamental de Credicorp Capital con una confirmación objetiva de momentum.

### Datos y señales

- Única corredora utilizada: **Credicorp Capital**.
- Se conserva sólo la recomendación más reciente conocida para cada acción.
- Comprar, sobreponderar, outperform y superior al mercado equivalen a `+1`.
- Mantener y neutral equivalen a `0`.
- Vender, subponderar, underperform e inferior al mercado equivalen a `-1`.
- Una recomendación caduca después de 365 días.
- Una fila sin acción explícita se descarta.
- Conflictos de una misma acción y fecha se envían a revisión manual.

### Indicador

`Momentum12-1 = PrecioAjustado[t-21] / PrecioAjustado[t-252] - 1`.

Se requieren al menos 252 sesiones de historia y el momentum debe ser estrictamente positivo.

**El precio ajustado debe estar estrictamente sobre la SMA de 200 sesiones**,
la misma condición que usan Delta-12 y Gamma-6. Entró el 21-09-2026: hasta
entonces Sigma-6 era la única estrategia accionaria sin ninguna condición que
mirara el precio de hoy, y `Momentum12-1` salta las últimas 21 ruedas, así que
una caída del último mes le era invisible. Es también condición de permanencia.
Medición en `research/sma200_sigma6/`.

### Entrada

Una acción entra sólo cuando se cumplen simultáneamente:

1. La última recomendación vigente de Credicorp tiene valor `+1`.
2. `Momentum12-1 > 0`.
3. Existen precios ajustados válidos y al menos 252 sesiones de historia.

El cálculo se realiza al cierre de la última sesión bursátil de cada semana. La ejecución simulada ocurre a la apertura de la sesión bursátil siguiente.

### Tamaño

- Ponderación igual entre todas las acciones elegibles.
- Máximo 10% por acción.
- Si hay menos de diez posiciones, el capital que no puede asignarse queda en caja.
- Si hay más de diez posiciones, se distribuye el 100% en partes iguales mientras ningún peso exceda 10%.
- No se permiten ventas cortas ni apalancamiento.
- No existe límite sectorial hasta contar con un mapa sectorial histórico confiable.

### Salida

Se vende en la siguiente apertura cuando ocurre cualquiera de estos eventos:

- La recomendación vigente de Credicorp pasa a `0` o `-1`.
- `Momentum12-1 <= 0`.
- **`PrecioAjustado <= SMA200`.**
- La recomendación caduca.
- Los precios son inválidos o están vencidos.

No se utilizan precio objetivo, stop-loss intraperiodo ni decisiones discrecionales por noticias.

**Sigma-6 no tiene tope de tenencia: rota por señal, no por calendario.** El
tope de 365 días salió el 21-09-2026. La consecuencia de carácter conviene
decirla: la estrategia puede sostener un nombre por años. BCI viene desde el
11-10-2024 y queda corriendo hasta que se caiga alguna condición de precio o
caduque su recomendación. El único reloj que queda es el de la caducidad.

### Costos

Se utiliza la tarifa Trii/Racional:

- Comisión variable antes de IVA: 0,15% del monto transado.
- IVA: 19%.
- Comisión efectiva: **0,1785%** sobre entradas, salidas y rebalanceos.
- Tarifa mínima: $1.990 cuando corresponda a operaciones de monto bajo.

Los backtests independientes del capital aplican 0,1785% al monto transado y no aplican el mínimo de $1.990. Las simulaciones con capital definido deben utilizar el mayor entre la comisión variable y la tarifa mínima cuando corresponda.

### Guardia de vigencia de las recomendaciones

Si en una revisión la recomendación más reciente del proveedor tiene **más de
90 días**, Sigma-6 **no abre posiciones nuevas**. El informe lo dice, y la
estrategia se reanuda sola en cuanto entren recomendaciones nuevas.

> **La regla, en su forma corta: un insumo viejo no puede agregar riesgo, pero
> uno fresco sí puede quitarlo.**

El principio es **no actuar sobre el dato que falta**, y lo que falta son las
recomendaciones: los precios siguen llegando. De ahí sale qué se suspende y qué
no.

| condición | durante la guardia |
|---|---|
| La recomendación baja de nota a `0` o `-1` | **suspendida** |
| La recomendación caduca a los 365 días | **suspendida** |
| Abrir una posición nueva | **suspendido** |
| `Momentum12-1 <= 0` | **sigue viva** |
| `PrecioAjustado <= SMA200` | **sigue viva** |

No se abre nada porque abrir sobre recomendaciones de tres meses es apostar
sobre información que ya no se confirma. Sí se cierra por precio, y hay un
argumento concreto además del principio: **la SMA200 se encendió precisamente
porque Sigma-6 era la única estrategia sin salida que mirara el precio de hoy.**
Suspenderla durante la guardia reabriría ese hueco justo en el periodo en que
nadie está mirando.

Sin la guardia, las posiciones se irían soltando una a una a medida que sus
recomendaciones cumplen 365 días, y esa liquidación sería un artefacto de que
nadie cargó el archivo, no una señal.

**Consecuencia:** durante una guardia larga la cartera sólo puede encoger hacia
caja. Es la dirección conservadora, y la regla de los dos disparos trae la
decisión de vuelta antes de que llegue lejos.

El umbral no está ajustado a la muestra: entre 2021 y 2026 el hueco más largo
entre recomendaciones fue de **29 días**, así que la guardia nunca se habría
activado y no cambia ninguna serie publicada.

### Límite de concentración

Ninguna posición puede pasar del **25% del valor de su propia pieza** —6,25%
del capital total, porque cada pieza es un cuarto—. Se revisa en cada revisión
de la estrategia; al pasarse se recorta hasta 25% exacto y el excedente queda
en la caja de la pieza. Aplica a Sigma-6, Delta-12 y Gamma-6, y **no al oro**,
que es 100% de su pieza por diseño. Entró el 21-09-2026. Es un límite de cola,
no una optimización: ver `POLITICA_REBALANCEO.md`.

## 2. Delta-12

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

## 3. Gamma-6

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

## 4. Oro

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

## 5. Conjunto AlphaData

El informe publica además el resultado de repartir el capital en partes iguales entre las cuatro estrategias oficiales —25% cada una—, reequilibrando al cierre de cada mes. Mientras una estrategia no tenga historial disponible, el conjunto reparte entre las que sí lo tienen en esa fecha.

## 6. Consenso-6 (histórica, no oficial)

Consenso-6 es el nuevo nombre de la antigua Sigma-6 versión 1.0.0. Utilizaba la suma de señales vigentes de Credicorp, BICE, Itaú, BTG Pactual, MBI y LarrainVial Estudios. Desde la versión 2.0.0 queda registrada como **estrategia histórica no oficial**. Su configuración permanece íntegra en `strategies.v1.json` y su historial no debe reescribirse.


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
