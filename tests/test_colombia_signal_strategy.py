import numpy as np
import pandas as pd

from src.colombia_signal_strategy import Rules, backtest_signals, performance, rsi


def test_rsi_is_bounded():
    values = pd.Series(np.linspace(100, 140, 80) + np.sin(np.arange(80)))
    result = rsi(values)
    assert result.dropna().between(0, 100).all()


def test_signal_executes_after_decision_day():
    dates = pd.bdate_range("2024-01-01", periods=280)
    base = np.linspace(100, 200, len(dates)) + 4 * np.sin(np.arange(len(dates)) / 4)
    prices = pd.DataFrame({"A": base, "B": np.linspace(100, 90, len(dates))}, index=dates)
    benchmark = pd.Series(np.linspace(100, 120, len(dates)), index=dates)
    vix = pd.Series(15.0, index=dates)
    rules = Rules(
        breakout_days=20, relative_strength_days=20, fast_ma=10, slow_ma=30,
        index_ma=30, rsi_entry_max=100,
    )
    nav, weights, trades = backtest_signals(prices, benchmark, vix, rules)
    first_buy = trades.loc[trades.action.eq("BUY")].iloc[0]
    assert nav.loc[first_buy.date] <= 1.0
    assert weights.loc[first_buy.date, first_buy.ticker] > 0


def test_vix_panic_exits_all_positions():
    dates = pd.bdate_range("2024-01-01", periods=320)
    price = pd.Series(
        np.linspace(100, 250, len(dates)) + 5 * np.sin(np.arange(len(dates)) / 4),
        index=dates,
    )
    prices = pd.DataFrame({"A": price})
    benchmark = pd.Series(np.linspace(100, 130, len(dates)), index=dates)
    vix = pd.Series(15.0, index=dates)
    vix.iloc[-2:] = 45.0
    rules = Rules(
        breakout_days=20, relative_strength_days=20, fast_ma=10, slow_ma=30,
        index_ma=30, rsi_entry_max=100,
    )
    _, weights, _ = backtest_signals(prices, benchmark, vix, rules)
    assert weights.iloc[-1].eq(0).all()


def test_performance_reports_drawdown():
    dates = pd.bdate_range("2020-01-01", periods=600)
    nav = pd.Series(np.linspace(1, 2, len(dates)), index=dates)
    nav.iloc[300] = 0.8
    result = performance(nav)
    assert result["cagr"] > 0
    assert result["max_drawdown"] < 0
