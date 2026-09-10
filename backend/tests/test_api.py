import math

import numpy as np
import pandas as pd

from backend.config import MODEL_STATUS
from backend.project_service import clean_value


def assert_json_safe(value):
    if isinstance(value, dict):
        for item in value.values():
            assert_json_safe(item)
    elif isinstance(value, list):
        for item in value:
            assert_json_safe(item)
    elif isinstance(value, float):
        assert math.isfinite(value)
    else:
        assert not isinstance(value, (np.generic, pd.Timestamp))


def test_health_and_model_load(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_version"] == "delay_3m_v1_1"
    assert body["delay_6m_model_loaded"] is True
    assert body["delay_6m_model_status"] in {"GREEN", "YELLOW"}
    assert body["model_status"] == MODEL_STATUS


def test_prediction_probability_risk_and_confidence(client, prediction_payload):
    response = client.post("/predict", json=prediction_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert 0 <= body["delay_probability_3m"] <= 1
    assert body["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert body["prediction_confidence"]["level"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0 <= body["prediction_confidence"]["score"] <= 100
    assert body["model_version"] == "delay_3m_v1_1"
    assert 0 <= body["delay_probability_6m"] <= 1
    assert body["delay_6m_model_status"] in {"GREEN", "YELLOW"}


def test_prediction_is_deterministic(client, prediction_payload):
    first = client.post("/predict", json=prediction_payload)
    second = client.post("/predict", json=prediction_payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_malformed_prediction_rejected(client):
    response = client.post("/predict", json={"data_quality_score": 101})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_project_lookup(client, project_id):
    listing = client.get("/projects")
    assert listing.status_code == 200
    assert any(row["canonical_project_id"] == project_id for row in listing.json())
    detail = client.get(f"/projects/{project_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["canonical_project_id"] == project_id
    assert 0 <= detail.json()["current_delay_probability_6m"] <= 1
    assert detail.json()["delay_6m_model_status"] in {"GREEN", "YELLOW"}


def test_trajectory_is_chronological(client, project_id):
    response = client.get(f"/projects/{project_id}/trajectory")
    assert response.status_code == 200, response.text
    trajectory = response.json()
    months = [row["snapshot_month"] for row in trajectory]
    assert trajectory
    assert months == sorted(months)
    assert all(0 <= row["predicted_delay_probability_3m"] <= 1 for row in trajectory)


def test_explanation_output(client, project_id):
    response = client.get(f"/projects/{project_id}/explanation")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["explanation"]
    assert "not causal" in body["explanation"]
    assert len(body["top_risk_drivers"]) <= 5
    assert len(body["top_protective_drivers"]) <= 5


def test_unknown_project_returns_404(client):
    assert client.get("/projects/DOES_NOT_EXIST").status_code == 404


def test_peer_comparison_is_deterministic_and_valid(client, project_id):
    first = client.get(f"/projects/{project_id}/peers")
    second = client.get(f"/projects/{project_id}/peers")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["peer_definition"] == body["peer_group_definition"]
    assert body["peer_count"] == 0 or body["peer_count"] >= body["minimum_peer_size"]
    for key in ("risk_percentile", "progress_percentile"):
        assert body[key] is None or 0 <= body[key] <= 100


def test_peer_group_excludes_project_itself(client, project_id):
    service = client.app.state.peers
    row = service.latest.loc[project_id]
    peers, _ = service._select(row)
    assert project_id not in set(peers.canonical_project_id)


def test_alert_queue_is_stable_and_project_scoped(client, project_id):
    first = client.get("/alerts?limit=50")
    second = client.get("/alerts?limit=50")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    priorities = [item["priority_score"] for item in first.json()]
    assert priorities == sorted(priorities, reverse=True)
    assert all(item["supporting_evidence"] for item in first.json())
    if first.json():
        severity = first.json()[0]["severity"]
        filtered = client.get(f"/alerts?severity={severity}&limit=2000")
        assert filtered.status_code == 200
        assert filtered.json() and all(item["severity"] == severity for item in filtered.json())
    scoped = client.get(f"/projects/{project_id}/alerts")
    assert scoped.status_code == 200
    assert all(item["canonical_project_id"] == project_id for item in scoped.json())


def test_alert_response_is_json_safe_and_filters_work(client):
    records = client.get("/alerts?limit=2000").json()
    assert records
    assert_json_safe(records)
    filters = (
        ("severity", "severity"),
        ("alert_type", "alert_type"),
        ("sector", "sector"),
        ("ministry", "ministry_department"),
    )
    for query_name, record_key in filters:
        sample = next(item for item in records if item.get(record_key))
        response = client.get("/alerts", params={query_name: sample[record_key], "limit": 2000})
        assert response.status_code == 200, response.text
        assert response.json()
        assert all(item[record_key].casefold() == sample[record_key].casefold() for item in response.json())


def test_empty_alert_queue_returns_empty_lists(client, project_id, monkeypatch):
    monkeypatch.setattr(client.app.state.alerts, "_alerts", [])
    assert client.get("/alerts").status_code == 200
    assert client.get("/alerts").json() == []
    assert client.get(f"/projects/{project_id}/alerts").json() == []


def test_what_if_validation_determinism_and_no_mutation(client, project_id):
    config = client.get(f"/projects/{project_id}/what-if/config").json()
    control = next(item for item in config["controls"] if item["current"] is not None)
    feature = control["feature"]
    original = client.app.state.projects.latest_row(project_id)[feature]
    value = min(control["maximum"], max(control["minimum"], control["current"] + control["step"]))
    payload = {feature: value}
    first = client.post(f"/projects/{project_id}/what-if", json=payload)
    second = client.post(f"/projects/{project_id}/what-if", json=payload)
    assert first.status_code == second.status_code == 200, first.text
    assert first.json() == second.json()
    assert 0 <= first.json()["scenario_risk"] <= 1
    assert first.json()["scenario_probability"] == first.json()["scenario_risk"]
    assert first.json()["current_probability"] == first.json()["current_risk"]
    nested = client.post(f"/projects/{project_id}/what-if", json={"changes": payload})
    assert nested.status_code == 200 and nested.json() == first.json()
    assert client.app.state.projects.latest_row(project_id)[feature] == original
    assert client.post(f"/projects/{project_id}/what-if", json={"state": "Changed"}).status_code == 422
    assert client.post(f"/projects/{project_id}/what-if", json={feature: control["maximum"] + 1000}).status_code == 422


def test_scenarios_are_noncausal_and_reproducible(client, project_id):
    first = client.get(f"/projects/{project_id}/scenarios")
    second = client.get(f"/projects/{project_id}/scenarios")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["recommendations"]) <= 3
    assert "does not imply guaranteed causal impact" in first.json()["disclaimer"]


def test_portfolio_analytics_endpoints(client):
    portfolio = client.get("/analytics/portfolio")
    assert portfolio.status_code == 200
    assert portfolio.json()["summary"]["project_count"] > 0
    summary = portfolio.json()["summary"]
    assert 0 <= summary["median_delay_risk"] <= 1
    assert 0 <= summary["high_risk_percentage"] <= 100
    assert summary["active_alert_count"] >= 0
    for path in ("sectors", "ministries", "states"):
        response = client.get(f"/analytics/{path}")
        assert response.status_code == 200
        assert all(item["project_count"] >= portfolio.json()["minimum_group_size"] for item in response.json())


def test_analytics_responses_are_json_safe_and_state_suppression_holds(client):
    for path in ("portfolio", "sectors", "ministries", "states"):
        response = client.get(f"/analytics/{path}")
        assert response.status_code == 200, response.text
        assert_json_safe(response.json())
    minimum = client.get("/analytics/portfolio").json()["minimum_group_size"]
    states = client.get("/analytics/states").json()
    assert all(row["project_count"] >= minimum for row in states)


def test_clean_value_normalizes_non_json_pandas_and_numpy_values():
    normalized = clean_value({
        "nan": np.float64("nan"),
        "infinity": np.float64("inf"),
        "integer": np.int64(7),
        "timestamp": pd.Timestamp("2026-04-01"),
        "missing": pd.NA,
    })
    assert normalized == {
        "nan": None,
        "infinity": None,
        "integer": 7,
        "timestamp": "2026-04-01T00:00:00",
        "missing": None,
    }
