"""Cinco esquemas de ponderación del conjunto, con el costo completo.

Los esquemas están fijados de antemano; no se optimiza nada. Las ponderaciones
que dependen de la volatilidad se recalculan en cada reequilibrio mensual con
los **doce meses anteriores**, así que son una regla implementable y no una
lectura del futuro.

## El modelo de costos

La comisión variable ya está dentro del NAV de cada pieza: 0,1785% para lo
chileno, 0,1% por lado para lo estadounidense. Faltan dos cosas.

**La tarifa mínima de $1.990**, que sólo aplica a las piezas chilenas. Se cobra
el exceso sobre el porcentual ya contado: `max(0, 1990 − monto × tasa)`. Entra
por dos vías, la rotación interna de cada pieza y el reequilibrio entre piezas.

**El reequilibrio mensual entre piezas.** Mover una pieza exige operar sus
posiciones, así que cuesta la comisión de esa pieza y, si es chilena, tantos
mínimos como posiciones tenga. Se aplica una banda de no-operar de 0,5% del
capital: por debajo de eso la deriva no se corrige, que es lo que haría
cualquiera con una tarifa mínima de por medio. Sin esa banda el costo de
reequilibrio es el mismo para todos los esquemas y deja de distinguirlos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.ponderaciones.piezas import CHILENAS, POSICIONES, TASAS

PIEZAS = ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]
MINIMO = 1990
BANDA_NO_OPERAR = .005
VENTANA_VOL = 252
MINIMO_HISTORIA = 60  # sin esto la volatilidad se estima sobre dos o tres días


# --- los cinco esquemas -------------------------------------------------------------

def igual(_returns):
    return pd.Series(.25, index=PIEZAS)


def _inv_vol(returns, columnas):
    if len(returns) < MINIMO_HISTORIA:
        return pd.Series(1 / len(columnas), index=columnas)
    vol = returns[columnas].std()
    vol = vol.replace(0, np.nan).dropna()
    if vol.empty:
        return pd.Series(1 / len(columnas), index=columnas)
    w = (1 / vol) / (1 / vol).sum()
    return w.reindex(columnas).fillna(0)


def inverso_vol(returns):
    return _inv_vol(returns, PIEZAS)


def paridad_riesgo(returns, iteraciones=500):
    """Contribución al riesgo igual entre las cuatro piezas.

    Resolver el sistema no es optimizar: la paridad de riesgo es una condición
    definida, no un máximo que se busca.
    """
    if len(returns) < MINIMO_HISTORIA:
        return igual(returns)
    cov = returns[PIEZAS].cov().to_numpy()
    if np.isnan(cov).any():
        return igual(returns)
    w = np.repeat(1 / len(PIEZAS), len(PIEZAS))
    for _ in range(iteraciones):
        marginal = cov @ w
        contribucion = w * marginal
        objetivo = contribucion.mean()
        w = w * (objetivo / np.where(contribucion > 0, contribucion, objetivo))
        w = np.clip(w, 1e-6, None)
        w = w / w.sum()
    return pd.Series(w, index=PIEZAS)


def oro_anclado_igual(_returns):
    """Oro en 25% y el resto parejo.

    Con cuatro piezas esto es **idéntico** al peso igual: el 75% restante entre
    tres da 25% a cada una. Se conserva como esquema porque estaba en la lista,
    pero no es una alternativa distinta y así se informa.
    """
    return pd.Series(.25, index=PIEZAS)


def oro_anclado_inv_vol(returns):
    otras = [p for p in PIEZAS if p != "Oro"]
    w = _inv_vol(returns, otras) * .75
    w["Oro"] = .25
    return w.reindex(PIEZAS).fillna(0)


ESQUEMAS = {
    "peso igual": igual,
    "inverso a volatilidad": inverso_vol,
    "paridad de riesgo": paridad_riesgo,
    "oro 25% + resto parejo": oro_anclado_igual,
    "oro 25% + resto inv. vol": oro_anclado_inv_vol,
}


# --- simulación ---------------------------------------------------------------------

def _exceso_minimo(monto_por_operacion, tasa):
    return max(0.0, MINIMO - monto_por_operacion * tasa)


def simular(navs: pd.DataFrame, ops_anio: dict, esquema, capital: float,
            pesos_fijos: pd.Series | None = None, banda: float = BANDA_NO_OPERAR) -> dict:
    datos = navs.set_index("date")[PIEZAS].apply(pd.to_numeric, errors="coerce").sort_index()
    retornos = datos.pct_change(fill_method=None)
    disponibles = datos.notna()

    pesos, nivel, filas, previo = None, 100.0, [], None
    mes = None
    for fecha in datos.index:
        vivas = [p for p in PIEZAS if disponibles.at[fecha, p]]
        if not vivas:
            continue
        if previo is not None and pesos:
            paso = sum(w * retornos.at[fecha, p] for p, w in pesos.items()
                       if p in retornos and pd.notna(retornos.at[fecha, p]))
            nivel *= 1 + paso
            # la deriva: los pesos corren con el retorno de cada pieza
            pesos = {p: w * (1 + (retornos.at[fecha, p] if pd.notna(retornos.at[fecha, p]) else 0))
                     for p, w in pesos.items()}
            total = sum(pesos.values())
            pesos = {p: w / total for p, w in pesos.items()}
            # arrastre diario de los mínimos de la rotación interna de cada pieza
            drag = sum(ops_anio.get(p, 0) / 252 * _exceso_minimo(pesos.get(p, 0) * capital / POSICIONES[p], TASAS[p])
                       for p in vivas if p in CHILENAS and pesos.get(p, 0) > 0) / capital
            nivel *= 1 - drag

        if mes != fecha.to_period("M") or pesos is None:
            historia = retornos.loc[retornos.index <= fecha].tail(VENTANA_VOL).dropna(how="all")
            objetivo = pesos_fijos if pesos_fijos is not None else esquema(historia)
            objetivo = objetivo.reindex(PIEZAS).fillna(0)
            objetivo = objetivo[vivas] / objetivo[vivas].sum() if objetivo[vivas].sum() > 0 else pd.Series(1 / len(vivas), index=vivas)
            actuales = pd.Series(pesos).reindex(vivas).fillna(0) if pesos else pd.Series(0.0, index=vivas)
            delta = (objetivo - actuales).abs()
            # Banda de disparo: si alguna pieza se apartó más que la banda se
            # reequilibra todo a objetivo; si ninguna lo hizo, no se opera nada.
            # Corregir sólo algunas y reescalar movería a las demás sin operarlas.
            if pesos is None or delta.max() > banda:
                if pesos:
                    costo = sum(delta[p] * TASAS[p] for p in vivas)
                    costo += sum(POSICIONES[p] * _exceso_minimo(delta[p] * capital / POSICIONES[p], TASAS[p]) / capital
                                 for p in vivas if p in CHILENAS and delta[p] > 0)
                    nivel *= 1 - costo
                pesos = dict(objetivo)
            mes = fecha.to_period("M")
        filas.append({"date": fecha, "nav": nivel}); previo = fecha

    serie = pd.DataFrame(filas).set_index("date")["nav"]
    anios = (serie.index[-1] - serie.index[0]).days / 365.25
    return {"anual": (serie.iloc[-1] / 100) ** (1 / anios) - 1,
            "peor_caida": float((serie / serie.cummax() - 1).min()),
            "base_100": float(serie.iloc[-1]), "serie": serie}
