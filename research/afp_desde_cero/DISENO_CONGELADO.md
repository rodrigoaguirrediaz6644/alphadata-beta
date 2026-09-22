# Diseño congelado — estrategia de fondos AFP, desde cero

**Escrito antes de correr una sola línea de estrategia.** Lo que está acá no se
cambia después de ver resultados. Si algo resulta mal elegido, se dice que
estaba mal elegido y se reporta igual.

Horizonte queda fuera por completo: no se leyó su código para esto, no se
reutiliza ninguna de sus series, sus parámetros ni sus umbrales. Lo único
heredado es dato público —el valor cuota de la Superintendencia de Pensiones—,
que existe con o sin Horizonte.

---

## La pregunta

**¿Existe una regla de cambio entre fondos AFP que, después del rezago, le gane
a quedarse en el Fondo A?**

**«Quedarse en A y no mirar» es un resultado válido**, y no cuesta nada, no
necesita sistema, no se rompe y no tiene mantención. Los dos precedentes del
proyecto apuntan ahí: el filtro de régimen de Gamma-6 restó 5-6 puntos sin
reducir el retroceso, y el filtro de tendencia sobre el oro perdió cinco puntos
y empeoró la caída.

## Los datos

| | |
|---|---|
| serie principal | **Cuprum**, la AFP de Rodrigo |
| réplica | **Habitat**, segunda serie completa e independiente |
| fuente | `collabmarket/data_afp`, distribución del valor cuota de la Superintendencia |
| movimiento | **binario, A contra E** |
| frecuencia de decisión | mensual, sobre el valor cuota de cierre de mes |

Binario A/E porque es lo que queda después de 2027 —el generacional más
agresivo contra el más conservador— y porque los fondos intermedios sólo tienen
sentido como refinamiento si lo binario funciona primero.

### Series externas, y lo que falta

| serie | símbolo | desde |
|---|---|---|
| renta variable global | `^990100-USD-STRD` (MSCI World) | 1999 |
| tipo de cambio | `USDCLP=X` | **2003-12** |

**La familia 2 no puede evaluarse antes de 2004-12**, porque el tipo de cambio
diario no existe antes de diciembre de 2003 y la media más larga necesita doce
meses. Pierde el episodio de 2002; conserva los otros seis. Las familias 1 y 3
cubren 2002-2026 completo. **Queda dicho acá y no se arregla después con otra
fuente elegida a conveniencia.**

## Las tres familias, un parámetro cada una

Doce configuraciones en total. **No se agrega una cuarta familia después.** La
lección del estudio v6 es explícita: 96 configuraciones sobre un período que se
dobla a sí mismo no discriminan nada.

### Familia 1 — tendencia de la propia serie del fondo

En A si el valor cuota del Fondo A está sobre su media de N meses; en E si no.

**N ∈ {3, 6, 9, 12} meses.**

Autorreferente: no necesita ninguna fuente externa. **Si funciona, la estrategia
no depende de nadie, y eso vale más que unas décimas de retorno.** Por eso es la
primera.

### Familia 2 — tendencia del mercado que compone al fondo, en pesos

En A si el MSCI World **convertido a pesos** está sobre su media de N meses; en
E si no.

**N ∈ {3, 6, 9, 12} meses.**

En pesos y no en dólares: el Fondo A rinde en pesos y tiene mucho activo
extranjero, así que cuando el peso se deprecia el Fondo A sube aunque los
mercados caigan. Una señal en dólares fallaría justo en los episodios donde más
importa, porque 2008 y 2020 tuvieron movimientos grandes de tipo de cambio.

### Familia 3 — régimen de volatilidad

En A si la volatilidad realizada del Fondo A —60 ruedas, anualizada— está bajo
su percentil P; en E si no.

**P ∈ {70, 80, 90, 95}.**

El percentil se calcula **expandiendo**, sólo con lo observado hasta esa fecha,
nunca sobre la serie completa. Un percentil calculado sobre todo el período es
lookahead disfrazado de umbral.

Mecanismo distinto de los otros dos: no dirección sino estrés. Sirve para saber
si lo que aporta, si algo aporta, es la tendencia o el miedo. También es
autorreferente.

## Los cortes

| | |
|---|---|
| **selección** | 2002-08 a 2013-12 |
| **evaluación** | 2014-01 a 2026-09 |

La primera contiene 2008. La segunda contiene 2020 y 2022 —una caída rápida y
una lenta—, que es exactamente el contraste que interesa.

**Se elige en la primera y se mide en la segunda. Ese número es el honesto.**

## Cómo se evalúa: por episodios, no por promedios

**Una regla defensiva pasa la mayor parte del tiempo sin hacer nada, y un
promedio sobre esos tramos no mide la regla, mide al Fondo A.**

El resultado principal es una **tabla de episodios**: las caídas grandes del
Fondo A entre 2002 y 2026, y para cada una qué hizo cada regla, qué habría
pasado quedándose en A, y qué hizo el Fondo E en ese mismo tramo.

Los episodios se identifican **por la serie del Fondo A**, con una regla
mecánica fijada acá: todo retroceso desde máximo de **más de 10%**, con sus
fechas de inicio, fondo y recuperación. Candidatos esperados: 2002, 2008, 2011,
2015-16, 2018, 2020 y 2022.

**Cada episodio se clasifica por velocidad** —días desde el máximo hasta el
fondo—, que es el discriminador que importa: una media larga llega tarde a una
caída de tres semanas por construcción, y eso no se arregla con parámetros.

**Aparte, el costo en calma:** cuánto restó cada regla en los tramos sin caída.
Ése es el precio del seguro y es donde se pagan los latigazos.

## El tamaño de muestra real

**24 años de datos diarios no son seis mil observaciones: son siete crisis.**

Una regla defensiva se juega en los episodios, y hay siete. Con siete eventos
repartidos en dos ventanas, **elegir la mejor regla en la primera es elegir
sobre tres o cuatro episodios.** Es poco, es lo que hay, y el resultado se
reporta con esa humildad.

## El rezago

Se mide de forma independiente, contra versiones sucesivas del historial de
valor cuota, y **no se da por buena ninguna cifra previa**.

Sensibilidad a **1, 2, 3, 5 y 10 días**. Si el resultado se da vuelta dentro de
ese rango, **la regla no es robusta y ése es el hallazgo**, no un detalle.

## Criterio de éxito hacia adelante

Si alguna regla sobrevive la ventana de evaluación, se registra desde el día uno
**sin recalibrar nada**, con su señal y la del Fondo A al lado.

Y una condición que se deriva de la evaluación por episodios: **el registro
hacia adelante no dice nada hasta que haya una caída.** Si pasan dos años sin
una, el registro sigue vacío, y eso no es evidencia a favor ni en contra. Queda
escrito ahora para que nadie lo lea como confirmación después.

## Lo que se afirma y lo que no

**El Fondo A de 2005 no es el Fondo A de 2025.** Los límites de inversión en el
extranjero se ampliaron varias veces en estos 24 años, así que una regla
calibrada sobre datos antiguos está calibrada sobre otro instrumento. No se
puede corregir; queda como límite de lo que se afirma.

**El Fondo E no es caja.** Es renta fija con duración, así que en un shock de
tasas pierde plata. Cambiarse a E no es ponerse a salvo, es cambiar un riesgo
por otro. Se reporta qué hizo E en cada episodio en vez de suponer que fue el
refugio.
