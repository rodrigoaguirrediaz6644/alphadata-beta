import pandas as pd

from src.backtest import build_signals, turnover


def test_signal_does_not_use_same_day_recommendation() -> None:
    recommendations = pd.DataFrame(
        [
            {
                "source_page": 1,
                "date": "2024-01-12",
                "ticker": "ABC",
                "broker": "Broker 1",
                "score": 1,
            }
        ]
    )
    signals = build_signals(
        recommendations,
        pd.DatetimeIndex(["2024-01-12", "2024-01-19"]),
        ["ABC"],
        staleness_days=120,
    ).set_index("date")

    assert signals.loc[pd.Timestamp("2024-01-12"), "broker_count"] == 0
    assert signals.loc[pd.Timestamp("2024-01-19"), "broker_count"] == 1


def test_turnover_includes_cash_leg() -> None:
    assert turnover({}, {"ABC": 1.0}) == 1.0
    assert turnover({"ABC": 1.0}, {"XYZ": 1.0}) == 1.0

