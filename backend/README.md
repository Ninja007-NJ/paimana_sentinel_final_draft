# PAIMANA Sentinel Backend

This read-only FastAPI service serves the frozen `delay_3m_v1_1` CatBoost bundle. It never retrains the model or writes to Dataset v1.0.

Run from the repository root:

```bash
uvicorn backend.main:app --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

The models are loaded once during application startup. Project history comes from the frozen V3 clean/master CSVs. Delay probability and prediction confidence are separate: confidence describes input reliability using data quality, completeness, identity provenance, and training-range checks.

## Project Intelligence Assistant

`POST /assistant/query` accepts a question and an optional `project_id`. With a project ID it builds a compact project context from the frozen 3-month and accepted 6-month predictions, trajectory, SHAP explanations, Data Reliability, peers, deterministic alerts, recommended scenarios, and backend-calculated intervention priority. Without a project ID it uses compact portfolio aggregates and the highest-ranked intervention records. The assistant may explain these values but never calculates risk or priority itself, and it never sends the full dataset to the provider.

Configure hosted responses in a local `.env` copied from `.env.example`:

```dotenv
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_NAME=PAIMANA Sentinel
```

The key is read only by FastAPI and is never returned to React. If the key is absent, a request times out, the free model is rate-limited, or the provider returns an invalid response, the endpoint returns a deterministic grounded summary with `provider: "deterministic-fallback"`. Provider errors are sanitized. The evaluated cost-escalation model was rejected and is never presented as operational.

Endpoints:

- `GET /health`
- `POST /predict`
- `GET /projects`
- `GET /projects/{project_id}`
- `GET /projects/{project_id}/trajectory`
- `GET /projects/{project_id}/explanation`
- `GET /priorities`
- `GET /priorities/audit`
- `GET /projects/{project_id}/priority`
- `POST /assistant/query`

Run tests:

```bash
pytest backend/tests -q
```
