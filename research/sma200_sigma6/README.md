# Sigma-6 con `adjusted_close > sma200`

## Por qué

Sigma-6 es **la única estrategia accionaria sin ninguna condición de salida que
mire el precio de hoy.** Sus condiciones son señal de Credicorp `+1`, momentum
12-1 positivo, caducidad de la recomendación y tope de tenencia. Y
`momentum = close.shift(21)/close.shift(252) - 1` **salta las últimas 21
ruedas**: una caída del último mes le es invisible.

Delta-12 usa `adjusted_close > sma200` y Gamma-6 usa `sobre_sma200` sobre el
cierre actual. Las dos tienen salida por precio. Agregarle a Sigma-6 la misma
condición es la adición menos arbitraria posible: no inventa un parámetro, usa
el que el sistema ya usa en dos de tres piezas.

## Reglas y predicción, fijadas antes de medir

Del pedido, textual: *reduce la peor caída de forma consistente y reduce algo el
retorno; si el orden se da vuelta en retorno entre submuestras, la conclusión es
que se decide por la caída.*

Ventana 2021-07-08 a 2026-07-15, partida por la mitad. Pesos que corren —la
política escrita en `POLITICA_REBALANCEO.md`— y comisión con el mínimo real de
$1.990 sobre $5.000.000.

## Resultado

| tramo | sin SMA200 | con SMA200 |
|---|---|---|
| completa | +10,54% anual · caída −20,7% | +13,93% anual · caída −12,8% |
| 1ª mitad | −2,95% anual · caída −20,7% | +3,35% anual · caída −12,8% |
| 2ª mitad | +25,89% anual · caída −11,7% | +25,58% anual · caída −11,3% |

Operaciones: 843 → **632** (−25%). Posiciones promedio: 9,75 → 7,74.

**Retorno: el orden se da vuelta.** Con SMA200 gana la primera mitad, sin
SMA200 gana la segunda. **No se distingue por retorno**, y la ventaja de 3,4
puntos anuales en la ventana completa no es evidencia: viene entera de una
submuestra.

**Caída: consistente en las dos.** Con SMA200 es menor en la primera mitad por
7,9 puntos (−12,8% contra −20,7%) y en la segunda por 0,4 (−11,3% contra
−11,7%). Es el único orden que se sostiene.

## Conclusión

La regla fijada de antemano dice que **se decide por la caída**, y la caída dice
que la condición entra. A eso se suma que baja las operaciones un 25%, que a
este capital no es menor.

La predicción se cumple a medias, y conviene decirlo: la parte de la caída sí;
la de que «reduce algo el retorno», **no**. El retorno no se puede distinguir,
y en la ventana completa la versión con SMA200 sale por delante. Tomar eso
último como ventaja sería exactamente el error que las dos submuestras existen
para evitar.

## Qué le hace a la cartera de hoy

La precaución que había que tomar antes de encenderla: la medición corrió
sobre 2021-2026, cuando Credicorp entregaba 17-19 filas mensuales. Hoy entrega
4-8 y Sigma-6 tenía cinco nombres. Si el filtro baja el promedio de 9,75 a
7,74 sobre una muestra sana, sobre una hambrienta podía dejar la cartera en
tres nombres y 70% de caja.

**No ocurrió: quedan cuatro nombres y 60% de caja** ($3.000.000 de $5.000.000).

| | cierre | SMA200 | |
|---|---|---|---|
| BCI | 65.600,00 | 61.282,07 | +7,0% pasa |
| **CENCOMALLS** | **2.240,00** | **2.446,80** | **−8,5% no pasa** |
| LTM | 24,78 | 24,26 | +2,2% pasa |
| PARAUCO | 3.900,00 | 3.761,10 | +3,7% pasa |
| VAPORES | 48,30 | 44,78 | +7,9% pasa |

Sale una sola: **CENCOMALLS**, y era justamente la única posición perdedora de
Sigma-6, que el informe mostraba en −8,1%. El hueco que la regla venía a tapar,
tapado en el primer caso real.

## Estado: encendida

`exigir_sma200` viene en `True` desde el 21-09-2026, y está en
`ESTRATEGIAS_ALPHADATA_v2.md` como condición de elegibilidad y de permanencia.

Dos consecuencias del encendido que conviene tener anotadas:

- **El libro se reconstruyó entero**, porque cambian las selecciones pasadas.
  Sigma-6 pasa de 85 a 99 posiciones anotadas en el recorrido: la condición
  añade rotación en una estrategia semanal. En la ventana completa medida las
  operaciones bajaban de 843 a 632, así que el efecto neto sigue siendo menos
  rotación; el tramo reciente va en la otra dirección.
- **La venta de CENCOMALLS no aparece en el informe de esta semana.** Bajo la
  regla nueva el recorrido la sitúa en la revisión del 11-09, no en la del
  17-09, y el bloque de movimientos muestra la revisión vigente. Es un
  artefacto de la transición y no tiene efecto práctico —nadie ha comprado
  todavía—; de aquí en adelante cada movimiento se informa la semana en que
  ocurre.
