"""Backtest económico por bloques para la cartera global de AlphaData."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.global_momentum_strategy import GlobalMomentumConfig, generate_target_weights


def load_block(path: Path) -> dict:
    block = json.loads(path.read_text(encoding="utf-8"))
    tickers = [item["ticker"] for item in block["instruments"]]
    if len(tickers) != len(set(tickers)):
        raise ValueError("El bloque contiene instrumentos duplicados.")
    if block["benchmark"] in tickers:
        raise ValueError("El benchmark debe permanecer fuera de la cartera.")
    return block


def prices_to_panel(prices: pd.DataFrame, block: dict) -> pd.DataFrame:
    """Convierte precios ajustados USD a la interfaz fechada del motor."""
    rows = []
    for item in block["instruments"]:
        ticker = item["ticker"]
        if ticker not in prices:
            continue
        series = prices[ticker].dropna()
        for date, price in series.items():
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "country": item["country"],
                    "sector": item["sector"],
                    "price_local": float(price),
                    "fx_to_base": 1.0,
                    # Los ETF de este bloque se filtran por catálogo; el bloque
                    # de acciones incorporará ADV histórico observado.
                    "adv_base": 1_000_000_000.0,
                }
            )
    if not rows:
        raise ValueError("No existen precios utilizables para el bloque.")
    return pd.DataFrame(rows)


def backtest_from_prices(
    prices: pd.DataFrame,
    block: dict,
    config: GlobalMomentumConfig | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Ejecuta al cierre siguiente, deja derivar posiciones y cobra costos.

    Las señales calculadas con el cierre de una rueda se ejecutan al cierre de
    la rueda siguiente. Por tanto, el nuevo peso participa en los retornos
    recién desde la jornada posterior a su ejecución.
    """
    config = config or GlobalMomentumConfig(
        max_positions=len(block["instruments"]),
        max_weight_per_asset=0.12,
        max_weight_per_country=0.12,
        max_weight_per_sector=1.0,
        min_adv_base=1.0,
    )
    panel = prices_to_panel(prices, block)
    targets = generate_target_weights(panel, config)
    asset_targets = (
        targets.loc[targets["ticker"].ne("CASH")]
        .pivot(index="date", columns="ticker", values="weight")
        .reindex(columns=[item["ticker"] for item in block["instruments"]])
        .fillna(0.0)
    )
    calendar = prices.index.sort_values()
    columns = asset_targets.columns
    returns = prices.reindex(index=calendar, columns=columns).pct_change(fill_method=None)

    execution_targets: dict[pd.Timestamp, pd.Series] = {}
    for decision_date, target in asset_targets.iterrows():
        next_dates = calendar[calendar > decision_date]
        if len(next_dates):
            execution_targets[next_dates[0]] = target

    asset_values = pd.Series(0.0, index=columns)
    cash = 1.0
    nav_records: list[float] = []
    weight_records: list[pd.Series] = []
    cost_rate = float(block["cost_rate"])

    for date in calendar:
        daily_return = returns.loc[date].fillna(0.0)
        asset_values *= 1.0 + daily_return
        nav_before_trade = float(asset_values.sum() + cash)

        if date in execution_targets:
            target = execution_targets[date].copy()
            unavailable = prices.loc[date, columns].isna()
            target.loc[unavailable] = 0.0
            pretrade_weights = (
                asset_values / nav_before_trade
                if nav_before_trade > 0
                else pd.Series(0.0, index=columns)
            )
            turnover = float((target - pretrade_weights).abs().sum())
            nav_after_cost = nav_before_trade * (1.0 - turnover * cost_rate)
            asset_values = target * nav_after_cost
            cash = nav_after_cost * max(0.0, 1.0 - float(target.sum()))
        else:
            nav_after_cost = nav_before_trade

        nav_records.append(nav_after_cost)
        if nav_after_cost > 0:
            weight_records.append(asset_values / nav_after_cost)
        else:
            weight_records.append(pd.Series(0.0, index=columns))

    nav = pd.Series(nav_records, index=calendar, name=block["block_code"])
    weights = pd.DataFrame(weight_records, index=calendar, columns=columns)
    return nav, weights


def benchmark_nav(prices: pd.DataFrame, ticker: str) -> pd.Series:
    """Normaliza un benchmark de comprar y mantener en su primera fecha válida."""
    if ticker not in prices:
        raise ValueError(f"No existe el benchmark {ticker} en los precios.")
    series = prices[ticker].dropna()
    if series.empty:
        raise ValueError(f"El benchmark {ticker} no tiene precios utilizables.")
    return (series / series.iloc[0]).rename(ticker)


def performance(nav: pd.Series) -> dict[str, float]:
    nav = nav.dropna()
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    drawdown = nav / nav.cummax() - 1.0
    cagr = nav.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    return {
        "total_return": float(nav.iloc[-1] - 1.0),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "calmar": float(cagr / abs(drawdown.min())) if drawdown.min() < 0 else np.nan,
    }
