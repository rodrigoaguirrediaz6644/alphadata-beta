# Guía de operación

## Lo único que debe hacer el usuario

**Nada, semana a semana.** Las tres piezas que quedan —Delta-12, Gamma-6 y el
oro— corren sólo con precios, que el sistema baja solo. La carga de
recomendaciones dejó de ser un requisito operativo cuando Sigma-6 salió de la
asignación el 22-09-2026; las instrucciones siguen al final de este archivo por
si alguna vez vuelve.

Lo que sí hay que hacer es **anotar lo que se opera de verdad** en
`data/operaciones_reales.csv`, porque es el único puente entre el modelo y la
cuenta, y hay una guardia que compara las dos. Ver `REGISTRO_OPERACIONES.md`.

## La cadencia: se queda semanal, y es una decisión

**Sigma-6 era la única estrategia semanal y ya no está.** Delta-12 y Gamma-6
deciden una vez al mes y el oro no tiene señal, así que había que contestar si
la corrida de los viernes todavía tiene razón de ser o es una herencia.

**Se queda semanal.** No por inercia: el viernes publica cosas que no dependen
de que haya una decisión de cartera.

- **Los precios al día y las guardias del feed.** El feed chileno estuvo
  congelado desde el 17-07-2026 y el sistema publicó dos meses de NAV falso.
  Detectar eso a los siete días no es lo mismo que a los treinta.
- **El panel de salud**, con sus nueve verificaciones.
- **La guardia de la cuenta real**, que avisa si hay comprado algo que el
  modelo ya no tiene. Esa sí puede cambiar cualquier semana, porque depende de
  lo que se opere y no del calendario del modelo.
- **La cartera de ingreso**, con los montos y los símbolos al precio de hoy.

Lo que el informe semanal **no** hace es cambiar la cartera. Eso ocurre una vez
al mes y el informe lo dice.

### Cuándo cambia la cartera de verdad

La señal de Delta-12 y de Gamma-6 es **el cierre del mes anterior**, así que la
cartera se revisa en la primera corrida de cada mes.

| corrida | qué hace |
|---|---|
| viernes **25-09-2026** | informe de estado; **no** es rebalanceo |
| martes **30-09-2026** | tampoco es rebalanceo: la señal sigue siendo la de agosto |
| viernes **02-10-2026** | **primera revisión de cartera** de las tres piezas, con el cierre de septiembre |

**Ojo con esto al comprar.** Quien entre el 30-09 compra la cartera de la señal
de agosto, y dos días después el modelo la revisa con la de septiembre. Si la
revisión cambia nombres, se paga la comisión de esas entradas dos veces en tres
días. Entrar el **02-10**, leyendo el informe de ese viernes, evita el doble
costo. Es una decisión de Rodrigo y las dos son defendibles: entrar antes cuesta
comisiones, entrar después son tres días fuera del mercado.

---

## Si vuelve una señal de corredora

Copiar las nuevas recomendaciones de Credicorp a un CSV basado en `templates/recomendaciones_credicorp.csv` y subirlo a `data/inbox/`. Puede subir varios archivos; el sistema elimina duplicados y conserva el historial.

Campos obligatorios: `published_at`, `available_at`, `broker`, `ticker` y `recommendation`. Los demás campos deben conservarse aunque queden vacíos. `broker` debe ser Credicorp Capital. Las recomendaciones admitidas son Comprar, Sobreponderar, Outperform, Superior al mercado, Mantener, Neutral, Vender, Subponderar, Underperform e Inferior al mercado.

## Ejecución manual

```bash
PYTHONPATH=. python alphadata.py run
```

## Ejecución programada

| flujo | cuándo | qué hace |
|---|---|---|
| `capture-daily.yml` | lunes a viernes, 23:00 UTC | captura el cierre chileno de la cotización viva y los precios de los CDV |
| `update-prices.yml` | **viernes, 20:30 UTC** | la corrida oficial: calcula, redacta, envía el informe por correo y guarda todo |
| `vigilancia.yml` | todos los días, 12:00 UTC | avisa si el informe no salió, y mantiene vivos los cron |

Los tres admiten ejecución manual desde la pestaña Actions.

### Por qué existe `vigilancia.yml`

**Un informe que no sale se veía igual que una semana tranquila.** El panel de
salud vive dentro del informe, así que una corrida que nunca ocurre no produce
ni informe ni alarma. Para quien está encima todos los días no importa; para
quien se va a ocupar de otra cosa, es el único modo de falla que importa.

La vigilancia corre **aparte** del flujo que produce el informe, a propósito: si
viviera adentro, la misma falla que impide el informe impediría el aviso. Manda
correo y además deja la corrida en rojo, porque un correo se puede perder.

Y hace una segunda cosa que parece menor: escribe un commit de marca si el
repositorio lleva 45 días quieto. **GitHub desactiva los flujos programados de
un repositorio público cuando no hay actividad en 60 días**, y lo que reinicia
ese reloj son commits, no corridas. Sin eso, cuanto mejor funcione el sistema
solo, más cerca está de apagarse en silencio: sin error, sin correo, sin
informe. Ver `src/vigilancia.py`.

## Controles

Una corrida se detiene si hay menos de 20 acciones locales con historia suficiente o si falta el benchmark. Las recomendaciones inválidas quedan en `data/recommendations_errors.csv`; nunca se usan silenciosamente. Cada corrida conserva carteras, movimientos, auditoría, NAV, fecha de corte, versión y estado.

## Correo opcional

Configure los secretos `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` y `REPORT_RECIPIENTS`. Sin ellos, el informe se genera igualmente.
