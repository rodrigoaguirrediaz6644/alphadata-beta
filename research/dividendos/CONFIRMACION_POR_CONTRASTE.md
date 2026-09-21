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

## El método

No sirve el que ya existe. `localizar_fecha_ex` busca la rueda cuya caída
coincide con la que el monto predice, y **declina cuando el dividendo es más
chico que dos veces la tolerancia**: el precio no puede decir nada. Los seis
estaban por debajo de ese umbral, que es por lo que entraron por convención. La
prueba nula ya había mostrado por qué: 82% de falsos positivos, 100% en los
dividendos chicos.

El que sí funciona es **el contraste entre las dos fuentes de precio**. El
relleno de investing.com sobrescribió las ruedas en que las dos series
discrepaban. Si una fuente aplica la caída y la otra todavía no, la discrepancia
es **exactamente el factor del dividendo, constante durante varias ruedas
seguidas**. Eso no se confunde con ruido: el ruido no es constante.

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

## Un hallazgo lateral, que no se toca todavía

El escalón **empieza en la fecha declarada**, no cinco ruedas antes. En cuatro
de los cinco casos la primera rueda sobrescrita es exactamente la fecha
declarada, y el escalón dura hasta que la fuente rezagada alcanza a la otra.

La convención hace lo contrario: coloca la fecha ex **cinco ruedas antes** de la
declarada. Si el contraste tiene razón, las fechas ex por convención están
corridas unas diez ruedas.

**No se cambió nada**, por dos razones. La primera es que son cinco casos y la
convención se calibró sobre 113. La segunda es que **no mueve ningún número
publicado hoy**: el factor se aplica a los precios anteriores a la fecha ex, y
ninguna posición viva entró dentro de las cinco ruedas en disputa, así que su
precio de entrada lleva el mismo factor con cualquiera de las dos fechas.

Queda anotado para cuando se revisen las fechas ex, que es otro trabajo.
