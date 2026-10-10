import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest_colombia import (
    buy_and_hold_nav,
    equal_weight_monthly_nav,
    performance_metrics,
    run_backtest,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "colombia_baseline_v1.json"


def test_config_has_exact_validated_universe_and_separate_benchmark():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    tickers = [item["local_ticker"] for item in config["universe"]]
    assert tickers == [
        "PFCIBEST", "ISA", "ECOPETROL", "GEB", "GRUPOSURA", "CEMARGOS",
        "GRUPOARGOS", "PFAVAL", "CELSIA", "CORFICOLCF", "EXITO",
    ]
    assert len(tickers) == len(set(tickers)) == 11
    assert config["benchmark"]["local_ticker"] == "ICOLCAP"
    assert "ICOLCAP" not in tickers
    assert config["base_currency"] == "COP"
    assert config["status"] == "experimental"


def test_buy_and_hold_charges_initial_transaction_cost():
    dates = pd.bdate_range("2025-01-02", periods=3)
    price = pd.Series([100.0, 110.0, 121.0], index=dates, name="TEST")
    nav = buy_and_hold_nav(price, 0.01)
    assert nav.iloc[0] == 0.99
    assert nav.iloc[-1] == 1.1979


def test_equal_weight_uses_only_prices_known_before_the_day():
    dates = pd.bdate_range("2025-01-02", periods=4)
    prices = pd.DataFrame(
        {"A": [100.0, 110.0, 121.0, 133.1], "B": [np.nan, 100.0, 200.0, 200.0]},
        index=dates,
    )
    nav = equal_weight_monthly_nav(prices, 0.0)
    # B cannot enter on the same day as its first observed price.
    assert nav.iloc[1] == 1.10
    assert np.isclose(nav.iloc[2], 1.21)


def test_equal_weight_charges_turnover_at_monthly_rebalance():
    dates = pd.to_datetime(["2025-01-30", "2025-01-31", "2025-02-03"])
    prices = pd.DataFrame({"A": [100.0, 100.0, 100.0]}, index=dates)
    nav = equal_weight_monthly_nav(prices, 0.01)
    assert nav.iloc[0] == 0.99
    assert nav.iloc[2] == 0.99


def test_performance_metrics_reports_drawdown_and_months():
    dates = pd.date_range("2024-01-31", periods=4, freq="ME")
    nav = pd.Series([1.0, 1.2, 0.9, 1.3], index=dates)
    metrics = performance_metrics(nav)
    assert metrics["status"] == "OK"
    assert metrics["max_drawdown"] == -0.25
    assert metrics["negative_month_ratio"] == 1 / 3


def test_run_backtest_keeps_benchmark_out_of_equal_weight_portfolio():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    dates = pd.bdate_range("2025-01-02", periods=40)
    prices = pd.DataFrame(
        {
            **{item["local_ticker"]: np.linspace(100, 110, len(dates)) for item in config["universe"]},
            "ICOLCAP": np.linspace(100, 90, len(dates)),
        },
        index=dates,
    )
    nav, metrics = run_backtest(config, prices)
    assert set(["EQUAL_WEIGHT_11", "ICOLCAP"]).issubset(nav.columns)
    assert nav["EQUAL_WEIGHT_11"].iloc[-1] > nav["EQUAL_WEIGHT_11"].iloc[0]
    assert metrics.loc[metrics["portfolio"].eq("ICOLCAP"), "total_return"].iloc[0] < 0
