"""Tests de las funciones puras del backtest exploratorio Beta-Insider.

No requieren red: no descargan nada de la SEC ni de Yahoo Finance.
"""
from __future__ import annotations

import pandas as pd
import pytest

import numpy as np

from research.insider_backtest.fetch_and_backtest import (
    capped_pro_rata,
    clean_transactions,
    delta12_like_audit,
    discover_quarterly_zip_urls,
    insider_activity,
    insider_signal,
    insider_veto,
    make_selector_relative,
    parse_quarter_zip,
    reconstruct_raw_close,
    resolve_cik_map,
    run_backtest,
    select_delta12_like,
    select_portfolio,
    select_relative,
)


def _fake_transactions() -> pd.DataFrame:
    return pd.DataFrame([
        {"cik": "1", "trans_date": pd.Timestamp("2024-01-05"), "trans_code": "P", "acquired_disposed": "A", "shares": 100, "price_per_share": 10.0, "value": 1000.0},
        {"cik": "1", "trans_date": pd.Timestamp("2024-02-01"), "trans_code": "S", "acquired_disposed": "D", "shares": 50, "price_per_share": 10.0, "value": -500.0},
        {"cik": "2", "trans_date": pd.Timestamp("2024-01-01"), "trans_code": "P", "acquired_disposed": "A", "shares": 200, "price_per_share": 5.0, "value": 1000.0},
        {"cik": "2", "trans_date": pd.Timestamp("2023-01-01"), "trans_code": "P", "acquired_disposed": "A", "shares": 999, "price_per_share": 5.0, "value": 4995.0},  # fuera de ventana
    ])


def test_insider_signal_only_counts_window_and_up_to_as_of():
    transactions = _fake_transactions()
    cik_to_ticker = {"1": "AAA", "2": "BBB"}
    signal = insider_signal(transactions, cik_to_ticker, pd.Timestamp("2024-02-10"), window_days=90)
    assert signal["AAA"] == pytest.approx(500.0)  # 1000 compra - 500 venta
    assert signal["BBB"] == pytest.approx(1000.0)  # la de 2023 queda fuera de la ventana de 90 días


def test_insider_signal_no_lookahead():
    transactions = _fake_transactions()
    cik_to_ticker = {"1": "AAA", "2": "BBB"}
    signal = insider_signal(transactions, cik_to_ticker, pd.Timestamp("2024-01-10"), window_days=90)
    # La venta del 2024-02-01 es posterior a as_of y no debe contarse
    assert signal["AAA"] == pytest.approx(1000.0)


def test_capped_pro_rata_respects_cap():
    scores = pd.Series({"A": 1.0, "B": 1.0, "C": 1.0})
    weights = capped_pro_rata(scores, cap=0.15)
    assert (weights <= 0.15 + 1e-9).all()
    assert weights.sum() == pytest.approx(0.45)  # 3 * 0.15, todas topadas


def test_select_portfolio_filters_by_trend_and_caps_positions():
    scores = pd.Series({"A": 5, "B": 4, "C": 3, "D": 2, "E": 1})
    trend_ok = pd.Series({"A": True, "B": False, "C": True, "D": True, "E": True})
    weights = select_portfolio(scores, trend_ok, max_positions=2, cap=0.5)
    # B tiene mejor score pero mala tendencia -> excluida; quedan A y C (mejores dos con tendencia ok)
    assert set(weights.index) == {"A", "C"}


def test_select_portfolio_empty_when_no_eligible():
    scores = pd.Series({"A": 5.0})
    trend_ok = pd.Series({"A": False})
    weights = select_portfolio(scores, trend_ok)
    assert weights.empty


def test_resolve_cik_map_raises_on_missing_ticker():
    company_tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    with pytest.raises(RuntimeError, match="MSFT"):
        resolve_cik_map(company_tickers, ["AAPL", "MSFT"])


def test_resolve_cik_map_happy_path():
    company_tickers = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp."},
    }
    result = resolve_cik_map(company_tickers, ["aapl", "MSFT"])
    assert result == {"AAPL": "320193", "MSFT": "789019"}


def test_discover_quarterly_zip_urls_filters_by_start_quarter():
    html = '''
    <a href="/files/structureddata/data/insider-transactions-data-sets/2015q4_form345.zip">2015 Q4</a>
    <a href="/files/structureddata/data/insider-transactions-data-sets/2016q1_form345.zip">2016 Q1</a>
    <a href="https://www.sec.gov/files/other/2016q2_form345.zip">2016 Q2</a>
    '''
    urls = discover_quarterly_zip_urls(html, start_quarter="2016q1")
    assert set(urls) == {"2016q1", "2016q2"}
    assert urls["2016q1"].startswith("https://www.sec.gov/")


def test_discover_quarterly_zip_urls_raises_when_nothing_found():
    with pytest.raises(RuntimeError):
        discover_quarterly_zip_urls("<html>sin links</html>", start_quarter="2016q1")


def test_parse_quarter_zip_filters_by_cik_and_codes():
    import io
    import zipfile

    submission_tsv = "ACCESSION_NUMBER\tISSUERCIK\tPERIOD_OF_REPORT\nACC1\t320193\t2024-01-05\nACC2\t999999\t2024-01-05\n"
    trans_tsv = (
        "ACCESSION_NUMBER\tTRANS_DATE\tTRANS_CODE\tTRANS_SHARES\tTRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n"
        "ACC1\t2024-01-05\tP\t100\t10.0\tA\n"  # CIK en universo, debe quedar
        "ACC1\t2024-01-06\tG\t100\t10.0\tA\n"  # código no-P/S, debe descartarse
        "ACC2\t2024-01-05\tP\t100\t10.0\tA\n"  # CIK fuera de universo, debe descartarse
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("SUBMISSION.tsv", submission_tsv)
        archive.writestr("NONDERIV_TRANS.tsv", trans_tsv)
    result = parse_quarter_zip(buffer.getvalue(), cik_set={"320193"})
    assert len(result) == 1
    assert result.iloc[0]["cik"] == "320193"
    assert result.iloc[0]["value"] == pytest.approx(1000.0)


def test_parse_quarter_zip_normalizes_zero_padded_cik():
    """Reproduce el bug real: SEC entrega ISSUERCIK con ceros a la izquierda
    (p. ej. "0000320193") mientras que resolve_cik_map produce CIKs sin
    padding (p. ej. "320193"). Sin normalizar ambos lados, el filtro isin()
    no hace match nunca y el backtest queda sin transacciones en silencio.
    """
    import io
    import zipfile

    submission_tsv = "ACCESSION_NUMBER\tISSUERCIK\tPERIOD_OF_REPORT\nACC1\t0000320193\t2024-01-05\n"
    trans_tsv = (
        "ACCESSION_NUMBER\tTRANS_DATE\tTRANS_CODE\tTRANS_SHARES\tTRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n"
        "ACC1\t2024-01-05\tP\t100\t10.0\tA\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("SUBMISSION.tsv", submission_tsv)
        archive.writestr("NONDERIV_TRANS.tsv", trans_tsv)
    result = parse_quarter_zip(buffer.getvalue(), cik_set={"320193"})
    assert len(result) == 1
    assert result.iloc[0]["cik"] == "320193"


# --------------------------------------------------------------------------
# v0.2: limpieza, sentimiento relativo, réplica Delta-12 con veto
# --------------------------------------------------------------------------

def _prices_flat(ticker: str, closes: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"date": dates, "ticker": ticker, "adjusted_close": closes, "close_raw": closes})


def test_clean_transactions_applies_every_rule_and_reports_counts():
    prices = _prices_flat("AAA", [100.0] * 10)
    base = {"accession": "ACC", "cik": "1", "trans_date": pd.Timestamp("2024-01-05"), "trans_code": "P", "acquired_disposed": "A", "shares": 10.0, "price_per_share": 100.0, "value": 1000.0, "ten_pct_owner": False}
    rows = [
        dict(base),  # se conserva
        dict(base),  # duplicado exacto -> fuera
        dict(base, accession="ACC2", trans_code="P", acquired_disposed="D", value=-1000.0),  # inconsistente -> fuera
        dict(base, accession="ACC3", ten_pct_owner=True),  # 10% owner -> fuera
        dict(base, accession="ACC4", price_per_share=2_000_000.0, value=2e7),  # precio absurdo -> fuera
        dict(base, accession="ACC5", shares=1e8, value=1e10),  # valor > tope -> fuera
        dict(base, accession="ACC6", trans_code="S", acquired_disposed="D", value=-1000.0),  # venta válida -> se conserva
    ]
    clean, report = clean_transactions(pd.DataFrame(rows), prices, {"1": "AAA"})
    assert report["dup"] == 1 and report["inconsistent"] == 1 and report["ten_pct_owner"] == 1
    assert report["price_sanity"] == 1 and report["value_cap"] == 1
    assert report["price_sanity_reference"] == "close_raw"
    assert len(clean) == 2 and report["output"] == 2
    assert set(clean["accession"]) == {"ACC", "ACC6"}


def test_clean_transactions_keeps_rows_without_price_reference_and_tolerates_missing_optional_columns():
    prices = _prices_flat("AAA", [100.0] * 5, start="2024-02-01")  # precios empiezan DESPUÉS de la operación
    rows = pd.DataFrame([{"cik": "1", "trans_date": pd.Timestamp("2024-01-05"), "trans_code": "P", "acquired_disposed": "A", "shares": 1.0, "price_per_share": 100.0, "value": 100.0}])
    clean, report = clean_transactions(rows, prices, {"1": "AAA"})
    assert len(clean) == 1 and report["ten_pct_owner"] == 0 and report["price_sanity"] == 0


def test_reconstruct_raw_close_undoes_future_splits():
    close = pd.Series([10.0, 10.0, 10.0, 10.0])
    splits = pd.Series([0.0, 0.0, 10.0, 0.0])  # split 10:1 el tercer día
    raw = reconstruct_raw_close(close, splits)
    assert raw.tolist() == [100.0, 100.0, 10.0, 10.0]
    assert reconstruct_raw_close(close, None).isna().all()


def test_insider_activity_scores_between_minus_one_and_one_and_respects_window():
    tx = pd.DataFrame({
        "cik": ["1", "1", "2", "3"],
        "trans_date": pd.to_datetime(["2024-03-01", "2024-03-10", "2024-03-05", "2023-01-01"]),
        "value": [300.0, -100.0, -500.0, 999.0],
    })
    act = insider_activity(tx, {"1": "AAA", "2": "BBB", "3": "CCC"}, pd.Timestamp("2024-03-31"), window_days=90)
    assert act.loc["AAA", "score"] == pytest.approx(0.5)  # (300-100)/(300+100)
    assert act.loc["BBB", "score"] == pytest.approx(-1.0) and act.loc["BBB", "n_buys"] == 0
    assert "CCC" not in act.index  # fuera de ventana


def test_select_relative_is_always_invested_and_ranks_by_score():
    act = pd.DataFrame({"score": [-1.0, 0.8], "net_usd": [-5e6, 1e6], "buy_usd": [0, 1e6], "sell_usd": [5e6, 0], "n_buys": [0, 1], "n_sells": [3, 0]}, index=["SELL", "BUY"])
    trend_ok = pd.Series({"SELL": True, "BUY": True, "QUIET": True, "DOWN": False})
    weights = select_relative(act, trend_ok, max_positions=2, cap=0.6)
    assert list(weights.index) == ["BUY", "QUIET"]  # QUIET (score 0) le gana a SELL (-1); DOWN no elegible
    assert weights.sum() == pytest.approx(1.0)
    assert select_relative(act, pd.Series({"SELL": False}), max_positions=2).empty


def test_delta12_like_audit_and_veto_selection():
    n = 300
    dates = pd.bdate_range("2023-01-02", periods=n)
    wiggle = 4 * np.sin(np.arange(n) / 2)  # ruido para que el RSI14 no se vaya a 100 en una serie monótona
    up = np.linspace(100, 200, n) + wiggle
    down = np.linspace(200, 100, n) + wiggle
    panel = pd.DataFrame({"UP": up, "UP2": up * 1.01, "DOWN": down}, index=dates)
    audit = delta12_like_audit(panel, dates[-1])
    assert bool(audit.loc["UP", "eligible"]) and bool(audit.loc["UP2", "eligible"])
    assert not bool(audit.loc["DOWN", "eligible"])
    act = pd.DataFrame({"net_usd": [-2e8, 1e6], "n_buys": [0, 1]}, index=["UP", "UP2"])
    vetoed = insider_veto(act, net_usd_threshold=-100e6)
    assert list(vetoed) == ["UP"]
    with_veto = select_delta12_like(audit, vetoed)
    without = select_delta12_like(audit, None)
    assert set(without.index) == {"UP", "UP2"} and set(with_veto.index) == {"UP2"}
    assert delta12_like_audit(panel.iloc[:100], dates[99]).empty  # historia insuficiente


def test_run_backtest_generic_selector_charges_costs_and_tracks_signals():
    dates = pd.bdate_range("2023-01-02", periods=320)
    prices = pd.concat([
        pd.DataFrame({"date": dates, "ticker": "AAA", "adjusted_close": np.linspace(100, 150, len(dates))}),
        pd.DataFrame({"date": dates, "ticker": "BBB", "adjusted_close": np.linspace(100, 90, len(dates))}),
    ])
    tx = pd.DataFrame({"cik": ["1"], "trans_date": [dates[0]], "value": [1e6]})
    start = dates[-60]
    nav, signals = run_backtest(prices, start, dates[-1], make_selector_relative(tx, {"1": "AAA"}), cost_rate=0.001)
    assert len(nav) == 60 and nav["nav"].iloc[0] == 100.0
    assert len(signals) >= 2 and (signals["n_selected"] > 0).all()
    assert nav["nav"].iloc[-1] > 100.0  # AAA sube; siempre invertida


def test_ticker_aliases_copies_activity_to_share_classes():
    from research.insider_backtest.fetch_and_backtest import ticker_aliases, _expand_aliases

    cik_to_ticker, aliases = ticker_aliases({"GOOG": "1652044", "GOOGL": "1652044", "AAPL": "320193"})
    assert cik_to_ticker == {"1652044": "GOOG", "320193": "AAPL"} and aliases == {"GOOG": ["GOOGL"]}
    act = pd.DataFrame({"score": [0.5], "net_usd": [1.0]}, index=["GOOG"])
    expanded = _expand_aliases(act, aliases)
    assert set(expanded.index) == {"GOOG", "GOOGL"} and expanded.loc["GOOGL", "score"] == 0.5
    assert _expand_aliases(pd.Series(dtype=float), aliases).empty
