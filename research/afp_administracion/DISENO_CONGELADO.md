# Diseño congelado — estrategia de administración A↔E

**Escrito antes de correr una sola línea de estrategia.** Commit propio y
anterior a cualquier resultado.

El estudio anterior fue un tamiz y descartó reglas de una sola velocidad, que es
una familia y no el espacio. Esto es el intento serio: tres cambios de
estructura, cada uno atacando una falla medida. **Si esto no transfiere entre
ventanas, la respuesta es que no hay estrategia y se cierra el tema.**

## Lo que cambia respecto del estudio anterior

Rodrigo levanta dos restricciones: **no hay límite de cambios y las AFP no
cobran por ellos**. Queda pendiente tenerlo por escrito de Cuprum, porque la
norma sí las autoriza a cobrar, pero no bloquea nada acá. **El único costo de
operar es el rezago y el costo de oportunidad.**

---

## 1. La réplica sintética del Fondo A

Una serie construida desde componentes, no desde el valor cuota.

| componente | serie | desde |
|---|---|---|
| renta variable extranjera | MSCI World (USD) × CLP/USD | 1985 / 1957 |
| renta variable local | índice de acciones de Chile, OCDE | 1990-01 |
| renta fija | tasa corto plazo Chile, devengada | **1996-01** |

**El alcance real es 1996, no 1990.** La renta fija chilena es el componente que
manda y empieza en 1996-01. Se dice acá y no después: la historia extendida
agrega **seis años y medio**, no doce.

### Calibración

Pesos por mínimos cuadrados no negativos que suman 1, ajustados **sólo sobre
2002-08 a 2013-12** contra el retorno mensual del Fondo A real de Cuprum, y
**verificados sobre 2014-2026**, que no participa del ajuste.

### Lo que la réplica es y lo que no es

**Antes de 2002 la réplica no es la historia de un fondo: es un contrafactual.**
Los multifondos se crearon en 2002; no existía un Fondo A. Lo que se mide en
1996-2002 es qué habría hecho una cartera con esos pesos, no qué hizo un fondo.

Y los pesos vienen de 2002-2013, mientras que **los límites de inversión en el
extranjero se ampliaron varias veces**. Aplicarlos hacia atrás supone una
composición que no era la de entonces. No se puede corregir; queda como límite
de lo que se afirma.

## 2. Frecuencia: mensual, en las dos ventanas

**Todo mensual.** Los componentes chilenos antes de 2003 sólo existen mensuales,
y desarrollar a una frecuencia y operar en otra sería trampa.

El estudio anterior mostró que una regla mensual **sí** alcanza a atrapar una
caída rápida: `propia-3m` capturó 2020 con −8,5% contra −26,5%, porque el
desplome de febrero-marzo cruzó un cierre de mes. Pasar a semanal es un
refinamiento posterior y necesitaría su propia ventana fuera de muestra.

## 3. Dos velocidades, con salida y regreso distintos

Dos mecanismos en paralelo. **Cada uno tiene su propia condición de salida y de
regreso** —histéresis— porque entrar y salir con el mismo umbral es la fábrica
del latigazo.

**Lento — mercados bajistas que se arrastran.** Vota salir cuando la réplica A
está bajo su media de N meses; vota volver cuando la supera.
**N ∈ {6, 9, 12}.**

**Rápido — desplomes.** Vota salir cuando el retorno de 1 mes de la renta
variable global en pesos cae bajo −U%; vota volver cuando el retorno de 1 mes
vuelve a ser positivo. **U ∈ {4%, 6%, 8%}.**

**Colchón cambiario — el mecanismo, no un predictor.** El peso chileno es
moneda de materias primas y suele debilitarse cuando los activos de riesgo
globales caen, así que el Fondo A recibe un colchón cambiario justo en las
caídas. **El peligro real no es que caiga la bolsa: es que caiga y el colchón no
aparezca.**

Se mide como la correlación móvil de 24 meses entre el retorno de CLP/USD y el
retorno de la renta variable global en dólares. En condiciones normales es
**negativa** —la bolsa cae y el dólar sube—. Vota salir cuando **deja de serlo**,
o sea cuando la correlación pasa de cero. **Umbral fijo en cero**, porque cero
es el punto con significado económico y no un parámetro que buscar.
**Entra o no entra: {con colchón, sin colchón}.**

**3 × 3 × 2 = 18 configuraciones.** Más historia paga por más parámetros; ése es
el trato y no se estira más.

## 4. Exposición graduada, que es la regla de precedencia

No hay un árbitro aparte: **cada mecanismo vota y la exposición es el conteo.**
Una señal falsa cuesta un escalón, no la posición entera.

| votos de salida | exposición a la réplica A | resto |
|---|---|---|
| 0 | 100% | — |
| 1 | 67% (con colchón) / 50% (sin) | refugio |
| 2 | 33% / 0% | refugio |
| 3 | 0% | refugio |

Con el colchón son tres votos y cuatro escalones; sin él, dos votos y tres.

## 5. Los dos refugios, porque en 2027 cambia

| mundo | refugio |
|---|---|
| **hoy** | Fondo E real (2002+) / renta fija corta (1996-2002) |
| **desde abril de 2027** | **Etapa 10**: 29% réplica A + 71% renta fija |

**Los dos se reportan.** El segundo es el que va a estar vigente cuando esto
opere de verdad, y diluye la protección por construcción.

## 6. El criterio combinado, pre-registrado

Fue el hueco declarado del estudio anterior. Se define **ahora**:

> **Se elige la regla con mayor `CAGR / |peor caída|` entre las que cumplan
> `CAGR ≥ CAGR(réplica A) − 1,0 punto anual`.**

El cociente pondera retorno contra retroceso en un solo número. **El piso es
imprescindible:** sin él gana una regla que se queda en el refugio para siempre,
que tiene caída casi nula y un cociente enorme.

Se reporta también qué habría elegido cada criterio por separado —sólo retorno,
sólo caída— para que se vea si el combinado está haciendo trabajo o
escondiéndolo.

## 7. Las ventanas

| | |
|---|---|
| **selección** | 1996-01 a 2002-07 — réplica contrafactual, historia extendida |
| **evaluación** | 2002-08 a 2026-09 — fondos reales |

**Se elige en la extendida y se mide en Chile 2002-2026.** Es el orden que pide
la orden: desarrollar sobre lo que no se ha mirado.

La ventana de selección es corta —seis años y medio— y contiene pocos episodios.
Se dice con esa humildad.

### Y hay que decirlo en voz alta: Chile 2002-2026 ya se miró

El estudio anterior probó doce configuraciones simples sobre esa misma ventana.
**Está parcialmente contaminada.** No es fatal, porque fueron doce reglas de una
familia distinta, pero significa que **la validación de verdad es hacia
adelante**: registro desde el día uno, sin recalibrar. El backtest es el tamiz;
el registro es la prueba.

## 8. Lo que se arrastra sin cambios

**Rezago de ejecución: 2 días corridos**, medido contra 40 versiones del
repositorio fuente. La señal puede ser de hoy; estar adentro no. Se reporta
sensibilidad, pero el número base es ése.

**El Fondo E no es caja.** Perdió 7,8% en 2020. Se reporta qué hizo el refugio
en cada episodio en vez de suponer que protegió.

## 9. La condición de cierre

**Si con dos velocidades, exposición graduada y la señal del colchón el
resultado sigue sin transferir entre ventanas, la respuesta es que no hay
estrategia y se cierra el tema para siempre.** No habrá un tercer intento con
más indicadores.

Y si además gana en retorno en las dos ventanas, **se mira con desconfianza y se
busca primero el error de construcción de la réplica**, que es donde un
sintético puede regalar retorno sin que se note.
