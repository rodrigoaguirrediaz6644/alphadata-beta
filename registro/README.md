# Ahorro Generacional — la grilla, hacia adelante

**Nada de esto se opera. Nada se recalibra.** Un archivo, una línea por día de
cotización: `ahorro_generacional.csv`.

Se produce con `PYTHONPATH=. python -m src.registro_generacional`, a diario, desde
`.github/workflows/ahorro-generacional.yml`.

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

**Sobre la protección, esto no va a decir nada hasta que haya una caída, y eso
puede tardar años.**

Queda escrito ahora, de antemano, para que a nadie —incluidos nosotros— se le
ocurra leer una racha tranquila como confirmación. Mientras el mercado suba,
las cinco configuraciones van a estar en Fondo A y las columnas de señal van a
ser una columna de `A` repetida. Eso no es evidencia de nada.

**Sobre el costo sí dice algo desde el primer mes, y por eso se guarda.** El
trato tiene dos mitades: cuánto ahorra en las caídas y **cuánto cuesta en los
años tranquilos**, que se paga en latigazos cada vez que la señal sale y vuelve
sin que pasara nada. Esa segunda mitad no necesita ninguna crisis.

Y da una pregunta que el archivo puede contestar mucho antes que la otra: **de
las cinco medias, cuál paga menos peaje en calma.** Si una se despega hacia
abajo en dos años de mercado tranquilo, queda descartada sin esperar el
desplome.

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
| votos para salir | **2 de 5** |
| refugio que se opera | **Fondo E** — por correlación, no por ser el más tranquilo |
| administradora | **Cuprum** |

**Las medias van en días de cotización, no corridos.** Esa distinción costó una
discrepancia entera entre dos sesiones —«126 días» eran 90 de rueda para una y
126 para la otra, y el resultado cambia seis puntos— y es la razón de que las
cinco medias incluyan 90 y 105: el borde está entre 100 y 110, así que la
grilla lo cruza a propósito en vez de quedarse de un lado.

`tests/test_registro_generacional.py` fija estos seis valores. **Si la prueba falla,
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
| `votos` | cuántas de las cinco indican salir, sobre la posición en vigor |
| `posicion` | **la instrucción única**: el fondo donde corresponde estar hoy |
| `acum_a` | retorno acumulado del Fondo A **desde el congelamiento** |
| `acum_{m}_{e\|d}` | lo mismo para cada configuración, con refugio E o D |
| `acum_voto` | lo mismo para la regla que de verdad se opera |
| `aviso`, `aviso_estado` | si ese día salió un aviso de cambio y si llegó |

Las columnas `acum_*` están vacías antes del congelamiento a propósito: acumular
sobre la historia con la que se eligieron los parámetros no mide nada. El peaje
de una configuración es `acum_{m}_{ref} − acum_a`, y queda guardado en vez de
derivado después porque si hay que reconstruirlo, alguien va a reconstruirlo
distinto.

El refugio no aparece en la señal a propósito: la señal dice si estar en el
Fondo A o fuera, y quien lea decide con cuál refugio valorizarlo. El Fondo D va
al lado del E porque **en abril de 2027 los dos desaparecen del menú** y todavía
no sabemos cuál de los generacionales ocupa ese lugar.

## La regla que se opera: la votación, no una media

Operar exige **una** instrucción, no cinco. Y elegir una de las cinco medias
sería justo la decisión contaminada, porque las elegimos mirando estos datos.

**La salida es no elegir: que voten.** Se va al refugio cuando **dos o más** de
las cinco lo indican, y vuelve al agresivo cuando menos de dos. Sobre la
posición en vigor, no sobre la señal del día: lo que se vota es lo que se puede
materializar.

El umbral de dos también se eligió mirando la tabla —es selección posterior,
como todo lo demás—. Lo que lo hace defendible es que **2 de 5 y 3 de 5 dan casi
lo mismo** en las tres ventanas medidas, así que la elección entre ellas no es
la que decide. **La que decide es no esperar a la unanimidad: esperar a las
cinco cuesta siete puntos de caída.**

Sobre la historia completa esto da **2,2 cambios al año**, y las cinco medias
están de acuerdo el **81,7%** de los días. El 18,3% restante es donde la regla
hace su trabajo.

## El aviso de cambio, el mismo día

El informe semanal no sirve como instrumento: entre que la señal habla un lunes
y se lee el viernes se pierden cuatro días, que sumados al rezago de ejecución
deterioran varios puntos la protección medida.

`src/aviso_generacional.py` corre dentro del mismo trabajo diario, después de calcular la
grilla. **Dispara sólo en la transición** —no cada día que la señal esté en
refugio— y se repite **tres días de cotización**: un correo se pierde, tres no.
Así tampoco hace falta que el sistema sepa en qué fondo está Rodrigo de verdad,
que es una complicación que no vale lo que cuesta.

El asunto lleva la instrucción completa, porque se lee desde la pantalla
bloqueada del teléfono. El cuerpo dice a qué fondo, cuántas de las cinco medias
lo indican, el valor cuota del día y cuándo quedaría materializado. **No
recomienda nada.**

### Lo que tiene que aguantar, que es lo que decide si sirve

**Un aviso que no llega es peor que no tener aviso**, porque él va a estar
confiando. Entonces:

- Si el correo falla, **la corrida sale en rojo** y reintenta al día siguiente.
- La fila del día queda marcada `fallo`, y se commitea igual: es el único rastro
  de que hubo un cambio que no se recibió.
- **El informe del viernes muestra la posición en vigor y desde cuándo.** Si los
  tres correos se perdieron, el viernes lo agarra.

**Un aviso falso por dato malo** es el otro modo de falla. Además de la guardia
que ya existe, si el valor cuota del fondo agresivo se mueve más de **8% en un
día** el aviso no dispara y la corrida sale en rojo. Nunca pasó en 24 años; si
pasa, es dato malo antes que mercado.

Y al revés: **la falta de aviso nunca tumba el registro ni el informe.** Es el
defecto que ya nos costó un informe entero con FRED.

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

## Cómo se sabe si esto se murió

**Un cron de GitHub Actions no muere haciendo ruido.** Los flujos programados
se deshabilitan solos cuando el repositorio queda quieto, y una corrida que deja
de dispararse no manda correo, no deja rojo y no deja rastro: el archivo
simplemente deja de crecer. Es exactamente la falla silenciosa que este proyecto
vino a eliminar.

**El aviso va donde Rodrigo ya mira: el informe del viernes.** El panel de salud
dice cuántas filas lleva el registro y de qué fecha es la última, aunque esté
todo bien —ahí el número *es* la información—, y se enciende si la última fila
tiene más de **siete días**.

Siete y no tres, que es lo natural de pedir, porque está medido: el hueco más
largo entre dos días de cotización consecutivos desde 2021 es de **seis**
—Fiestas Patrias de 2024, del 17 al 23 de septiembre— y el percentil 99 es
cuatro. Con tres días la alarma estaría roja cada septiembre y cada Navidad, y
**una alarma que suena por el calendario deja de ser una alarma.**

## Qué se podrá preguntarle, y cuándo

Cuando haya ocurrido una caída de las que importan —no un susto de dos
semanas— el archivo permite responder, sin recalibrar nada:

0. **Cuál media paga menos peaje en calma.** Ésta se contesta primero y sin
   crisis: es la única que empieza a acumular evidencia desde el primer mes.
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

Los estudios que llevaron hasta acá están en `research/afp_*`. **Esos directorios conservan el nombre viejo a propósito:** son el registro de lo que se midió y cuándo, y renombrarlos reescribiría esa historia. El que explica
por qué se congela es `research/afp_2027/`.

## Qué reemplazó, y por qué no conviven

**Ahorro Generacional reemplazó a la Estrategia Horizonte el 23-09-2026.** No
es que convivan: las dos contestan exactamente la misma pregunta —en qué fondo
está parada la plata previsional— y **dos estrategias contestando lo mismo es un
valor con más de una casa.** El día que discrepen, y van a discrepar, no hay
regla que diga cuál manda y el informe estaría publicando dos respuestas
contradictorias en el mismo correo.

Horizonte perdió por su auditoría, no por su idea: ventana publicada que
arrancaba en 2012 sin razón escrita y dejaba fuera la crisis, registro hacia
adelante vacío —once publicaciones sin un solo cambio—, y backtest que la dejaba
3,6 años quieta en Fondo A, que es el Fondo A con otro nombre.

**Su código no se borró.** Está en `src/horizonte.py` con la nota de por qué se
retiró: borrarlo borraría la auditoría que la retiró, y esa auditoría es lo
único que explica la decisión dentro de un año.

Y el premio de sacarla vale más que la sección: **se llevó con ella la única
consulta a FRED del informe del viernes**, que es la fuente externa que ya tumbó
el correo y el commit una vez.
