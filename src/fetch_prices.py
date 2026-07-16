from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "tickers.csv"
DATA_DIR = ROOT / "data"
START_DATE = "2021-01-01"


def load_universe(path: Path = CONFIG_PATH) -> pd.DataFrame:
    universe = pd.read_csv(path, dtype=str).fillna("")
    required = {"alphadata_ticker", "yahoo_ticker", "nombre", "tipo", "moneda", "estado"}
    missing = required.difference(universe.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el universo: {sorted(missing)}")
    if universe["alphadata_ticker"].duplicated().any():
        raise ValueError("Existen tickers AlphaData duplicados")
    return universe


def normalize_download(raw: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(
            columns=["date", "alphadata_ticker", "yahoo_ticker", "close", "volume"]
        )

    frames: list[pd.DataFrame] = []
    for row in universe.itertuples(index=False):
        try:
            close = raw["Close"][row.yahoo_ticker]
            volume = raw["Volume"][row.yahoo_ticker]
        except (KeyError, TypeError):
            continue
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(close.index).tz_localize(None),
                "alphadata_ticker": row.alphadata_ticker,
                "yahoo_ticker": row.yahoo_ticker,
                "close": pd.to_numeric(close, errors="coerce").to_numpy(),
                "volume": pd.to_numeric(volume, errors="coerce").to_numpy(),
            }
        )
        frames.append(frame.dropna(subset=["close"]))

    if not frames:
        return pd.DataFrame(
            columns=["date", "alphadata_ticker", "yahoo_ticker", "close", "volume"]
        )
    return pd.concat(frames, ignore_index=True).sort_values(["date", "alphadata_ticker"])


def build_coverage(prices: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for item in universe.itertuples(index=False):
        subset = prices.loc[prices["alphadata_ticker"] == item.alphadata_ticker]
        rows.append(
            {
                "alphadata_ticker": item.alphadata_ticker,
                "yahoo_ticker": item.yahoo_ticker,
                "nombre": item.nombre,
                "rows": int(len(subset)),
                "first_date": subset["date"].min().date().isoformat() if len(subset) else "",
                "last_date": subset["date"].max().date().isoformat() if len(subset) else "",
                "status": "OK" if len(subset) else "SIN_DATOS",
                "checked_at_utc": checked_at,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    universe = load_universe()
    yahoo_tickers = universe["yahoo_ticker"].tolist()
    raw = yf.download(
        tickers=yahoo_tickers,
        start=START_DATE,
        interval="1wk",
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
    )
    prices = normalize_download(raw, universe)
    coverage = build_coverage(prices, universe)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prices.to_csv(DATA_DIR / "prices_weekly.csv", index=False, date_format="%Y-%m-%d")
    coverage.to_csv(DATA_DIR / "coverage_report.csv", index=False)

    missing = coverage.loc[coverage["status"] != "OK", "alphadata_ticker"].tolist()
    print(f"Instrumentos con datos: {(coverage['status'] == 'OK').sum()}/{len(coverage)}")
    if missing:
        print(f"Sin datos: {', '.join(missing)}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()

