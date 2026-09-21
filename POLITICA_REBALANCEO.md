# Política de rebalanceo

Hasta ahora no existía escrita. Estaba implícita en la aritmética del NAV, y lo
que esa aritmética supone no es lo que nadie iba a hacer.

## El problema

Las cuatro estrategias devuelven `portfolio[ticker, target_weight]` y el peso
sale de `capped_pro_rata`: partes iguales, calculadas de cero en cada revisión,
ciegas a lo que la posición haya rendido. No hay número de acciones ni memoria
de tamaño en ninguna parte del motor.

El NAV histórico calcula el retorno diario como
`retorno_dia += peso * (precio_hoy/precio_ayer - 1)` con el peso **constante**.
Ésa es la fórmula de una cartera que vuelve al objetivo todos los días. Y el
costo se cobra sólo cuando cambia el objetivo, que casi nunca cambia porque
partes iguales dan el mismo número pase lo que pase con los precios.

De ahí salen dos cosas, las dos falsas:

1. **El rebalanceo es gratis.** El NAV supone que la cartera vuelve al 10% cada
   día y no cobra nada por ello.
2. **La orden nunca se emite.** Como el modelo cree que la posición está en su
   peso objetivo, nunca dice «recorta». Una posición que crece se va
   concentrando en la cuenta real mientras el informe sigue diciendo 16,7%.

Hay además una inconsistencia interna que lo confirma:
`combined_equal_weight` declara en su propio comentario que entre estrategias
los pesos se dejan correr dentro del mes, «igual que ocurriría en una cuenta
real». Dos supuestos distintos en el mismo informe.

## Lo medido

Banco de pruebas con las selecciones calculadas **una sola vez** y compartidas
por todas las políticas: por construcción no pueden diferir en qué se compra,
sólo en qué pasa con los pesos entre revisiones. Control: la política
`constante` reproduce `delta12_historical_nav` con desvío máximo 0,000000%
(315,8942 en las dos).

### Primero, sin comisión mínima

Retorno anual y peor caída, 2021-07 a 2026-07.

| | constante (el NAV de hoy) | rebalancea al objetivo | deja correr |
|---|---|---|---|
| Delta-12 | +25,76% / −14,9% | +25,42% / −15,2% | +24,93% / −15,0% |
| Gamma-6 | +23,83% / −26,4% | +24,06% / −26,4% | +27,24% / −28,9% |
| Sigma-6 | +18,94% / −15,2% | +18,69% / −15,1% | +18,06% / −17,2% |

Brecha acumulada contra el NAV publicado: Delta-12 −1,34% / −3,27%, Sigma-6
−1,05% / −3,65%, Gamma-6 **+0,92% / +14,60%**.

La predicción era «chica pero sistemática, y mayor en Gamma-6 que en
Delta-12». Las dos partes se cumplen. Lo que no estaba previsto es **el signo**:
en Delta-12 y Sigma-6 el NAV publicado sobreestima lo que obtiene una cuenta;
en Gamma-6 lo subestima, y por mucho.

En Delta-12 y Sigma-6 el orden se mantiene en las dos submuestras. En Gamma-6
`deja correr` es primero en las dos, pero `constante` contra `rebalancea` se da
vuelta: **entre esas dos no se distingue.**

### Después, con la comisión mínima de $1.990 sobre $5.000.000

Ésta es la que decide, porque es la que se paga. Banda = cuánto puede apartarse
una posición del objetivo antes de corregirla; entradas y salidas se ejecutan
siempre.

| banda | Delta-12 (ops/año, retorno) | Gamma-6 | Sigma-6 |
|---|---|---|---|
| 0% | 117 · +22,61% | 93 · +23,60% | **550 · −19,21%, caída −67%** |
| 2% | 91 · +23,29% | 78 · +24,06% | 207 · +9,63% |
| 3% | 87 · +23,06% | 79 · +23,50% | 164 · +10,57% |
| 5% | 92 · +22,88% | 81 · +24,29% | 172 · +10,49% |
| 7% | 91 · +23,28% | 82 · +24,08% | 168 · +10,54% |
| 10% | 91 · +23,28% | 83 · +24,54% | 168 · +10,54% |
| sin corregir | 91 · +23,28% | 85 · +25,37% | 168 · +10,54% |

**Dos resultados, y sólo dos.**

**La banda 0 es la peor en las dos submuestras, en las tres piezas.** Es lo
único que el orden sostiene. En Sigma-6 no es «peor»: es destructivo. 550
operaciones al año a $1.990 son $1.095.000 sobre una pieza de $5.000.000, o sea
**22% del capital al año en comisiones**, y el resultado pasa de +10,5% a
−19,2% anual con una caída de −67%. Rebalancear una estrategia semanal a este
capital la destruye.

**Entre todas las demás bandas, el orden se da vuelta entre submuestras en las
tres piezas. No se distinguen.** Delta-12: 1ª mitad 7% > 10% > sin > 2% > 5% >
3%; 2ª mitad 3% > 2% > 7% > 10% > sin > 5%. Gamma-6 y Sigma-6, lo mismo. No hay
banda óptima que la medición pueda identificar, y elegir una por el resultado
de la ventana completa sería elegir ruido.

Lo que sí separa es el conteo de operaciones, y a partir del 7% coincide
exactamente con no corregir nunca: la deriva casi nunca llega tan lejos.

## La política

**Se dejan correr los pesos. Sólo se operan entradas y salidas.**

Es una de las opciones indistinguibles entre sí, es la única que no requiere
elegir un número que la medición no puede justificar, y es la más simple de
ejecutar: la orden es la que ya aparece en el informe.

Consecuencias que hay que aceptar con ella:

- **Los ganadores se concentran.** INTC ya está en 19,9% de Gamma-6 contra un
  objetivo de 16,7%. Eso es deliberado, no un defecto.
- **Bajo rebalanceo a objetivo pasaría lo contrario**, y peor: una posición que
  cae queda bajo su peso y volver a ponerla en el objetivo es **comprar más del
  perdedor**. Promediar a la baja dentro de una estrategia de momentum, sin que
  nadie lo haya decidido. Ésa es otra razón para no hacerlo.
- **No hay guardia de concentración.** Si una posición se va muy arriba, nada la
  recorta. Poner un tope sería inventar un número que la medición no respalda;
  queda anotado como decisión pendiente, no como regla.

## Lo que falta

El modelo todavía calcula `constante`. Mientras no se cambie, **el NAV publicado
describe una cartera que nadie tiene.** Cambiar
`delta12_historical_nav`, `gamma6_historical_nav` y la serie de Sigma-6 a la
aritmética de pesos que corren mueve todos los números publicados: Delta-12 y
Sigma-6 bajan unos tres puntos acumulados en cinco años, Gamma-6 sube quince.
No se toca hasta que la política esté aprobada.
