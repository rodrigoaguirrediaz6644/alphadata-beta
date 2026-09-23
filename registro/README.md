# Registro AFP — la grilla, hacia adelante

**Nada de esto se opera. Nada se recalibra.** Un archivo, una línea por día de
cotización: `afp_senales.csv`.

Se produce con `PYTHONPATH=. python -m src.registro_afp`, a diario, desde
`.github/workflows/registro-afp.yml`.

---

## Por qué existe

El backtest se acabó. No porque no diera resultados, sino porque los resultados
que da ya no distinguen entre hipótesis:

- **La banda de 2% se eligió después de ver los datos.**
- **El largo de la media se eligió después de ver dónde estaba el salto.**
- Las siete AFP son la misma prueba repetida siete veces: sus Fondos A se
  mueven casi idénticos.
- Los episodios son **siete en veintitrés años**, y una prueba sobre siete
  observaciones no tiene potencia para nada.
- Y lo último que aprendimos es lo que cierra el tema: **el precipicio del
  largo de la media aparece en 2011-2026 y no existe en 2004-2019.** Hasta la
  forma de la curva de parámetros es un rasgo de la ventana, no de la regla.

Seguir barriendo parámetros sobre siete crisis es arqueología, no medición.

**Entonces no se registra un punto: se registra la grilla.** Con datos que
nadie miró antes de elegir los parámetros, el tiempo puede hacer lo que el
backtest ya no puede.

## Lo que hay que leer antes de leer cualquier resultado

**Esto no va a decir nada hasta que haya una caída, y eso puede tardar años.**

Queda escrito ahora, de antemano, para que a nadie —incluidos nosotros— se le
ocurra leer una racha tranquila como confirmación. Mientras el mercado suba,
las cinco configuraciones van a estar en Fondo A y el registro va a ser una
columna de `A` repetida. Eso no es evidencia de nada.

**Y la historia que trae el archivo tampoco cuenta.** El CSV incluye la serie
completa desde 2002 porque una señal de histéresis depende de todo lo anterior
y no se puede empezar en el aire. Pero es exactamente la historia sobre la que
se eligieron los parámetros: **sólo las filas posteriores a `CONGELADO`
(2026-09-23) discriminan algo.** El módulo lleva esa fecha como constante y la
prueba la fija.

## La grilla congelada

| | |
|---|---|
| banda | **2%** — sale del Fondo A bajo `−0,02`, vuelve sobre `+0,02` |
| medias | **45, 64, 90, 105 y 126 días de cotización** |
| ejecución teórica | **4 días de cotización** de rezago |
| refugios | **Fondo E**, con el **D** al lado |
| AFP | **Cuprum** |

**Las medias van en días de cotización, no corridos.** Esa distinción costó una
discrepancia entera entre dos sesiones —«126 días» eran 90 de rueda para una y
126 para la otra, y el resultado cambia seis puntos— y es la razón de que las
cinco medias incluyan 90 y 105: el borde está entre 100 y 110, así que la
grilla lo cruza a propósito en vez de quedarse de un lado.

`tests/test_registro_afp.py` fija estos seis valores. **Si la prueba falla,
alguien recalibró**, y esa es toda su función: los parámetros no se eligieron
midiendo, así que el registro sólo sirve si nadie los toca mientras corre.

## Las columnas

| columna | qué es |
|---|---|
| `fecha` | día de cotización |
| `vc_a`, `vc_e`, `vc_d` | valor cuota de los tres fondos |
| `razon_{m}` | `precio / media de m días − 1`. Sirve para ver qué tan cerca del umbral está |
| `senal_{m}` | `A` o `fuera`: lo que la configuración indicaría **hoy** |
| `pos_{m}` | lo que estaría **en vigor** hoy, o sea la señal de hace 4 días |

El refugio no aparece en la señal a propósito: la señal dice si estar en el
Fondo A o fuera, y quien lea decide con cuál refugio valorizarlo. El Fondo D va
al lado del E porque **en abril de 2027 los dos desaparecen del menú** y todavía
no sabemos cuál de los generacionales ocupa ese lugar.

## Dos decisiones de construcción que no son obvias

**Se recalcula entero en cada corrida.** No se agrega una línea: se reconstruye
el archivo completo desde la fuente. Es la norma del censo de series aplicada
acá — una señal de histéresis depende de todo lo anterior, y guardar el estado
e ir agregando es justo la forma de que se quede atrás sin que nadie lo note.

**Y se niega a sobrescribir si el pasado cambió.** Como el cálculo es
determinista sobre una serie pública, una fila vieja sólo puede cambiar si la
fuente revisó su historia. La corrida sale en rojo y no escribe. Un registro
hacia adelante cuyo pasado se reescribe solo no sirve para nada, y lo peor es
que no se nota.

## Qué se podrá preguntarle, y cuándo

Cuando haya ocurrido una caída de las que importan —no un susto de dos
semanas— el archivo permite responder, sin recalibrar nada:

1. **Cuáles de las cinco medias salieron, y cuántos días antes del fondo.**
2. **Si el borde entre 100 y 110 días de cotización era real o era de la
   ventana 2011-2026.** Es la pregunta que dejó abierta el último estudio.
3. **Cuánto habría costado el rezago de 4 días** contra la señal sin rezago.
4. **Cuál refugio funcionó**, valorizando la misma señal con E y con D.

Ninguna de esas cuatro se puede contestar con el backtest, y las cuatro se
contestan solas si el registro sigue corriendo.

## Lo que sigue dependiendo de una gestión humana

La AFP tiene que confirmar por escrito cuántos días hábiles toma el cambio, con
qué valor cuota se materializa, si cobran, y qué pasa con volumen inusual de
solicitudes. El rezago de 4 días de esta grilla es el número documentado, no uno
confirmado — y todo el trabajo previo mostró que el resultado se da vuelta entre
6 y 8 días corridos.

Y para después de abril de 2027: **la correlación de la cartera de referencia
del fondo de Consolidación con la del Fondo Inicial.** No su volatilidad ni su
porcentaje de renta variable. Ése es el número que decide si esto sigue
existiendo, y no se puede calcular desde acá.

---

Los estudios que llevaron hasta acá están en `research/afp_*`. El que explica
por qué se congela es `research/afp_2027/`.
