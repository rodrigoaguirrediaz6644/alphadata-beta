import pandas as pd

from src.evaluate_regional_universe import Thresholds, evaluate_country, raw_metrics


def frame(start="2021-01-01", periods=900, volume=1000, adjusted=True):
    index = pd.bdate_range(start, periods=periods)
    data = {"Close": range(10, 10 + periods), "Volume": volume}
    if adjusted:
        data["Adj Close"] = range(10, 10 + periods)
    data["Dividends"] = 0.0
    data["Stock Splits"] = 0.0
    return pd.DataFrame(data, index=index)


def universe(status="candidato"):
    return pd.DataFrame([{
        "country": "PERU", "local_ticker": "TEST", "data_symbol_candidate": "TEST.LM",
        "eligibility_status": status, "currency": "PEN", "quote_currency": "PEN",
        "listing_scope": "local_bvl", "data_role": "precio_y_liquidez_local",
    }])


def test_raw_metrics_detects_history_adjustment_and_liquidity():
    prices = frame()
    prices.iloc[0, prices.columns.get_loc("Dividends")] = 1.0
    checked = prices.index.max() + pd.Timedelta(days=1)
    metrics = raw_metrics(prices, checked)
    assert metrics["download_status"] == "OK"
    assert metrics["history_years"] >= 3
    assert metrics["adjusted_coverage"] == 1
    assert metrics["traded_day_ratio"] == 1
    assert metrics["dividend_events"] == 1


def test_evaluate_country_marks_complete_liquid_symbol_eligible():
    prices = frame()
    checked = prices.index.max() + pd.Timedelta(days=1)
    report = evaluate_country(universe(), {"TEST.LM": prices}, checked)
    assert report.iloc[0]["technical_status"] == "OK"
    assert report.iloc[0]["liquidity_status"] == "OK"
    assert report.iloc[0]["measured_eligibility"] == "ELEGIBLE"


def test_missing_data_is_not_eligible():
    report = evaluate_country(universe(), {}, pd.Timestamp("2026-07-28"))
    assert report.iloc[0]["download_status"] == "SIN_DATOS"
    assert report.iloc[0]["measured_eligibility"] == "NO_ELEGIBLE"


def test_benchmark_never_becomes_selectable():
    prices = frame()
    checked = prices.index.max() + pd.Timedelta(days=1)
    report = evaluate_country(universe("benchmark_operable"), {"TEST.LM": prices}, checked)
    assert report.iloc[0]["measured_eligibility"] == "BENCHMARK"


def test_thin_trading_is_conditioned():
    prices = frame(volume=0)
    prices.loc[prices.index[::5], "Volume"] = 1000
    checked = prices.index.max() + pd.Timedelta(days=1)
    report = evaluate_country(
        universe(), {"TEST.LM": prices}, checked,
        Thresholds(min_traded_day_ratio=0.80),
    )
    assert report.iloc[0]["technical_status"] == "OK"
    assert report.iloc[0]["liquidity_status"] == "NO_CUMPLE"
    assert report.iloc[0]["measured_eligibility"] == "CONDICIONADO_LIQUIDEZ"


def test_proxy_is_not_classified_as_local_eligible():
    prices = frame()
    checked = prices.index.max() + pd.Timedelta(days=1)
    proxy = universe()
    proxy.loc[0, "listing_scope"] = "internacional_proxy"
    proxy.loc[0, "quote_currency"] = "USD"
    proxy.loc[0, "data_role"] = "proxy_senal_no_liquidez_local"
    report = evaluate_country(proxy, {"TEST.LM": prices}, checked)
    assert report.iloc[0]["measured_eligibility"] == "PROXY_SENAL"
    assert report.iloc[0]["liquidity_group"] == "internacional_proxy:USD"


def test_liquidity_floor_is_calculated_per_scope_and_currency():
    prices = frame(volume=1000)
    local_thin = frame(volume=0)
    local_thin.loc[local_thin.index[::5], "Volume"] = 1
    items = pd.concat([universe(), universe()], ignore_index=True)
    items.loc[0, ["local_ticker", "data_symbol_candidate"]] = ["LOCAL", "LOCAL.LM"]
    items.loc[1, ["local_ticker", "data_symbol_candidate", "listing_scope", "quote_currency", "data_role"]] = [
        "PROXY", "PROXY", "internacional_proxy", "USD", "proxy_senal_no_liquidez_local"
    ]
    checked = prices.index.max() + pd.Timedelta(days=1)
    report = evaluate_country(items, {"LOCAL.LM": local_thin, "PROXY": prices}, checked)
    local = report.loc[report["local_ticker"].eq("LOCAL")].iloc[0]
    proxy = report.loc[report["local_ticker"].eq("PROXY")].iloc[0]
    assert local["liquidity_group"] == "local_bvl:PEN"
    assert proxy["liquidity_group"] == "internacional_proxy:USD"
    assert proxy["measured_eligibility"] == "PROXY_SENAL"
