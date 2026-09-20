"""Motor de backtest mensual reutilizable para la investigación paralela.

Es código de investigación (carpeta `research/`), NO parte de la metodología
oficial. No lee ni escribe `data/`, `reports/` ni `strategy_state.json`.

Convenciones (las mismas que usa el proyecto para Delta-12):
- Revisión el último día hábil de cada mes; la nueva cartera rige desde la
  sesión siguiente.
- Retorno diario = suma de peso x variación del precio ajustado; el resto es
  caja al 0%.
- Costo = 0,5 x (turnover de posiciones + variación de caja) x `cost_rate`,
  es decir `cost_rate` por lado sobre lo que efectivamente se mueve.
- `selector(panel, review_date) -> (pesos: Series, n_elegibles: int)` decide
  la cartera objetivo usando SOLO datos con fecha <= review_date.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

Selector = Callable[[pd.DataFrame, pd.Timestamp], tuple[pd.Series, int]]


def to_panel(prices: pd.DataFrame) -> pd.DataFrame:
    """prices largo (date, ticker, adjusted_close) -> panel ancho (index=date, columns=ticker)."""
    panel = prices.pivot(index="date", columns="ticker", values="adjusted_close").sort_index()
    panel.index = pd.to_datetime(panel.index)
    return panel


def equal_weights(tickers, cap: float | None = None) -> pd.Series:
    """Pesos iguales (1/n) con tope opcional por posición; el resto queda en caja."""
    tickers = list(tickers)
    if not tickers:
        return pd.Series(dtype=float)
    weight = 1.0 / len(tickers)
    if cap is not None:
        weight = min(weight, cap)
    return pd.Series(weight, index=tickers)


def run_backtest(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, selector: Selector, cost_rate: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (nav_diaria[date, nav], señales[review_date, n_eligible, n_selected, tickers_selected])."""
    panel = panel.loc[panel.index <= end]
    sessions = panel.index[panel.index >= start]
    if len(sessions) == 0:
        raise RuntimeError("No hay sesiones de precio en el rango pedido.")
    weights: dict[str, float] = {}
    nav = 100.0
    rows, signal_rows = [], []
    previous_date = None
    current_month = None
    for session in sessions:
        if previous_date is None:
            rows.append({"date": session, "nav": nav})
            previous_date, current_month = session, session.to_period("M")
            continue
        day_return = 0.0
        for ticker, weight in weights.items():
            prev_px, cur_px = panel.at[previous_date, ticker], panel.at[session, ticker]
            if pd.notna(prev_px) and pd.notna(cur_px) and prev_px > 0:
                day_return += weight * (cur_px / prev_px - 1)
        nav *= 1 + day_return
        month = session.to_period("M")
        if month != current_month:
            review_dates = panel.index[panel.index < session]
            if len(review_dates):
                review = pd.Timestamp(review_dates[-1])
                target, n_eligible = selector(panel, review)
                new_weights = {k: float(v) for k, v in target.to_dict().items() if v > 0}
                risky = sum(abs(new_weights.get(t, 0.0) - weights.get(t, 0.0)) for t in set(weights) | set(new_weights))
                cash = abs((1 - sum(new_weights.values())) - (1 - sum(weights.values())))
                nav *= 1 - 0.5 * (risky + cash) * cost_rate
                weights = new_weights
                signal_rows.append({"review_date": review.date().isoformat(), "n_eligible": int(n_eligible), "n_selected": len(new_weights), "tickers_selected": ",".join(sorted(new_weights))})
            current_month = month
        rows.append({"date": session, "nav": nav})
        previous_date = session
    return pd.DataFrame(rows), pd.DataFrame(signal_rows, columns=["review_date", "n_eligible", "n_selected", "tickers_selected"])


def performance_metrics(nav: pd.Series, dates: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(nav, errors="coerce")
    keep = values.notna()
    values, dates = values[keep], pd.to_datetime(dates[keep])
    if len(values) < 2 or values.iloc[0] <= 0:
        return {"return": None, "cagr": None, "vol": None, "mdd": None, "sharpe": None}
    returns = values.pct_change().dropna()
    years = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    vol = returns.std() * np.sqrt(252) if len(returns) > 2 else None
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1 if years >= 0.25 else None
    drawdown = values / values.cummax() - 1
    return {
        "return": float(values.iloc[-1] / values.iloc[0] - 1),
        "cagr": float(cagr) if cagr is not None else None,
        "vol": float(vol) if vol is not None else None,
        "mdd": float(drawdown.min()),
        "sharpe": float(cagr / vol) if (cagr is not None and vol not in (None, 0)) else None,
    }


def yearly_returns(nav: pd.DataFrame) -> pd.Series:
    """Retorno por año calendario a partir de una serie [date, nav] (el primer año es parcial)."""
    s = nav.set_index(pd.to_datetime(nav["date"]))["nav"]
    year_end = s.resample("YE").last()
    first = pd.Series([s.iloc[0]], index=[year_end.index[0] - pd.offsets.YearEnd(1)])
    out = pd.concat([first, year_end]).pct_change().dropna()
    out.index = out.index.year
    return out


def turnover_per_review(signals: pd.DataFrame) -> float:
    """Promedio de tickers nuevos que entran por revisión."""
    previous: set[str] = set()
    total = 0
    for value in signals["tickers_selected"].fillna(""):
        current = set(value.split(",")) if value else set()
        total += len(current - previous)
        previous = current
    return total / len(signals) if len(signals) else 0.0


def download_prices(tickers: list[str], start: str) -> pd.DataFrame:
    """Precios ajustados diarios vía yfinance -> DataFrame largo (date, ticker, adjusted_close)."""
    import yfinance as yf

    raw = yf.download(tickers=tickers, start=start, interval="1d", auto_adjust=False, actions=False, group_by="column", threads=True, progress=False, timeout=30)
    frames = []
    for ticker in tickers:
        if isinstance(raw.columns, pd.MultiIndex):
            if ticker not in raw.columns.get_level_values(-1):
                print(f"ADVERTENCIA: sin precios para {ticker}")
                continue
            sub = raw.xs(ticker, axis=1, level=-1, drop_level=True)
        else:
            sub = raw
        if "Close" not in sub:
            continue
        adjusted = sub["Adj Close"] if "Adj Close" in sub else sub["Close"]
        frames.append(pd.DataFrame({"date": pd.to_datetime(sub.index).tz_localize(None), "ticker": ticker, "adjusted_close": pd.to_numeric(adjusted, errors="coerce")}).dropna())
    if not frames:
        raise RuntimeError("No se pudo descargar precios para ningún ticker del universo.")
    return pd.concat(frames, ignore_index=True)
