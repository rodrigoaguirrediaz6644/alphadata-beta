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

### Cómo se financia una entrada

La política dejaba esto abierto, y la implementación lo iba a resolver sola.
Delta-12 vende ILC, que después de subir vale más de lo que pesaba al entrar, y
compra ANDINA-B. **ANDINA-B recibe el producto de la venta**, no un octavo del
valor de la pieza: lo segundo obligaría a mover plata desde o hacia las demás
posiciones, y eso ya es un rebalanceo parcial, justo lo que esta política dice
no hacer.

En cada revisión:

1. Las que siguen conservan el peso al que llegaron. **No se tocan.**
2. Las que salen se venden enteras.
3. Lo liberado, más la caja, se reparte **en partes iguales entre las que
   entran**, con tope en el peso de referencia de la estrategia; lo que sobre
   queda en caja.

El tope del punto 3 evita que una entrada herede de golpe el tamaño de un
ganador recién vendido. Es lo que se midió y lo que `src/nav_historico.py`
calcula. Requiere exactamente las mismas operaciones que ya se hacen.

### El peso de referencia no es un objetivo

Bajo esta política el peso de referencia **sólo aplica en el momento de
entrar**; de ahí en adelante el peso real es el único que existe. Por eso el
informe no lo llama «objetivo»: una columna que dijera «objetivo 16,7%» al lado
de «hoy 19,9%», con una política que dice no corregir nunca, se leería como una
instrucción pendiente que nadie va a ejecutar.

Consecuencias que hay que aceptar con ella:

- **Los ganadores se concentran.** INTC ya está en 19,9% de Gamma-6 contra un
  objetivo de 16,7%. Eso es deliberado, no un defecto.
- **Bajo rebalanceo a objetivo pasaría lo contrario**, y peor: una posición que
  cae queda bajo su peso y volver a ponerla en el objetivo es **comprar más del
  perdedor**. Promediar a la baja dentro de una estrategia de momentum, sin que
  nadie lo haya decidido. Ésa es otra razón para no hacerlo.
### Esta política concentra, y hay que decirlo

El +14,6% de Gamma-6 y el INTC en 19,9% contra 16,7% son el mismo fenómeno
visto dos veces: dejar correr los pesos captura al ganador completo —por eso
gana— y **por eso mismo concentra**.

Si INTC sigue corriendo puede llegar a ser un tercio de la pieza. El único
techo que existe hoy es que el nombre salga del top 6 en alguna revisión,
momento en el cual se vende entero; para INTC eso no ha ocurrido en doce meses.

La peor caída medida —−28,9% contra −26,4%— probablemente **subestima** esto,
porque depende de si la ventana contiene un caso donde el ganador grande se dio
vuelta. Con un solo ganador de esa magnitud en la muestra, no hay cómo saberlo.

Esto no cambia la decisión, pero se toma con los ojos abiertos.

### El límite de concentración: 25% de la pieza

**Decidido el 21-09-2026.** Ninguna posición puede pasar del **25% del valor de
su propia pieza**. Como cada pieza es un cuarto del total, equivale a **6,25%
de los $20 millones**; las dos lecturas son plausibles y sólo una es la
correcta.

- Se revisa **en cada revisión de la estrategia**, con el mismo calendario que
  todo lo demás. No es un control continuo ni intradía.
- Al pasarse, **se recorta hasta 25% exacto y nada más.** No se vuelve al peso
  de entrada: eso sería rebalancear, que es justo lo que esta política
  descartó. El recorte mínimo es coherente con la justificación y es el más
  barato.
- **Lo recortado va a la caja de la pieza**, no se reparte entre las otras
  posiciones. Queda ahí hasta que una entrada lo use, igual que el producto de
  las ventas.
- Aplica a Sigma-6, Delta-12 y Gamma-6. **No aplica al oro**, que es 100% de su
  pieza por diseño: excepción explícita, no un caso que no se dio.
- Aplica también a la reconstrucción, o la serie publicada dejaría de describir
  la regla.

**No es una banda de rebalanceo**, que se descartó por ruido. Es un límite de
cola, y su justificación no es «mejora el retorno» sino «no quiero un tercio de
una pieza en un solo papel». Esa pregunta no se contesta con backtest.

#### Lo medido, aunque la decisión ya estuviera tomada

Un tope al 25% es, estructuralmente, una banda de un solo lado en un umbral
ancho, así que había que saber si dispara dos veces en cinco años o veinte.

| pieza | disparos en 5 años | comisión acumulada |
|---|---|---|
| Delta-12 | **0** | $0 |
| Sigma-6 | **0** | $0 |
| Gamma-6 | **12** (2,4 al año) | **$3.839** |

En las piezas chilenas nunca llega a atarse. En Gamma-6 dispara sobre dos
nombres: NVDA nueve veces entre 2021 y 2024, e INTC tres veces en 2026, la
mayor de ellas al 32,9%.

$3.839 en cinco años sobre una pieza de $5.000.000 es **0,077% acumulado**, o
sea 0,015% al año. No es la banda rechazada entrando por la puerta de atrás: la
banda 0 costaba $1.095.000 **al año** sólo en Sigma-6.

**El costo real no es la comisión, es el retorno que se deja de componer:**

| Gamma-6 | sin límite | con límite |
|---|---|---|
| completa | +27,24% · −28,9% | **+26,08% · −26,9%** |
| 1ª mitad | +16,94% · −21,9% | +16,95% · −21,9% |
| 2ª mitad | +38,41% · −28,9% | +35,89% · −26,9% |

Cuesta **1,16 puntos anuales** y compra **2 puntos de peor caída**. En la
primera mitad no se nota, porque no hubo un ganador de ese tamaño; todo el
efecto está en la segunda. Es exactamente lo que un límite de cola hace, y es
el precio que se acepta al ponerlo.

Sobre la serie publicada: Gamma-6 pasa de 335,00 a 319,95 y el Conjunto de
293,05 a 288,93.

## El modelo ya calcula esto

Hecho el 21-09-2026. Ver `data/archivo/cambio_aritmetica_nav.md` para las
cifras antes y después, incluida una que la medición no anticipaba: la serie de
Sigma-6 nunca se reconstruía, así que al recalcularla por primera vez con los
datos reparados cae mucho más que lo que explica el cambio de aritmética.

## El bloque de movimientos compara informes, no fechas de señal

Antes leía el libro **en la fecha de señal vigente**, así que cualquier cambio
que el libro situara en una fecha anterior quedaba invisible. No era
excepcional: **ocurre cada vez que el libro se reconstruye**, o sea cada vez que
cambia una regla, y eso pasó dos veces en una semana.

Y ya había causado daño. El primer informe dijo «Comprar CENCOMALLS». Al
encender la SMA200, el recorrido situó su salida en la revisión del 11-09 y no
en la del 17-09, así que el informe siguiente no la tenía y **nunca dijo que la
vendiera**. Quien la hubiera comprado se quedaba con una posición que el modelo
ya no tiene y sin ninguna instrucción.

Ahora el bloque compara **la cartera del informe anterior contra la vigente** y
muestra la diferencia completa, venga de una revisión nueva o de una
reconstrucción del libro. La cartera emitida se guarda en
`data/cartera_publicada.json` después de generar el informe: lo que se compara
la próxima vez es lo que el lector efectivamente recibió.

Un cambio de fecha de entrada **no** es una operación: si LTM sigue en cartera
y sólo cambió su fecha al reconstruirse el libro, no aparece.

La prueba de invariante pasa a tener sus dos direcciones. La que existía cubría
que toda COMPRAR estuviera en la cartera; faltaba la simétrica, que es la que
habría atrapado a CENCOMALLS: **toda posición que estaba en el informe anterior
y ya no está tiene que aparecer como VENDER.**
