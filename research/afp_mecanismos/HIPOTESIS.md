# Hipótesis, escritas antes de medir

Dos mecanismos, dos predicciones, **cero parámetros que ajustar**. La prueba es
si el mecanismo explica lo que ya pasó. Si no lo explica en los episodios que
hay, el mecanismo es falso y se cierra.

Commit propio y anterior a cualquier resultado.

---

## Cómo se definen los episodios

Todo retroceso del **Fondo A** de más de 10% desde su máximo, sobre la serie
diaria de valor cuota, 2002-2026. Para cada uno: fecha del máximo previo, fecha
del fondo, y la ventana entre ambas.

Es la misma regla mecánica de los estudios anteriores. **No se elige ninguno a
mano.**

## H1 — El colchón cambiario dice *cuánto vale* salirse, no *si* salirse

### El mecanismo

El Fondo A tiene del orden de 60-70% de su valor en moneda extranjera, y el peso
chileno es moneda de materias primas: se debilita cuando los activos de riesgo
caen. Entonces **el Fondo A recibe amortiguación automática en cada crisis**.

Lo maté mal en el estudio anterior: lo probé como señal binaria de alerta —«el
colchón desapareció, sal»— y no aportó nada. Estaba mal planteado. El colchón no
es una señal de salida: **es el precio de la salida.**

> Cuando el peso se debilita durante la caída, lo que te ahorras cambiándote es
> poco, porque el Fondo A ya se está amortiguando solo. Cuando el peso se queda
> firme mientras la bolsa cae, el Fondo A está expuesto entero y cambiarse vale
> mucho más.

### Lo que se mide

| | |
|---|---|
| **beneficio de haberse cambiado** | retorno del Fondo E menos retorno del Fondo A en la ventana del episodio |
| **estado del peso** | retorno de USDCLP en la misma ventana. Positivo = el peso se debilita = hay colchón |

### La predicción, antes de mirar

**Correlación negativa entre el estado del peso y el beneficio de cambiarse.**

Los episodios donde el peso se debilitó mucho deben ser los episodios donde
cambiarse aportó menos; los episodios donde el peso se quedó firme, donde aportó
más.

### Qué contaría como confirmación

Con siete episodios, una correlación de rangos de Spearman con **|rho| ≥ 0,75**
alcanza p < 0,05. Se reporta rho, p, y **la tabla completa de los siete
episodios**, para que se vea si la relación es monótona o la arrastra un punto.

**Si rho es positivo o cercano a cero, el mecanismo es falso y se cierra.**

## H2 — Los emergentes explican por qué el Fondo A cae distinto de la bolsa global

### El mecanismo

Las AFP tienen alrededor de un tercio de su riesgo en emergentes —medido en la
descomposición por factores: beta 0,226 al MSCI Emerging contra 0,419 al MSCI
World, con 35% de la varianza—. Ningún estudio lo probó.

> Si la exposición emergente es lo que hace que el Fondo A caiga distinto de la
> bolsa desarrollada, entonces una señal calculada sobre un índice desarrollado
> llega tarde o llega mal justo cuando más importa.

### Lo que se mide

| | |
|---|---|
| **lo explicado** | beta del Fondo A al MSCI World en pesos × retorno del MSCI World en pesos en la ventana |
| **el residuo** | retorno real del Fondo A menos lo explicado |
| **el diferencial emergente** | retorno de emergentes menos retorno de desarrollados, en dólares, en la ventana |

La beta es **una sola, estimada sobre toda la muestra**, no una por episodio. No
se ajusta nada dentro del episodio.

### La predicción, antes de mirar

**Correlación positiva entre el residuo y el diferencial emergente.**

Los episodios donde el Fondo A cayó *más* de lo que explicaba la bolsa
desarrollada —residuo negativo— deben ser los episodios donde los emergentes
cayeron *más* que los desarrollados —diferencial negativo—.

### Qué contaría como confirmación

Lo mismo: Spearman sobre los episodios con datos, |rho| ≥ 0,75 para p < 0,05, y
la tabla completa.

**Limitación conocida y escrita antes:** la serie de emergentes que hay
—`EEM`— empieza en abril de 2003, así que **el episodio de 2002 queda fuera de
H2**. Se dice cuántos episodios quedan y no se rellena con nada.

## La regla que separa esto de otro backtest

**Primero se verifica que el mecanismo explique lo que ya pasó, sin tocar un
parámetro. Sólo si lo explica se construye algo encima.**

No se prueba ninguna estrategia en este documento. No se ajusta ningún umbral.
No se busca la ventana que funcione. Son dos correlaciones sobre siete
observaciones, decididas de antemano.
