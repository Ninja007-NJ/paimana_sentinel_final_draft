import json
from pathlib import Path

import joblib

from ml.features.feature_registry import ALLOWED_FEATURES


ROOT = Path(__file__).resolve().parents[2]


def test_delay_6m_bundle_is_accepted_and_leakage_safe():
    bundle = joblib.load(ROOT / "ml" / "artifacts" / "models" / "delay_6m_model_bundle_v1.joblib")
    assert bundle["model_version"] == "delay_6m_v1"
    assert bundle["status"] in {"GREEN", "YELLOW"}
    assert "canonical_project_id" not in bundle["features"]
    assert "reporting_regime" not in bundle["features"]
    assert not any(feature.startswith(("delay_event_next_", "cost_escalation_next_", "future_coverage_", "valid_")) for feature in bundle["features"])
    assert set(ALLOWED_FEATURES).issubset(bundle["features"])


def test_secondary_test_windows_are_chronological_and_cost_rejection_is_preserved():
    delay = json.loads((ROOT / "ml" / "artifacts" / "reports" / "delay_6m_result.json").read_text(encoding="utf-8"))
    cost = json.loads((ROOT / "ml" / "artifacts" / "reports" / "cost_3m_result.json").read_text(encoding="utf-8"))
    for result in (delay, cost):
        split = result["split"]
        assert max(split["train"]) < min(split["selection"])
        assert max(split["selection"]) < min(split["calibration"])
        assert max(split["calibration"]) < min(split["test"])
    assert delay["status"] in {"GREEN", "YELLOW"}
    assert cost["status"] == "RED"
    assert cost["test_metrics"]["pr_auc"] > 0
    assert cost["test_metrics"]["roc_auc"] < .65
    assert cost["test_metrics"]["recall"] < .15
