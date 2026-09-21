"""La reconstrucción del NAV, con los pesos corriendo entre revisiones.

Hasta septiembre de 2026 las tres series accionarias se calculaban como
`retorno_dia += peso * (precio_hoy/precio_ayer - 1)` con el peso **constante**.
Ésa es la aritmética de una cartera que vuelve al objetivo todos los días, y de
ahí salían dos cosas falsas: el rebalanceo era gratis —el costo sólo se cobraba
cuando cambiaba el objetivo, que casi nunca cambia— y la orden de recortar
nunca se emitía, porque el modelo creía que la posición ya estaba en su peso.

La política escrita en `POLITICA_REBALANCEO.md` dice dejar correr los pesos y
operar sólo entradas y salidas. Este módulo calcula eso.

## Cómo se financia una entrada

Es la pregunta que la política dejaba abierta y que la implementación resolvía
sola. Cuando Delta-12 vende ILC y compra ANDINA-B, ANDINA-B recibe **el
producto de la venta**, no un octavo del valor de la pieza: lo segundo
obligaría a mover plata desde las demás posiciones, que es el rebalanceo que la
política descarta.

Concretamente, en cada revisión:

1. Las que siguen conservan el peso al que llegaron. **No se tocan.**
2. Las que salen se venden enteras.
3. Lo liberado, más la caja, se reparte **en partes iguales entre las que
   entran**, con tope en el peso de referencia de la estrategia; lo que sobre
   queda en caja.

El tope existe para que una entrada no herede de golpe el tamaño de un ganador
que se acaba de vender. Es lo que se midió.
"""

from __future__ import annotations

import pandas as pd


def nav_corrido(panel: pd.DataFrame, sesiones: pd.DatetimeIndex, marca: str,
                elegir, cost_rate: float, nombre: str) -> pd.DataFrame:
    """Serie base 100 con los pesos corriendo entre revisiones.

    `marca` es el periodo del calendario de la estrategia (`"M"` mensual,
    `"W-FRI"` semanal) y `elegir(fecha_de_revision)` devuelve
    `{ticker: peso_de_referencia}`.
    """
    if len(sesiones) == 0:
        return pd.DataFrame(columns=["date", nombre])
    pesos: dict[str, float] = {}
    caja, valor, filas = 1., 100., []
    anterior, periodo = None, None
    for sesion in sesiones:
        if anterior is None:
            filas.append({"date": sesion, nombre: valor})
            anterior, periodo = sesion, sesion.to_period(marca)
            continue
        retornos = {t: panel.at[sesion, t] / panel.at[anterior, t] - 1 for t in pesos
                    if t in panel.columns and pd.notna(panel.at[anterior, t])
                    and pd.notna(panel.at[sesion, t]) and panel.at[anterior, t] > 0}
        dia = sum(peso * retornos.get(t, 0.) for t, peso in pesos.items())
        valor *= 1 + dia
        if pesos:
            # Los pesos corren: cada uno crece con su propio precio y todos se
            # renormalizan por el retorno de la cartera. La caja no se mueve.
            factor = 1 + dia
            pesos = {t: w * (1 + retornos.get(t, 0.)) / factor for t, w in pesos.items()}
            caja /= factor
        actual = sesion.to_period(marca)
        if actual != periodo:
            previas = panel.index[panel.index < sesion]
            if len(previas):
                referencia = elegir(pd.Timestamp(previas[-1]))
                nuevos, nueva_caja = _reasignar(pesos, caja, referencia)
                riesgo = sum(abs(nuevos.get(t, 0) - pesos.get(t, 0)) for t in set(pesos) | set(nuevos))
                valor *= 1 - .5 * (riesgo + abs(nueva_caja - caja)) * cost_rate
                pesos, caja = nuevos, nueva_caja
            periodo = actual
        filas.append({"date": sesion, nombre: valor})
        anterior = sesion
    return pd.DataFrame(filas)


def _reasignar(pesos: dict[str, float], caja: float,
               referencia: dict[str, float]) -> tuple[dict[str, float], float]:
    """Las entradas se financian con el producto de las salidas."""
    salen = set(pesos) - set(referencia)
    entran = [t for t in referencia if t not in pesos]
    liberado = sum(pesos[t] for t in salen) + caja
    nuevos = {t: w for t, w in pesos.items() if t not in salen}
    if entran:
        nuevos.update({t: min(referencia[t], liberado / len(entran)) for t in entran})
    return nuevos, 1 - sum(nuevos.values())
