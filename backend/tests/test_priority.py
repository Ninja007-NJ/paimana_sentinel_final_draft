from __future__ import annotations

import json
import math

import pytest

from backend.llm_service import SYSTEM_PROMPT
from backend.priority_service import PriorityService, trajectory_metrics


THRESHOLDS = {
    "meaningful_change": .02,
    "rapid_change_1m": .30,
    "rapid_change_3m": .56,
    "acceleration": .20,
}


def test_risk_change_velocity_and_acceleration_calculation():
    result = trajectory_metrics([.20, .25, .35, .70], THRESHOLDS)
    assert result["risk_change_1m"] == pytest.approx(.35)
    assert result["risk_change_3m"] == pytest.approx(.50)
    assert result["risk_velocity"] == pytest.approx((.05 + .10 + .35) / 3)
    assert result["risk_acceleration"] == pytest.approx(.25)


def test_insufficient_history_returns_null_acceleration():
    result = trajectory_metrics([.20, .40], THRESHOLDS)
    assert result["trajectory_status"] == "INSUFFICIENT_HISTORY"
    assert result["risk_change_1m"] == pytest.approx(.20)
    assert result["risk_change_3m"] is None
    assert result["risk_acceleration"] is None


def test_improving_rising_and_accelerating_states_are_exclusive():
    assert trajectory_metrics([.60, .50, .40], THRESHOLDS)["trajectory_status"] == "IMPROVING"
    assert trajectory_metrics([.20, .20, .25], THRESHOLDS)["trajectory_status"] == "RISING"
    assert trajectory_metrics([.20, .25, .35, .70], THRESHOLDS)["trajectory_status"] == "ACCELERATING"


def test_priority_scores_are_bounded_unique_and_deterministically_sorted(client):
    first = client.app.state.priorities.all(limit=3000)
    second = client.app.state.priorities.all(limit=3000)
    assert first == second
    assert len(first) == len({item["canonical_project_id"] for item in first}) == 2804
    assert all(0 <= item["intervention_priority_score"] <= 100 for item in first)
    assert all(0 <= item["delay_probability_3m"] <= 1 and 0 <= item["delay_probability_6m"] <= 1 for item in first)
    ordering = [(-item["intervention_priority_score"], item["canonical_project_id"]) for item in first]
    assert ordering == sorted(ordering)


def test_priority_output_contains_no_nan_or_infinity(client):
    payload = client.get("/priorities?limit=3000").json()
    encoded = json.dumps(payload, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_low_reliability_high_risk_changes_recommended_action(client):
    service: PriorityService = client.app.state.priorities
    item = {"risk_level": "CRITICAL", "data_reliability_score": 50,
            "trajectory_status": "RISING", "intervention_priority_level": "CRITICAL"}
    assert service._recommended_action(item) == "VERIFY_DATA_URGENTLY"
    item["data_reliability_score"] = 90
    assert service._recommended_action(item) == "IMMEDIATE_REVIEW"


def test_project_and_portfolio_priority_endpoints(client, project_id):
    project = client.get(f"/projects/{project_id}/priority")
    assert project.status_code == 200, project.text
    assert project.json()["canonical_project_id"] == project_id
    portfolio = client.get("/priorities?limit=20")
    assert portfolio.status_code == 200
    assert len(portfolio.json()) == 20
    assert portfolio.json()[0]["rank"] == 1
    assert client.get("/projects/DOES-NOT-EXIST/priority").status_code == 404


def test_priority_filters_match_requested_values(client):
    for query, field in (
        ("priority_level=CRITICAL", "intervention_priority_level"),
        ("trajectory_status=ACCELERATING", "trajectory_status"),
        ("recommended_action=IMMEDIATE_REVIEW", "recommended_review_action"),
    ):
        rows = client.get(f"/priorities?{query}&limit=3000").json()
        expected = query.split("=", 1)[1]
        assert rows and all(item[field] == expected for item in rows)
    sample = client.app.state.priorities.all(limit=3000)[0]
    for query_name, field in (("sector", "sector"), ("ministry", "ministry_department"), ("state", "state")):
        if sample[field]:
            rows = client.get("/priorities", params={query_name: sample[field], "limit": 3000}).json()
            assert rows and all(item[field].casefold() == sample[field].casefold() for item in rows)


def test_audit_distributions_cover_the_portfolio(client):
    audit = client.get("/priorities/audit").json()
    assert audit["eligible_projects"] == 2804
    assert sum(audit["trajectory_distribution"].values()) == 2804
    assert sum(audit["priority_distribution"].values()) == 2804
    assert sum(audit["recommended_action_distribution"].values()) == 2804
    assert audit["insufficient_history_projects"] == audit["trajectory_distribution"]["INSUFFICIENT_HISTORY"]


def test_assistant_context_receives_backend_priority_without_calculating_it(client, project_id):
    context, sources = client.app.state.assistant_context.project(project_id)
    priority = client.app.state.priorities.get(project_id)
    supplied = context["intervention_priority"]
    assert supplied["intervention_priority_score"] == priority["intervention_priority_score"]
    assert supplied["trajectory_status"] == priority["trajectory_status"]
    assert supplied["risk_acceleration"] == priority["risk_acceleration"]
    assert "intervention_priority" in sources
    assert "never calculate or alter" in SYSTEM_PROMPT
