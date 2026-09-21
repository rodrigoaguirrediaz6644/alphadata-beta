# Confirmar dividendos por contraste entre fuentes

## El hueco que se nos pasó

Los 127 dividendos fechados por convención se dejaron así con un argumento
explícito: **salen de la ventana del momentum 12-1 en un año y dejan de
importar.** Eso sigue siendo cierto para la señal.

**No para el número publicado.** La variación de una posición se calcula sobre
el ajustado desde la entrada hasta hoy, y al quitar el tope de tenencia las
posiciones pueden correr años: esa ventana creció con ellas. **Envejecen fuera
de la señal, no fuera de la pantalla.** BCI viene desde el 11-10-2024 y su
+146,4% descansa sobre dos dividendos que nunca se habían confirmado.

## El alcance se define solo

No hay que rehacer los 127: sólo los que caen **dentro de la ventana de
tenencia de una posición viva**. Al 21-09-2026 son **seis**, sobre cuatro
instrumentos.

## El método, y por qué es mejor instrumento que el que reemplaza

**El viejo buscaba una caída de un día**, y declinaba justo cuando el dividendo
era chico —`localizar_fecha_ex` exige que el monto sea más de dos veces la
tolerancia—. Es decir, declinaba exactamente en el caso en que el ruido diario
tapa la señal, que es también el caso más frecuente. La prueba nula ya lo había
mostrado por el otro lado: 82% de falsos positivos, 100% en los dividendos
chicos.

**El contraste no busca una caída: busca una discrepancia que se mantiene
constante varias ruedas seguidas.** El relleno de investing.com sobrescribió las
ruedas en que las dos series discrepaban; cuando una fuente aplica la caída y la
otra todavía no, la discrepancia es el factor del dividendo, idéntico rueda tras
rueda hasta que la rezagada alcanza a la otra.

**El ruido no hace eso.** Dos series con errores independientes discrepan de
forma distinta cada día; un escalón plano de tres a cinco ruedas que además
coincide con el monto declarado no se produce por azar. Por eso errores de 0,003
a 0,329 puntos son confirmación y no coincidencia: no es que el número esté
cerca una vez, es que está igual de cerca cinco veces seguidas.

Y el instrumento no depende del tamaño del dividendo, que es lo que lo hace
mejor: un dividendo de 0,25% deja un escalón de 0,25% igual de plano que uno de
6%.

### Medido: sobre los mismos dividendos, el contraste es más preciso

Cinco dividendos quedaron al alcance de los dos métodos. En los cinco el
contraste queda más cerca del monto declarado:

| | esperada | por precio | error | por contraste | error |
|---|---|---|---|---|---|
| BSANTANDER | −5,600% | −3,779% | 1,82 pp | **−5,386%** | **0,21 pp** |
| CHILE | −7,633% | −6,158% | 1,47 pp | **−7,373%** | **0,26 pp** |
| QUINENCO 2025 | −6,022% | −5,203% | 0,82 pp | **−6,005%** | **0,02 pp** |
| QUINENCO 2026 | −7,933% | −8,715% | 0,78 pp | **−8,061%** | **0,13 pp** |
| VAPORES | −7,415% | −6,964% | 0,45 pp | **−7,376%** | **0,04 pp** |

Entre cuatro y diez veces más preciso, y la razón es estructural: el método por
precio mide el retorno crudo de un día, que trae **la caída del dividendo más el
movimiento del mercado de esa jornada**. El contraste mide la razón entre dos
fuentes del mismo día, y ahí el movimiento del mercado se cancela.

Las confirmaciones por precio que ya existían **no se sobrescribieron**: son
evidencia directa y se conservan como están.

## Resultado: cinco de seis

| instrumento | fecha ex | monto | esperada | observada | error |
|---|---|---|---|---|---|
| BCI | 28-03-2025 | 1.110,00 | −3,2754% | **−3,1715%** | 0,104 pp |
| BCI | 26-03-2026 | 1.500,00 | −2,5253% | **−2,4631%** | 0,062 pp |
| ITAUCL | 08-04-2026 | 1.187,27 | −5,9031% | **−5,5740%** | 0,329 pp |
| MALLPLAZA | 23-03-2026 | 40,00 | −1,0499% | **−1,0389%** | 0,011 pp |
| PARAUCO | 17-04-2026 | 44,39 | −1,0311% | **−1,0344%** | 0,003 pp |

En los cinco el escalón es constante a lo largo de cinco o seis ruedas
consecutivas y coincide con el monto declarado. Quedan marcados en
`data/dividendos.csv` como `confirmada por contraste entre fuentes`.

### El que no confirma: MALLPLAZA, 03-09-2026

Su ventana cae **dentro del tramo del feed congelado**: el `valor_anterior` es
3.950,00 en las veintitrés ruedas reparadas, que es el valor repetido. Ahí la
reparación está arreglando el congelamiento, no revelando un dividendo, y no hay
ningún escalón constante. **No se puede confirmar con este método y se queda
como estaba.** Es el único de los seis que sigue sosteniendo un número publicado
sin respaldo de precio: los $30 de MALLPLAZA dentro de sus $70 de dividendos
cobrados.

## El solape completo: 101 de 112, y la convención queda confirmada

Con cinco casos dije que el escalón empezaba en la fecha declarada y que, por lo
tanto, las fechas ex por convención podían estar corridas unas diez ruedas.
**Eso era falso, y el error fue mío al leer**: en el script llamé «declarada» a
la columna `fecha_ex`. El escalón empezaba en la fecha ex de la convención, que
es justo lo que la convención predice.

Corrido sobre **los 112 dividendos del solape de las dos fuentes**, con 101
escalones aceptados, el resultado es el contrario del que reporté:

| dónde empieza el escalón | casos |
|---|---|
| contra la fecha **declarada** | mediana **−5 ruedas**; ninguno de 101 empieza en ella o después |
| contra la fecha **ex de la convención** | mediana **0 ruedas** |

| diferencia contra la convención | casos |
|---|---|
| 0 ruedas | 58 |
| 1 rueda | 34 |
| 2 ruedas | 8 |
| 3 ruedas | 1 |

**92 de 101 calzan exacto o a una rueda.** La convención de «cinco ruedas antes
de la declarada» está bien calibrada, y la hipótesis de que pudiera haberse
calibrado contra el mismo proveedor cuyo rezago venía a corregir queda
descartada: el contraste usa la **otra** fuente y llega al mismo lugar.

### Lo que sí queda, y es chico

Nueve dividendos empiezan dos o tres ruedas después de la fecha ex asignada:
CENCOSUD, CONCHATORO, COPEC, ILC, INDISA, LTM, QUINENCO, RIPLEY y SMSAAM. Ahí el
contraste da una fecha mejor evidenciada que la convención.

**No se movió ninguna fecha.** Corregirlas cambia la serie ajustada y con ella
el momentum 12-1, la SMA200, el RSI y los retornos diarios del NAV, que es
precisamente el argumento por el que esto había que medirlo y no archivarlo. La
decisión está disponible y el desglose por dividendo queda en el propio
`data/dividendos.csv`.

## Estado de la tabla

| origen | filas |
|---|---|
| confirmada por contraste entre fuentes | **96** |
| confirmada por el precio | 7 |
| fecha por convención | 31 |

**103 de 134 confirmados**, contra 7 antes de esto.

Los 31 que siguen por convención están fuera del solape de las dos fuentes
—antes de 2025, o instrumentos que el relleno no cubrió— así que no hay con qué
contrastarlos. Once del solape no dieron escalón aceptable y se quedan como
estaban: AGUAS-A, ANDINA-B, BESALCO, CHILE, FALABELLA, FORUS, MALLPLAZA, SMU
(dos), SQM-B y VAPORES.

## MALLPLAZA del 03-09-2026: la fuente primaria no cierra el caso

Es el único de los seis que sostienen posiciones vivas que el contraste no puede
confirmar, porque su ventana cae dentro del tramo del feed congelado.

Mallplaza publica su historial de dividendos. Dice **septiembre de 2025 por
$28,000**, abril de 2025 por $21,530 y diciembre de 2024 por $22,000. Pero
**no tiene ninguna entrada de 2026** —termina en septiembre de 2025— y tiene un
hueco visible entre octubre de 2022 y abril de 2024. **No es una lista completa
y no sirve como referencia definitiva.**

Así que **no confirma ni desmiente los $30**. Lo que aporta:

- **La magnitud calza**: $28 en septiembre de 2025 contra ~$30 en septiembre de
  2026.
- **El calendario también**: reparte en abril y en septiembre, consistente con
  las dos fechas ex que el sistema le tiene.

Queda **sin respaldo de precio pero corroborado en magnitud y calendario**, y
con una dirección concreta a la que volver cuando publiquen 2026.

Fuente: <https://corporativo.mallplaza.com/en/stock-info/dividend-history/>
