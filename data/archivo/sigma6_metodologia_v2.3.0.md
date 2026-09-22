# Sigma-6 — especificación al retirarse, 22-09-2026

Se conserva tal como estaba el día en que salió de la asignación. No se
reescribe: si alguna vez vuelve una señal de corredora que aporte, ésta es
la especificación de la que se parte.

## 1. Sigma-6

Sigma-6 es la estrategia anteriormente evaluada como Credicorp Momentum. Combina la recomendación fundamental de Credicorp Capital con una confirmación objetiva de momentum.

### Datos y señales

- Única corredora utilizada: **Credicorp Capital**.
- Se conserva sólo la recomendación más reciente conocida para cada acción.
- Comprar, sobreponderar, outperform y superior al mercado equivalen a `+1`.
- Mantener y neutral equivalen a `0`.
- Vender, subponderar, underperform e inferior al mercado equivalen a `-1`.
- Una recomendación caduca después de 365 días.
- Una fila sin acción explícita se descarta.
- Conflictos de una misma acción y fecha se envían a revisión manual.

### Indicador

`Momentum12-1 = PrecioAjustado[t-21] / PrecioAjustado[t-252] - 1`.

Se requieren al menos 252 sesiones de historia y el momentum debe ser estrictamente positivo.

**El precio ajustado debe estar estrictamente sobre la SMA de 200 sesiones**,
la misma condición que usan Delta-12 y Gamma-6. Entró el 21-09-2026: hasta
entonces Sigma-6 era la única estrategia accionaria sin ninguna condición que
mirara el precio de hoy, y `Momentum12-1` salta las últimas 21 ruedas, así que
una caída del último mes le era invisible. Es también condición de permanencia.
Medición en `research/sma200_sigma6/`.

### Entrada

Una acción entra sólo cuando se cumplen simultáneamente:

1. La última recomendación vigente de Credicorp tiene valor `+1`.
2. `Momentum12-1 > 0`.
3. Existen precios ajustados válidos y al menos 252 sesiones de historia.

El cálculo se realiza al cierre de la última sesión bursátil de cada semana. La ejecución simulada ocurre a la apertura de la sesión bursátil siguiente.

### Tamaño

- Ponderación igual entre todas las acciones elegibles.
- Máximo 10% por acción.
- Si hay menos de diez posiciones, el capital que no puede asignarse queda en caja.
- Si hay más de diez posiciones, se distribuye el 100% en partes iguales mientras ningún peso exceda 10%.
- No se permiten ventas cortas ni apalancamiento.
- No existe límite sectorial hasta contar con un mapa sectorial histórico confiable.

### Salida

Se vende en la siguiente apertura cuando ocurre cualquiera de estos eventos:

- La recomendación vigente de Credicorp pasa a `0` o `-1`.
- `Momentum12-1 <= 0`.
- **`PrecioAjustado <= SMA200`.**
- La recomendación caduca.
- Los precios son inválidos o están vencidos.

No se utilizan precio objetivo, stop-loss intraperiodo ni decisiones discrecionales por noticias.

**Sigma-6 no tiene tope de tenencia: rota por señal, no por calendario.** El
tope de 365 días salió el 21-09-2026. La consecuencia de carácter conviene
decirla: la estrategia puede sostener un nombre por años. BCI viene desde el
11-10-2024 y queda corriendo hasta que se caiga alguna condición de precio o
caduque su recomendación. El único reloj que queda es el de la caducidad.

### Costos

Se utiliza la tarifa Trii/Racional:

- Comisión variable antes de IVA: 0,15% del monto transado.
- IVA: 19%.
- Comisión efectiva: **0,1785%** sobre entradas, salidas y rebalanceos.
- Tarifa mínima: $1.990 cuando corresponda a operaciones de monto bajo.

Los backtests independientes del capital aplican 0,1785% al monto transado y no aplican el mínimo de $1.990. Las simulaciones con capital definido deben utilizar el mayor entre la comisión variable y la tarifa mínima cuando corresponda.

### Guardia de vigencia de las recomendaciones

Si en una revisión la recomendación más reciente del proveedor tiene **más de
90 días**, Sigma-6 **no abre posiciones nuevas**. El informe lo dice, y la
estrategia se reanuda sola en cuanto entren recomendaciones nuevas.

> **La regla, en su forma corta: un insumo viejo no puede agregar riesgo, pero
> uno fresco sí puede quitarlo.**

El principio es **no actuar sobre el dato que falta**, y lo que falta son las
recomendaciones: los precios siguen llegando. De ahí sale qué se suspende y qué
no.

| condición | durante la guardia |
|---|---|
| La recomendación baja de nota a `0` o `-1` | **suspendida** |
| La recomendación caduca a los 365 días | **suspendida** |
| Abrir una posición nueva | **suspendido** |
| `Momentum12-1 <= 0` | **sigue viva** |
| `PrecioAjustado <= SMA200` | **sigue viva** |

No se abre nada porque abrir sobre recomendaciones de tres meses es apostar
sobre información que ya no se confirma. Sí se cierra por precio, y hay un
argumento concreto además del principio: **la SMA200 se encendió precisamente
porque Sigma-6 era la única estrategia sin salida que mirara el precio de hoy.**
Suspenderla durante la guardia reabriría ese hueco justo en el periodo en que
nadie está mirando.

Sin la guardia, las posiciones se irían soltando una a una a medida que sus
recomendaciones cumplen 365 días, y esa liquidación sería un artefacto de que
nadie cargó el archivo, no una señal.

**Consecuencia:** durante una guardia larga la cartera sólo puede encoger hacia
caja. Es la dirección conservadora, y la regla de los dos disparos trae la
decisión de vuelta antes de que llegue lejos.

El umbral no está ajustado a la muestra: entre 2021 y 2026 el hueco más largo
entre recomendaciones fue de **29 días**, así que la guardia nunca se habría
activado y no cambia ninguna serie publicada.

### Límite de concentración

Ninguna posición puede pasar del **25% del valor de su propia pieza** —6,25%
del capital total, porque cada pieza es un cuarto—. Se revisa en cada revisión
de la estrategia; al pasarse se recorta hasta 25% exacto y el excedente queda
en la caja de la pieza. Aplica a Sigma-6, Delta-12 y Gamma-6, y **no al oro**,
que es 100% de su pieza por diseño. Entró el 21-09-2026. Es un límite de cola,
no una optimización: ver `POLITICA_REBALANCEO.md`.

