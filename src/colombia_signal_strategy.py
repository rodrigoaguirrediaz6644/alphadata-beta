from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rules:
    rsi_period: int = 14
    rsi_entry_min: float = 45.0
    rsi_entry_max: float = 80.0
    rsi_exit: float = 38.0
    fast_ma: int = 50
    slow_ma: int = 200
    breakout_days: int = 20
    relative_strength_days: int = 126
    atr_period: int = 14
    atr_stop_multiple: float = 3.0
    index_ma: int = 200
    vix_max: float = 32.0
    vix_panic: float = 40.0
    max_positions: int = 5
    cost_rate: float = 0.001785


def rsi(price: pd.Series, period: int = 14) -> pd.Series:
    change = price.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(loss.ne(0), 100.0)


def _indicators(
    prices: pd.DataFrame,
    benchmark: pd.Series,
    vix: pd.Series,
    rules: Rules,
) -> dict[str, pd.DataFrame | pd.Series]:
    returns = prices.pct_change(fill_method=None)
    fast = prices.rolling(rules.fast_ma).mean()
    slow = prices.rolling(rules.slow_ma).mean()
    rsi_frame = prices.apply(rsi, period=rules.rsi_period)
    breakout = prices.shift(1).rolling(rules.breakout_days).max()
    asset_mom = prices / prices.shift(rules.relative_strength_days) - 1
    bench_mom = benchmark / benchmark.shift(rules.relative_strength_days) - 1
    strength = asset_mom.sub(bench_mom, axis=0)
    vol = returns.rolling(63).std() * np.sqrt(252)
    bench_ma = benchmark.rolling(rules.index_ma).mean()
    aligned_vix = vix.reindex(prices.index).ffill()
    return {
        "fast": fast,
        "slow": slow,
        "rsi": rsi_frame,
        "breakout": breakout,
        "strength": strength,
        "vol": vol,
        "market_ok": benchmark.gt(bench_ma) & aligned_vix.lt(rules.vix_max),
        "panic": aligned_vix.ge(rules.vix_panic),
    }


def backtest_signals(
    prices: pd.DataFrame,
    benchmark: pd.Series,
    vix: pd.Series,
    rules: Rules = Rules(),
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """Long-only backtest; signals at close t execute for return t+1."""
    prices = prices.sort_index()
    benchmark = benchmark.reindex(prices.index).ffill()
    ind = _indicators(prices, benchmark, vix, rules)
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    weights = pd.Series(0.0, index=prices.columns)
    nav = 1.0
    nav_rows: list[tuple[pd.Timestamp, float]] = []
    weight_rows: list[pd.Series] = []
    trades: list[dict] = []
    peaks = pd.Series(np.nan, index=prices.columns)

    for date in prices.index:
        day_return = float((weights * returns.loc[date]).sum())
        nav *= 1.0 + day_return
        gross = weights * (1 + returns.loc[date])
        if gross.sum() > 0:
            weights = gross / gross.sum()

        held = weights.gt(0)
        position = prices.index.get_loc(date)
        next_date = prices.index[position + 1] if position + 1 < len(prices.index) else None
        month_end = next_date is None or (date.year, date.month) != (next_date.year, next_date.month)
        if not month_end and not bool(ind["panic"].loc[date]):
            nav_rows.append((date, nav))
            weight_rows.append(weights.rename(date))
            continue

        peaks.loc[held] = pd.concat([peaks.loc[held], prices.loc[date, held]], axis=1).max(axis=1)
        trailing_floor = peaks * (1 - rules.atr_stop_multiple * ind["vol"].loc[date] / np.sqrt(252))
        exit_signal = (
            prices.loc[date].lt(ind["slow"].loc[date])
            | ind["rsi"].loc[date].lt(rules.rsi_exit)
            | prices.loc[date].lt(trailing_floor)
            | bool(ind["panic"].loc[date])
        ) & held

        eligible = (
            prices.loc[date].gt(ind["fast"].loc[date])
            & ind["fast"].loc[date].gt(ind["slow"].loc[date])
            & prices.loc[date].ge(ind["breakout"].loc[date])
            & ind["rsi"].loc[date].between(rules.rsi_entry_min, rules.rsi_entry_max)
            & ind["strength"].loc[date].gt(0)
            & bool(ind["market_ok"].loc[date])
        )
        score = (
            ind["strength"].loc[date].rank(pct=True)
            + ind["rsi"].loc[date].sub(50).clip(lower=0).rank(pct=True)
            - ind["vol"].loc[date].rank(pct=True)
        )
        selected = score.where(eligible).nlargest(rules.max_positions).dropna().index
        target_names = set(weights.index[held & ~exit_signal]) | set(selected)
        ranked = score.reindex(list(target_names)).sort_values(ascending=False).head(rules.max_positions)
        target = pd.Series(0.0, index=prices.columns)
        if len(ranked):
            target.loc[ranked.index] = 1 / len(ranked)

        delta = target - weights
        turnover = float(delta.abs().sum())
        if turnover:
            nav *= 1 - turnover * rules.cost_rate
            for ticker, amount in delta[delta.ne(0)].items():
                trades.append(
                    {"date": date, "ticker": ticker, "action": "BUY" if amount > 0 else "SELL",
                     "weight_change": float(amount), "price": float(prices.loc[date, ticker])}
                )
        exited = weights.gt(0) & target.eq(0)
        peaks.loc[exited] = np.nan
        weights = target
        nav_rows.append((date, nav))
        weight_rows.append(weights.rename(date))

    nav_series = pd.Series(dict(nav_rows), name="COLOMBIA_SIGNALS")
    return nav_series, pd.DataFrame(weight_rows), pd.DataFrame(trades)


def performance(nav: pd.Series) -> dict[str, float]:
    nav = nav.dropna()
    daily = nav.pct_change().dropna()
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    drawdown = nav / nav.cummax() - 1
    cagr = nav.iloc[-1] ** (1 / years) - 1
    return {
        "total_return": float(nav.iloc[-1] - 1),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "volatility": float(daily.std() * np.sqrt(252)),
        "calmar": float(cagr / abs(drawdown.min())) if drawdown.min() < 0 else np.nan,
    }


def load_rules(path: Path) -> Rules:
    return Rules(**json.loads(path.read_text(encoding="utf-8"))["rules"])
