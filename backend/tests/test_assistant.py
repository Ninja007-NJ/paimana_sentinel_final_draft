from __future__ import annotations

import json

import pytest

from backend.intelligence_service import GroundedFallbackSummarizer, IntelligenceService
from backend.llm_service import OpenRouterClient, OpenRouterError, SYSTEM_PROMPT, clean_model_answer, validate_grounded_answer


def test_blank_question_rejected(client):
    response = client.post("/assistant/query", json={"question": "   "})
    assert response.status_code == 422


def test_overlong_question_rejected(client):
    response = client.post("/assistant/query", json={"question": "x" * 1501})
    assert response.status_code == 422


def test_unknown_project_handled(client):
    response = client.post("/assistant/query", json={"question": "Why?", "project_id": "DOES-NOT-EXIST"})
    assert response.status_code == 404


def test_project_question_uses_grounded_no_key_fallback(client, project_id):
    response = client.post("/assistant/query", json={"question": "Why should this project be reviewed?", "project_id": project_id})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] == "project"
    assert body["project_id"] == project_id
    assert body["provider"] == "deterministic-fallback"
    assert body["grounded"] is True
    assert body["model"] == "google/gemma-4-26b-a4b-it:free"


def test_portfolio_question_works_without_sending_all_projects(client):
    response = client.post("/assistant/query", json={"question": "Which sectors need the most attention?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] == "portfolio"
    assert body["project_id"] is None
    assert body["provider"] == "deterministic-fallback"
    assert {"portfolio", "sectors", "ministries", "alerts"}.issubset(body["sources_used"])


def test_unrelated_coding_question_is_refused(client):
    response = client.post(
        "/assistant/query",
        json={"question": "Write Python code for reversing a linked list."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "scope-guard"
    assert body["sources_used"] == []
    assert "only answer questions about PAIMANA Sentinel" in body["answer"]
    assert "class ListNode" not in body["answer"]


def test_project_scope_guard_still_allows_domain_question(client, project_id):
    response = client.post(
        "/assistant/query",
        json={"question": "What are this project's active warnings?", "project_id": project_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider"] in {"deterministic-fallback", "openrouter"}


def test_project_scope_guard_rejects_casual_question(client, project_id):
    body = client.post("/assistant/query", json={"question": "Hello, how are you?", "project_id": project_id}).json()
    assert body["provider"] == "scope-guard"
    assert body["sources_used"] == []


def test_project_fallback_answers_the_requested_topic(client, project_id):
    reliability = client.post("/assistant/query", json={"question": "What is the data reliability?", "project_id": project_id}).json()
    warnings = client.post("/assistant/query", json={"question": "What are the active warnings?", "project_id": project_id}).json()
    assert reliability["provider"] == "deterministic-fallback"
    assert warnings["provider"] == "deterministic-fallback"
    assert reliability["answer"] != warnings["answer"]
    assert "Data Reliability" in reliability["answer"]
    assert "warnings" in warnings["answer"]


def test_all_project_suggestions_are_in_scope_and_answered(client, project_id):
    questions = [
        "Why is this project high risk?",
        "How has its risk changed recently?",
        "Compare this project with similar projects.",
        "Explain the active warnings.",
        "How reliable is this prediction?",
        "What model-based scenarios should officials review?",
        "Compare the 3-month and 6-month risks.",
        "Why is this project prioritized for intervention?",
    ]
    for question in questions:
        body = client.post("/assistant/query", json={"question": question, "project_id": project_id}).json()
        assert body["provider"] != "scope-guard", question
        assert body["answer"], question

        reliability = client.post("/assistant/query", json={"question": "How reliable is this prediction?", "project_id": project_id}).json()
        priority = client.post("/assistant/query", json={"question": "Why is this project prioritized for intervention?", "project_id": project_id}).json()
        assert "Data Reliability" in reliability["answer"]
        assert "Intervention Priority" in priority["answer"]


def test_project_context_uses_existing_3m_6m_reliability_and_analytics(client, project_id):
    context, sources = client.app.state.assistant_context.project(project_id)
    latest = client.app.state.projects.latest_row(project_id)
    prediction = client.app.state.model.predict_one(latest, project_id=project_id, explain=True)
    assert context["schedule_risk"]["delay_risk_3m"] == prediction["delay_probability_3m"]
    assert context["schedule_risk"]["delay_risk_6m"] == prediction["delay_probability_6m"]
    assert context["data_reliability"]["score"] == float(latest["data_quality_score"])
    assert context["data_reliability"]["score"] != context["schedule_risk"]["delay_risk_3m"]
    assert context["trajectory"] == client.app.state.trajectories.trajectory(project_id)[-6:]
    assert context["peer_comparison"] == client.app.state.peers.compare(project_id)
    assert context["alerts"] == client.app.state.alerts.for_project(project_id)[:5]
    assert {"prediction_3m", "prediction_6m", "shap", "peers", "alerts", "scenarios"}.issubset(sources)
    assert "cost_risk" not in context and context["limitations"]["cost_escalation_prediction_operational"] is False


def test_cost_prediction_is_not_fabricated(client, project_id):
    body = client.post("/assistant/query", json={"question": "What is the cost escalation risk prediction?", "project_id": project_id}).json()
    assert body["provider"] == "deterministic-fallback"
    assert "not operational" in body["answer"]
    assert "not deployed" in body["answer"]
    assert "temporal test performance was insufficient" in body["answer"]


class FailingClient:
    configured = True
    provider = "openrouter"
    model = "google/gemma-4-26b-a4b-it:free"
    api_key = "test-secret-never-return"

    def answer(self, question, context):
        raise OpenRouterError("provider unavailable")


def test_provider_failure_uses_fallback(client, project_id, monkeypatch):
    monkeypatch.setattr(client.app.state.intelligence, "client", FailingClient())
    body = client.post("/assistant/query", json={"question": "Explain the active warnings.", "project_id": project_id}).json()
    assert body["provider"] == "deterministic-fallback"
    assert body["grounded"] is True
    assert "test-secret-never-return" not in json.dumps(body)


class LeakyMockClient(FailingClient):
    def answer(self, question, context):
        return f"Grounded response {self.api_key}"


def test_api_key_is_defensively_redacted(client, project_id, monkeypatch):
    monkeypatch.setattr(client.app.state.intelligence, "client", LeakyMockClient())
    body = client.post("/assistant/query", json={"question": "Summarize the risk.", "project_id": project_id}).json()
    assert body["provider"] == "openrouter"
    assert "test-secret-never-return" not in json.dumps(body)
    assert "[redacted]" in body["answer"]


def test_openrouter_request_uses_fixed_model_and_grounding_prompt(monkeypatch):
    captured = {}
    openrouter = OpenRouterClient(api_key="fake-key")

    def fake_request(payload):
        captured.update(json.loads(payload))
        return json.dumps({"choices": [{"message": {"content": "Grounded answer"}}]}).encode()

    monkeypatch.setattr(openrouter, "_request", fake_request)
    assert openrouter.answer("Why?", {"scope": "portfolio"}) == "Grounded answer"
    assert captured["model"] == "google/gemma-4-26b-a4b-it:free"
    assert captured["messages"][0]["content"] == SYSTEM_PROMPT
    assert "Never independently calculate" in SYSTEM_PROMPT
    assert "Cost escalation prediction is not operational" in SYSTEM_PROMPT
    assert "Answer the user's exact question first" in SYSTEM_PROMPT
    assert "Only answer questions about PAIMANA Sentinel" in SYSTEM_PROMPT


def test_model_reasoning_is_not_returned_to_user():
    leaked = """Here's a thinking process:\n\n1. Analyze User Input:\n- User asks review priorities\n\nFinal answer: Review the highest-priority projects first."""
    assert clean_model_answer(leaked) == "Review the highest-priority projects first."


def test_unmarked_model_reasoning_is_rejected():
    with pytest.raises(OpenRouterError):
        clean_model_answer("Here's a thinking process:\n1. Analyze User Input")


def test_unsupported_numeric_claim_is_rejected():
    context = {"scope": "portfolio", "portfolio": {"summary": {"project_count": 42, "average_delay_risk": .25}}}
    assert validate_grounded_answer("There are 42 projects with 25% average risk.", context)
    with pytest.raises(OpenRouterError):
        validate_grounded_answer("There are 73 critical projects.", context)


def test_scenario_fallback_uses_required_noncausal_wording():
    context = {
        "scope": "project",
        "project": {"canonical_project_id": "P-1", "project_name": "Test Project"},
        "schedule_risk": {"risk_level": "HIGH", "delay_risk_3m": .7, "delay_risk_6m": .8},
        "data_reliability": {"score": 90, "level": "HIGH"},
        "trajectory": [], "risk_drivers": [], "peer_comparison": {}, "alerts": [],
        "recommended_scenarios": [{"label": "Required Monthly Progress"}],
    }
    answer = GroundedFallbackSummarizer().answer("What scenarios should officials review?", context)
    assert "Under this model-based scenario" in answer
    assert "does not establish causal impact" in answer
