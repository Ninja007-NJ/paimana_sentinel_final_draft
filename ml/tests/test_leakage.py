import pytest
from ml.features.feature_registry import ALLOWED_FEATURES
from ml.features.leakage_guard import assert_leakage_safe


def test_registry_is_safe():
    assert assert_leakage_safe(ALLOWED_FEATURES)
    assert not any("future" in name or "delay_event" in name or "valid_" in name for name in ALLOWED_FEATURES)
    assert "canonical_project_id" not in ALLOWED_FEATURES
    assert "reporting_regime" not in ALLOWED_FEATURES


def test_target_cannot_enter_x():
    with pytest.raises(ValueError): assert_leakage_safe(ALLOWED_FEATURES+["delay_event_next_3m"])
