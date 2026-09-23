# El privilegio del calendario: mis doce reglas mensuales no sobreviven

Tu sesión hermana encontró que mover el día de la señal cinco días hábiles
destruía la protección de su regla mensual. **Corrí la misma prueba sobre mis
doce reglas y el resultado es peor que el suyo.**

Investigación pura: no toca `data/`, `reports/`, el pipeline ni el informe.

---

## La prueba

Una regla mensual lee el cierre de mes. Pero **el fin de mes no tiene nada de
especial para el mercado**: es una fecha saliente para nosotros, no para los
precios. Si la protección depende de leer justo ese día, no es una regla.

Las mismas doce reglas de `research/afp_desde_cero/`, leídas 0, 7, 14 y 21 días
corridos después del cierre de mes. Mismo rezago de ejecución real —7 días
corridos— en las cuatro. Cuprum, 2014-2026.

## El resultado

| regla | cierre de mes | +7d | +14d | +21d |
|---|---:|---:|---:|---:|
| propia-3m | −16,58% | −19,75% | −26,09% | −26,48% |
| propia-6m | −26,48% | −26,48% | −26,09% | −26,48% |
| propia-9m | −26,48% | −26,48% | −26,09% | −26,48% |
| propia-12m | −26,48% | −26,48% | −26,09% | −26,48% |
| mercado-3m | −26,48% | −26,48% | −26,48% | −26,48% |
| mercado-6m | −26,48% | −26,48% | −26,48% | −26,48% |
| mercado-9m | −26,48% | −26,48% | −26,48% | −26,48% |
| mercado-12m | −26,48% | −26,48% | −26,48% | −26,48% |
| **vol-p70** | **−11,04%** | −19,75% | **−28,45%** | −25,17% |
| **vol-p80** | **−14,19%** | −19,75% | **−28,45%** | −27,00% |
| vol-p90 | −26,48% | −26,48% | −26,09% | −26,48% |
| vol-p95 | −26,48% | −26,48% | −26,09% | −26,48% |
| **Fondo A** | **−26,48%** | −26,48% | −26,48% | −26,48% |

**Reglas que protegen en los cuatro días de lectura: 0 de 12.**

**Nueve de las doce dan la caída completa del Fondo A en las cuatro lecturas.**
No es que se degraden al mover el día: nunca protegieron. Lo que mostraban era
que la señal estaba en A casi todo el tiempo.

**Las tres que sí protegían al cierre de mes pierden la protección entera.**
`vol-p70` era mi mejor regla mensual —−11,04%— y leída dos semanas más tarde
cae **−28,45%: peor que no hacer nada.** Lo mismo `vol-p80`.

El retorno anual salta entre +8,09% y +11,95% sin patrón. **Eso es ruido, no
una regla.**

## Dos errores de signo míos en esta misma corrida

El resumen automático salió invertido **dos veces** antes de quedar bien:

1. Usé `max()` sobre caídas negativas creyendo que tomaba la peor. Toma la más
   suave.
2. Comparé `caida < umbral` para decir "protege", cuando con negativos es al
   revés.

La tabla estuvo bien desde la primera corrida; el resumen no. Ahora la
comparación se hace sobre la **ventaja en puntos contra el Fondo A**, donde más
es mejor, para no volver a caer en el signo.

## Lo que esto cambia

**Mis estudios mensuales quedan cerrados, no corregidos.** No es que el rezago
los degradara unas décimas: es que la protección que mostraban dependía de leer
el cierre de mes.

Antes ya había medido, en `research/afp_mecanismos/`, que `tendencia 100d`
evaluada **a diario** da **+10,70% con −10,82% de caída** contra +9,07% y
−26,06% del Fondo A. Con esto, esa deja de ser una alternativa más y pasa a ser
**la única línea que queda en pie**: evaluar todos los días, sin fecha
privilegiada, sin modelo.

Y hay que decir lo que le sigue pegado: bajo el tope de dos traspasos al año
—`research/afp_mecanismos/`, punto 3— esa misma regla pasa de −10,82% a
−40,43%. La evaluación diaria es lo único que funciona, y es exactamente lo que
el proyecto de ley de 2020 habría impedido.

## Lo que NO hace este estudio

No propone una regla nueva, no ajusta ningún parámetro, no agrega
características ni ventanas, y no implementa nada. Es una prueba de robustez
sobre reglas que ya existían, con el criterio escrito en el encabezado del
script antes de mirar los números.

---

Reproducir: `PYTHONPATH=. python research/afp_calendario/estudio.py`
