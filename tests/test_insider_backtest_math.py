"""Tests de las funciones puras del backtest exploratorio Beta-Insider.

No requieren red: no descargan nada de la SEC ni de Yahoo Finance.
"""
from __future__ import annotations

import pandas as pd
import pytest

from research.insider_backtest.fetch_and_backtest import (
    capped_pro_rata,
    discover_quarterly_zip_urls,
    insider_signal,
    parse_quarter_zip,
    resolve_cik_map,
    select_portfolio,
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
