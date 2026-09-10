from __future__ import annotations

from backend.assistant_context import AssistantContextBuilder
from backend.llm_service import OpenRouterClient, OpenRouterError


COST_MODEL_MESSAGE = (
    "Cost escalation prediction is not operational in PAIMANA Sentinel. "
    "The cost model was evaluated but was not deployed because its temporal test performance was insufficient. "
    "No operational cost-risk probability is available."
)

OUT_OF_SCOPE_MESSAGE = (
    "I can only answer questions about PAIMANA Sentinel's infrastructure analytics. "
    "Ask about portfolio or project risk, delay predictions, sectors, ministries, states, "
    "alerts, trajectories, peers, data reliability, scenarios, or intervention priorities."
)

PAIMANA_TERMS = {
    "alert", "cost", "delay", "driver", "escalat", "forecast", "infrastructure", "intervention",
    "ministr", "peer", "portfolio", "priorit", "progress", "project", "reliability", "risk",
    "scenario", "sector", "sentinel", "state", "trajectory", "warning", "paimana", "review",
    "summar", "explain", "status", "compare", "similar", "reliable", "prediction",
}
NON_PAIMANA_TERMS = (
    "python", "javascript", "typescript", "java ", "code", "coding", "programming",
    "function", "class ", "linked list", "algorithm", "sql", "html", "css", "debug",
)


def is_paimana_question(question: str, project_id: str | None = None) -> bool:
    """Keep the assistant focused on its PAIMANA decision-support domain."""
    lowered = question.casefold()
    if any(term in lowered for term in NON_PAIMANA_TERMS):
        return False
    # A project ID selects the data scope; it must not turn greetings or casual
    # conversation into an analytics question.
    return any(term in lowered for term in PAIMANA_TERMS)


def _percent(value) -> str:
    return f"{float(value) * 100:.1f}%"


def _alert_label(value: str) -> str:
    return value.replace("_", " ").title().replace("High Risk", "High-Risk")


def _short_name(value: str, limit: int = 95) -> str:
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


class GroundedFallbackSummarizer:
    provider = "deterministic-fallback"

    def answer(self, question: str, context: dict) -> str:
        context = {**context, "question": question}
        lowered = question.casefold()
        if "cost" in lowered and any(term in lowered for term in ("risk", "escalat", "predict", "forecast")):
            return COST_MODEL_MESSAGE
        return self._project(context) if context["scope"] == "project" else self._portfolio(context)

    def _project(self, context: dict) -> str:
        question = context.get("question", "").casefold()
        project = context["project"]
        risk = context["schedule_risk"]
        reliability = context["data_reliability"]
        trajectory = context.get("trajectory", [])
        drivers = context.get("risk_drivers", [])
        peers = context.get("peer_comparison", {})
        alerts = context.get("alerts", [])
        scenarios = context.get("recommended_scenarios", [])
        priority = context.get("intervention_priority", {})
        name = project.get("project_name") or project["canonical_project_id"]
        if any(term in question for term in ("reliability", "reliable", "quality", "data quality")):
            return f"{name} has Data Reliability of {reliability['score']:.0f}/100 ({reliability['level']}). This is a source-quality measure, not a risk probability."
        if any(term in question for term in ("alert", "warning")):
            if not alerts:
                return "No active deterministic warnings are available in the current PAIMANA Sentinel data for this project."
            return "Active deterministic warnings for " + name + ": " + ", ".join(_alert_label(item["alert_type"]) for item in alerts[:5]) + "."
        if any(term in question for term in ("peer", "comparable", "percentile", "similar")):
            if not peers.get("available") or peers.get("risk_percentile") is None:
                return "Peer comparison is not available in the current PAIMANA Sentinel data for this project."
            return f"{name} is at the {peers['risk_percentile']:.0f}th risk percentile among {peers['peer_count']} comparable projects."
        if any(term in question for term in ("priority", "priorit", "review first", "action", "intervention")) or (
            "review" in question and "intervention" in question
        ):
            if not priority:
                return "Intervention priority is not available in the current PAIMANA Sentinel data for this project."
            action = priority["recommended_review_action"].replace("_", " ").title()
            return f"{name} has Intervention Priority Score {priority['intervention_priority_score']:.1f}/100 ({priority['intervention_priority_level']}); recommended action: {action}. This is a deterministic review ranking, not a probability."
        if any(term in question for term in ("scenario", "what if")):
            if not scenarios:
                return "No recommended model-based scenarios are available in the current PAIMANA Sentinel data for this project."
            return "Under this model-based scenario, officials may review " + scenarios[0]["label"].lower() + "; the estimate does not establish causal impact."
        if "3-month" in question and "6-month" in question:
            return f"{name} has {_percent(risk['delay_risk_3m'])} 3-month delay risk and {_percent(risk['delay_risk_6m'])} 6-month delay risk. These are separate model horizons, not guarantees."
        if any(term in question for term in ("trajectory", "trend", "changed", "change")):
            if len(trajectory) < 2:
                return "A risk trajectory is not available in the current PAIMANA Sentinel data for this project."
            change = (trajectory[-1]["predicted_delay_probability_3m"] - trajectory[0]["predicted_delay_probability_3m"]) * 100
            direction = "increased" if change > .05 else ("decreased" if change < -.05 else "was broadly stable")
            return f"Across the available recent trajectory, 3-month risk {direction} by {abs(change):.1f} percentage points."
        if not any(term in question for term in ("risk", "delay", "status", "progress", "driver", "explain", "summary", "summar")):
            return "This information is not available in the current PAIMANA Sentinel data. Ask about this project's risk, delay prediction, progress, drivers, reliability, warnings, peers, scenarios, or intervention priority."
        sentences = [
            f"{name} is currently rated {risk['risk_level']} risk, with {_percent(risk['delay_risk_3m'])} 3-month delay risk and {_percent(risk['delay_risk_6m'])} 6-month delay risk.",
            f"Data Reliability is {reliability['score']:.0f}/100 ({reliability['level']}); this is a source-quality measure, not a risk probability.",
        ]
        if len(trajectory) >= 2:
            change = (trajectory[-1]["predicted_delay_probability_3m"] - trajectory[0]["predicted_delay_probability_3m"]) * 100
            direction = "increased" if change > .05 else ("decreased" if change < -.05 else "was broadly stable")
            sentences.append(f"Across the available recent trajectory, 3-month risk {direction} by {abs(change):.1f} percentage points.")
        if drivers:
            labels = ", ".join(item.get("label") or item["feature"] for item in drivers[:3])
            sentences.append(f"Main model-associated drivers are {labels}; these are associations, not causes.")
        if peers.get("available") and peers.get("risk_percentile") is not None:
            sentences.append(f"The project is at the {peers['risk_percentile']:.0f}th risk percentile among {peers['peer_count']} comparable projects.")
        if alerts:
            sentences.append("Active deterministic warnings: " + ", ".join(_alert_label(item["alert_type"]) for item in alerts[:3]) + ".")
        if priority:
            action = priority["recommended_review_action"].replace("_", " ").title()
            sentences.append(f"Intervention Priority Score is {priority['intervention_priority_score']:.1f}/100 ({priority['intervention_priority_level']}); recommended action: {action}. This score is a deterministic review ranking, not a probability.")
        if scenarios:
            scenario = scenarios[0]
            sentences.append(f"Under this model-based scenario, officials may review {scenario['label'].lower()}; the estimate does not establish causal impact.")
        sentences.append("PAIMANA Sentinel provides decision support and does not guarantee future outcomes.")
        return " ".join(sentences)

    def _portfolio(self, context: dict) -> str:
        summary = context["portfolio"]["summary"]
        sectors = context.get("top_sector_aggregates", [])
        ministries = context.get("top_ministry_aggregates", [])
        warnings = context.get("top_prioritized_warnings", [])
        priorities = context.get("top_intervention_priorities", [])
        question = context.get("question", "").casefold()
        if "sector" in question:
            if not sectors:
                return "Sector risk rankings are not available in the current PAIMANA Sentinel data."
            return "Highest average-risk sectors are " + ", ".join(
                f"{row['sector']} ({_percent(row['average_delay_risk'])})" for row in sectors[:5]
            ) + ". These are portfolio-level model signals, not guarantees."
        if "ministr" in question or "department" in question:
            if not ministries:
                return "Ministry risk rankings are not available in the current PAIMANA Sentinel data."
            return "Highest average-risk ministries/departments are " + ", ".join(
                f"{row['ministry_department']} ({_percent(row['average_delay_risk'])})" for row in ministries[:5]
            ) + ". These are portfolio-level model signals, not guarantees."
        if "warning" in question or "pattern" in question:
            patterns = context.get("warning_patterns", [])
            if not patterns:
                return "No portfolio warning patterns are available in the current PAIMANA Sentinel data."
            return "The major portfolio warning patterns are " + "; ".join(
                f"{row['alert_type']} ({row['count']} records, {row['high_priority_count']} high/critical)"
                for row in patterns[:5]
            ) + ". Review these as deterministic warning signals alongside model risk."
        if any(term in question for term in ("review", "first", "priorit", "critical project", "attention")):
            if priorities:
                return "Projects to review first are " + "; ".join(
                    f"{item['canonical_project_id']} ({_short_name(item['project_name'])}; "
                    f"Intervention Priority {item['intervention_priority_score']:.1f}/100, "
                    f"{item['intervention_priority_level']}; {item['key_reason']})"
                    for item in priorities[:5]
                ) + ". The score is a deterministic review ranking, not a probability."
            if not warnings:
                return "No prioritized project records are available in the current PAIMANA Sentinel data."
            return "Projects to review first are " + "; ".join(
                f"{item['canonical_project_id']} ({_short_name(item['project_name'])}; "
                f"priority {item['priority_score']:.1f}; {_alert_label(item['alert_type'])}; "
                f"current risk {item['current_risk'] * 100:.1f}%)"
                for item in warnings[:5]
            ) + ". Prioritization uses the available warning and risk signals; it is not a guaranteed outcome."
        sentences = [
            f"PAIMANA Sentinel monitors {summary['project_count']:,} projects. {summary['high_risk_count']:,} are currently high or critical risk ({summary['high_risk_percentage']:.1f}%).",
            f"Average 3-month delay risk is {_percent(summary['average_delay_risk'])}, with average Data Reliability of {summary['average_data_reliability']:.1f}/100.",
        ]
        if sectors:
            sentences.append("Highest average-risk sectors in the reportable aggregates include " + ", ".join(f"{row['sector']} ({_percent(row['average_delay_risk'])})" for row in sectors[:3]) + ".")
        if ministries:
            sentences.append("Highest average-risk ministries/departments include " + ", ".join(f"{row['ministry_department']} ({_percent(row['average_delay_risk'])})" for row in ministries[:3]) + ".")
        if warnings:
            unique = []
            for item in warnings:
                if item["canonical_project_id"] not in unique:
                    unique.append(item["canonical_project_id"])
            sentences.append("Officials should first review the top prioritized warning records, including projects " + ", ".join(unique[:5]) + ".")
        sentences.append("These are structured decision-support signals, not guaranteed outcomes.")
        return " ".join(sentences)


class IntelligenceService:
    def __init__(self, contexts: AssistantContextBuilder, client: OpenRouterClient | None = None,
                 fallback: GroundedFallbackSummarizer | None = None):
        self.contexts = contexts
        self.client = client or OpenRouterClient()
        self.fallback = fallback or GroundedFallbackSummarizer()

    def answer(self, question: str, project_id: str | None = None) -> dict:
        if project_id:
            # Preserve the API's not-found contract even when the question is
            # rejected by the scope guard.
            self.contexts.projects.latest_row(project_id)
        if not is_paimana_question(question, project_id):
            return {
                "answer": OUT_OF_SCOPE_MESSAGE,
                "scope": "project" if project_id else "portfolio",
                "project_id": project_id,
                "provider": "scope-guard",
                "model": self.client.model,
                "grounded": True,
                "sources_used": [],
            }
        context, sources = self.contexts.project(project_id) if project_id else self.contexts.portfolio()
        context["question"] = question
        lowered = question.casefold()
        force_cost_fallback = "cost" in lowered and any(term in lowered for term in ("risk", "escalat", "predict", "forecast"))
        provider = self.fallback.provider
        if self.client.configured and not force_cost_fallback:
            try:
                answer = self.client.answer(question, context)
                provider = self.client.provider
            except OpenRouterError:
                answer = self.fallback.answer(question, context)
        else:
            answer = self.fallback.answer(question, context)
        if self.client.api_key and self.client.api_key in answer:
            answer = answer.replace(self.client.api_key, "[redacted]")
        return {
            "answer": answer,
            "scope": context["scope"],
            "project_id": project_id,
            "provider": provider,
            "model": self.client.model,
            "grounded": True,
            "sources_used": sources,
        }
