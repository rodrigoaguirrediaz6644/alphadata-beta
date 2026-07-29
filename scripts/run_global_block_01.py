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
from src.global_momentum_strategy import GlobalMomentumConfig


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


def diagnostic_configs(block: dict) -> dict[str, GlobalMomentumConfig]:
    common = {
        "max_positions": len(block["instruments"]),
        "max_weight_per_asset": 0.12,
        "max_weight_per_country": 0.12,
        "max_weight_per_sector": 1.0,
        "min_adv_base": 1.0,
    }
    return {
        "baseline": GlobalMomentumConfig(**common),
        "equal_weight": GlobalMomentumConfig(**common, weighting_method="equal"),
        "momentum_only": GlobalMomentumConfig(**common, require_trend=False),
        "trend_only": GlobalMomentumConfig(
            **common, require_positive_momentum=False
        ),
        "always_invested_equal": GlobalMomentumConfig(
            **common,
            weighting_method="equal",
            require_trend=False,
            require_positive_momentum=False,
        ),
    }


def run(block_path: Path, output_dir: Path, diagnostics: bool = False) -> dict:
    block = load_block(block_path)
    prices = download_prices(block)
    variants = (
        diagnostic_configs(block)
        if diagnostics
        else {"baseline": diagnostic_configs(block)["baseline"]}
    )
    reference_nav = benchmark_nav(prices, block["benchmark"])
    navs: dict[str, pd.Series] = {}
    summaries: dict[str, dict] = {}
    weights_by_variant: dict[str, pd.DataFrame] = {}
    for name, config in variants.items():
        strategy_nav, weights = backtest_from_prices(prices, block, config)
        strategy_nav = strategy_nav.rename(name)
        navs[name] = strategy_nav
        weights_by_variant[name] = weights
        exposure = weights.sum(axis=1)
        first_invested = exposure[exposure.gt(0)].index.min()
        summaries[name] = {
            **performance(strategy_nav),
            "average_exposure": float(exposure.mean()),
            "median_exposure": float(exposure.median()),
            "max_exposure": float(exposure.max()),
            "first_invested_date": (
                first_invested.date().isoformat() if pd.notna(first_invested) else None
            ),
        }
    combined = pd.concat([*navs.values(), reference_nav], axis=1).dropna(how="all")
    summary = {
        "block_code": block["block_code"],
        "status": block["status"],
        "data_start": prices.dropna(how="all").index.min().date().isoformat(),
        "data_end": prices.dropna(how="all").index.max().date().isoformat(),
        "cost_rate": block["cost_rate"],
        "variants": summaries,
        "benchmark": performance(reference_nav),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output_dir / "adjusted_prices.csv", index_label="date")
    combined.to_csv(output_dir / "nav.csv", index_label="date")
    for name, weights in weights_by_variant.items():
        weights.to_csv(output_dir / f"weights_{name}.csv", index_label="date")
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
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    run(args.block, args.output, diagnostics=args.diagnostics)


if __name__ == "__main__":
    main()
