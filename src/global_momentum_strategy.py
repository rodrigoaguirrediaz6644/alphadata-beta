"""Motor reproducible para la cartera global de momentum de AlphaData.

El módulo no descarga datos ni selecciona retrospectivamente ganadores. Recibe
un panel histórico fechado y produce pesos objetivo usando solamente datos
disponibles hasta cada fecha de decisión.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "ticker",
    "country",
    "sector",
    "price_local",
    "fx_to_base",
    "adv_base",
}


@dataclass(frozen=True)
class GlobalMomentumConfig:
    base_currency: str = "USD"
    momentum_long_days: int = 252
    momentum_short_days: int = 126
    volatility_days: int = 63
    trend_days: int = 200
    rebalance_frequency: str = "M"
    max_positions: int = 30
    max_weight_per_asset: float = 0.04
    max_weight_per_country: float = 0.12
    max_weight_per_sector: float = 0.25
    min_adv_base: float = 1_000_000
    target_gross_exposure: float = 1.0

    def __post_init__(self) -> None:
        bounds = (
            self.max_weight_per_asset,
            self.max_weight_per_country,
            self.max_weight_per_sector,
            self.target_gross_exposure,
        )
        if any(value <= 0 or value > 1 for value in bounds):
            raise ValueError("Los límites y la exposición deben estar entre 0 y 1.")
        if self.max_positions < 1:
            raise ValueError("max_positions debe ser positivo.")


def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Valida y enriquece el panel, convirtiendo precios a moneda base."""
    missing = REQUIRED_COLUMNS.difference(panel.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    data = panel.copy()
    data["date"] = pd.to_datetime(data["date"], utc=False)
    data = data.sort_values(["ticker", "date"])
    if data.duplicated(["date", "ticker"]).any():
        raise ValueError("El panel contiene fechas duplicadas por ticker.")
    numeric = ["price_local", "fx_to_base", "adv_base"]
    if (data[numeric] <= 0).any().any():
        raise ValueError("Precios, FX y liquidez deben ser positivos.")
    data["price_base"] = data["price_local"] * data["fx_to_base"]
    return data


def _last_trading_dates(dates: pd.Series, frequency: str) -> pd.DatetimeIndex:
    calendar = pd.Series(pd.to_datetime(dates).drop_duplicates()).sort_values()
    return pd.DatetimeIndex(calendar.groupby(calendar.dt.to_period(frequency)).max())


def compute_signals(
    panel: pd.DataFrame, config: GlobalMomentumConfig
) -> pd.DataFrame:
    """Calcula señales históricas por activo sin usar datos futuros."""
    data = prepare_panel(panel)
    grouped = data.groupby("ticker", group_keys=False)
    price = data["price_base"]
    data["momentum_long"] = grouped["price_base"].pct_change(
        config.momentum_long_days, fill_method=None
    )
    data["momentum_short"] = grouped["price_base"].pct_change(
        config.momentum_short_days, fill_method=None
    )
    data["trend"] = grouped["price_base"].transform(
        lambda values: values.rolling(config.trend_days).mean()
    )
    returns = grouped["price_base"].pct_change(fill_method=None)
    data["volatility"] = returns.groupby(data["ticker"]).transform(
        lambda values: values.rolling(config.volatility_days).std() * np.sqrt(252)
    )
    data["score"] = 0.6 * data["momentum_long"] + 0.4 * data["momentum_short"]
    data["eligible"] = (
        (price > data["trend"])
        & (data["momentum_long"] > 0)
        & (data["momentum_short"] > 0)
        & (data["volatility"] > 0)
        & (data["adv_base"] >= config.min_adv_base)
    )
    return data


def _constrained_weights(
    candidates: pd.DataFrame, config: GlobalMomentumConfig
) -> dict[str, float]:
    """Asigna por volatilidad inversa respetando topes sin renormalizar efectivo."""
    selected = candidates.nlargest(config.max_positions, "score").copy()
    if selected.empty:
        return {}
    selected["raw"] = 1.0 / selected["volatility"]
    selected["raw"] /= selected["raw"].sum()

    weights: dict[str, float] = {}
    country_used: dict[str, float] = {}
    sector_used: dict[str, float] = {}
    remaining = config.target_gross_exposure

    # Rondas sucesivas permiten redistribuir capacidad sin violar límites.
    active = selected.set_index("ticker")
    for _ in range(len(active) + 1):
        if remaining <= 1e-12 or active.empty:
            break
        raw = active["raw"] / active["raw"].sum()
        allocated = 0.0
        exhausted: list[str] = []
        for ticker, row in active.iterrows():
            country_room = config.max_weight_per_country - country_used.get(
                row["country"], 0.0
            )
            sector_room = config.max_weight_per_sector - sector_used.get(
                row["sector"], 0.0
            )
            asset_room = config.max_weight_per_asset - weights.get(ticker, 0.0)
            addition = min(
                remaining * float(raw[ticker]),
                max(country_room, 0.0),
                max(sector_room, 0.0),
                max(asset_room, 0.0),
            )
            if addition > 0:
                weights[ticker] = weights.get(ticker, 0.0) + addition
                country_used[row["country"]] = (
                    country_used.get(row["country"], 0.0) + addition
                )
                sector_used[row["sector"]] = (
                    sector_used.get(row["sector"], 0.0) + addition
                )
                allocated += addition
            if addition + 1e-12 >= min(
                max(country_room, 0.0),
                max(sector_room, 0.0),
                max(asset_room, 0.0),
            ):
                exhausted.append(ticker)
        remaining -= allocated
        active = active.drop(index=exhausted, errors="ignore")
        if allocated <= 1e-12:
            break
    return weights


def generate_target_weights(
    panel: pd.DataFrame, config: GlobalMomentumConfig | None = None
) -> pd.DataFrame:
    """Genera pesos en cada cierre de rebalanceo y conserva efectivo residual."""
    config = config or GlobalMomentumConfig()
    signals = compute_signals(panel, config)
    decision_dates = _last_trading_dates(signals["date"], config.rebalance_frequency)
    records: list[dict[str, object]] = []

    for date in decision_dates:
        cross_section = signals[signals["date"].eq(date)]
        candidates = cross_section[cross_section["eligible"]]
        weights = _constrained_weights(candidates, config)
        for ticker, weight in weights.items():
            row = candidates.loc[candidates["ticker"].eq(ticker)].iloc[0]
            records.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "country": row["country"],
                    "sector": row["sector"],
                    "weight": weight,
                    "score": row["score"],
                }
            )
        invested = sum(weights.values())
        records.append(
            {
                "date": date,
                "ticker": "CASH",
                "country": "CASH",
                "sector": "CASH",
                "weight": max(0.0, 1.0 - invested),
                "score": np.nan,
            }
        )
    return pd.DataFrame.from_records(records)


def validate_universe_history(
    panel: pd.DataFrame, membership: pd.DataFrame
) -> None:
    """Exige membresía histórica para impedir universos actuales retroactivos."""
    required = {"date", "ticker", "is_investable"}
    missing = required.difference(membership.columns)
    if missing:
        raise ValueError(f"Falta membresía histórica: {sorted(missing)}")
    panel_keys = prepare_panel(panel)[["date", "ticker"]]
    member_keys = membership.copy()
    member_keys["date"] = pd.to_datetime(member_keys["date"], utc=False)
    merged = panel_keys.merge(member_keys, on=["date", "ticker"], how="left")
    if merged["is_investable"].isna().any():
        raise ValueError("Hay observaciones sin estado histórico de inversión.")


def markets_catalog() -> Iterable[tuple[str, str]]:
    """Treinta mercados objetivo de la primera cobertura global."""
    return (
        ("United States", "USD"),
        ("Canada", "CAD"),
        ("Mexico", "MXN"),
        ("Brazil", "BRL"),
        ("Chile", "CLP"),
        ("Colombia", "COP"),
        ("Peru", "PEN"),
        ("Argentina", "ARS"),
        ("United Kingdom", "GBP"),
        ("Germany", "EUR"),
        ("France", "EUR"),
        ("Spain", "EUR"),
        ("Italy", "EUR"),
        ("Netherlands", "EUR"),
        ("Switzerland", "CHF"),
        ("Sweden", "SEK"),
        ("Norway", "NOK"),
        ("Denmark", "DKK"),
        ("Poland", "PLN"),
        ("Japan", "JPY"),
        ("China", "CNY"),
        ("Hong Kong", "HKD"),
        ("South Korea", "KRW"),
        ("Taiwan", "TWD"),
        ("India", "INR"),
        ("Singapore", "SGD"),
        ("Indonesia", "IDR"),
        ("Malaysia", "MYR"),
        ("Australia", "AUD"),
        ("South Africa", "ZAR"),
    )
