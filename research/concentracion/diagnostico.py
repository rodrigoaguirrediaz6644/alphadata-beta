"""¿Son Sigma-6 y Delta-12 dos estrategias o una con dos nombres?

Los diagnósticos van antes que el ranking, porque responden la objeción
estructural —la mitad de la cartera en un solo mercado— sin depender de qué
rindió más en la muestra.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import delta12, sigma6, validate_recommendations

ROOT = Path(__file__).resolve().parents[2]


def carteras_mensuales(precios, universo, valid, inicio, fin):
    """Cartera de cada estrategia en las fechas de revisión mensuales."""
    ses = pd.DatetimeIndex(sorted(precios.loc[(precios.alphadata_ticker != "IPSA_TR")
                                              & precios.date.between(inicio, fin), "date"].dropna().unique()))
    revisiones = pd.Series(ses, index=ses).groupby(ses.to_period("M")).max().tolist()
    estado, filas = {"sigma_entries": {}}, []
    semanas = pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max().tolist()
    fila_sigma = {}
    for fecha in sorted(set(semanas) | set(revisiones)):
        cartera, _, estado = sigma6(valid, precios, pd.Timestamp(fecha), estado)
        fila_sigma = dict(zip(cartera.ticker, cartera.target_weight))
        if fecha in revisiones:
            d, _ = delta12(precios, universo, pd.Timestamp(fecha))
            filas.append({"fecha": pd.Timestamp(fecha), "sigma": dict(fila_sigma),
                          "delta": dict(zip(d.ticker, d.target_weight))})
    return filas


def solape(carteras):
    """Cuántos nombres y cuánto peso comparten las dos carteras chilenas."""
    filas = []
    for punto in carteras:
        s, d = punto["sigma"], punto["delta"]
        comunes = set(s) & set(d)
        union = set(s) | set(d)
        filas.append({
            "fecha": punto["fecha"],
            "n_sigma": len(s), "n_delta": len(d), "n_comunes": len(comunes),
            "jaccard": len(comunes) / len(union) if union else np.nan,
            "frac_sigma_en_delta": len(comunes) / len(s) if s else np.nan,
            "peso_comun": sum(min(s.get(t, 0), d.get(t, 0)) for t in comunes),
            "caja_sigma": 1 - sum(s.values()),
            "caja_delta": 1 - sum(d.values()),
        })
    return pd.DataFrame(filas)
