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
    """Ejecuta al cierre, aplica pesos desde la rueda siguiente y cobra costos."""
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
    target_daily = asset_targets.reindex(calendar).ffill().shift(1).fillna(0.0)
    returns = prices.reindex(columns=target_daily.columns).pct_change(fill_method=None)
    usable = returns.notna().astype(float)
    weights = target_daily * usable
    gross_return = (weights * returns.fillna(0.0)).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1)
    if len(turnover):
        turnover.iloc[0] = weights.iloc[0].abs().sum()
    net_return = gross_return - turnover * float(block["cost_rate"])
    nav = (1.0 + net_return).cumprod().rename(block["block_code"])
    return nav, weights


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
