# Estrategias oficiales de AlphaData

Versión de metodología: **2.0.0**  
Vigencia: **16 de julio de 2026**  
Estado: **paper trading; no publicadas como recomendación de inversión**

La configuración operativa oficial es `strategies.v2.json`. Esta versión no modifica retroactivamente la metodología 1.0.0: la antigua Sigma-6 pasa a llamarse **Consenso-6** y queda como estrategia histórica no oficial. Las estrategias oficiales desde esta versión son **Sigma-6** y **Delta-12**.

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
- La recomendación caduca.
- La posición alcanza 365 días.
- Los precios son inválidos o están vencidos.

No se utilizan precio objetivo, stop-loss intraperiodo ni decisiones discrecionales por noticias. Después de una salida por 365 días se permite una nueva entrada en la revisión semanal siguiente si todas las condiciones siguen vigentes.

### Costos

Se utiliza la tarifa Trii/Racional:

- Comisión variable antes de IVA: 0,15% del monto transado.
- IVA: 19%.
- Comisión efectiva: **0,1785%** sobre entradas, salidas y rebalanceos.
- Tarifa mínima: $1.990 cuando corresponda a operaciones de monto bajo.

Los backtests independientes del capital aplican 0,1785% al monto transado y no aplican el mínimo de $1.990. Las simulaciones con capital definido deben utilizar el mayor entre la comisión variable y la tarifa mínima cuando corresponda.

## 2. Delta-12

Delta-12 es una estrategia mensual independiente de las corredoras que busca tendencias persistentes mediante precio, momentum y liquidez.

### Indicadores y elegibilidad

Una acción es elegible sólo si:

1. `Momentum12-1 = PrecioAjustado[t-21] / PrecioAjustado[t-252] - 1 > 0`.
2. El precio ajustado está estrictamente sobre la SMA de 200 sesiones.
3. Cuenta con al menos 252 sesiones de historia y 200 observaciones para la SMA.
4. No pertenece al 20% menos líquido.
5. La liquidez corresponde a la mediana de `PrecioAjustado × Volumen` durante 60 sesiones, con al menos 30 observaciones.
6. Los datos requeridos son completos y no están vencidos.

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
- Cae bajo el percentil 20 de liquidez.
- Presenta datos inválidos o vencidos.

No existen stops intrames ni decisiones por noticias.

### Costos

Delta-12 utiliza el mismo modelo Trii/Racional de Sigma-6: 0,1785% sobre el monto transado y tarifa mínima de $1.990 cuando corresponda. Los backtests sin capital definido no incluyen la tarifa mínima.

## 3. Consenso-6

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
