from __future__ import annotations

from backend.model_service import ModelService
from backend.project_service import ProjectService


class TrajectoryService:
    def __init__(self, projects: ProjectService, model: ModelService):
        self.projects = projects
        self.model = model

    def trajectory(self, project_id: str) -> list[dict]:
        rows = self.projects.rows_for_project(project_id)
        return [
            {
                "snapshot_month": row.snapshot_month,
                "predicted_delay_probability_3m": float(probability),
                "risk_level": self.model.risk_level(float(probability)),
                "data_quality_score": float(row.data_quality_score),
            }
            for row, probability in zip(rows.itertuples(index=False), rows["predicted_delay_probability_3m"])
        ]
