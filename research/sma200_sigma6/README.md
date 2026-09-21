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

## Estado

`sigma6(..., exigir_sma200=...)` existe y viene **apagada**. Encenderla cambia
la cartera publicada —de 9,75 a 7,74 nombres promedio— y eso no se hace sin
decisión explícita.
