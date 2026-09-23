# El intento elaborado: batería técnica, ensemble y walk-forward

Tenías razón en la crítica. Los tres estudios anteriores probaron **indicadores
sueltos a frecuencia mensual**, con un rezago de ejecución que además resultó
ser optimista. Eso no es análisis técnico elaborado: es un tamiz.

Éste es el intento en serio. **Y encontró algo** — aunque no lo suficiente para
apostarle plata, y eso hay que decirlo con los números.

---

## Lo que este estudio hace distinto

| | los tres anteriores | éste |
|---|---|---|
| frecuencia | mensual | **diaria** |
| indicadores | 1 por familia, 12-18 combinaciones | **25 características técnicas** |
| combinación | votos fijos | **tres modelos que las combinan** |
| validación | dos ventanas | **walk-forward por año, 17 años** |
| rezago de ejecución | 2-3 días (**optimista**) | **6 días corridos, el real** |
| dónde se calcula la señal | sobre el valor cuota | **sobre los mercados y la cuota** |

### Dos cosas que descubrí y que cambian dónde hay que buscar

**1. El valor cuota va un día atrás del mercado.** La beta del Fondo A al MSCI
World de **ayer** es **0,428 con t = 59,7**; la de hoy es **0,004 con t = 0,5**.

> El valor cuota publicado para el día *t* refleja el movimiento del mundo del
> día *t−1*.

Eso significa que **todas las señales que calculé antes sobre la serie del fondo
iban un día más tarde de lo necesario.** Acá las señales se calculan también
sobre los mercados, que van adelante.

**2. El rezago real de ejecución es más largo de lo que supuse.** El cambio de
fondo se hace efectivo en **4 días hábiles contados desde el día hábil siguiente
a la solicitud**, y se aplica el valor cuota **del día anterior a la
materialización**. Eso son del orden de 6 a 7 días corridos, no 2 ni 3.

**Mis estudios anteriores usaron 2-3 días. Fui optimista, y eso favorecía a las
reglas.** Acá está corregido.

## El resultado, fuera de muestra

Walk-forward: se entrena con todo lo anterior a cada año y se opera ese año.
El modelo nunca ve el futuro. 2010-2026, Habitat.

| modelo | acierto | anual | peor caída | cambios/año |
|---|---:|---:|---:|---:|
| regresión logística | 51,9% | +8,11% | −25,02% | 26,8 |
| **bosque aleatorio** | **51,1%** | **+9,54%** | **−23,80%** | **23,3** |
| gradient boosting | 50,7% | +8,61% | −23,10% | 44,9 |
| **comprar A y no mirar** | | **+8,94%** | −26,06% | 0 |
| comprar E y no mirar | | +6,75% | −21,18% | 0 |
| mezcla fija 40/60 | | +7,76% | **−13,83%** | 0 |

**El bosque aleatorio le gana al Fondo A en las dos cosas**: +0,60 puntos de
retorno y 2,3 puntos menos de caída, fuera de muestra, sobre 17 años. Es la
primera vez en estos cuatro estudios que algo hace eso.

Año por año le gana en **10 de 17**.

## Y ahora las pruebas que deciden si se puede creer

### No es estadísticamente distinguible de la suerte

| | diferencia anual | **t** | **p** |
|---|---:|---:|---:|
| Habitat | +1,23% | **0,82** | **0,415** |
| Cuprum | +0,72% | **0,45** | **0,655** |

Gana 11 de 17 años en las dos AFP: **p = 0,332**.

Ninguna de las tres pruebas se acerca a significancia. **Con 17 años de datos
diarios, una ventaja de un punto anual con esta volatilidad no se distingue de
haber tenido suerte.**

### Muere justo en el rango de rezago que rige

| rezago | anual | contra Fondo A |
|---|---:|---:|
| 2 días | +9,73% | +1,29% |
| 4 días | +9,76% | +1,33% |
| **6 días** | +9,54% | **+1,23%** |
| **8 días** | +7,78% | **−0,55%** |
| 10 días | +7,12% | −1,22% |

**El rezago real cae entre 6 y 8 días**, que es exactamente donde el resultado
cambia de signo. Y hay algo peor: la norma permite **extender el plazo cuando
hay volumen inusual de solicitudes**, porque la AFP sólo puede traspasar hasta
el **5% del patrimonio del fondo por día**.

> Es decir: el plazo se alarga justo cuando todo el mundo quiere cambiarse, que
> es exactamente cuando la señal tendría valor.

### La ventaja necesita 23 cambios al año para existir

| banda de convicción | anual | cambios/año | contra Fondo A |
|---|---:|---:|---:|
| sin banda | +9,54% | **23,3** | **+1,23%** |
| ±5% | +7,17% | 4,7 | **−1,15%** |
| ±10% | +7,02% | 2,2 | **−1,29%** |
| ±15% | +8,19% | 1,0 | −0,12% |

En cuanto se exige algo de convicción antes de mover, la ventaja **desaparece y
se da vuelta**. No es una estrategia con señales claras: es un goteo de muchas
decisiones marginales.

**Y eso choca de frente con un hecho regulatorio:** hay un proyecto de ley
ingresado que limita los traspasos a **dos al año** con plazo máximo de 30 días.
Con dos cambios al año esta estrategia no existe.

### Las tres refinaciones que probé, y fallaron

**Condicionar por régimen.** El exceso es +3,40% anual en estrés (t=1,62) y
**−0,92% en régimen normal**. Pero operar sólo en estrés y quedarse en A el
resto da **−0,47%** contra el Fondo A: hay que acertarle también a cuándo no
estar.

**Entrenar para evitar caídas en vez de para ganar.** Las tres variantes pierden
contra el Fondo A (+7,88% a +8,13% contra +8,35%) y la peor caída apenas mejora.

**Subir el horizonte y bajar el turnover.** Es la tabla de la banda de
convicción: mata la ventaja.

## Lo que sí salió de acá, y vale

**Las dos características que el modelo más usa no las había probado nunca:**

| característica | importancia |
|---|---:|
| **`fx_corr`** — correlación móvil entre el dólar y la bolsa global | **0,163** |
| **`em_rel`** — fuerza relativa de emergentes contra desarrollados | **0,134** |
| `spread_mom60` | 0,065 |
| `cobre_mom` | 0,060 |
| `mkt_ma200` | 0,060 |

`fx_corr` es **el colchón cambiario**, que yo había descartado por medirlo como
una señal binaria. En un modelo no lineal es lo que más pesa. Tu intuición sobre
ese mecanismo era mejor que mi prueba.

`em_rel` no lo había probado en absoluto, y las AFP tienen un tercio de su
riesgo en emergentes.

**Eso es una pista concreta de dónde buscar**, no una estrategia.

## El veredicto, sin adornos

**No es «no se puede».** Es esto:

> Con 25 indicadores, tres familias de modelos, 17 años de validación
> walk-forward y el rezago correcto, la ventaja mide **+1,2 puntos anuales con
> p = 0,42**, se da vuelta a 8 días de rezago cuando el real son 6-8, y necesita
> **23 cambios al año** cuando hay un proyecto de ley para limitarlos a dos.

**Eso es una pista, no una estrategia.** La diferencia importa: una pista se
sigue investigando, una estrategia se financia. Ésta no se financia.

Y para comparar honestamente: la **mezcla fija 40/60** da +7,76% con **−13,83%**
de peor caída. El modelo da +9,54% con −23,80%. **Si lo que quieres es
protección, la mezcla fija sigue ganando por diez puntos de caída, sin modelo,
sin datos y sin cambios.** Si lo que quieres es retorno, el Fondo A da +8,94% y
el modelo +9,54%, con p = 0,42 sobre la diferencia.

## Qué haría falta para que esto cambie

Tres cosas concretas, en orden de cuánto moverían la aguja:

1. **Probar `fx_corr` y `em_rel` como mecanismos, con hipótesis propia**, en vez
   de como dos features entre veinticinco. Son lo que el modelo usa y nunca se
   midieron solos.
2. **Un rezago de ejecución menor.** Si se confirmara con la AFP que en la
   práctica el cambio se materializa antes de 6 días, la ventaja pasa de +1,23%
   a +1,33% y deja de estar en el filo. Es una pregunta para Cuprum, no un
   cálculo.
3. **Más episodios.** El problema de fondo no es el método: son cuatro o cinco
   crisis en veintidós años. Ningún modelo resuelve eso.

---

Reproducir: `PYTHONPATH=. python research/afp_tecnico_serio/estudio.py`

Fuentes de los hechos regulatorios:
[Compendio de Pensiones — Cambio y Asignación de Fondos](https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3623.html) ·
[AFP Capital — cambio de fondo](https://ww2.afpcapital.cl/Afiliado/Multifondos/Paginas/Cambio-de-Fondo.aspx) ·
[Diario Financiero — proyecto que limita a dos traspasos al año](https://www.df.cl/mercados/pensiones/gobierno-ingresa-proyecto-que-limita-el-cambio-de-fondos-en-las-afp)
