import numpy as np
import pandas as pd
from src.strategy_engine import Sigma6DataQualityError, capped_pro_rata, delta12, normalize_broker, normalize_signal, sigma6, validate_recommendations

def test_normalization_accepts_official_terms():
    assert normalize_broker('Credicorp Capital')=='Credicorp Capital'
    assert normalize_signal('Sobreponderar')==1
    assert normalize_signal('Inferior al mercado')==-1

def test_cap_leaves_cash_when_fewer_than_ten_sigma_positions():
    w=capped_pro_rata(pd.Series({'A':3,'B':1}),.10)
    assert w.to_dict()=={'A':.10,'B':.10}
    assert w.sum()==.20

def test_invalid_manual_row_is_audited():
    raw=pd.DataFrame([{'published_at':'2026-01-01','available_at':'2026-01-01','broker':'Otra','ticker':'ABC','recommendation':'Comprar','target_price_min':'','target_price_max':'','currency':'CLP','source_url':'','notes':''}])
    valid,errors=validate_recommendations(raw,{'ABC'})
    assert valid.empty
    assert 'corredora' in errors.iloc[0].errors


def test_delta12_excludes_overbought_rsi():
    dates=pd.bdate_range('2025-01-02',periods=300)
    prices=pd.DataFrame({
        'date':dates,
        'alphadata_ticker':'TEST',
        'adjusted_close':np.linspace(100,220,len(dates)),
        'volume':1_000_000,
    })
    universe=pd.DataFrame([{'tipo':'accion_local','alphadata_ticker':'TEST'}])
    portfolio,audit=delta12(prices,universe,dates[-1])
    row=audit.set_index('ticker').loc['TEST']
    assert row.rsi14 > 65
    assert row.reason == 'RSI14 superior a 65'
    assert portfolio.empty


def _sigma_valid(ticker="BCI"):
    return pd.DataFrame([{
        "ticker": ticker,
        "broker_normalized": "Credicorp Capital",
        "signal": 1,
        "available_at_parsed": pd.Timestamp("2026-01-01"),
        "row_number": 2,
    }])


def test_sigma6_tolerates_three_session_calendar_mismatch():
    dates = pd.bdate_range("2024-01-02", periods=300)
    local = pd.DataFrame({
        "date": dates,
        "alphadata_ticker": "BCI",
        "adjusted_close": np.linspace(100, 180, len(dates)),
    })
    # Simula dos ruedas globales en las que Chile no tuvo observación.
    local = local.loc[~local.index.isin([len(local)-22, len(local)-253])]
    foreign = pd.DataFrame({
        "date": dates,
        "alphadata_ticker": "SQM-ADR",
        "adjusted_close": np.linspace(40, 60, len(dates)),
    })
    portfolio, audit, _ = sigma6(
        _sigma_valid().assign(available_at_parsed=dates[-1]),
        pd.concat([local, foreign]), dates[-1], {"sigma_entries": {}}
    )
    assert set(portfolio.ticker) == {"BCI"}
    assert pd.notna(audit.set_index("ticker").loc["BCI", "momentum_12_1"])


def test_sigma6_aborts_instead_of_selling_held_position_when_indicator_missing():
    dates = pd.bdate_range("2026-01-02", periods=100)
    prices = pd.DataFrame({
        "date": dates,
        "alphadata_ticker": "BCI",
        "adjusted_close": np.linspace(100, 120, len(dates)),
    })
    with np.testing.assert_raises(Sigma6DataQualityError):
        sigma6(
            _sigma_valid(), prices, dates[-1],
            {"sigma_entries": {"BCI": "2026-03-01"}},
        )
