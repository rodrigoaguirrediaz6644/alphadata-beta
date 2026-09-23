# El oro: la serie está limpia, y el problema está al lado

Investigación pura: no toca producción. El cambio en el informe —mostrar lo
comprado de verdad— va aparte y con su prueba.

---

## 1. La serie es IAU en Nueva York, no IAUCL

**El defecto que temías no está.** `ORO_TICKER = "IAU"` y `config/tickers.csv`
trae `IAUCL` en una columna aparte, `cdv_ticker`, que sólo se usa para la puerta
de símbolos al comprar. La medición corre sobre el ETF en dólares, convertido a
pesos con `to_clp`.

Y no lo digo por la configuración —ese sería justo el error de mirar el rótulo
en vez del dato— sino por la serie guardada:

| | |
|---|---|
| ticker de origen | **IAU**, 2.947 filas, 2015-01-02 a 2026-09-22 |
| último precio | **82,03** (dólares, no pesos) |
| volumen típico | **5.843.250 unidades diarias** |
| días con precio exactamente repetido | 80 de 2.946 (**2,7%**) |
| huecos de más de 4 días corridos | **0** |

Los saltos grandes vienen con volumen **enorme**, que es lo contrario de lo que
haría un CDV sin libro:

| día | movimiento | volumen |
|---|---:|---:|
| 2026-01-30 | −10,21% | 76.121.500 |
| 2026-02-03 | +6,24% | 36.182.400 |
| 2025-10-21 | −6,21% | 39.834.100 |

Un instrumento sin contraparte da saltos con volumen **bajo o nulo**: el precio
se queda quieto y después alguien transa al nivel que ya correspondía. Acá el
único salto sobre 8% vino con trece veces el volumen de un día normal. Es una
sesión real, no un hueco.

Los 80 días de precio repetido se concentran en 2015-2019, cuando IAU valía
$11-13: a ese precio un tick de un centavo es 0,08% y los empates exactos son
normales.

**Entonces es sólo un cambio de instrumento, como decías en el primer caso.**

## 2. Pero midiendo para contestarlo aparece otra cosa

La correlación no está subestimada por precios rancios. **Está inflada la
diversificación por otro motivo: la pieza de oro en pesos es, en casi la mitad
de su varianza, una posición en dólares.**

| | en pesos | quitando el dólar de los dos lados |
|---|---:|---:|
| oro contra **Gamma-6** | **+0,549** | **+0,182** |
| oro contra **Delta-12** | +0,125 | +0,174 |

- oro en pesos contra el dólar: **+0,669**
- oro en dólares contra el dólar: **−0,008**
- volatilidad anual: **18,4% en dólares → 25,6% en pesos**

**El dólar le agrega 7,2 puntos de volatilidad, no se los quita.** Y la
regresión de la pieza sobre el tipo de cambio da beta 0,97 con **R² de 45%**.

### Qué significa para el 25%

**El oro diversifica bien a Delta-12 y mal a Gamma-6**, y la razón es que
Gamma-6 también está en dólares. Contra Gamma-6, casi todo lo que el oro aporta
es más de lo mismo: más dólar.

Eso no invalida el 25% —Delta-12 es la mitad de la cartera y ahí la
diversificación es real— **pero sí cambia cómo se justifica.** Decir «el oro
amortigua las caídas de las otras dos» es correcto para una y flojo para la
otra, y el número que lo dice es +0,549, no +0,125.

**Y hace la pregunta del instrumento todavía menos importante de lo que
parecía**: comprar IAU en dólares en Renta 4 da exactamente la misma exposición
—oro más dólar— que IAUCL. Lo que cambia el perfil no es dónde se ejecuta sino
si se quiere el dólar adentro, y eso es una decisión de diseño de cartera que no
estaba escrita en ninguna parte.

## Lo que este estudio no hace

No propone cambiar la ponderación ni el instrumento. Mide lo que se preguntó y
el hallazgo que apareció al lado, y los dos números quedan para que la decisión
se tome con ellos.

---

Reproducir: `PYTHONPATH=. python research/oro_serie/estudio.py`
