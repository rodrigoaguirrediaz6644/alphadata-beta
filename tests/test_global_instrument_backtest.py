import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.global_instrument_backtest import backtest_from_prices, load_block
from src.global_momentum_strategy import GlobalMomentumConfig


ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "config" / "global_universe_block_01.json"


def test_block_01_is_small_unique_and_benchmark_is_separate():
    block = load_block(BLOCK)
    tickers = [item["ticker"] for item in block["instruments"]]
    assert len(tickers) == len(set(tickers)) == 10
    assert block["benchmark"] == "ACWI"
    assert "ACWI" not in tickers
    assert block["status"] == "diagnostic"


def test_backtest_applies_signal_after_decision_and_charges_costs():
    block = json.loads(BLOCK.read_text(encoding="utf-8"))
    block["instruments"] = block["instruments"][:2]
    dates = pd.bdate_range("2020-01-01", periods=90)
    prices = pd.DataFrame(
        {
            "SPY": 100 * 1.002 ** np.arange(len(dates)),
            "EWC": 100 * 1.001 ** np.arange(len(dates)),
        },
        index=dates,
    )
    config = GlobalMomentumConfig(
        momentum_long_days=20,
        momentum_short_days=10,
        volatility_days=5,
        trend_days=15,
        max_positions=2,
        max_weight_per_asset=0.5,
        max_weight_per_country=0.5,
        max_weight_per_sector=1.0,
        min_adv_base=1,
    )
    nav, weights = backtest_from_prices(prices, block, config)
    first_invested = weights.sum(axis=1).gt(0).idxmax()
    previous_day = weights.index[weights.index.get_loc(first_invested) - 1]
    assert weights.loc[previous_day].sum() == 0
    assert nav.loc[first_invested] < (
        1 + (weights.loc[first_invested] * prices.pct_change().loc[first_invested]).sum()
    )


def test_missing_history_does_not_reallocate_to_unavailable_instrument():
    block = json.loads(BLOCK.read_text(encoding="utf-8"))
    block["instruments"] = block["instruments"][:2]
    dates = pd.bdate_range("2020-01-01", periods=90)
    prices = pd.DataFrame(
        {
            "SPY": 100 * 1.002 ** np.arange(len(dates)),
            "EWC": np.nan,
        },
        index=dates,
    )
    config = GlobalMomentumConfig(
        momentum_long_days=20,
        momentum_short_days=10,
        volatility_days=5,
        trend_days=15,
        max_positions=2,
        max_weight_per_asset=0.5,
        max_weight_per_country=0.5,
        max_weight_per_sector=1.0,
        min_adv_base=1,
    )
    _, weights = backtest_from_prices(prices, block, config)
    assert weights["EWC"].eq(0).all()
    assert weights.sum(axis=1).max() <= 0.5 + 1e-12
