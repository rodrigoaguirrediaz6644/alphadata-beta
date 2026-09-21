# Parte 1 del protocolo: Sigma-6 sin el filtro de corredora

La pregunta no es cuál corredora es mejor. Es **si aporta algo la recomendación
de una corredora por encima de lo que ya aporta el momentum.**

## Las reglas, fijadas antes de mirar

- Mismo universo, misma revisión semanal W-FRI, mismo tope de 10% por posición,
  misma SMA200, mismas salidas. **Lo único que cambia es el filtro de
  corredora.**
- La variante nula elige **las diez de mayor momentum 12-1 entre las elegibles
  por las condiciones de producción**. El top 10 no es un parámetro nuevo:
  reproduce la forma que Sigma-6 tiene cuando el filtro de corredora ata. Sin
  él, la nula tendría cuarenta posiciones al 2,5% y no sería comparable en
  concentración.
- Corte fijado por el protocolo: **2021-07 a 2023-12** y **2024-01 a 2026-07**.
- Misma política de pesos y misma comisión, con el mínimo real de $1.990 sobre
  $5.000.000.
- Los datos anteriores a 2025 no están reparados. Los defectos conocidos afectan
  por igual a las dos variantes, así que **la comparación es válida aunque los
  niveles absolutos no sean exactos**: es un estudio relativo y ahí el defecto
  común se cancela.

### Una construcción descartada, porque el resultado dependía de ella

La primera versión fabricaba una recomendación semanal para el top 10 y dejaba
que `sigma6` filtrara. **No servía**: una recomendación vale 365 días, así que
la unión de los top 10 de un año daba **15,5 posiciones promedio contra 7,8**
de la variante con Credicorp. La nula ganaba en las dos mitades, pero con el
doble de nombres —otra estrategia, no una comparación—. Se detectó comparando
los conteos de posiciones, no los retornos.

La versión corregida deja la nula en **9,3 posiciones promedio contra 7,8**.

## Resultado: no se distingue

Retorno anual y peor caída:

| tramo | con Credicorp | sin corredora |
|---|---|---|
| completa | +17,15% · −12,9% | +20,04% · −20,9% |
| **1ª mitad** (2021-07/2023-12) | **+6,84%** · −11,3% | +5,71% · −20,9% |
| **2ª mitad** (2024-01/2026-07) | +28,26% · −12,9% | **+36,41%** · −10,9% |

**El orden se da vuelta entre mitades.** Con Credicorp gana la primera por 1,14
puntos anuales; la nula gana la segunda por 8,14. Por el protocolo de este
proyecto, eso es un empate: **no se puede distinguir.**

La peor caída también se da vuelta: Credicorp es mejor en la primera mitad
(−11,3% contra −20,9%) y peor en la segunda (−12,9% contra −10,9%).

Y la ventaja de la nula en la ventana completa —+2,9 puntos anuales— **no es
evidencia**: viene entera de la segunda mitad. Tomarla sería el error que las
dos submuestras existen para evitar.

### Lo que sí se puede afirmar

**No hay evidencia de que la recomendación de corredora agregue retorno por
encima del momentum solo.** Eso no prueba que no aporte; prueba que esta
medición no lo detecta.

La asimetría importa: el filtro de corredora es **la única dependencia manual
que le queda al sistema**, y la carga de justificarla estaba de su lado. No la
superó.

La predicción escrita antes de medir —«la prueba nula queda dentro del
ruido»— se cumple.

## La consecuencia que el protocolo anticipaba, medida

Si sin corredora Sigma-6 fuera Delta-12 con revisión semanal, las dos deberían
tener casi las mismas posiciones. Solape de Jaccard con la cartera de Delta-12,
en 61 revisiones mensuales (1 = idénticas, 0 = disjuntas):

| | mediana | media |
|---|---|---|
| Sigma-6 **sin corredora** | **0,42** | 0,45 |
| Sigma-6 **con Credicorp** | 0,25 | 0,27 |

Sin el filtro, el solape con Delta-12 **casi se duplica**, pero **no llega a
ser la misma cartera**: 0,42 de mediana significa que de cada diez nombres
distintos comparten unos cuatro. Las separa la frecuencia de revisión —semanal
contra mensual— y que Delta-12 exige además RSI≤65 y liquidez.

Así que la afirmación exacta no es «sería Delta-12», sino que **sin corredora
las dos piezas se parecen bastante más**, y la pregunta de si deben existir por
separado deja de ser retórica.

## Lo que no se pudo hacer

**Las Partes 2 y 3 están bloqueadas por falta de datos, no por trabajo.**

- `data/recommendations_input.csv` y `recommendations_history.csv` tienen **una
  sola corredora**: Credicorp Capital. `BROKER_KEYS` reconoce esa y nada más.
- `config/strategies.v1.json`, donde la metodología dice que vive la
  configuración de Consenso-6, **no existe en el repositorio**.

Sin el archivo de las seis corredoras no se puede rankearlas en la primera
mitad ni medir la mejor en la segunda, ni correr Consenso-6 como control. Las
dos partes quedan pendientes de ese archivo.

## Qué decide esto, y qué no

No decide. **Empata**, y un empate deja la decisión donde estaba, con un dato
más: la dependencia manual no tiene evidencia a favor.

Lo que sigue abierto —y es de Rodrigo— es si Sigma-6 se queda con corredora, se
queda sin ella y el sistema pasa a ser automático de punta a punta, o se funde
con Delta-12. Las opciones están en `DEPENDENCIAS_MANUALES.md`.
