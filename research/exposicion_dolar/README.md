# El 62,5% de la cartera está montado en el dólar, y eso no lo decidió nadie

Investigación pura. La línea del informe va aparte y con su prueba.

---

## Primero, la corrección que me hiciste y que tomo

Escribí que la pieza de oro era **«dos tercios dólar»**. Eso describe la
varianza —R² de 45%— y no la exposición. **La beta es 0,97: dólar entero.**
Cada peso puesto ahí se mueve uno a uno con el tipo de cambio *además* de
moverse con el oro. Son dos cosas distintas y usé la primera para decir la
segunda.

## La cuenta que faltaba

| pieza | reparto | en dólares | monto |
|---|---:|---:|---:|
| Delta-12 | 37,5% | 0% | $0 |
| Gamma-6 | 37,5% | **100%** | $7.500.000 |
| Oro | 25,0% | **100%** | $5.000.000 |
| | | **62,5%** | **$12.500.000** |

**El 62,5% de la cartera se mueve uno a uno con el tipo de cambio.** Salió de
elegir tres piezas por separado, cada una por sus propios motivos, y no hay
ninguna decisión escrita que diga que ésa era la intención.

## La cartera con el dólar y sin el dólar

Rebalanceo diario al reparto, 1.247 días desde 2021-07-09. El retorno sin dólar
se despeja de la identidad `r_clp = (1+r_usd)(1+r_fx) − 1`, no por aproximación.

| | anual | peor caída | volatilidad |
|---|---:|---:|---:|
| **con el dólar** | +26,17% | **−13,96%** | 17,09% |
| **sin el dólar** | +23,92% | **−10,95%** | 13,32% |
| el dólar solo | +2,34% | −23,98% | 17,55% |

**El dólar aportó +2,25 puntos de retorno anual y 3,01 puntos más de caída.**

## Y acá los números contradicen la historia del colchón

Tu explicación mecánica era que el dólar trabaja contra Delta-12 porque el peso
es moneda de materias primas y se debilita cuando los activos de riesgo caen.
**La primera mitad se confirma y la segunda no.**

| | en pesos | sin el dólar |
|---|---:|---:|
| Gamma-6 contra Delta-12 | +0,219 | **+0,292** |
| Oro contra Delta-12 | +0,125 | **+0,178** |

Quitar el dólar **sube** las correlaciones, o sea que el dólar las estaba
bajando — tal como decías. Pero:

- **El dólar contra Delta-12 da −0,014, que es cero**, no negativo. El colchón
  no aparece en esta ventana.
- Y la cartera con dólar tiene **más** volatilidad y **peor** caída.

**Correlación más baja no es riesgo más bajo cuando lo que se agrega es esto de
volátil:** el dólar solo rinde +2,34% anual con −23,98% de caída propia y
17,55% de volatilidad. Entra como un activo riesgoso con correlación cero, no
como un amortiguador.

**En esta ventana el dólar agrega retorno y agrega riesgo. No amortigua.**

Lo que **no** se puede contestar con 2021-2026 es si amortiguaría en una caída
de la bolsa chilena de las que importan: en esta ventana no hubo una, y el
mecanismo del colchón en las AFP se midió sobre episodios que sí la tuvieron.
Son dos afirmaciones distintas y sólo una está medida acá.

## Lo que esto deja decidido y lo que no

**Decidido:** el número existe y ahora está en el informe. Deja de ser una
consecuencia y pasa a ser una decisión que se puede tomar o revisar.

**No decidido, y es de Rodrigo:** si quiere el 62,5%. Vive en pesos, así que un
colchón en dólares contra una caída global es razonable —pero lo que está
medido en esta ventana es que le costó 3 puntos de caída a cambio de 2,25 de
retorno, y eso es una apuesta direccional al dólar, no un seguro.

**No cambia el 25% del oro** ni la pregunta del instrumento: IAU en dólares da
exactamente la misma exposición que IAUCL.

---

Reproducir: `PYTHONPATH=. python research/exposicion_dolar/estudio.py`
