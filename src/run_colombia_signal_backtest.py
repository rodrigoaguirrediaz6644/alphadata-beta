from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.backtest_colombia import DEFAULT_CONFIG, collect_prices, load_config
from src.colombia_signal_strategy import backtest_signals, load_rules, performance

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "config" / "colombia_signals_v1.json"


def download_vix(start: str) -> pd.Series:
    import yfinance as yf

    raw = yf.download(
        "^VIX", start=start, interval="1d", auto_adjust=False,
        progress=False, threads=False, timeout=30
    )
    if raw.empty:
        raise RuntimeError("VIX sin datos; no se ejecuta un backtest parcial")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    series = pd.to_numeric(raw["Close"], errors="coerce").dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    return series.sort_index().rename("VIX")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest de señales objetivas de Colombia")
    parser.add_argument("--baseline-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "colombia_signals")
    args = parser.parse_args()

    config = load_config(args.baseline_config)
    prices, coverage = collect_prices(config)
    benchmark_name = config["benchmark"]["local_ticker"]
    assets = [item["local_ticker"] for item in config["universe"]]
    vix = download_vix(config["start_date"])
    nav, weights, trades = backtest_signals(
        prices.reindex(columns=assets),
        prices[benchmark_name],
        vix,
        load_rules(args.rules),
    )

    periods = {
        "full": nav,
        "train_2015_2020": nav.loc[:"2020-12-31"],
        "test_2021_present": nav.loc["2021-01-01":],
    }
    metrics = []
    for name, series in periods.items():
        normalized = series / series.iloc[0]
        metrics.append({"period": name, **performance(normalized)})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    nav.to_csv(args.output_dir / "nav.csv", index_label="date")
    weights.to_csv(args.output_dir / "weights.csv", index_label="date")
    trades.to_csv(args.output_dir / "trades.csv", index=False)
    coverage.to_csv(args.output_dir / "coverage.csv", index=False)
    pd.DataFrame(metrics).to_csv(args.output_dir / "metrics.csv", index=False)
    vix.to_csv(args.output_dir / "vix.csv", index_label="date")
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == "__main__":
    main()
