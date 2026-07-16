from pathlib import Path

import pandas as pd
import pytest

from src.fetch_prices import build_coverage, load_universe


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
            {"alphadata_ticker": "ABC", "yahoo_ticker": "ABC.SN", "nombre": "A"},
            {"alphadata_ticker": "XYZ", "yahoo_ticker": "XYZ.SN", "nombre": "X"},
        ]
    )
    prices = pd.DataFrame(
        [{"date": pd.Timestamp("2024-01-05"), "alphadata_ticker": "ABC", "close": 10.0}]
    )
    coverage = build_coverage(prices, universe)

    assert coverage.set_index("alphadata_ticker").loc["ABC", "status"] == "OK"
    assert coverage.set_index("alphadata_ticker").loc["XYZ", "status"] == "SIN_DATOS"

