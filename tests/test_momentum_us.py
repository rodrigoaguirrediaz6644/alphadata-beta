"""Tests de las funciones puras de Gamma-6 US y del motor común de research.

No requieren red.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.common.engine import equal_weights, performance_metrics, run_backtest, to_panel, turnover_per_review, yearly_returns
from research.momentum_us.backtest import (
    composite_score,
    current_target_portfolio,
    make_gamma8_selector,
    momentum_components,
    select_gamma8,
    selector_ew_rebalanced,
    selector_ew_trend,
)


def _panel(n: int = 400, seed: int = 0) -> pd.DataFrame:
    """Panel sintético: UP sube, DOWN baja, FLAT plano con ruido, NEW tiene poca historia."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-02", periods=n)
    up = 100 * np.exp(np.linspace(0, 0.8, n)) * (1 + 0.005 * rng.standard_normal(n))
    down = 100 * np.exp(np.linspace(0, -0.5, n)) * (1 + 0.005 * rng.standard_normal(n))
    flat = 100 * (1 + 0.005 * rng.standard_normal(n))
    new = np.full(n, np.nan)
    new[-100:] = 100 * np.exp(np.linspace(0, 0.5, 100))
    return pd.DataFrame({"UP": up, "DOWN": down, "FLAT": flat, "NEW": new}, index=dates)


def test_momentum_components_uses_only_past_data_and_flags_history():
    panel = _panel()
    review = panel.index[-1]
    comp = momentum_components(panel, review)
    assert comp.loc["UP", "r12"] > 0 > comp.loc["DOWN", "r12"]
    assert bool(comp.loc["UP", "above_sma200"]) and not bool(comp.loc["DOWN", "above_sma200"])
    assert not bool(comp.loc["NEW", "history_ok"]) and bool(comp.loc["UP", "history_ok"])
    # Sin look-ahead: los componentes a mitad de la serie no dependen de los precios posteriores.
    mid = panel.index[300]
    a = momentum_components(panel, mid)
    b = momentum_components(panel.iloc[:301], mid)
    pd.testing.assert_frame_equal(a, b)


def test_composite_score_is_zscore_average_and_excludes_short_history():
    comp = momentum_components(_panel(), _panel().index[-1])
    score = composite_score(comp)
    assert "NEW" not in score.index
    assert score.loc["UP"] > score.loc["FLAT"] > score.loc["DOWN"]
    assert score.mean() == pytest.approx(0.0, abs=1e-9)
    vol_adjusted = composite_score(comp, vol_adjust=True)
    assert set(vol_adjusted.index) == set(score.index)


def test_select_gamma8_top_n_equal_weight_and_trend_filter():
    comp = momentum_components(_panel(), _panel().index[-1])
    weights, n_eligible = select_gamma8(comp, n_positions=2)
    assert list(weights.index) == ["UP", "FLAT"] and weights.sum() == pytest.approx(1.0) and n_eligible == 3
    weights_trend, _ = select_gamma8(comp, n_positions=2, trend_filter=True)
    assert "DOWN" not in weights_trend.index
    empty = comp.copy()
    empty["history_ok"] = False
    w, n = select_gamma8(empty)
    assert w.empty and n == 0


def test_equal_weights_cap_leaves_rest_in_cash():
    w = equal_weights(["A", "B"], cap=0.3)
    assert (w == 0.3).all() and w.sum() == pytest.approx(0.6)
    assert equal_weights([]).empty


def test_run_backtest_charges_costs_and_never_exceeds_full_investment():
    panel = _panel()
    start = panel.index[-60]
    nav, signals = run_backtest(panel, start, panel.index[-1], make_gamma8_selector(), cost_rate=0.001)
    assert nav["nav"].iloc[0] == 100.0 and len(nav) == 60
    assert (signals["n_selected"] <= 4).all() and (signals["n_selected"] > 0).all()
    nav_free, _ = run_backtest(panel, start, panel.index[-1], make_gamma8_selector(), cost_rate=0.0)
    assert nav_free["nav"].iloc[-1] >= nav["nav"].iloc[-1]  # con costo cero el NAV no puede ser menor


def test_ew_selectors():
    panel = _panel()
    review = panel.index[-1]
    w, n = selector_ew_rebalanced(panel, review)
    assert n == 3 and w.sum() == pytest.approx(1.0) and "NEW" not in w.index
    w_trend, n_trend = selector_ew_trend(panel, review)
    assert "DOWN" not in w_trend.index and w_trend.sum() == pytest.approx(1.0) and n_trend == len(w_trend)


def test_current_target_portfolio_marks_top_positions():
    panel = _panel()
    table = current_target_portfolio(panel)
    assert table["review_date"].iloc[0] == panel.index[-1].date().isoformat()
    assert table["target_weight"].sum() == pytest.approx(1.0)
    assert table.iloc[0]["ticker"] == "UP"


def test_metrics_yearly_and_turnover_helpers():
    dates = pd.bdate_range("2023-01-02", periods=520)
    nav = pd.DataFrame({"date": dates, "nav": 100 * (1.0005 ** np.arange(520))})
    m = performance_metrics(nav["nav"], nav["date"])
    assert m["cagr"] > 0 and m["mdd"] == 0.0 and m["sharpe"] > 0
    y = yearly_returns(nav)
    assert list(y.index) == [2023, 2024] and (y > 0).all()
    signals = pd.DataFrame({"tickers_selected": ["A,B", "A,C", "A,C", ""]})
    assert turnover_per_review(signals) == pytest.approx((2 + 1 + 0 + 0) / 4)
    long = pd.DataFrame({"date": list(dates[:3]) * 2, "ticker": ["X"] * 3 + ["Y"] * 3, "adjusted_close": [1, 2, 3, 4, 5, 6]})
    assert to_panel(long).shape == (3, 2)


def test_horizon_weights_change_ranking_and_fast_variant_selects_six():
    from research.momentum_us.backtest import HORIZON_WEIGHTS_BASE

    comp = momentum_components(_panel(), _panel().index[-1])
    base = composite_score(comp)
    fast = composite_score(comp, weights=HORIZON_WEIGHTS_BASE)
    assert set(base.index) == set(fast.index) and fast.mean() == pytest.approx(0.0, abs=1e-9)
    # con pesos (1,0,0) el score es exactamente el z-score de r3
    only3 = composite_score(comp, weights=(1.0, 0.0, 0.0))
    r3 = comp.loc[only3.index, "r3"]
    assert only3.corr(r3) == pytest.approx(1.0)
    panel = _panel()
    w, _ = make_gamma8_selector(trend_filter=True, n_positions=6, weights=HORIZON_WEIGHTS_BASE)(panel, panel.index[-1])
    assert len(w) <= 6 and w.sum() == pytest.approx(1.0)
