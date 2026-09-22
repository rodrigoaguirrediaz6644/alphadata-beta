"""El panel de salud: una línea que diga si hay que preocuparse.

El sistema ya verifica bastante —las guardias del feed, la cobertura, las series
reconstruidas, las carteras reproducidas, la vigencia de las recomendaciones, la
tabla de dividendos— pero **está repartido y ninguna de esas cosas le habla al
lector**. Esto no agrega verificaciones: consolida las que ya corren.

**El criterio para que algo entre acá:** que su falla pueda ensuciar un número
publicado sin avisar. Un panel con veinte filas verdes no se lee, así que lo
que no cumple eso queda fuera.

Y la regla que ya aprendimos: **una alarma que siempre está roja por una razón
conocida deja de ser una alarma.** Lo que está roto y anotado —AESANDES, el
dividendo de MALLPLAZA— no aparece acá todas las semanas; vive en
`PENDIENTES.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.cdv import BANDA


# Lo que está roto, anotado y no cambia de semana a semana. **Una alarma que
# siempre está roja por una razón conocida deja de ser una alarma**, así que
# esto sale del panel. No se esconde: el panel dice cuántos hay y dónde están
# escritos, y agregar uno acá exige que exista su entrada en PENDIENTES.md.
# Quedó **vacío**, y esa es la meta: cada uno se cerró en su lugar en vez de
# quedar apartado para siempre. AESANDES pasó a estado `deslistado`, que la
# cobertura ya no trata como falla; MULTIFOODS aparece como `ACUMULANDO`, que
# es lo que es; y el dividendo de MALLPLAZA quedó aceptado con la base que
# tiene. Ver PENDIENTES.md.
#
# El mecanismo se conserva porque va a volver a hacer falta, y con él la
# prueba que exige que todo lo que se aparte tenga su entrada escrita.
CONOCIDOS: dict[str, str] = {}


@dataclass(frozen=True)
class Chequeo:
    nombre: str
    sano: bool
    detalle: str


def _fecha(valor) -> str:
    f = pd.to_datetime(valor, errors="coerce")
    return f"{f:%d-%m-%Y}" if pd.notna(f) else "—"


def revisar(*, as_of, precios_al_dia, series_detenidas, cobertura_incompleta,
            series_recalculadas, series_publicadas, carteras_reproducidas,
            dias_sin_recomendaciones, umbral_vigencia, dividendos_sin_respaldo,
            suite_verde, premio_cdv=None, descalce_real=None) -> tuple[list[Chequeo], list[str]]:
    """Consolida lo que ya se verificó en esta corrida. No verifica de nuevo.

    `cobertura_incompleta` y `dividendos_sin_respaldo` son conjuntos de claves,
    no números, para poder apartar las conocidas. Devuelve los chequeos y la
    lista de lo apartado.
    """
    conocidos = sorted((set(cobertura_incompleta) | set(dividendos_sin_respaldo)) & set(CONOCIDOS))
    cobertura_incompleta = sorted(set(cobertura_incompleta) - set(CONOCIDOS))
    dividendos_sin_respaldo = sorted(set(dividendos_sin_respaldo) - set(CONOCIDOS))
    detenidas = sorted(set(series_detenidas) - set(CONOCIDOS))
    faltan = sorted(set(series_publicadas) - set(series_recalculadas))
    if dias_sin_recomendaciones is None:
        vigencia = Chequeo("Recomendaciones", False, "no hay ninguna recomendación disponible")
    else:
        quedan = umbral_vigencia - int(dias_sin_recomendaciones)
        vigencia = Chequeo(
            "Recomendaciones",
            quedan > 0,
            f"la más reciente tiene {int(dias_sin_recomendaciones)} días; "
            + (f"quedan {quedan} para que Sigma-6 deje de abrir" if quedan > 0
               else "Sigma-6 conserva la cartera y no abre"))
    return [
        Chequeo("Precios", precios_al_dia and not detenidas,
                f"al día al {_fecha(as_of)}, ninguna serie detenida" if precios_al_dia and not detenidas
                else (f"{len(detenidas)} series detenidas: {', '.join(detenidas[:4])}" if detenidas
                      else f"el último dato es del {_fecha(as_of)}")),
        Chequeo("Cobertura", not cobertura_incompleta,
                "completa" if not cobertura_incompleta
                else f"sin datos suficientes: {', '.join(cobertura_incompleta)}"),
        Chequeo("Series publicadas", not faltan,
                f"las {len(series_publicadas)} recalculadas en esta corrida" if not faltan
                else f"sin recalcular: {', '.join(faltan)}"),
        Chequeo("Carteras", bool(carteras_reproducidas),
                "reproducidas por las reglas" if carteras_reproducidas
                else "no reproducen lo que publican las reglas"),
        vigencia,
        Chequeo("Dividendos", not dividendos_sin_respaldo,
                "todos los de las posiciones vivas, confirmados" if not dividendos_sin_respaldo
                else f"sin respaldo de precio: {', '.join(dividendos_sin_respaldo)}"),
        Chequeo("Pruebas", bool(suite_verde), "la suite pasó" if suite_verde else "la suite no pasó"),
        _premio(premio_cdv),
        _cuenta_real(descalce_real),
    ], conocidos


def _cuenta_real(descalce) -> Chequeo:
    """Lo que hay en la cuenta contra lo que tiene el modelo.

    Desde que hay plata real existe una falla que antes no podía: **tener
    comprado algo que el modelo ya vendió**. Nada la detectaría sola, porque el
    informe habla de la cartera del modelo y la cuenta habla de otra cosa, y
    las dos se ven sanas por separado.

    Va sobre instrumentos y no sobre cantidades a propósito: las cantidades no
    calzan ni tienen por qué —la primera compra fue de 8 IAUCL contra 63 de
    referencia— y una alarma por eso sonaría siempre.
    """
    if descalce is None:
        return Chequeo("Cuenta real", True, "sin operaciones registradas todavía")
    if descalce:
        return Chequeo("Cuenta real", False,
                       f"hay en la cuenta {len(descalce)} instrumento"
                       + ("" if len(descalce) == 1 else "s")
                       + f" que el modelo no tiene: {', '.join(descalce)}")
    return Chequeo("Cuenta real", True, "todo lo comprado sigue en alguna cartera del modelo")


def _premio(p) -> Chequeo:
    """El premio del CDV sobre su valor teórico, que es plata que no se ve.

    Entra al panel porque **no está en ninguna parte del modelo de costo** y sí
    afecta lo que Rodrigo paga: el precio publicado de Gamma-6 y del oro es el
    subyacente en dólares por el tipo de cambio, y lo que la corredora cobra es
    el CDV. Si esa diferencia se mueve, nada más lo notaría.

    La banda es ancha a propósito. Lo que hay que pillar es un cambio de
    régimen —que la corredora meta un punto— y no el ruido de un mes flojo: el
    premio medido tiene un error estándar de 0,05% sobre dos años y de 0,08%
    sobre el año corrido, así que una banda estrecha sonaría sola.
    """
    if p is None:
        return Chequeo("Premio del CDV", True,
                       "sin ruedas frescas suficientes para medirlo en esta ventana")
    cuanto = f"{p.medio:+.2%}".replace(".", ",")
    error = f"{p.error:.2%}".replace(".", ",")
    cierre = (f"sobre {p.ruedas} ruedas en que el CDV transó de verdad, {p.nombres} nombres")
    if not p.dentro_de_la_banda:
        return Chequeo("Premio del CDV", False,
                       f"el CDV cotiza {cuanto} sobre su valor teórico, fuera de la banda "
                       f"de ±{BANDA:.0%}; {cierre}")
    if not p.distinguible:
        return Chequeo("Premio del CDV", True,
                       f"{cuanto} ± {error}, que no se distingue de cero; {cierre}")
    return Chequeo("Premio del CDV", True, f"{cuanto} ± {error}; {cierre}")


def _apartados(conocidos: list[str]) -> str:
    if not conocidos:
        return ""
    return (f" Hay {len(conocidos)} " + ("asunto conocido" if len(conocidos) == 1 else "asuntos conocidos")
            + " apartado" + ("" if len(conocidos) == 1 else "s") + f" —{', '.join(conocidos)}— "
            "que no ensucian ningún número publicado y están anotados.")


def html(chequeos: list[Chequeo], conocidos: list[str] | None = None) -> str:
    """Una línea cuando todo está bien; qué falló y desde cuándo cuando no."""
    malos = [c for c in chequeos if not c.sano]
    if not malos:
        return ('<p class="calm"><strong>Los datos están sanos y los cálculos cuadran.</strong> '
                f'Pasaron las {len(chequeos)} verificaciones de esta corrida.'
                f'{_apartados(conocidos or [])}</p>')
    filas = "".join(f"<li><strong>{c.nombre}:</strong> {c.detalle}</li>" for c in malos)
    return (f'<div class="warn"><strong>Hay {len(malos)} '
            f'{"verificación que no pasó" if len(malos) == 1 else "verificaciones que no pasaron"}:'
            f'</strong><ul>{filas}</ul></div>')


def markdown(chequeos: list[Chequeo], conocidos: list[str] | None = None) -> str:
    malos = [c for c in chequeos if not c.sano]
    if not malos:
        return (f"- Los datos están sanos y los cálculos cuadran ({len(chequeos)} verificaciones)."
                + (f" {len(conocidos)} asuntos conocidos apartados: {', '.join(conocidos)}."
                   if conocidos else ""))
    return "\n".join(f"- **{c.nombre}:** {c.detalle}" for c in malos)
