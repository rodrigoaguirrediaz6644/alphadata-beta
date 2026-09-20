"""Gamma-6: reglas de selección, conversión a pesos y conjunto de estrategias."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy_engine import combined_equal_weight, gamma6, sanear_fx, to_clp


def _universe() -> pd.DataFrame:
    rows = [{"alphadata_ticker": t, "yahoo_ticker": t, "nombre": t, "tipo": "accion_us", "moneda": "USD", "estado": "activo"} for t in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]]
    rows.append({"alphadata_ticker": "CHILE", "yahoo_ticker": "CHILE.SN", "nombre": "Local", "tipo": "accion_local", "moneda": "CLP", "estado": "activo"})
    rows.append({"alphadata_ticker": "USDCLP", "yahoo_ticker": "USDCLP=X", "nombre": "Dólar", "tipo": "fx", "moneda": "CLP", "estado": "activo"})
    return pd.DataFrame(rows)


def _prices(sessions: int = 400) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", periods=sessions)
    rng = np.random.default_rng(3)
    frames = []
    # Ocho acciones con pendientes distintas: AAA la más fuerte, HHH la más débil.
    for index, ticker in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]):
        drift = np.linspace(0, .9 - .18 * index, sessions)
        series = 100 * np.exp(drift) * (1 + .002 * rng.standard_normal(sessions))
        frames.append(pd.DataFrame({"date": dates, "alphadata_ticker": ticker, "adjusted_close": series, "open": series, "high": series, "low": series, "close": series, "volume": 1e6}))
    frames.append(pd.DataFrame({"date": dates, "alphadata_ticker": "CHILE", "adjusted_close": 1000.0, "open": 1000.0, "high": 1000.0, "low": 1000.0, "close": 1000.0, "volume": 1e6}))
    return pd.concat(frames, ignore_index=True)


def test_gamma6_selects_six_strongest_stocks_with_equal_weight():
    prices, universe = _prices(), _universe()
    portfolio, audit = gamma6(prices, universe, prices.date.max())
    assert len(portfolio) == 6
    assert portfolio.target_weight.sum() == pytest.approx(1.0)
    assert portfolio.target_weight.nunique() == 1
    assert set(portfolio.ticker) == {"AAA", "BBB", "CCC", "DDD", "EEE", "FFF"}
    assert "CHILE" not in set(audit.ticker)  # sólo acciones estadounidenses


def test_gamma6_excludes_stocks_below_their_own_sma200():
    prices, universe = _prices(), _universe()
    crash = prices.alphadata_ticker.eq("AAA") & prices.date.ge(prices.date.max() - pd.Timedelta(days=40))
    prices.loc[crash, "adjusted_close"] *= .4
    portfolio, audit = gamma6(prices, universe, prices.date.max())
    assert "AAA" not in set(portfolio.ticker)
    assert audit.set_index("ticker").loc["AAA", "reason"] == "bajo SMA200"


def test_gamma6_needs_a_year_of_history_and_never_looks_ahead():
    prices, universe = _prices(), _universe()
    short = prices.loc[prices.date <= prices.date.min() + pd.Timedelta(days=200)]
    empty, _ = gamma6(short, universe, short.date.max())
    assert empty.empty
    review = prices.date.unique()[300]
    before = gamma6(prices, universe, review)[0]
    truncated = gamma6(prices.loc[prices.date <= review], universe, review)[0]
    pd.testing.assert_frame_equal(before.reset_index(drop=True), truncated.reset_index(drop=True))


def test_to_clp_converts_only_instruments_quoted_in_dollars():
    prices, universe = _prices(), _universe()
    fx = pd.DataFrame({"date": sorted(prices.date.unique()), "alphadata_ticker": "USDCLP", "adjusted_close": 950.0})
    converted = to_clp(prices, universe, fx)
    usd_before = prices.loc[prices.alphadata_ticker.eq("AAA"), "adjusted_close"].iloc[-1]
    assert converted.loc[converted.alphadata_ticker.eq("AAA"), "adjusted_close"].iloc[-1] == pytest.approx(usd_before * 950.0)
    assert converted.loc[converted.alphadata_ticker.eq("CHILE"), "adjusted_close"].iloc[-1] == 1000.0


def test_to_clp_carries_the_last_known_rate_when_the_local_market_is_closed():
    prices, universe = _prices(), _universe()
    dates = sorted(prices.date.unique())
    fx = pd.DataFrame({"date": dates[:-3], "alphadata_ticker": "USDCLP", "adjusted_close": 900.0})
    converted = to_clp(prices, universe, fx)
    assert converted.loc[converted.alphadata_ticker.eq("AAA"), "adjusted_close"].iloc[-1] == pytest.approx(prices.loc[prices.alphadata_ticker.eq("AAA"), "adjusted_close"].iloc[-1] * 900.0)


def test_combined_portfolio_is_one_third_in_each_strategy():
    dates = pd.bdate_range("2026-01-01", periods=80)
    frame = pd.DataFrame({"date": dates, "A": 100 * 1.001 ** np.arange(80), "B": 100 * 1.002 ** np.arange(80), "C": 100 * 1.003 ** np.arange(80)})
    combined = combined_equal_weight(frame, ["A", "B", "C"])
    assert combined.iloc[0] == pytest.approx(100.0)
    assert frame.A.iloc[-1] / 100 < combined.iloc[-1] / 100 < frame.C.iloc[-1] / 100  # queda entre la peor y la mejor
    single = combined_equal_weight(frame[["date", "A"]], ["A", "B", "C"])
    assert single.iloc[-1] == pytest.approx(frame.A.iloc[-1])  # con una sola serie disponible, replica esa serie


def test_combined_portfolio_waits_for_a_strategy_without_history():
    dates = pd.bdate_range("2026-01-01", periods=80)
    frame = pd.DataFrame({"date": dates, "A": 100 * 1.001 ** np.arange(80), "B": 100 * 1.001 ** np.arange(80)})
    frame["C"] = [np.nan] * 60 + list(100 * 1.05 ** np.arange(20))
    combined = combined_equal_weight(frame, ["A", "B", "C"])
    assert combined.notna().all()
    assert len(combined) == len(frame)


def test_to_clp_no_se_deja_envenenar_por_un_tipo_de_cambio_imposible():
    """El 22-12-2016 el proveedor entregó 5 pesos por dólar con apertura de 671.
    Un dato así hundía un 99% la valorización en pesos de Gamma-6."""
    prices, universe = _prices(), _universe()
    fechas = sorted(prices.date.unique())
    fx = pd.DataFrame({"date": fechas, "alphadata_ticker": "USDCLP", "adjusted_close": 950.0})
    fx.loc[fx.index[100], "adjusted_close"] = 5.0
    convertido = to_clp(prices, universe, fx)
    serie = convertido.loc[convertido.alphadata_ticker.eq("AAA")].sort_values("date")["adjusted_close"]
    assert (serie / serie.cummax() - 1).min() > -0.5   # sin saneo, acá había un -99%
    limpio, descartados = sanear_fx(fx.set_index("date")["adjusted_close"])
    assert list(descartados) == [5.0] and limpio.iloc[100] == 950.0


def test_oro_es_una_posicion_fija_y_no_contamina_el_universo_de_gamma6():
    """El oro no rankea ni predice: si hay historia, es 100% de su propia pieza.
    Y va con un `tipo` propio para no colarse en el universo de Gamma-6."""
    from src.strategy_engine import ORO_TICKER, oro

    prices, universe = _prices(), _universe()
    universe = pd.concat([universe, pd.DataFrame([{"alphadata_ticker": ORO_TICKER, "yahoo_ticker": ORO_TICKER, "nombre": "Oro", "tipo": "etf_us", "moneda": "USD", "estado": "activo"}])], ignore_index=True)
    fechas = sorted(prices.date.unique())
    serie = pd.DataFrame({"date": fechas, "alphadata_ticker": ORO_TICKER, "adjusted_close": np.linspace(100, 150, len(fechas))})
    for columna in ["open", "high", "low", "close"]:
        serie[columna] = serie["adjusted_close"]
    serie["volume"] = 0.0
    con_oro = pd.concat([prices, serie], ignore_index=True)

    cartera, auditoria = oro(con_oro, universe, con_oro.date.max())
    assert cartera.ticker.tolist() == [ORO_TICKER] and cartera.target_weight.tolist() == [1.0]
    assert bool(auditoria.eligible.iloc[0])

    seleccion, _ = gamma6(con_oro, universe, con_oro.date.max())
    assert ORO_TICKER not in set(seleccion.ticker)   # no entra al universo de acciones

    corta, auditoria_corta = oro(con_oro[con_oro.date <= fechas[30]], universe, fechas[30])
    assert corta.empty and auditoria_corta.reason.iloc[0] == "historia insuficiente"
