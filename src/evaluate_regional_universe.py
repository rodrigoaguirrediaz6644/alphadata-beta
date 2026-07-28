from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
COUNTRY_FILES = {"PERU": CONFIG_DIR / "universe_peru.csv", "COLOMBIA": CONFIG_DIR / "universe_colombia.csv"}
START_DATE = "2015-01-01"


@dataclass(frozen=True)
class Thresholds:
    min_history_years: float = 3.0
    min_market_coverage: float = 0.95
    min_adjusted_coverage: float = 0.95
    min_traded_day_ratio: float = 0.80
    max_staleness_days: int = 10
    liquidity_quantile: float = 0.40


def download_symbol(symbol: str, start: str = START_DATE, attempts: int = 3) -> pd.DataFrame:
    import yfinance as yf

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            raw = yf.download(
                symbol, start=start, interval="1d", auto_adjust=False, actions=True,
                progress=False, threads=False, timeout=30,
            )
            if not raw.empty:
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                raw.index = pd.to_datetime(raw.index).tz_localize(None)
                return raw.sort_index()
        except Exception as error:
            last_error = error
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    if last_error:
        print(f"ADVERTENCIA {symbol}: {last_error}")
    return pd.DataFrame()


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        return pd.Series(index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce")


def raw_metrics(frame: pd.DataFrame, checked_at: pd.Timestamp) -> dict[str, object]:
    if frame.empty or "Close" not in frame:
        return {
            "rows": 0, "first_date": "", "last_date": "", "history_years": 0.0,
            "adjusted_coverage": 0.0, "traded_day_ratio": 0.0,
            "median_value_traded_local": 0.0, "staleness_days": None,
            "dividend_events": 0, "split_events": 0, "download_status": "SIN_DATOS",
        }
    close = _series(frame, "Close")
    valid = close.gt(0)
    work = frame.loc[valid].copy()
    if work.empty:
        return raw_metrics(pd.DataFrame(), checked_at)
    adjusted = _series(work, "Adj Close")
    volume = _series(work, "Volume").fillna(0)
    first, last = work.index.min(), work.index.max()
    years = max((last - first).days / 365.25, 0.0)
    dividends = _series(work, "Dividends").fillna(0)
    splits = _series(work, "Stock Splits").fillna(0)
    return {
        "rows": int(len(work)),
        "first_date": first.date().isoformat(),
        "last_date": last.date().isoformat(),
        "history_years": round(years, 3),
        "adjusted_coverage": float(adjusted.notna().mean()),
        "traded_day_ratio": float(volume.gt(0).mean()),
        "median_value_traded_local": float((close.loc[work.index] * volume).replace(0, np.nan).median() or 0),
        "staleness_days": int(max((checked_at.normalize() - last.normalize()).days, 0)),
        "dividend_events": int(dividends.gt(0).sum()),
        "split_events": int(splits.ne(0).sum()),
        "download_status": "OK",
    }


def evaluate_country(
    universe: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    checked_at: pd.Timestamp,
    thresholds: Thresholds = Thresholds(),
) -> pd.DataFrame:
    market_dates = sorted({date for frame in frames.values() for date in frame.index})
    rows: list[dict[str, object]] = []
    for item in universe.to_dict("records"):
        symbol = str(item["data_symbol_candidate"])
        frame = frames.get(symbol, pd.DataFrame())
        metrics = raw_metrics(frame, checked_at)
        valid_dates = set(frame.index[frame["Close"].notna()]) if not frame.empty and "Close" in frame else set()
        if metrics["first_date"] and market_dates:
            first = pd.Timestamp(metrics["first_date"])
            comparable = {date for date in market_dates if date >= first}
            market_coverage = len(valid_dates & comparable) / len(comparable) if comparable else 0.0
        else:
            market_coverage = 0.0
        rows.append({**item, **metrics, "market_coverage": market_coverage})

    result = pd.DataFrame(rows)
    is_benchmark = result["eligibility_status"].eq("benchmark_operable")
    is_proxy = result.get("data_role", pd.Series("", index=result.index)).eq("proxy_senal_no_liquidez_local")
    selectable = ~is_benchmark & ~is_proxy

    # La liquidez sólo es comparable dentro de la misma plaza y moneda.
    # Una serie NYSE/ADR nunca puede convertir una acción BVL en líquida.
    scope = result.get("listing_scope", pd.Series("sin_clasificar", index=result.index)).fillna("sin_clasificar")
    quote_currency = result.get("quote_currency", result["currency"]).fillna(result["currency"])
    result["liquidity_group"] = scope.astype(str) + ":" + quote_currency.astype(str)
    result["liquidity_floor_group"] = np.nan
    for _, indexes in result.groupby("liquidity_group").groups.items():
        group_selectable = selectable.loc[indexes]
        group_values = result.loc[
            indexes[
                group_selectable
                & result.loc[indexes, "download_status"].eq("OK")
                & result.loc[indexes, "median_value_traded_local"].gt(0)
            ],
            "median_value_traded_local",
        ]
        floor = float(group_values.quantile(thresholds.liquidity_quantile)) if len(group_values) else np.inf
        result.loc[indexes, "liquidity_floor_group"] = floor

    technical = (
        result["download_status"].eq("OK")
        & result["history_years"].ge(thresholds.min_history_years)
        & result["market_coverage"].ge(thresholds.min_market_coverage)
        & result["adjusted_coverage"].ge(thresholds.min_adjusted_coverage)
        & result["staleness_days"].fillna(9999).le(thresholds.max_staleness_days)
    )
    liquid = (
        result["traded_day_ratio"].ge(thresholds.min_traded_day_ratio)
        & result["median_value_traded_local"].ge(result["liquidity_floor_group"])
    )
    result["technical_status"] = np.where(technical, "OK", "NO_CUMPLE")
    result["liquidity_status"] = np.where(liquid, "OK", "NO_CUMPLE")
    result["measured_eligibility"] = np.select(
        [
            is_benchmark,
            is_proxy & technical,
            is_proxy,
            technical & liquid & selectable,
            technical & selectable,
        ],
        ["BENCHMARK", "PROXY_SENAL", "PROXY_SIN_DATOS", "ELEGIBLE", "CONDICIONADO_LIQUIDEZ"],
        default="NO_ELEGIBLE",
    )
    result["checked_at_utc"] = checked_at.isoformat()
    return result


def evaluate_all(output_dir: Path = DATA_DIR) -> pd.DataFrame:
    checked_at = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    reports = []
    for country, path in COUNTRY_FILES.items():
        universe = pd.read_csv(path, dtype=str).fillna("")
        symbols = universe["data_symbol_candidate"].drop_duplicates().tolist()
        frames = {symbol: download_symbol(symbol) for symbol in symbols if symbol}
        report = evaluate_country(universe, frames, checked_at)
        report.insert(0, "measured_country", country)
        reports.append(report)
    combined = pd.concat(reports, ignore_index=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_dir / "regional_universe_coverage.csv", index=False)
    summary = combined.groupby(["measured_country", "measured_eligibility"], dropna=False).size().rename("instruments").reset_index()
    summary.to_csv(output_dir / "regional_universe_summary.csv", index=False)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide cobertura y liquidez del universo Perú/Colombia")
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    result = evaluate_all(args.output_dir)
    print(result.groupby(["measured_country", "measured_eligibility"]).size().to_string())


if __name__ == "__main__":
    main()
