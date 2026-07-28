import pandas as pd

from src.cuprum_ae import backtest, monthly_features


def test_five_signals_are_boolean_and_threshold_selects_a():
    dates = pd.date_range("2020-01-01", periods=800, freq="D")
    cuotas = pd.DataFrame(
        {
            "date": dates,
            "a": [100 + i * .20 for i in range(len(dates))],
            "e": [100 + i * .02 for i in range(len(dates))],
        }
    )
    external = pd.DataFrame(
        {
            "date": dates,
            "nasdaq": [100 + i * .10 for i in range(len(dates))],
            "vix": [20.0] * len(dates),
        }
    )
    features = monthly_features(cuotas, external)
    latest = features.dropna(subset=["recommendation"]).iloc[-1]
    assert latest["score"] == 5
    assert latest["recommendation"] == "A"
    for column in [
        "relative_momentum",
        "absolute_momentum",
        "cuprum_a_trend",
        "nasdaq_trend",
        "vix_below_30",
    ]:
        assert bool(latest[column]) is True


def test_switch_executes_on_fourth_subsequent_quote():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    cuotas = pd.DataFrame({"date": dates, "a": range(100, 200), "e": range(200, 300)})
    signal_date = dates[30]
    features = pd.DataFrame({"recommendation": ["A"]}, index=[signal_date])
    _, trades = backtest(cuotas, features)
    assert trades.iloc[0]["execution_date"] == dates[34].date().isoformat()
