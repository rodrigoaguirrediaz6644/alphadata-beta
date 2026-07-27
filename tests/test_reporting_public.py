import pandas as pd

from src.reporting_public import _metrics, build_public_report


def test_metrics_do_not_invent_history_with_one_observation():
    result = _metrics(pd.Series([100.0]), pd.Series(["2026-07-16"]))
    assert result["return"] is None
    assert result["mdd"] is None


def test_public_report_hides_strategy_methodology():
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1}])
    moves = pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}])
    coverage = pd.DataFrame([{"status": "OK"}])
    history = pd.DataFrame([{"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "IPSA TR": 100}])
    _, html = build_public_report(pd.Timestamp("2026-07-16"), portfolio, portfolio, moves, moves, coverage, pd.DataFrame(), history)
    assert "Información reservada" in html
    assert "Ingreso" in html
    assert "Precio ingreso" in html
    assert "Precio actual" in html
    assert "Rentabilidad actual" in html
    assert "—" in html
    assert "momentum_12_1" not in html
    assert "SMA200" not in html
