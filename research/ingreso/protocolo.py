"""Protocolo de ingreso: qué compra el que entra hoy.

Tres mediciones, con las reglas fijadas antes de mirar el resultado:

1. Comprar la cartera vigente completa contra comprar sólo las posiciones que
   están bajo su precio de entrada del modelo. Horizontes de 3, 6 y 12 meses.
2. Escalonar el ingreso: dispersión del resultado a 12 meses entrando en un día
   contra 4, 8 y 12 semanas, y el costo en comisiones de cada esquema.
3. Cuánto le queda de vida a una posición tomada a mitad de camino, y cuánto
   encarece eso el costo de entrada por mes mantenido.

Todo sobre Delta-12, que es la pieza con estructura más limpia para esto:
revisión mensual, ocho posiciones, fecha y precio de entrada bien definidos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import delta12

MINIMO, TASA_CL = 1990, .001785
POSICIONES_D12 = 8
HORIZONTES = {"3 meses": 63, "6 meses": 126, "12 meses": 252}


def historia_de_carteras(precios, universo, inicio, fin):
    """Por cada revisión mensual: qué se tiene, desde cuándo y a qué precio."""
    ses = pd.DatetimeIndex(sorted(precios.loc[precios.date.between(inicio, fin), "date"].unique()))
    panel = precios[precios.date.isin(ses)].pivot_table(index="date", columns="alphadata_ticker",
                                                        values="adjusted_close", aggfunc="last").sort_index().ffill(limit=3)
    revisiones = pd.Series(ses, index=ses).groupby(ses.to_period("M")).max().tolist()
    tenencia, historia = {}, []
    for fecha in revisiones:
        fecha = pd.Timestamp(fecha)
        cartera, _ = delta12(precios, universo, fecha)
        actual = set(cartera.ticker)
        for t in set(tenencia) - actual:
            tenencia.pop(t)
        for t in actual - set(tenencia):
            tenencia[t] = {"desde": fecha, "precio": float(panel.at[fecha, t]) if t in panel and pd.notna(panel.at[fecha, t]) else np.nan}
        historia.append({"fecha": fecha, "tenencia": {t: dict(v) for t, v in tenencia.items()}})
    return historia, panel


def retorno_cesta(panel, tickers, desde, sesiones):
    """Retorno de comprar una canasta igual ponderada y mantenerla."""
    futuras = panel.index[panel.index > desde]
    if len(futuras) < sesiones or not tickers:
        return np.nan
    hasta = futuras[sesiones - 1]
    rets = []
    for t in tickers:
        if t not in panel:
            continue
        a, b = panel.at[desde, t], panel.at[hasta, t]
        if pd.notna(a) and pd.notna(b) and a > 0:
            rets.append(b / a - 1)
    return float(np.mean(rets)) if rets else np.nan


def comparar_entradas(historia, panel):
    """Cartera completa contra sólo las que van bajo su precio de entrada."""
    filas = []
    for punto in historia:
        fecha, tenencia = punto["fecha"], punto["tenencia"]
        if not tenencia or fecha not in panel.index:
            continue
        completas = list(tenencia)
        perdedoras = [t for t, v in tenencia.items()
                      if t in panel and pd.notna(panel.at[fecha, t]) and pd.notna(v["precio"])
                      and v["precio"] > 0 and panel.at[fecha, t] < v["precio"]]
        fila = {"fecha": fecha, "n_completa": len(completas), "n_perdedoras": len(perdedoras)}
        for etiqueta, sesiones in HORIZONTES.items():
            fila[f"completa {etiqueta}"] = retorno_cesta(panel, completas, fecha, sesiones)
            fila[f"perdedoras {etiqueta}"] = retorno_cesta(panel, perdedoras, fecha, sesiones)
        filas.append(fila)
    return pd.DataFrame(filas)


def dispersion_escalonada(panel, historia, tramos_semanas=(0, 4, 8, 12), sesiones=252):
    """Dispersión del resultado a 12 meses según en cuántas semanas se entre."""
    resultados = {f"{s} semanas" if s else "un día": [] for s in tramos_semanas}
    for punto in historia:
        fecha, tickers = punto["fecha"], list(punto["tenencia"])
        if not tickers or fecha not in panel.index:
            continue
        futuras = panel.index[panel.index >= fecha]
        if len(futuras) < sesiones + 60:
            continue
        objetivo = futuras[sesiones - 1]
        for semanas in tramos_semanas:
            n = max(1, semanas)
            fechas_tramo = [futuras[min(i * 5, len(futuras) - 1)] for i in range(n)] if semanas else [fecha]
            total = []
            for t in tickers:
                if t not in panel or pd.isna(panel.at[objetivo, t]):
                    continue
                precios = [panel.at[f, t] for f in fechas_tramo if pd.notna(panel.at[f, t]) and panel.at[f, t] > 0]
                if not precios:
                    continue
                # cada tramo compra 1/n del monto al precio de esa fecha
                unidades = sum((1 / len(precios)) / p for p in precios)
                total.append(unidades * panel.at[objetivo, t] - 1)
            if total:
                resultados[f"{semanas} semanas" if semanas else "un día"].append(float(np.mean(total)))
    return {k: pd.Series(v) for k, v in resultados.items()}


def tenencia_residual(historia):
    """Cuántos meses más vive una posición tomada en una fecha cualquiera."""
    restos = []
    for i, punto in enumerate(historia):
        for t in punto["tenencia"]:
            vive = 0
            for j in range(i + 1, len(historia)):
                if t in historia[j]["tenencia"] and historia[j]["tenencia"][t]["desde"] == punto["tenencia"][t]["desde"]:
                    vive += 1
                else:
                    break
            restos.append(vive)
    return pd.Series(restos)


def costo_entrada(capital_pieza, posiciones, tramos, tasa=TASA_CL, minimo=MINIMO):
    monto = capital_pieza / posiciones / tramos
    return posiciones * tramos * (max(minimo, monto * tasa) if minimo else monto * tasa)
