from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MEMBERSHIP = ROOT / "config" / "index_membership_observations.csv"
ALTERNATIVES = ROOT / "config" / "peru_alternative_sources.csv"
PERU_UNIVERSE = ROOT / "config" / "universe_peru.csv"
EVENTS = ROOT / "config" / "index_membership_events.csv"
REVIEWS = ROOT / "config" / "index_review_results.csv"


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
    assert {"2022-12-01", "2023-12-01", "2024-06-03", "2024-08-30", "2025-11-26", "2026-06-30"}.issubset(
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
        ("2024-06-03", "PEI", "ADD"),
        ("2025-11-26", "EXITO", "ADD"),
        ("2025-11-26", "ETB", "REMOVE"),
        ("2025-11-26", "CNEC", "REMOVE"),
    }.issubset(set(events[["event_date", "local_ticker", "event_type"]].itertuples(index=False, name=None)))


def test_colombia_symbol_lineage_is_preserved_by_observation_date():
    data = pd.read_csv(MEMBERSHIP)
    colombia = data[data["country"].eq("COLOMBIA")]
    historical = colombia[colombia["observation_date"].lt("2025-01-01")]
    current = colombia[colombia["observation_date"].eq("2026-06-30")]
    # Historical Bancolombia symbols must not be rewritten as Grupo Cibest.
    assert {"BCOLOMBIA", "PFBCOLOM"}.issubset(set(historical["local_ticker"]))
    assert not {"CIBEST", "PFCIBEST"}.intersection(set(historical["local_ticker"]))
    assert {"CIBEST", "PFCIBEST"}.issubset(set(current["local_ticker"]))


def test_june_2024_snapshot_records_only_published_constituents():
    data = pd.read_csv(MEMBERSHIP)
    june = data[
        data["country"].eq("COLOMBIA")
        & data["observation_date"].eq("2024-06-03")
    ]
    assert set(june["local_ticker"]) == {
        "PEI", "PFBCOLOM", "ECOPETROL", "BCOLOMBIA",
        "PFCORFICOL", "MINEROS", "ETB",
    }
    assert june["notes"].str.contains("Partial snapshot").all()
    assert june["effective_from"].isna().all()
    assert june["effective_to"].isna().all()


def test_august_2024_snapshot_remains_partial_despite_no_composition_changes():
    data = pd.read_csv(MEMBERSHIP)
    august = data[
        data["country"].eq("COLOMBIA")
        & data["observation_date"].eq("2024-08-30")
    ]
    assert set(august["local_ticker"]) == {
        "PFBCOLOM", "ECOPETROL", "BCOLOMBIA", "CNEC", "PFCORFICOL", "ETB"
    }
    assert august["notes"].str.contains("Partial snapshot").all()
    assert august["effective_from"].isna().all()
    assert august["effective_to"].isna().all()


def test_no_change_reviews_are_recorded_without_fake_membership_events():
    reviews = pd.read_csv(REVIEWS)
    required = {
        "country", "index_name", "review_date", "effective_date",
        "composition_change", "source_url", "source_type", "completeness",
    }
    assert required.issubset(reviews.columns)
    assert not reviews.duplicated(["country", "index_name", "review_date"]).any()
    assert reviews["composition_change"].eq("NO_CHANGE").all()
    assert reviews["completeness"].eq("explicit_review_result").all()
    assert {"2024-11-14", "2025-02-18", "2025-05-20", "2025-08-26"} == set(reviews["review_date"])
    events = pd.read_csv(EVENTS)
    assert not set(reviews["effective_date"]).intersection(set(events["event_date"]))


def test_2025_partial_snapshots_preserve_symbol_lineage():
    data = pd.read_csv(MEMBERSHIP)
    february = data[
        data["country"].eq("COLOMBIA")
        & data["observation_date"].eq("2025-02-28")
    ]
    may = data[
        data["country"].eq("COLOMBIA")
        & data["observation_date"].eq("2025-05-30")
    ]
    assert set(february["local_ticker"]) == {
        "PFBCOLOM", "BCOLOMBIA", "ECOPETROL", "PFCORFICOL", "CNEC", "ETB"
    }
    assert set(may["local_ticker"]) == {
        "PFCIBEST", "CIBEST", "ISA", "ECOPETROL", "PFCORFICOL", "CNEC", "ETB"
    }
    assert not {"CIBEST", "PFCIBEST"}.intersection(set(february["local_ticker"]))
    assert not {"BCOLOMBIA", "PFBCOLOM"}.intersection(set(may["local_ticker"]))
    assert february["effective_from"].isna().all()
    assert may["effective_to"].isna().all()


def test_2025_no_change_reviews_do_not_claim_complete_snapshots():
    reviews = pd.read_csv(REVIEWS)
    reviews_2025 = reviews[reviews["review_date"].str.startswith("2025-")]
    assert len(reviews_2025) == 3
    observations = pd.read_csv(MEMBERSHIP)
    snapshot_dates = set(observations["observation_date"])
    assert {"2025-02-28", "2025-05-30"}.issubset(snapshot_dates)
    assert "2025-08-26" not in snapshot_dates
