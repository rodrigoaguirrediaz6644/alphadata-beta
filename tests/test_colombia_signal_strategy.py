import numpy as np
import pandas as pd

from src.colombia_signal_strategy import Rules, backtest_signals, performance, rsi


def fixture(periods=320):
    dates = pd.bdate_range("2024-01-01", periods=periods)
    a = np.linspace(100, 250, periods) + 5 * np.sin(np.arange(periods) / 4)
    prices = pd.DataFrame({"A": a, "B": a * 0.98}, index=dates)
    benchmark = pd.Series(np.linspace(100, 130, periods), index=dates)
    vix = pd.Series(15.0, index=dates)
    rules = Rules(
        breakout_days=20, relative_strength_days=20, fast_ma=10, slow_ma=30,
        index_ma=30, rsi_entry_max=100,
    )
    return dates, prices, benchmark, vix, rules


def test_rsi_is_bounded():
    values = pd.Series(np.linspace(100, 140, 80) + np.sin(np.arange(80)))
    assert rsi(values).dropna().between(0, 100).all()


def test_signal_executes_after_decision_day():
    _, prices, benchmark, vix, rules = fixture()
    nav, weights, trades = backtest_signals(prices, benchmark, vix, rules)
    first_buy = trades.loc[trades.action.eq("BUY")].iloc[0]
    assert nav.loc[first_buy.date] <= 1.0
    assert weights.loc[first_buy.date, first_buy.ticker] > 0


def test_single_position_never_consumes_all_cash():
    _, prices, benchmark, vix, rules = fixture()
    prices = prices[["A"]]
    _, weights, _ = backtest_signals(prices, benchmark, vix, rules)
    weekly = weights.groupby(weights.index.to_period("W-FRI")).tail(1)
    assert weekly.max().max() <= rules.max_position_weight + 1e-12
    assert weekly.sum(axis=1).max() <= rules.max_position_weight + 1e-12


def test_cash_is_not_renormalized_after_asset_return():
    _, prices, benchmark, vix, rules = fixture()
    prices = prices[["A"]]
    _, weights, _ = backtest_signals(prices, benchmark, vix, rules)
    invested = weights["A"][weights["A"].gt(0)]
    assert invested.max() < 0.30


def test_vix_panic_exits_all_positions():
    _, prices, benchmark, vix, rules = fixture()
    vix.iloc[-2:] = 45.0
    _, weights, _ = backtest_signals(prices, benchmark, vix, rules)
    assert weights.iloc[-1].eq(0).all()


def test_weekly_stop_can_exit_before_month_end():
    dates, prices, benchmark, vix, rules = fixture()
    prices.loc[dates[-8]:, "A"] *= 0.70
    prices = prices[["A"]]
    _, _, trades = backtest_signals(prices, benchmark, vix, rules)
    last_sell = pd.Timestamp(trades.loc[trades.action.eq("SELL"), "date"].iloc[-1])
    assert last_sell.weekday() == 4


def test_performance_reports_drawdown():
    dates = pd.bdate_range("2020-01-01", periods=600)
    nav = pd.Series(np.linspace(1, 2, len(dates)), index=dates)
    nav.iloc[300] = 0.8
    result = performance(nav)
    assert result["cagr"] > 0
    assert result["max_drawdown"] < 0
