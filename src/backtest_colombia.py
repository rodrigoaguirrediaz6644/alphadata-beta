from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "colombia_baseline_v1.json"
DEFAULT_OUTPUT = ROOT / "data" / "colombia_baseline"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def download_adjusted(symbol: str, start: str) -> pd.Series:
    import yfinance as yf

    raw = yf.download(
        symbol,
        start=start,
        interval="1d",
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
        timeout=30,
    )
    if raw.empty:
        return pd.Series(dtype=float, name=symbol)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if "Adj Close" not in raw:
        return pd.Series(dtype=float, name=symbol)
    series = pd.to_numeric(raw["Adj Close"], errors="coerce")
    series.index = pd.to_datetime(series.index).tz_localize(None)
    return series[series.gt(0)].sort_index().rename(symbol)


def collect_prices(
    config: dict,
    downloader: Callable[[str, str], pd.Series] = download_adjusted,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    items = [*config["universe"], config["benchmark"]]
    columns: dict[str, pd.Series] = {}
    coverage = []
    for item in items:
        ticker, symbol = item["local_ticker"], item["provider_symbol"]
        series = downloader(symbol, config["start_date"])
        columns[ticker] = series
        coverage.append(
            {
                "local_ticker": ticker,
                "provider_symbol": symbol,
                "role": "benchmark" if ticker == config["benchmark"]["local_ticker"] else "asset",
                "rows": int(series.notna().sum()),
                "first_date": series.first_valid_index(),
                "last_date": series.last_valid_index(),
                "download_status": "OK" if series.notna().any() else "SIN_DATOS",
            }
        )
    return pd.concat(columns, axis=1).sort_index(), pd.DataFrame(coverage)


def buy_and_hold_nav(price: pd.Series, cost_rate: float) -> pd.Series:
    valid = price.dropna()
    if len(valid) < 2:
        return pd.Series(dtype=float, name=price.name)
    nav = (valid / valid.iloc[0]) * (1.0 - cost_rate)
    return nav.rename(price.name)


def equal_weight_monthly_nav(prices: pd.DataFrame, cost_rate: float) -> pd.Series:
    returns = prices.pct_change(fill_method=None)
    nav_values: list[float] = []
    dates: list[pd.Timestamp] = []
    weights = pd.Series(0.0, index=prices.columns)
    nav = 1.0
    previous_month: tuple[int, int] | None = None

    for date, row in prices.iterrows():
        daily = returns.loc[date].where(weights.ne(0), 0.0).fillna(0.0)
        nav *= 1.0 + float((weights * daily).sum())

        gross_weights = weights * (1.0 + daily)
        total = float(gross_weights.sum())
        if total > 0:
            weights = gross_weights / total

        month = (date.year, date.month)
        available = row.notna()
        if previous_month != month or (weights.eq(0).all() and available.any()):
            target = pd.Series(0.0, index=prices.columns)
            if available.any():
                target.loc[available] = 1.0 / int(available.sum())
            turnover = float((target - weights).abs().sum())
            nav *= 1.0 - turnover * cost_rate
            weights = target
            previous_month = month

        nav_values.append(nav)
        dates.append(date)

    return pd.Series(nav_values, index=dates, name="EQUAL_WEIGHT_11")


def performance_metrics(nav: pd.Series) -> dict[str, float | str | int]:
    nav = nav.dropna()
    if len(nav) < 2:
        return {"rows": int(len(nav)), "status": "INSUFFICIENT_DATA"}
    daily = nav.pct_change().dropna()
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    total_return = nav.iloc[-1] - 1.0
    cagr = nav.iloc[-1] ** (1.0 / years) - 1.0 if years > 0 else np.nan
    anchored = pd.concat([pd.Series([1.0], index=[nav.index[0] - pd.Timedelta(days=1)]), nav])
    drawdown = anchored / anchored.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    volatility = float(daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 else np.nan
    downside = daily[daily.lt(0)]
    downside_vol = float(downside.std(ddof=1) * np.sqrt(252)) if len(downside) > 1 else np.nan
    sortino = float(cagr / downside_vol) if downside_vol and downside_vol > 0 else np.nan
    calmar = float(cagr / abs(max_drawdown)) if max_drawdown < 0 else np.nan
    monthly = nav.resample("ME").last().pct_change().dropna()
    return {
        "status": "OK",
        "rows": int(len(nav)),
        "first_date": nav.index[0].date().isoformat(),
        "last_date": nav.index[-1].date().isoformat(),
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "calmar": calmar,
        "sortino": sortino,
        "negative_month_ratio": float(monthly.lt(0).mean()) if len(monthly) else np.nan,
    }


def run_backtest(config: dict, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cost = float(config["transaction_cost_rate"])
    benchmark = config["benchmark"]["local_ticker"]
    assets = [item["local_ticker"] for item in config["universe"]]
    navs = {
        ticker: buy_and_hold_nav(prices[ticker], cost)
        for ticker in assets
        if ticker in prices
    }
    if benchmark in prices:
        navs[benchmark] = buy_and_hold_nav(prices[benchmark], cost)
    available_assets = prices.reindex(columns=assets)
    navs["EQUAL_WEIGHT_11"] = equal_weight_monthly_nav(available_assets, cost)
    nav = pd.concat(navs, axis=1).sort_index()
    metrics = pd.DataFrame(
        [{"portfolio": name, **performance_metrics(nav[name])} for name in nav.columns]
    )
    return nav, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest base experimental de Colombia")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    config = load_config(args.config)
    prices, coverage = collect_prices(config)
    nav, metrics = run_backtest(config, prices)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prices.to_csv(args.output_dir / "adjusted_prices.csv", index_label="date")
    coverage.to_csv(args.output_dir / "coverage.csv", index=False)
    nav.to_csv(args.output_dir / "nav.csv", index_label="date")
    metrics.to_csv(args.output_dir / "metrics.csv", index=False)
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
