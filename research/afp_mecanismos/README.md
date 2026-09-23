# Los tres puntos: el Fondo E, los dos mecanismos, y el tope de traspasos

Hipótesis congeladas en `HIPOTESIS.md`, en un commit anterior a cualquier
resultado. Investigación pura: no toca producción ni el informe.

**El adjunto con el código de la regla diaria no llegó a esta sesión.** Lo que
sigue se hizo con mis propios datos, y donde reconstruyo la regla diaria lo digo.

---

## 1. El Fondo E: mis series están completas

| | Cuprum | Habitat |
|---|---|---|
| Fondo A | 8.817 datos, hasta 2026-09-20 | 8.817 |
| Fondo B | **8.817**, hasta 2026-09-20 | 8.817 |
| Fondo C | 16.548 | 16.548 |
| Fondo D | 8.817 | 8.817 |
| **Fondo E** | **9.700 datos, 2000-03-01 a 2026-09-20** | 9.700 |
| días calendario ausentes en E | **0** | **0** |

**El truncamiento está en los archivos de la otra sesión, no en los míos.** Mi
fuente es `collabmarket/data_afp`, que distribuye el valor cuota de la
Superintendencia y trae los cinco fondos completos. Dejé el archivo exportado en
`valor_cuota_completo_cuprum.csv` para que se pueda usar directo.

### La pregunta que abriste: de dónde salieron −7,8% y −4,12%

Los dos números son míos, los dos reproducen, y **la diferencia es la definición
de caída**, no un dato faltante:

| | Fondo A | Fondo E |
|---|---:|---:|
| contra su máximo previo | **−26,48%** | **−7,80%** |
| contra el 25-02-2020 | −24,87% | −3,68% |
| febrero-marzo, mensual | −19,60% | **−4,12%** |

El −7,80% salió de la tabla de episodios, que mide **contra el máximo previo** —
la misma definición para las dos columnas, así que −26,48% y −7,80% son
comparables entre sí. El −4,12% salió de la tabla mensual de otro estudio.

**Los dos estudios usaron convenciones distintas y eso no estaba dicho.** Queda
dicho ahora.

## 2. Los dos mecanismos

### Dos errores míos antes de los resultados

**El primero invalidó H2 en la primera corrida.** Estimé la beta del Fondo A al
mercado con alineación contemporánea y salió **−0,000**: es mi propio hallazgo
mordiéndome, porque el valor cuota del día *t* refleja el mercado del día *t−1*.
Con el mercado rezagado un día la beta es 0,201.

**El segundo.** El proveedor entrega dos precios imposibles del dólar —5,46 el
10-04-2014 y 5,00 el 22-12-2016—. Sin limpiarlos, la desviación estándar del
mercado sale **180% diaria** y la beta colapsa. El pipeline ya tiene una guardia
para esto; el estudio no la tenía.

### El resultado pre-registrado: los dos refutados

**H1 — el colchón dice cuánto vale salirse.** Predicción escrita antes:
correlación **negativa** entre el estado del peso y el beneficio de cambiarse.

| episodio | días | Fondo A | Fondo E | beneficio | peso |
|---|---:|---:|---:|---:|---:|
| 2021-12 a 2023-03 | 443 | −14,37% | +21,75% | +36,12% | **−7,26%** |
| 2015-11 a 2016-02 | 83 | −11,04% | +1,12% | +12,16% | −1,48% |
| 2006-05 a 2006-06 | 36 | −11,72% | +0,34% | +12,06% | +1,77% |
| 2011-01 a 2011-10 | 272 | −17,42% | +9,01% | +26,42% | +2,91% |
| 2020-02 a 2020-03 | 29 | −26,48% | −3,36% | +23,11% | +7,08% |
| 2007-10 a 2009-03 | 490 | −44,00% | +13,23% | **+57,23%** | **+23,83%** |

**Spearman = +0,314, p = 0,544.** Signo al revés del predicho. En Habitat,
+0,429 con p = 0,337.

**H2 — los emergentes explican el residuo.** Predicción: correlación
**positiva**. **Spearman = −0,371, p = 0,468.** También al revés.

### Pero mi prueba no podía confirmar nada

Fijé el criterio en |rho| ≥ 0,75 sobre seis o siete episodios. Simulando un
mecanismo **verdadero** de cada fuerza, ¿cuántas veces lo habría detectado?

| rho verdadero | n=6 | n=12 | n=20 |
|---:|---:|---:|---:|
| 0,30 | **9%** | 2% | 1% |
| 0,40 | **12%** | 5% | 1% |
| 0,60 | 22% | 18% | 11% |
| 0,75 | **36%** | 42% | 42% |

**Con seis episodios, un mecanismo perfecto se detectaba 36% de las veces y uno
moderado el 12%.** El criterio que yo escribí exigía prácticamente un mecanismo
sin ruido. Para detectar rho = 0,37 con 80% de potencia harían falta **unas 56
observaciones**, y hay seis.

**Así que «refutado» no se sostiene, y «confirmado» tampoco.** Lo que se
sostiene es: **la prueba por episodios no puede resolver esto, en ninguna
dirección.** El diseño era mío y estaba mal dimensionado.

### Y hay algo más, etiquetado como lo que es

Mirando la tabla se ve que **la severidad arrastra las dos variables de H1**: el
episodio con mayor beneficio de cambiarse (+57,23%, 2008) es también el de mayor
debilitamiento del peso (+23,83%). Una crisis profunda debilita más el peso *y*
hace que cambiarse aporte más en términos absolutos.

Normalizando por severidad —cuánto aporta cambiarse **por cada punto que cae el
Fondo A**—:

| episodio | cae el A | peso | beneficio por punto |
|---|---:|---:|---:|
| 2021-12 | −14,37% | −7,26% | **2,51×** |
| 2015-11 | −11,04% | −1,48% | 1,10× |
| 2006-05 | −11,72% | +1,77% | 1,03× |
| 2011-01 | −17,42% | +2,91% | 1,52× |
| 2020-02 | −26,48% | +7,08% | **0,87×** |
| 2007-10 | −44,00% | +23,83% | 1,30× |

**Los dos signos se dan vuelta al predicho:** H1 pasa a −0,371 y H2 a +0,371.

**Esto no reemplaza la prueba pre-registrada y no lo voy a presentar como que el
mecanismo apareció.** Es una segunda mirada decidida después de ver el
resultado, con p = 0,47 y seis puntos. Lo que sí permite decir es que **la
dirección del mecanismo no está descartada**, y que el instrumento para probarlo
no es la tabla de episodios.

### Dónde sí habría que probarlos

En el random forest, con datos diarios, `fx_corr` y `em_rel` salieron como las
dos variables más usadas de veinticinco (0,163 y 0,134). Eso son miles de
observaciones, no seis. **Si los mecanismos se van a probar, tiene que ser a esa
granularidad** — con una hipótesis por escrito sobre el signo del efecto
continuo, no sobre el orden de seis episodios.

## 3. El tope de dos traspasos al año

### Estado del proyecto

**Es de diciembre de 2020, no reciente, y no prosperó.** Lo ingresó el gobierno
en el contexto de los traspasos masivos de esos años, que movían del orden de
**US$5.000 millones por episodio** con efecto sobre el tipo de cambio y los
precios de los activos. Proponía dos traspasos por año calendario y un plazo
máximo de 30 días.

La evidencia de que no está vigente es directa: hoy las AFP publican cambios sin
costo y permiten repartir el saldo entre dos fondos, y tú mismo confirmas que no
hay límite. **Han pasado cinco años y medio.**

Pero el precedente es real y va en la dirección que planteaste: **cuando los
traspasos masivos empezaron a mover el mercado, el Estado intentó limitarlos.**
No fueron las AFP: fue Hacienda.

### Y si prosperara: no degrada, mata

Medido sobre las reglas diarias, con el rezago real:

| regla | tope | anual | **peor caída** | cambios/año |
|---|---|---:|---:|---:|
| tendencia 100d | sin | +10,70% | **−10,82%** | 18,0 |
| tendencia 100d | **2/año** | +9,77% | **−40,43%** | 2,0 |
| tendencia 50d | sin | +9,63% | −15,10% | 30,0 |
| tendencia 50d | **2/año** | +9,80% | **−39,70%** | 2,0 |
| random forest | sin | +9,54% | −23,80% | 23,3 |
| random forest | **2/año** | +7,98% | −26,54% | 2,1 |
| Fondo A | — | +9,07% | −26,06% | 0 |

**El retorno casi no se mueve. La protección se evapora entera:** de −10,82% a
−40,43%, que es prácticamente la caída completa del Fondo A.

Tiene sentido mecánico: con dos cambios al año puedes salir una vez y volver una
vez. Una caída que exige estar afuera en tres tramos separados no se puede
manejar. **Y la protección es el único producto de esta estrategia.**

### Y una cosa que corrobora a la otra sesión

`tendencia 100d` evaluada a diario da **+10,70% con −10,82% de caída** contra
+9,07% y −26,06% del Fondo A. **Le gana a mi random forest en las dos cosas**,
con menos cambios y sin modelo.

Eso coincide con lo que reportaste: **evaluar todos los días en vez de una vez
al mes es el arreglo, y es estructural y barato.** Mi estudio mensual tenía el
mismo privilegio del calendario que el tuyo.

## Lo que queda pendiente y no pude hacer

**Pedirle a Cuprum por escrito el tiempo real de un cambio y si cobran.** No
puedo enviar esa consulta. Es una gestión tuya y cierra el supuesto del que
cuelga todo: medí 4 días hábiles contra el historial, y la sensibilidad del
random forest muestra que entre 6 y 8 días corridos el resultado cambia de
signo.

Conviene preguntar tres cosas concretas:

1. **Cuántos días hábiles** transcurren entre la solicitud y quedar en el otro
   fondo, y **con qué valor cuota** se materializa.
2. **Si cobran** por el cambio, y desde qué número de cambios al año.
3. **Qué pasa cuando hay volumen inusual de solicitudes** — la norma permite
   extender el plazo porque la AFP sólo puede traspasar 5% del patrimonio por
   día. Es decir, el plazo se alarga justo cuando la señal valdría algo.

---

Reproducir: `PYTHONPATH=. python research/afp_mecanismos/estudio.py`

Fuentes:
[Diario Financiero — el proyecto de diciembre de 2020](https://www.df.cl/mercados/pensiones/gobierno-ingresa-proyecto-que-limita-el-cambio-de-fondos-en-las-afp) ·
[Compendio de Pensiones — Cambio y Asignación de Fondos](https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3623.html) ·
[AFP Capital — cambio de fondo](https://ww2.afpcapital.cl/Afiliado/Multifondos/Paginas/Cambio-de-Fondo.aspx)
