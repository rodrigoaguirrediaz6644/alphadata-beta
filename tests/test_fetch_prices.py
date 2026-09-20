from pathlib import Path

import pandas as pd
import pytest

from src.fetch_prices import PRICE_COLUMNS, build_coverage, load_universe, merge_with_cache


def test_load_universe_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "tickers.csv"
    pd.DataFrame(
        [
            {
                "alphadata_ticker": "ABC",
                "yahoo_ticker": "ABC.SN",
                "nombre": "A",
                "tipo": "accion_local",
                "moneda": "CLP",
                "estado": "piloto",
            },
            {
                "alphadata_ticker": "ABC",
                "yahoo_ticker": "ABC2.SN",
                "nombre": "B",
                "tipo": "accion_local",
                "moneda": "CLP",
                "estado": "piloto",
            },
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="duplicados"):
        load_universe(path)


def test_coverage_marks_missing_symbol() -> None:
    universe = pd.DataFrame(
        [
            {
                "alphadata_ticker": "ABC",
                "yahoo_ticker": "ABC.SN",
                "nombre": "A",
                "tipo": "accion_local",
            },
            {
                "alphadata_ticker": "XYZ",
                "yahoo_ticker": "XYZ.SN",
                "nombre": "X",
                "tipo": "accion_local",
            },
        ]
    )
    prices = pd.DataFrame(
        [{"date": pd.Timestamp("2024-01-05"), "alphadata_ticker": "ABC", "close": 10.0}]
    )
    coverage = build_coverage(prices, universe, min_rows=1)

    assert coverage.set_index("alphadata_ticker").loc["ABC", "status"] == "OK"
    assert coverage.set_index("alphadata_ticker").loc["XYZ", "status"] == "SIN_DATOS"


def test_partial_download_keeps_cached_symbol_and_prefers_fresh_rows() -> None:
    cached = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-08-06"),
                "alphadata_ticker": "IPSA_TR",
                "yahoo_ticker": "^IPSA",
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "adjusted_close": 100.0,
                "volume": 0.0,
            },
            {
                "date": pd.Timestamp("2026-08-06"),
                "alphadata_ticker": "ABC",
                "yahoo_ticker": "ABC.SN",
                "open": 10.0,
                "high": 10.0,
                "low": 10.0,
                "close": 10.0,
                "adjusted_close": 10.0,
                "volume": 1.0,
            },
        ],
        columns=PRICE_COLUMNS,
    )
    fresh = cached.loc[cached.alphadata_ticker == "ABC"].copy()
    fresh.loc[:, "close"] = 11.0
    fresh.loc[:, "adjusted_close"] = 11.0

    merged = merge_with_cache(fresh, cached)

    assert set(merged.alphadata_ticker) == {"ABC", "IPSA_TR"}
    assert merged.loc[merged.alphadata_ticker == "ABC", "close"].iloc[0] == 11.0


def test_coverage_records_validated_cache_without_rejecting_history() -> None:
    universe = pd.DataFrame(
        [
            {
                "alphadata_ticker": "IPSA_TR",
                "yahoo_ticker": "CFMITNIPSA.SN",
                "nombre": "IPSA proxy ETF",
                "tipo": "benchmark",
            }
        ]
    )
    prices = pd.DataFrame(
        [
            {"date": pd.Timestamp("2026-08-06"), "alphadata_ticker": "IPSA_TR", "close": 100.0}
            for _ in range(20)
        ]
    )

    coverage = build_coverage(prices, universe, fresh_tickers=set())

    assert coverage.loc[0, "status"] == "OK"
    assert coverage.loc[0, "data_source"] == "CACHE_VALIDADA"


def test_coverage_rejects_stale_benchmark_even_with_long_history() -> None:
    universe = pd.DataFrame(
        [
            {
                "alphadata_ticker": "ABC",
                "yahoo_ticker": "ABC.SN",
                "nombre": "Acción",
                "tipo": "accion_local",
            },
            {
                "alphadata_ticker": "IPSA_TR",
                "yahoo_ticker": "CFMITNIPSA.SN",
                "nombre": "IPSA proxy ETF",
                "tipo": "benchmark",
            },
        ]
    )
    prices = pd.DataFrame(
        [
            *[
                {"date": pd.Timestamp("2026-09-18"), "alphadata_ticker": "ABC", "close": 10.0}
            ],
            *[
                {
                    "date": pd.Timestamp("2026-07-17") - pd.offsets.BDay(i),
                    "alphadata_ticker": "IPSA_TR",
                    # El precio varía a propósito: esta prueba es sobre el
                    # rezago de la fecha. Con la serie plana también se
                    # cumpliría DETENIDO y no quedaría claro cuál de las dos
                    # condiciones se está verificando.
                    "close": 100.0 + i,
                }
                for i in range(20)
            ],
        ]
    )

    coverage = build_coverage(prices, universe, min_rows=1)
    benchmark = coverage.set_index("alphadata_ticker").loc["IPSA_TR"]

    assert benchmark["status"] == "DESACTUALIZADO"
    assert benchmark["lag_business_days"] > 3


def test_provider_change_replaces_old_scale_instead_of_splicing_series() -> None:
    cached = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-07-17"),
                "alphadata_ticker": "IPSA_TR",
                "yahoo_ticker": "^IPSA",
                "open": 10800.0,
                "high": 10900.0,
                "low": 10700.0,
                "close": 10887.72,
                "adjusted_close": 10887.72,
                "volume": 0.0,
            }
        ],
        columns=PRICE_COLUMNS,
    )
    fresh = cached.copy()
    fresh["yahoo_ticker"] = "CFMITNIPSA.SN"
    fresh["close"] = 5000.0
    fresh["adjusted_close"] = 5000.0

    merged = merge_with_cache(fresh, cached)

    assert set(merged["yahoo_ticker"]) == {"CFMITNIPSA.SN"}
    assert merged.iloc[0]["adjusted_close"] == 5000.0
