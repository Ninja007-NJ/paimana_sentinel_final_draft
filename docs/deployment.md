# Deployment

## Local

Backend: install `backend/requirements.txt`, then run `uvicorn backend.main:app --host 0.0.0.0 --port 8000`. Frontend: run `npm ci` and `npm run build` in `frontend/`; use `npm run dev` for development.

Set `VITE_API_URL` at frontend build time. Backend paths may be overridden with `PAIMANA_MODEL_BUNDLE`, `PAIMANA_DELAY_6M_MODEL_BUNDLE`, `PAIMANA_TRAINING_DATA`, `PAIMANA_TRAINING_MASTER`, `PAIMANA_RAW_SNAPSHOTS`, and `PAIMANA_IDENTITY_AUDIT`. Set comma-separated `PAIMANA_ALLOWED_ORIGINS` for CORS.

For hosted Project Intelligence Assistant responses, copy `.env.example` to a local `.env` and set `OPENROUTER_API_KEY`. The default model is `google/gemma-4-26b-a4b-it:free`; `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_APP_NAME`, `OPENROUTER_SITE_URL`, and `OPENROUTER_TIMEOUT_SECONDS` are configurable. `.env` is ignored and must never be committed or bundled into React. The free OpenRouter model can be rate-limited. Without a key or when the provider fails, the API automatically uses deterministic grounded fallback mode.

Example development values: `VITE_API_URL=http://localhost:8000` and `PAIMANA_ALLOWED_ORIGINS=http://localhost:5173`. Verify deployment with `GET http://localhost:8000/health`; it must report both frozen schedule models and whether hosted assistant mode is configured. This boolean never exposes the API key.

## Containers

Run `docker compose up --build`. The backend health check calls `/health`; nginx serves the frontend and proxies `/api/` to FastAPI. Mount frozen artifacts read-only in managed deployments. Back up and checksum the model bundle and CSVs before release.
