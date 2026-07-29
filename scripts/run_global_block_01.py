"""Ejecuta y conserva un backtest reproducible de un bloque global."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.global_instrument_backtest import (
    backtest_from_prices,
    benchmark_nav,
    load_block,
    performance,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOCK_PATH = ROOT / "config" / "global_universe_block_01.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "global_block_01"


def download_prices(block: dict) -> pd.DataFrame:
    tickers = [item["ticker"] for item in block["instruments"]]
    tickers.append(block["benchmark"])
    raw = yf.download(
        tickers=tickers,
        start=block["start_date"],
        auto_adjust=True,
        actions=False,
        progress=False,
        group_by="column",
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("La descarga no devolvió precios.")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index().reindex(columns=tickers)
    missing = [ticker for ticker in tickers if close[ticker].dropna().empty]
    if missing:
        raise RuntimeError(f"Instrumentos sin historia: {missing}")
    return close


def annual_returns(nav: pd.DataFrame) -> pd.DataFrame:
    year_end = nav.groupby(nav.index.year).last()
    year_start = nav.groupby(nav.index.year).first()
    result = year_end / year_start - 1.0
    result.index.name = "year"
    return result


def run(block_path: Path, output_dir: Path) -> dict:
    block = load_block(block_path)
    prices = download_prices(block)
    strategy_nav, weights = backtest_from_prices(prices, block)
    reference_nav = benchmark_nav(prices, block["benchmark"])
    combined = pd.concat([strategy_nav, reference_nav], axis=1).dropna(how="all")

    strategy_exposure = weights.sum(axis=1)
    first_invested = strategy_exposure[strategy_exposure.gt(0)].index.min()
    summary = {
        "block_code": block["block_code"],
        "status": block["status"],
        "data_start": prices.dropna(how="all").index.min().date().isoformat(),
        "data_end": prices.dropna(how="all").index.max().date().isoformat(),
        "first_invested_date": (
            first_invested.date().isoformat() if pd.notna(first_invested) else None
        ),
        "cost_rate": block["cost_rate"],
        "strategy": performance(strategy_nav),
        "benchmark": performance(reference_nav),
        "average_exposure": float(strategy_exposure.mean()),
        "median_exposure": float(strategy_exposure.median()),
        "max_exposure": float(strategy_exposure.max()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output_dir / "adjusted_prices.csv", index_label="date")
    combined.to_csv(output_dir / "nav.csv", index_label="date")
    weights.to_csv(output_dir / "weights.csv", index_label="date")
    annual_returns(combined).to_csv(output_dir / "annual_returns.csv")
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=Path, default=DEFAULT_BLOCK_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    run(args.block, args.output)


if __name__ == "__main__":
    main()
