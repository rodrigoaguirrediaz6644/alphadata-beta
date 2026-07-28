from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MEMBERSHIP = ROOT / "config" / "index_membership_observations.csv"
ALTERNATIVES = ROOT / "config" / "peru_alternative_sources.csv"
PERU_UNIVERSE = ROOT / "config" / "universe_peru.csv"
EVENTS = ROOT / "config" / "index_membership_events.csv"


def test_membership_observations_are_point_in_time_and_unique():
    data = pd.read_csv(MEMBERSHIP)
    required = {
        "country", "index_name", "observation_date", "local_ticker",
        "membership_state", "effective_from", "effective_to",
        "source_url", "source_type",
    }
    assert required.issubset(data.columns)
    assert not data.duplicated(["country", "index_name", "observation_date", "local_ticker"]).any()
    assert data["membership_state"].eq("OBSERVED").all()
    assert data["effective_from"].isna().all()
    assert data["effective_to"].isna().all()
    assert data["source_url"].str.startswith("https://").all()


def test_historical_observations_cover_distinct_dates_without_implying_intervals():
    data = pd.read_csv(MEMBERSHIP)
    dates = set(data["observation_date"])
    assert {"2024-12-27", "2025-01-24", "2026-04-13"}.issubset(dates)
    assert {"IPCHBC1", "AUNA"}.issubset(set(data["local_ticker"]))


def test_alternative_sources_do_not_promote_missing_series_automatically():
    data = pd.read_csv(ALTERNATIVES)
    assert {"BACKUSI1", "PODERC1", "ORYGENC1", "AENZAC1"} == set(data["local_ticker"])
    assert not data["decision"].str.contains("ELEGIBLE", case=False).any()


def test_new_peru_candidates_remain_non_productive():
    data = pd.read_csv(PERU_UNIVERSE)
    rows = data[data["local_ticker"].isin(["IPCHBC1", "AUNA"])]
    assert len(rows) == 2
    assert rows["eligibility_status"].eq("reserva").all()
    auna = rows.loc[rows["local_ticker"].eq("AUNA")].iloc[0]
    assert auna["data_role"] == "proxy_senal_no_liquidez_local"


def test_colombia_snapshots_are_partial_observations_not_assumed_intervals():
    data = pd.read_csv(MEMBERSHIP)
    colombia = data[data["country"].eq("COLOMBIA")]
    assert {"2022-12-01", "2023-12-01", "2025-11-26"}.issubset(
        set(colombia["observation_date"])
    )
    assert colombia["effective_from"].isna().all()
    assert colombia["effective_to"].isna().all()
    assert colombia["notes"].str.contains("Partial snapshot").all()


def test_colombia_membership_events_only_record_explicit_changes():
    events = pd.read_csv(EVENTS)
    required = {
        "country", "index_name", "event_date", "local_ticker", "event_type",
        "source_url", "source_type", "completeness",
    }
    assert required.issubset(events.columns)
    assert not events.duplicated(
        ["country", "index_name", "event_date", "local_ticker", "event_type"]
    ).any()
    assert set(events["event_type"]).issubset({"ADD", "REMOVE"})
    assert events["completeness"].eq("explicit_event").all()
    assert {
        ("2023-12-01", "EXITO", "ADD"),
        ("2025-11-26", "EXITO", "ADD"),
        ("2025-11-26", "ETB", "REMOVE"),
        ("2025-11-26", "CNEC", "REMOVE"),
    }.issubset(set(events[["event_date", "local_ticker", "event_type"]].itertuples(index=False, name=None)))
