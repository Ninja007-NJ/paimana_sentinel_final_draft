from __future__ import annotations

from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.alert_service import AlertService
from backend.assistant_context import AssistantContextBuilder
from backend.analytics_service import AnalyticsService
from backend.config import ALLOWED_ORIGINS, API_VERSION, MODEL_STATUS
from backend.intelligence_service import IntelligenceService
from backend.model_service import ModelService
from backend.peer_service import PeerService
from backend.priority_service import PriorityService
from backend.project_service import ProjectService
from backend.schemas import (
    ExplanationResponse,
    PredictionResponse,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectSnapshotInput,
    PriorityRecord,
    AlertRecord,
    AssistantQuery,
    AssistantResponse,
    IntelligenceQuestion,
    PeerComparisonResponse,
    ScenarioRecommendationsResponse,
    TrajectoryPoint,
    WhatIfRequest,
    WhatIfResponse,
)
from backend.trajectory_service import TrajectoryService
from backend.what_if_service import WhatIfService


@asynccontextmanager
async def lifespan(app: FastAPI):
    model = ModelService()
    projects = ProjectService(model)
    app.state.model = model
    app.state.projects = projects
    app.state.trajectories = TrajectoryService(projects, model)
    app.state.peers = PeerService(projects)
    app.state.alerts = AlertService(projects)
    app.state.what_if = WhatIfService(projects, model)
    app.state.analytics = AnalyticsService(projects, app.state.alerts)
    app.state.priorities = PriorityService(projects, model, app.state.alerts, app.state.peers)
    app.state.assistant_context = AssistantContextBuilder(
        projects, model, app.state.trajectories, app.state.peers,
        app.state.alerts, app.state.what_if, app.state.analytics, app.state.priorities,
    )
    app.state.intelligence = IntelligenceService(app.state.assistant_context)
    yield


app = FastAPI(
    title="PAIMANA Sentinel",
    version=API_VERSION,
    description="Read-only PAIMANA risk analytics and grounded project-intelligence service.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _not_found(project_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def _prediction_payload(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "explanation_sentence"}


def _explanation(project_id: str, snapshot_month: str, prediction: dict) -> dict:
    return {
        "canonical_project_id": project_id,
        "snapshot_month": snapshot_month,
        "delay_probability_3m": prediction["delay_probability_3m"],
        "risk_level": prediction["risk_level"],
        "top_risk_drivers": prediction["top_risk_drivers"],
        "top_protective_drivers": prediction["top_protective_drivers"],
        "explanation": prediction["explanation_sentence"],
    }


@app.get("/health")
def health(request: Request):
    model = request.app.state.model
    return {
        "status": "ok",
        "model_loaded": True,
        "model_version": model.model_version,
        "model_status": MODEL_STATUS,
        "delay_6m_model_loaded": True,
        "delay_6m_model_status": model.delay_6m_status,
        "assistant_hosted_mode_configured": request.app.state.intelligence.client.configured,
        "assistant_model": request.app.state.intelligence.client.model,
        "api_version": API_VERSION,
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(snapshot: ProjectSnapshotInput, request: Request):
    values = snapshot.model_dump()
    project_id = values.pop("canonical_project_id")
    threshold_profile = values.pop("threshold_profile")
    row = pd.Series(values)
    result = request.app.state.model.predict_one(
        row, project_id=project_id, threshold_profile=threshold_profile, explain=True
    )
    return _prediction_payload(result)


@app.get("/projects", response_model=list[ProjectListItem])
def projects(request: Request):
    return request.app.state.projects.list_projects()


@app.get("/alerts", response_model=list[AlertRecord])
def alerts(request: Request, limit: int = Query(default=500, ge=1, le=2000),
           severity: str | None = None, alert_type: str | None = None,
           sector: str | None = None, ministry: str | None = None):
    records = request.app.state.alerts.all(limit, severity, alert_type, sector, ministry)
    return request.app.state.priorities.enrich_alerts(records)


@app.get("/priorities", response_model=list[PriorityRecord])
def priorities(request: Request, limit: int = Query(default=500, ge=1, le=3000),
               priority_level: str | None = None, trajectory_status: str | None = None,
               sector: str | None = None, ministry: str | None = None, state: str | None = None,
               recommended_action: str | None = None):
    return request.app.state.priorities.all(
        limit=limit, priority_level=priority_level, trajectory_status=trajectory_status,
        sector=sector, ministry=ministry, state=state, recommended_action=recommended_action,
    )


@app.get("/priorities/audit")
def priority_audit(request: Request):
    return request.app.state.priorities.audit()


@app.get("/analytics/portfolio")
def portfolio_analytics(request: Request):
    return request.app.state.analytics.portfolio()


@app.get("/analytics/sectors")
def sector_analytics(request: Request):
    return request.app.state.analytics.groups("sector")


@app.get("/analytics/ministries")
def ministry_analytics(request: Request):
    return request.app.state.analytics.groups("ministry_department")


@app.get("/analytics/states")
def state_analytics(request: Request):
    return request.app.state.analytics.groups("state")


@app.get("/projects/{project_id}/trajectory", response_model=list[TrajectoryPoint])
def project_trajectory(project_id: str, request: Request):
    try:
        return request.app.state.trajectories.trajectory(project_id)
    except KeyError:
        raise _not_found(project_id)


@app.get("/projects/{project_id}/peers", response_model=PeerComparisonResponse)
def project_peers(project_id: str, request: Request):
    try:
        return request.app.state.peers.compare(project_id)
    except KeyError:
        raise _not_found(project_id)


@app.get("/projects/{project_id}/alerts", response_model=list[AlertRecord])
def project_alerts(project_id: str, request: Request):
    try:
        return request.app.state.priorities.enrich_alerts(request.app.state.alerts.for_project(project_id))
    except KeyError:
        raise _not_found(project_id)


@app.get("/projects/{project_id}/priority", response_model=PriorityRecord)
def project_priority(project_id: str, request: Request):
    try:
        return request.app.state.priorities.get(project_id)
    except KeyError:
        raise _not_found(project_id)


@app.get("/projects/{project_id}/what-if/config")
def project_what_if_config(project_id: str, request: Request):
    try:
        return request.app.state.what_if.configuration(project_id)
    except KeyError:
        raise _not_found(project_id)


@app.post("/projects/{project_id}/what-if", response_model=WhatIfResponse)
def project_what_if(project_id: str, scenario: WhatIfRequest, request: Request):
    try:
        return request.app.state.what_if.simulate(project_id, scenario.scenario_changes())
    except KeyError:
        raise _not_found(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/projects/{project_id}/scenarios", response_model=ScenarioRecommendationsResponse)
def project_scenarios(project_id: str, request: Request):
    try:
        return request.app.state.what_if.recommendations(project_id)
    except KeyError:
        raise _not_found(project_id)


@app.post("/assistant/query", response_model=AssistantResponse)
def assistant_query(query: AssistantQuery, request: Request):
    try:
        return request.app.state.intelligence.answer(query.question, query.project_id)
    except KeyError:
        raise _not_found(query.project_id or "")


@app.post("/projects/{project_id}/assistant")
def project_assistant(project_id: str, question: IntelligenceQuestion, request: Request):
    try:
        return request.app.state.intelligence.answer(question.question, project_id)
    except KeyError:
        raise _not_found(project_id)


@app.get("/projects/{project_id}/explanation", response_model=ExplanationResponse)
def project_explanation(project_id: str, request: Request):
    try:
        row = request.app.state.projects.latest_row(project_id)
    except KeyError:
        raise _not_found(project_id)
    prediction = request.app.state.model.predict_one(row, project_id=project_id, explain=True)
    return _explanation(project_id, str(row["snapshot_month"]), prediction)


@app.get("/projects/{project_id}", response_model=ProjectDetailResponse)
def project_detail(project_id: str, request: Request):
    service = request.app.state.projects
    try:
        rows = service.rows_for_project(project_id)
        latest = rows.iloc[-1]
    except KeyError:
        raise _not_found(project_id)
    prediction = request.app.state.model.predict_one(latest, project_id=project_id, explain=True)
    return {
        "canonical_project_id": project_id,
        "project_metadata": service.metadata(project_id, latest),
        "latest_snapshot": service.snapshot_record(latest),
        "historical_snapshots": [service.snapshot_record(row) for _, row in rows.iterrows()],
        "current_delay_probability_3m": prediction["delay_probability_3m"],
        "current_delay_probability_6m": prediction["delay_probability_6m"],
        "delay_6m_model_status": prediction["delay_6m_model_status"],
        "risk_level": prediction["risk_level"],
        "explanation": _explanation(project_id, str(latest["snapshot_month"]), prediction),
        "data_quality_score": float(latest["data_quality_score"]),
    }
