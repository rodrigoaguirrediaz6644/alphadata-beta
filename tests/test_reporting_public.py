import pandas as pd
import pytest

from src.reporting_public import _metrics, _open_portfolio_return, build_public_report


def test_metrics_do_not_invent_history_with_one_observation():
    result = _metrics(pd.Series([100.0]), pd.Series(["2026-07-16"]))
    assert result["return"] is None
    assert result["mdd"] is None


def test_open_portfolio_return_uses_position_weights_and_leaves_cash_at_zero():
    portfolio = pd.DataFrame([
        {"ticker": "BCI", "target_weight": .1, "open_return": .20},
        {"ticker": "LTM", "target_weight": .1, "open_return": -.10},
    ])
    assert _open_portfolio_return(portfolio) == pytest.approx(.01)


def test_open_portfolio_return_requires_complete_position_data():
    portfolio = pd.DataFrame([
        {"ticker": "BCI", "target_weight": .1, "open_return": .20},
        {"ticker": "LTM", "target_weight": .1, "open_return": pd.NA},
    ])
    assert _open_portfolio_return(portfolio) is None


def test_public_report_hides_strategy_methodology(monkeypatch, tmp_path):
    monkeypatch.setattr("src.reporting_public.HISTORICAL", tmp_path / "missing.csv")
    sigma = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "open_return": .20}])
    delta = pd.DataFrame([{"ticker": "LTM", "target_weight": .5, "open_return": -.10}])
    moves = pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}])
    coverage = pd.DataFrame([{"status": "OK"}])
    _, html = build_public_report(pd.Timestamp("2026-07-16"), sigma, delta, moves, moves, coverage, pd.DataFrame())
    assert "Información reservada" in html
    assert "2.0%" in html
    assert "-5.0%" in html
    assert "Rentabilidad ponderada de las posiciones abiertas desde su ingreso" in html
    assert "Paper trading" not in html
    assert "Seguimiento oficial" not in html
    assert "Métricas del paper trading" not in html
    assert "Ingreso" in html
    assert "Precio ingreso" in html
    assert "Precio actual" in html
    assert "Rentabilidad actual" in html
    assert "Retrocesos del paper trading" not in html
    assert "durante el último año" not in html
    assert "—" in html
    assert "momentum_12_1" not in html
    assert "SMA200" not in html
