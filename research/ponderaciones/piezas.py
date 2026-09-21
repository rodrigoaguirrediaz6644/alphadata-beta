"""Reconstrucción de las cuatro piezas sobre una ventana, con su rotación.

La rotación por pieza no es un dato accesorio: es lo que determina cuánto pesa
la tarifa mínima de $1.990, que sólo aplica a las piezas chilenas y que a
capital bajo domina el costo completo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import (delta12, delta12_historical_nav, gamma6_historical_nav,
                                 oro_historical_nav, sigma6, validate_recommendations)

ROOT = Path(__file__).resolve().parents[2]
COSTO_CL, COSTO_US = .001785, .001
POSICIONES = {"Sigma-6": 10, "Delta-12": 8, "Gamma-6": 6, "Oro": 1}
CHILENAS = {"Sigma-6", "Delta-12"}
TASAS = {"Sigma-6": COSTO_CL, "Delta-12": COSTO_CL, "Gamma-6": COSTO_US, "Oro": COSTO_US}


def _sigma(precios, valid, inicio, fin, costo=COSTO_CL):
    ses = pd.DatetimeIndex(sorted(precios.loc[(precios.alphadata_ticker != "IPSA_TR")
                                              & precios.date.between(inicio - pd.Timedelta(days=500), fin), "date"].dropna().unique()))
    panel = precios[precios.date.isin(ses)].pivot_table(index="date", columns="alphadata_ticker",
                                                        values="adjusted_close", aggfunc="last").sort_index().ffill(limit=3)
    revisiones = {pd.Timestamp(r) for r in pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max() if r >= inicio}
    estado, pesos, nav, filas, previo, ops = {"sigma_entries": {}}, {}, 100.0, [], None, 0
    for s in panel.index[panel.index >= inicio]:
        if previo is not None:
            nav *= 1 + sum(w * (panel.at[s, t] / panel.at[previo, t] - 1) for t, w in pesos.items()
                           if t in panel and pd.notna(panel.at[previo, t]) and pd.notna(panel.at[s, t]) and panel.at[previo, t] > 0)
        if s in revisiones:
            cartera, _, estado = sigma6(valid, precios, s, estado)
            nuevos = dict(zip(cartera.ticker, cartera.target_weight))
            ops += len(set(nuevos) - set(pesos)) + len(set(pesos) - set(nuevos))
            rot = sum(abs(nuevos.get(t, 0) - pesos.get(t, 0)) for t in set(pesos) | set(nuevos))
            caja = abs((1 - sum(nuevos.values())) - (1 - sum(pesos.values())))
            nav *= 1 - .5 * (rot + caja) * costo
            pesos = nuevos
        filas.append({"date": s, "Sigma-6": nav}); previo = s
    return pd.DataFrame(filas), ops


def _ops_delta(precios, universo, inicio, fin):
    ses = pd.DatetimeIndex(sorted(precios.loc[precios.date.between(inicio, fin), "date"].unique()))
    previo, ops = set(), 0
    for f in pd.Series(ses, index=ses).groupby(ses.to_period("M")).max():
        cartera, _ = delta12(precios, universo, pd.Timestamp(f))
        actual = set(cartera.ticker)
        ops += len(actual - previo) + len(previo - actual)
        previo = actual
    return ops


def construir(inicio: pd.Timestamp, fin: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    u = load_universe()
    p = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    raw = pd.read_csv(ROOT / "data" / "recommendations_input.csv", dtype=str).fillna("")
    valid, _ = validate_recommendations(raw, set(u.alphadata_ticker))
    us = set(u.loc[u.tipo == "accion_us", "alphadata_ticker"])
    etf = set(u.loc[u.tipo == "etf_us", "alphadata_ticker"])
    fx = p[p.alphadata_ticker == "USDCLP"]

    sigma, ops_sigma = _sigma(p, valid, inicio, fin)
    delta = delta12_historical_nav(p, u, inicio, fin, COSTO_CL)
    gamma = gamma6_historical_nav(p[p.alphadata_ticker.isin(us)], u, fx, inicio, fin, COSTO_US)
    oro = oro_historical_nav(p[p.alphadata_ticker.isin(etf)], u, fx, inicio, fin, COSTO_US)
    ops_delta = _ops_delta(p, u, inicio, fin)

    navs = sigma
    for otra in (delta, gamma, oro):
        navs = navs.merge(otra, on="date", how="outer")
    navs = navs.sort_values("date")
    navs = navs[navs.date.between(inicio, fin)].reset_index(drop=True)
    anios = (navs.date.iloc[-1] - navs.date.iloc[0]).days / 365.25
    return navs, {"Sigma-6": ops_sigma / anios, "Delta-12": ops_delta / anios, "Gamma-6": 0.0, "Oro": 0.0}
