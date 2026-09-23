# Diseño congelado, antes de medir

La pregunta: **¿el dólar amortigua las caídas de la bolsa chilena, o sólo tiene
correlación cero en promedio?** Son dos afirmaciones distintas y sólo la segunda
está medida —en `research/exposicion_dolar/`, sobre 2021-2026, donde el dólar
agregó retorno y agregó riesgo—.

El colchón es una afirmación **sobre episodios**, así que se prueba como
probamos los mecanismos de las AFP: verificando que explique lo que ya pasó, sin
ajustar un solo parámetro.

---

## Las series, y por qué éstas

| | |
|---|---|
| bolsa chilena en pesos | **`ECH` × `USDCLP=X`** — el ETF de Chile cotiza en dólares, así que multiplicarlo por el tipo de cambio devuelve acciones chilenas en pesos |
| tipo de cambio | `USDCLP=X` |
| bolsa global | `^990100-USD-STRD` (MSCI World, dólares) |
| oro | `GC=F` (dólares) |

**`^IPSA` no existe en el proveedor y las acciones chilenas del almacén del
proyecto empiezan en 2015**, o sea que no llegan a 2008 ni a 2011. `ECH` empieza
el **20-11-2007**, y eso fija el comienzo de la prueba.

**La contra de usar ECH, dicha antes:** es un ETF y no el índice, así que tiene
diferencias de seguimiento y su cartera no es exactamente el IPSA. Para lo que
se mide acá —si el peso se debilita cuando la bolsa chilena cae— eso no debería
importar, pero el episodio de **2008 empieza con la serie ya empezada**: el
máximo real fue en octubre de 2007 y ECH arranca un mes después, así que la
caída de 2008 va a salir subestimada. Se dice en el resultado, no se corrige.

## Cómo se eligen los episodios

**Regla mecánica, sin elegir ninguno a mano:** todo retroceso de la bolsa
chilena en pesos de **más de 15%** desde su máximo previo, entre 2007-11-20 y
hoy. Para cada uno: fecha del máximo, fecha del fondo, y la ventana entre ambas.

15% y no 10% porque lo que se quiere son las caídas que importan, no cada susto
de tres semanas. El umbral se fija acá y no se mueve después.

Las candidatas que nombraste —2008, 2011, 2015-16, octubre de 2019, 2020 y
2022— **no se imponen**: si la regla no las produce, salen las que produzca.

## Qué se reporta por episodio

1. Cuánto cayó la bolsa chilena en pesos.
2. **Qué hizo el USD/CLP en esa misma ventana.**
3. Cuánto habría caído una cartera **con 62,5% en dólares** contra una **sin
   dólar**, con el reparto real del proyecto: 37,5% Chile, 37,5% global, 25%
   oro, rebalanceo diario.

«Sin dólar» significa medir las dos piezas en dólares en su propia moneda,
despejando de la identidad `r_clp = (1+r_usd)(1+r_fx) − 1`. No es aproximación.

**Octubre de 2019 va señalado aparte** porque es el único episodio de estrés
chileno puro: en 2008 y 2020 la bolsa chilena y la global cayeron juntas y no
distinguen si el colchón responde a Chile o al mundo.

## Las dos predicciones, antes de mirar

**Primera: el peso se debilita en los episodios.** Espero que el USD/CLP suba en
**al menos 5 de los 6** episodios que salgan, y que en octubre de 2019 suba con
fuerza. Si eso pasa, el colchón existe en las crisis aunque el promedio sea
cero.

**Segunda, y ésta es la que me juego en contra:** espero que **la cartera con
dólar igual tenga peor caída máxima que la cartera sin dólar sobre la ventana
completa**, a pesar de amortiguar en los episodios. El razonamiento es que el
dólar tiene 17,5% de volatilidad propia y correlación cero, así que fuera de los
episodios agrega riesgo todo el tiempo, y la caída máxima puede ocurrir en un
tramo donde el colchón no esté operando.

**Si la segunda falla, la que se cae es mi predicción, no el dato.** Vengo de
equivocarme llamando «dos tercios» a una exposición uno a uno.

## Qué contaría como que el colchón existe

Fijado antes: **el peso sube en al menos 5 de los episodios Y el beneficio
mediano de tener el dólar es de al menos 2 puntos de caída evitada.**

Si el peso no se debilita en los episodios, **la historia del colchón se retira
del proyecto**, no se suaviza.

## Lo que este estudio no hace

No propone cambiar el 62,5% ni ninguna ponderación. No ajusta ningún parámetro:
el reparto viene de `config/runtime.v2.json` y el umbral de episodio está fijado
arriba.

Investigación pura: no toca `data/`, `reports/`, el pipeline ni el informe.
