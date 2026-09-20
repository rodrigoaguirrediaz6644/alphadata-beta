import json
from pathlib import Path

import pandas as pd

from src.ingest_recommendations import ingest
from src.run_pipeline import enrich_open_positions, movements_for_report
from src.strategy_engine import movements, normalize_broker, normalize_signal
from src.strategy_registry import load_registry


def test_only_credicorp_is_accepted_for_sigma6():
    assert normalize_broker("Credicorp Capital") == "Credicorp Capital"
    assert normalize_broker("BICE") is None
    assert normalize_signal("Sobreponderar") == 1


def test_registry_has_the_four_official_components():
    assert set(load_registry()) == {"SIGMA6", "DELTA12", "GAMMA6", "ORO"}


def test_methodology_document_matches_the_runtime_configuration():
    # La documentación oficial y la configuración que corre el pipeline se
    # escriben en archivos distintos: sin esta prueba se separan en silencio.
    root = Path(__file__).resolve().parents[1]
    runtime = json.loads((root / "config" / "runtime.v2.json").read_text())
    oficial = json.loads((root / "strategies.v2.json").read_text())
    esperadas = set(runtime["enabled_strategies"])
    assert set(oficial["official_strategies"]) == esperadas
    assert set(oficial["combined_portfolio"]["components"]) == esperadas
    assert set(runtime["combined_portfolio"]["components"]) == esperadas
    assert {s["strategy_code"] for s in oficial["strategies"]} == esperadas
    assert oficial["methodology_version"] == runtime["methodology_version"]


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


def test_open_position_return_uses_entry_date_and_buy_cost():
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2026-07-01", "2026-07-24"]),
        "alphadata_ticker": ["BCI", "BCI"],
        "adjusted_close": [100.0, 110.0],
    })
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-01"}])
    result = enrich_open_positions(portfolio, prices, pd.Timestamp("2026-07-24"))
    assert result.iloc[0].entry_price == 100.0
    assert result.iloc[0].current_price == 110.0
    assert abs(result.iloc[0].open_return - (110 / 100.1785 - 1)) < 1e-10


def test_latest_meaningful_movements_are_kept(tmp_path):
    prior = pd.DataFrame([{"ticker": "LTM", "action": "SALE", "previous_weight": .125, "target_weight": 0.0, "change": -.125}])
    path = tmp_path / "movements.csv"
    prior.to_csv(path, index=False)
    routine = pd.DataFrame([{"ticker": "BCI", "action": "MANTIENE", "previous_weight": .125, "target_weight": .125, "change": 0.0}])
    result = movements_for_report(routine, path)
    assert result.iloc[0].action == "SALE"
