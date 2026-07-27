import json
from pathlib import Path

import pandas as pd

from src.ingest_recommendations import ingest
from src.strategy_engine import movements, normalize_broker, normalize_signal
from src.strategy_registry import load_registry


def test_only_credicorp_is_accepted_for_sigma6():
    assert normalize_broker("Credicorp Capital") == "Credicorp Capital"
    assert normalize_broker("BICE") is None
    assert normalize_signal("Sobreponderar") == 1


def test_registry_has_two_official_strategies():
    assert set(load_registry()) == {"SIGMA6", "DELTA12"}


def test_runtime_uses_trii_effective_rate():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config" / "runtime.v2.json").read_text())
    assert config["transaction_cost"]["rate"] == 0.001785
    assert config["benchmark"]["alphadata_ticker"] == "IPSA_TR"


def test_position_metadata_does_not_change_movement_logic():
    previous = [{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06"}]
    current = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06"}])
    result = movements(previous, current)
    assert result.iloc[0].action == "MANTIENE"
