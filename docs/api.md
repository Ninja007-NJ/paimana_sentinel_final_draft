# API

Run with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.

- `GET /health` — model and service status.
- `POST /predict` — one validated snapshot prediction.
- `GET /projects` and `GET /projects/{id}` — project catalogue and intelligence.
- `GET /projects/{id}/trajectory` and `/explanation` — historical risk and local drivers.
- `GET /projects/{id}/peers` — comparative cohort statistics.
- `GET /alerts` and `GET /projects/{id}/alerts` — deterministic warnings with evidence. Portfolio filters: `severity`, `alert_type`, `sector`, `ministry`, and `limit`.
- `GET /priorities` — national intervention queue sorted by deterministic Intervention Priority Score. Filters: `priority_level`, `trajectory_status`, `sector`, `ministry`, `state`, `recommended_action`, and optional `limit`.
- `GET /projects/{id}/priority` — one project's priority score, exclusive trajectory state, velocity/acceleration values, recommended action, and deterministic reasons.
- `GET /priorities/audit` — score formula, measured thresholds, and portfolio distributions used for validation.
- `GET /projects/{id}/what-if/config`, `POST /projects/{id}/what-if`, `GET /projects/{id}/scenarios` — constrained model scenarios.
- `GET /analytics/portfolio|sectors|ministries|states` — management analytics.
- `POST /assistant/query` — grounded project or portfolio explanation. Body: `{ "question": "Why is this project high risk?", "project_id": "P-618861" }`; omit `project_id` for portfolio scope. Responses identify `openrouter` or `deterministic-fallback`, the configured model, grounding sources, and scope.

The what-if POST body uses `{ "changes": { "progress_velocity_3m": 4.0 } }`. Flat approved fields remain accepted for compatibility. Unknown, immutable, non-finite, and out-of-range changes return HTTP 422.

OpenAPI documentation is available at `/docs` while the backend is running.

The assistant receives only compact structured analytics, not the dataset. The OpenRouter key remains backend-only. Cost-escalation prediction is not operational and the assistant explicitly reports that limitation.

The Intervention Priority Score is a 0–100 deterministic review ranking, not a probability. Risk changes are returned in probability points; clients multiply by 100 when displaying percentage points. See [Intervention Intelligence](intervention_priority.md) for the formula and measured thresholds.
