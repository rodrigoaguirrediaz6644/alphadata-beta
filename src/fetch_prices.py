from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "tickers.csv"
DATA_DIR = ROOT / "data"
START_DATE = os.getenv("ALPHADATA_PRICE_START", "2015-01-01")
MIN_HISTORY_ROWS = 252
PRICE_COLUMNS = ["date", "alphadata_ticker", "yahoo_ticker", "open", "high", "low", "close", "adjusted_close", "volume"]


def load_universe(path: Path = CONFIG_PATH) -> pd.DataFrame:
    universe = pd.read_csv(path, dtype=str).fillna("")
    required = {"alphadata_ticker", "yahoo_ticker", "nombre", "tipo", "moneda", "estado"}
    missing = required.difference(universe.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el universo: {sorted(missing)}")
    if universe["alphadata_ticker"].duplicated().any():
        raise ValueError("Existen tickers AlphaData duplicados")
    if universe["yahoo_ticker"].eq("").any():
        raise ValueError("Existen instrumentos sin ticker de mercado")
    return universe


def _ticker_frame(raw: pd.DataFrame, yahoo_ticker: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if yahoo_ticker in raw.columns.get_level_values(-1):
            return raw.xs(yahoo_ticker, axis=1, level=-1, drop_level=True)
        if yahoo_ticker in raw.columns.get_level_values(0):
            return raw.xs(yahoo_ticker, axis=1, level=0, drop_level=True)
        return pd.DataFrame()
    return raw


def normalize_daily(raw: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for item in universe.itertuples(index=False):
        source = _ticker_frame(raw, item.yahoo_ticker)
        if source.empty or "Close" not in source:
            continue
        adjusted = source["Adj Close"] if "Adj Close" in source else source["Close"]
        frame = pd.DataFrame({
            "date": pd.to_datetime(source.index).tz_localize(None),
            "alphadata_ticker": item.alphadata_ticker,
            "yahoo_ticker": item.yahoo_ticker,
            "open": pd.to_numeric(source.get("Open"), errors="coerce").to_numpy(),
            "high": pd.to_numeric(source.get("High"), errors="coerce").to_numpy(),
            "low": pd.to_numeric(source.get("Low"), errors="coerce").to_numpy(),
            "close": pd.to_numeric(source["Close"], errors="coerce").to_numpy(),
            "adjusted_close": pd.to_numeric(adjusted, errors="coerce").to_numpy(),
            "volume": pd.to_numeric(source.get("Volume"), errors="coerce").to_numpy(),
        })
        frames.append(frame.dropna(subset=["date", "close"]))
    if not frames:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    daily = pd.concat(frames, ignore_index=True)
    return daily[PRICE_COLUMNS].sort_values(["date", "alphadata_ticker"]).drop_duplicates(["date", "alphadata_ticker"], keep="last")


def daily_to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return daily.copy()
    work = daily.copy(); work["week"] = work["date"].dt.to_period("W-FRI")
    weekly = work.sort_values("date").groupby(["alphadata_ticker", "yahoo_ticker", "week"], as_index=False).agg(
        date=("date", "max"), open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), adjusted_close=("adjusted_close", "last"), volume=("volume", "sum")
    )
    return weekly.drop(columns="week")[PRICE_COLUMNS].sort_values(["date", "alphadata_ticker"])


def normalize_download(raw: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Compatibilidad con el piloto: devuelve precios semanales normalizados."""
    return daily_to_weekly(normalize_daily(raw, universe))


def merge_with_cache(fresh: pd.DataFrame, cached: pd.DataFrame) -> pd.DataFrame:
    """Conserva la última serie validada cuando Yahoo entrega un lote parcial.

    Las filas recién descargadas prevalecen para una misma fecha e instrumento.
    """
    frames = [frame for frame in (cached, fresh) if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce", utc=True).dt.tz_localize(None)
    return (
        combined[PRICE_COLUMNS]
        .dropna(subset=["date", "alphadata_ticker", "close"])
        .drop_duplicates(["date", "alphadata_ticker"], keep="last")
        .sort_values(["date", "alphadata_ticker"])
        .reset_index(drop=True)
    )


def build_coverage(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    min_rows: int = MIN_HISTORY_ROWS,
    fresh_tickers: set[str] | None = None,
) -> pd.DataFrame:
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for item in universe.itertuples(index=False):
        subset = prices.loc[prices["alphadata_ticker"] == item.alphadata_ticker]
        required_rows = min_rows if item.tipo == "accion_local" else 20
        data_source = (
            "DESCARGA_ACTUAL"
            if fresh_tickers is None or item.alphadata_ticker in fresh_tickers
            else "CACHE_VALIDADA"
            if len(subset)
            else "SIN_DATOS"
        )
        rows.append({
            "alphadata_ticker": item.alphadata_ticker, "yahoo_ticker": item.yahoo_ticker, "nombre": item.nombre,
            "tipo": item.tipo, "rows": int(len(subset)),
            "first_date": subset["date"].min().date().isoformat() if len(subset) else "",
            "last_date": subset["date"].max().date().isoformat() if len(subset) else "",
            "status": "OK" if len(subset) >= required_rows else "INSUFICIENTE" if len(subset) else "SIN_DATOS",
            "data_source": data_source,
            "checked_at_utc": checked_at,
        })
    return pd.DataFrame(rows)


def main() -> None:
    import yfinance as yf
    universe = load_universe(); tickers = universe["yahoo_ticker"].tolist()
    last_error = None
    for attempt in range(3):
        try:
            raw = yf.download(tickers=tickers, start=START_DATE, interval="1d", auto_adjust=False, actions=False, group_by="column", threads=True, progress=False, timeout=30)
            if not raw.empty: break
        except Exception as exc:
            last_error = exc
    else:
        cached = DATA_DIR / "market_prices_daily.csv"
        if cached.exists():
            print(f"ADVERTENCIA: descarga falló; se conserva caché existente. Error: {last_error}")
            return
        raise SystemExit(f"No fue posible descargar precios y no existe caché: {last_error}")
    fresh = normalize_daily(raw, universe)
    fresh_tickers = set(fresh["alphadata_ticker"].unique())

    # Una respuesta no vacía de Yahoo puede omitir algunos instrumentos por
    # rate limiting. Se reintentan sólo los ausentes para no repetir todo el lote.
    missing = universe.loc[~universe["alphadata_ticker"].isin(fresh_tickers)]
    for item in missing.itertuples(index=False):
        try:
            individual_raw = yf.download(
                tickers=item.yahoo_ticker,
                start=START_DATE,
                interval="1d",
                auto_adjust=False,
                actions=False,
                group_by="column",
                threads=False,
                progress=False,
                timeout=30,
            )
            individual = normalize_daily(individual_raw, universe.loc[universe.alphadata_ticker == item.alphadata_ticker])
            if not individual.empty:
                fresh = merge_with_cache(individual, fresh)
                fresh_tickers.add(item.alphadata_ticker)
        except Exception as exc:
            print(f"ADVERTENCIA: reintento individual falló para {item.alphadata_ticker}: {exc}")

    cached_path = DATA_DIR / "market_prices_daily.csv"
    cached = pd.read_csv(cached_path, parse_dates=["date"]) if cached_path.exists() else pd.DataFrame(columns=PRICE_COLUMNS)
    daily = merge_with_cache(fresh, cached)
    weekly = daily_to_weekly(daily)
    coverage = build_coverage(daily, universe, fresh_tickers=fresh_tickers)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    daily.to_csv(DATA_DIR / "market_prices_daily.csv", index=False, date_format="%Y-%m-%d")
    weekly.to_csv(DATA_DIR / "prices_weekly.csv", index=False, date_format="%Y-%m-%d")
    coverage.to_csv(DATA_DIR / "coverage_report.csv", index=False)
    local_ok = coverage.loc[(coverage["tipo"] == "accion_local") & (coverage["status"] == "OK")]
    print(f"Acciones locales con historia suficiente: {len(local_ok)}/{(coverage['tipo'] == 'accion_local').sum()}")
    missing_coverage = coverage.loc[coverage["status"] != "OK", "alphadata_ticker"].tolist()
    if missing_coverage: print("Cobertura incompleta: " + ", ".join(missing_coverage))
    cached_symbols = coverage.loc[coverage["data_source"] == "CACHE_VALIDADA", "alphadata_ticker"].tolist()
    if cached_symbols: print("ADVERTENCIA: se usó caché validada para: " + ", ".join(cached_symbols))
    benchmark_ok = coverage.loc[(coverage.alphadata_ticker == "IPSA_TR") & (coverage.status == "OK")]
    if daily.empty or len(local_ok) < 20: raise SystemExit("Menos de 20 acciones locales tienen historia suficiente; se cancela el cálculo para evitar una cartera incompleta")
    if benchmark_ok.empty: raise SystemExit("El benchmark IPSA_TR no tiene cobertura suficiente")


if __name__ == "__main__":
    main()
