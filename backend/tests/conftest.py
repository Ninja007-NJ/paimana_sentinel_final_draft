from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def project_id(client):
    return client.app.state.projects.list_projects()[0]["canonical_project_id"]


@pytest.fixture(scope="session")
def prediction_payload(client, project_id):
    service = client.app.state.projects
    model = client.app.state.model
    row = service.latest_row(project_id)
    payload = {"canonical_project_id": project_id}
    for feature in model.features:
        value = row[feature]
        if isinstance(value, float) and not math.isfinite(value):
            value = None
        elif hasattr(value, "item"):
            value = value.item()
        payload[feature] = value
    return payload
