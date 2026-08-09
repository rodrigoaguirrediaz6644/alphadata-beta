import numpy as np
import pandas as pd
import pytest

from src.global_momentum_strategy import (
    GlobalMomentumConfig,
    generate_target_weights,
    markets_catalog,
    validate_universe_history,
)


def make_panel(periods=330, tickers=30):
    dates = pd.bdate_range("2020-01-01", periods=periods)
    rows = []
    for number in range(tickers):
        for step, date in enumerate(dates):
            rows.append(
                {
                    "date": date,
                    "ticker": f"T{number:02}",
                    "country": f"C{number // 3:02}",
                    "sector": f"S{number % 5}",
                    "price_local": 100 * (1.0005 + number / 1_000_000) ** step,
                    "fx_to_base": 1.0,
                    "adv_base": 5_000_000,
                }
            )
    return pd.DataFrame(rows)


def test_catalog_contains_thirty_unique_markets():
    markets = list(markets_catalog())
    assert len(markets) == 30
    assert len({country for country, _ in markets}) == 30


def test_weights_respect_asset_country_sector_and_cash():
    config = GlobalMomentumConfig(min_adv_base=1, max_positions=30)
    weights = generate_target_weights(make_panel(), config)
    final = weights.loc[weights["date"].eq(weights["date"].max())]
    invested = final.loc[final["ticker"].ne("CASH")]
    assert invested["weight"].max() <= 0.04 + 1e-12
    assert invested.groupby("country")["weight"].sum().max() <= 0.12 + 1e-12
    assert invested.groupby("sector")["weight"].sum().max() <= 0.25 + 1e-12
    assert final["weight"].sum() == pytest.approx(1.0)


def test_single_signal_never_receives_full_portfolio():
    panel = make_panel(tickers=1)
    weights = generate_target_weights(
        panel, GlobalMomentumConfig(min_adv_base=1, max_positions=30)
    )
    final = weights.loc[weights["date"].eq(weights["date"].max())]
    assert final.loc[final["ticker"].eq("T00"), "weight"].iloc[0] <= 0.04
    assert final.loc[final["ticker"].eq("CASH"), "weight"].iloc[0] >= 0.96


def test_future_price_change_does_not_change_previous_weights():
    panel = make_panel()
    config = GlobalMomentumConfig(min_adv_base=1)
    original = generate_target_weights(panel, config)
    cutoff = original["date"].sort_values().iloc[-2]
    changed = panel.copy()
    changed.loc[changed["date"] > cutoff, "price_local"] *= np.linspace(
        1, 20, changed.loc[changed["date"] > cutoff].shape[0]
    )
    revised = generate_target_weights(changed, config)
    pd.testing.assert_frame_equal(
        original.loc[original["date"] <= cutoff].reset_index(drop=True),
        revised.loc[revised["date"] <= cutoff].reset_index(drop=True),
    )


def test_requires_complete_historical_membership():
    panel = make_panel(periods=2, tickers=1)
    incomplete = pd.DataFrame(
        {"date": [panel["date"].iloc[0]], "ticker": ["T00"], "is_investable": [True]}
    )
    with pytest.raises(ValueError, match="sin estado histórico"):
        validate_universe_history(panel, incomplete)


def test_equal_weighting_assigns_same_weight_to_eligible_assets():
    config = GlobalMomentumConfig(
        min_adv_base=1,
        max_positions=3,
        max_weight_per_asset=1.0,
        max_weight_per_country=1.0,
        max_weight_per_sector=1.0,
        weighting_method="equal",
    )
    weights = generate_target_weights(make_panel(tickers=3), config)
    final = weights[
        weights["date"].eq(weights["date"].max()) & weights["ticker"].ne("CASH")
    ]
    assert final["weight"].nunique() == 1


def test_filters_can_be_disabled_for_always_invested_control():
    panel = make_panel(tickers=3)
    panel.loc[panel["ticker"].eq("T00"), "price_local"] = np.linspace(
        200, 50, panel["ticker"].eq("T00").sum()
    )
    config = GlobalMomentumConfig(
        min_adv_base=1,
        max_positions=3,
        max_weight_per_asset=1.0,
        max_weight_per_country=1.0,
        max_weight_per_sector=1.0,
        weighting_method="equal",
        require_trend=False,
        require_positive_momentum=False,
    )
    weights = generate_target_weights(panel, config)
    final = weights[weights["date"].eq(weights["date"].max())]
    assert set(final.loc[final["ticker"].ne("CASH"), "ticker"]) == {
        "T00",
        "T01",
        "T02",
    }
