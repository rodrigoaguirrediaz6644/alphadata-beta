from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "strategy.json"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_signals(
    recommendations: pd.DataFrame,
    market_dates: pd.DatetimeIndex,
    tickers: list[str],
    staleness_days: int,
) -> pd.DataFrame:
    recommendations = recommendations.copy()
    recommendations["date"] = pd.to_datetime(recommendations["date"])
    rows: list[dict] = []

    for market_date in market_dates:
        cutoff = market_date - pd.Timedelta(days=staleness_days)
        available = recommendations.loc[
            (recommendations["date"] < market_date)
            & (recommendations["date"] >= cutoff)
        ]
        for ticker in tickers:
            subset = available.loc[available["ticker"] == ticker]
            latest = (
                subset.sort_values(["date", "source_page"])
                .drop_duplicates(subset=["broker"], keep="last")
            )
            scores = pd.to_numeric(latest["score"], errors="coerce").dropna()
            rows.append(
                {
                    "date": market_date,
                    "ticker": ticker,
                    "broker_count": int(len(scores)),
                    "consensus_score": float(scores.mean()) if len(scores) else np.nan,
                    "positive_count": int((scores > 0).sum()),
                    "neutral_count": int((scores == 0).sum()),
                    "negative_count": int((scores < 0).sum()),
                    "latest_recommendation_date": (
                        latest["date"].max() if len(latest) else pd.NaT
                    ),
                }
            )
    return pd.DataFrame(rows)


def choose_weights(signal_slice: pd.DataFrame, config: dict) -> dict[str, float]:
    candidates = signal_slice.loc[
        (signal_slice["broker_count"] >= config["min_brokers"])
        & (signal_slice["consensus_score"] >= config["entry_threshold"])
    ].sort_values(
        ["consensus_score", "broker_count", "ticker"],
        ascending=[False, False, True],
    )
    selected = candidates.head(config["top_n"])["ticker"].tolist()
    if not selected:
        return {}
    weight = 1.0 / len(selected)
    return {ticker: weight for ticker in selected}


def turnover(previous: dict[str, float], current: dict[str, float]) -> float:
    tickers = set(previous) | set(current)
    risky = sum(abs(current.get(t, 0.0) - previous.get(t, 0.0)) for t in tickers)
    previous_cash = 1.0 - sum(previous.values())
    current_cash = 1.0 - sum(current.values())
    return 0.5 * (risky + abs(current_cash - previous_cash))


def run_backtest(prices: pd.DataFrame, signals: pd.DataFrame, config: dict) -> pd.DataFrame:
    price_matrix = prices.pivot(index="date", columns="alphadata_ticker", values="close")
    price_matrix.index = pd.to_datetime(price_matrix.index)
    returns = price_matrix.pct_change(fill_method=None)
    cost_rate = config["transaction_cost_bps"] / 10_000
    previous_weights: dict[str, float] = {}
    equity = 1.0
    benchmark_equity = 1.0
    rows: list[dict] = []

    for index, market_date in enumerate(price_matrix.index):
        period_returns = returns.loc[market_date]
        gross_return = sum(
            weight * float(period_returns.get(ticker, 0.0))
            for ticker, weight in previous_weights.items()
            if pd.notna(period_returns.get(ticker, np.nan))
        )
        available_returns = period_returns.dropna()
        benchmark_return = float(available_returns.mean()) if len(available_returns) else 0.0

        signal_slice = signals.loc[signals["date"] == market_date]
        current_weights = choose_weights(signal_slice, config)
        period_turnover = turnover(previous_weights, current_weights)
        cost = period_turnover * cost_rate
        net_return = gross_return - cost
        equity *= 1.0 + net_return
        benchmark_equity *= 1.0 + benchmark_return

        rows.append(
            {
                "date": market_date,
                "gross_return": gross_return,
                "transaction_cost": cost,
                "net_return": net_return,
                "equity": equity,
                "universe_equal_weight_return": benchmark_return,
                "universe_equal_weight_equity": benchmark_equity,
                "turnover": period_turnover,
                "positions": "|".join(sorted(current_weights)),
                "position_count": len(current_weights),
                "cash_weight": 1.0 - sum(current_weights.values()),
                **{
                    f"weight_{ticker}": current_weights.get(ticker, 0.0)
                    for ticker in price_matrix.columns
                },
            }
        )
        previous_weights = current_weights
    return pd.DataFrame(rows)


def summarize(backtest: pd.DataFrame) -> pd.DataFrame:
    periods = max(len(backtest) - 1, 1)
    years = periods / 52
    total_return = backtest["equity"].iloc[-1] - 1
    benchmark_return = backtest["universe_equal_weight_equity"].iloc[-1] - 1
    annualized = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0
    running_max = backtest["equity"].cummax()
    drawdown = backtest["equity"] / running_max - 1
    return pd.DataFrame(
        [
            {
                "start_date": backtest["date"].min(),
                "end_date": backtest["date"].max(),
                "weeks": len(backtest),
                "total_return": total_return,
                "annualized_return": annualized,
                "annualized_volatility": backtest["net_return"].std(ddof=0) * np.sqrt(52),
                "max_drawdown": drawdown.min(),
                "benchmark_total_return": benchmark_return,
                "invested_weeks": int((backtest["position_count"] > 0).sum()),
                "average_positions": backtest["position_count"].mean(),
                "total_turnover": backtest["turnover"].sum(),
                "total_transaction_cost": backtest["transaction_cost"].sum(),
            }
        ]
    )


def main() -> None:
    config = load_config()
    prices = pd.read_csv(DATA_DIR / "prices_weekly.csv", parse_dates=["date"])
    recommendations = pd.read_csv(DATA_DIR / "recommendations_pilot.csv", parse_dates=["date"])
    local_prices = prices.loc[prices["alphadata_ticker"].isin(recommendations["ticker"].unique())]
    dates = pd.DatetimeIndex(sorted(local_prices["date"].unique()))
    tickers = sorted(recommendations["ticker"].unique())

    signals = build_signals(
        recommendations,
        dates,
        tickers,
        staleness_days=config["staleness_days"],
    )
    backtest = run_backtest(local_prices, signals, config)
    summary = summarize(backtest)

    signals.to_csv(DATA_DIR / "signals_weekly.csv", index=False, date_format="%Y-%m-%d")
    backtest.to_csv(DATA_DIR / "backtest_weekly.csv", index=False, date_format="%Y-%m-%d")
    summary.to_csv(DATA_DIR / "backtest_summary.csv", index=False, date_format="%Y-%m-%d")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

