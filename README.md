# PAIMANA Sentinel

PAIMANA Sentinel is a decision-support dashboard for monitoring public infrastructure projects across India. It combines a React dashboard, a read-only FastAPI service, frozen machine-learning artifacts, project-level risk explanations, intervention prioritization, and a grounded AI assistant.

## Features

- National portfolio health and early-warning dashboard
- Searchable project registry with state, sector, ministry, risk, and reliability filters
- Interactive geographical risk map with state-level project drill-down
- Project trajectories, peer comparisons, alerts, and explanation views
- Intervention priority ranking and what-if analysis
- Grounded Sentinel AI assistant backed by project and portfolio context
- Deterministic assistant fallback when the hosted LLM is unavailable

## Technology

- **Frontend:** React, TypeScript, Vite, React Router, Recharts
- **Backend:** FastAPI, Pydantic, pandas, CatBoost, scikit-learn
- **AI provider:** OpenRouter, with a deterministic local fallback
- **Deployment:** Docker Compose and nginx

## Quick start with Docker

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Add an OpenRouter API key to `.env` if hosted assistant responses are required. The application remains usable without a key because the assistant returns grounded deterministic summaries.

3. Build and start the application:

   ```bash
   docker compose up --build
   ```

4. Open the dashboard at [http://localhost:8080](http://localhost:8080). The backend API and interactive documentation are available at [http://localhost:8000](http://localhost:8000) and [http://localhost:8000/docs](http://localhost:8000/docs).

## Run locally

Create and activate a Python virtual environment, then install the backend dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API requests to the backend at `http://127.0.0.1:8000`.

## Assistant configuration

The hosted assistant is optional. Copy `.env.example` to `.env` and configure:

```dotenv
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
OPENROUTER_FALLBACK_MODELS=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_NAME=PAIMANA Sentinel
```

The API key is read only by the backend. The assistant receives compact, backend-generated project or portfolio context and is instructed to answer only from that context. Provider failures and invalid responses fall back to a deterministic grounded summary.

## Tests

Run backend tests from the repository root:

```bash
pytest backend/tests -q
```

Run frontend tests and create a production build:

```bash
cd frontend
npm test
npm run build
```

## Repository structure

```text
paimana_sentinel_final_draft/
├── backend/                       # FastAPI application
│   ├── main.py                    # API entry point and route registration
│   ├── config.py                  # Environment and model configuration
│   ├── assistant_context.py       # Grounded assistant context builder
│   ├── llm_service.py             # Hosted LLM and deterministic fallback
│   ├── project_service.py         # Project data access
│   ├── priority_service.py        # Intervention priority calculations
│   ├── analytics_service.py       # Portfolio analytics
│   ├── explanation_service.py     # Risk explanation generation
│   ├── model_service.py           # Frozen model loading and inference
│   ├── tests/                     # Backend API and service tests
│   ├── requirements.txt           # Python dependencies
│   └── Dockerfile                 # Backend container image
├── frontend/                      # React and TypeScript dashboard
│   ├── public/                    # Static browser assets
│   ├── src/
│   │   ├── api/                   # FastAPI client
│   │   ├── components/            # Shared UI and map components
│   │   ├── data/                  # Map and reference data
│   │   ├── hooks/                 # Shared React hooks
│   │   ├── pages/                 # Dashboard, projects, analytics, and alerts
│   │   ├── test/                  # Frontend component and page tests
│   │   ├── utils/                 # Formatting and reliability helpers
│   │   ├── App.tsx                # Application routes
│   │   ├── main.tsx               # Frontend entry point
│   │   └── styles.css             # Global interface styles
│   ├── package.json               # Frontend scripts and dependencies
│   ├── vite.config.ts             # Vite configuration and API proxy
│   ├── nginx.conf                 # Production web-server configuration
│   └── Dockerfile                 # Frontend container image
├── ml/                            # Machine-learning pipeline and artifacts
│   ├── artifacts/
│   │   ├── models/                # Frozen production model bundles
│   │   ├── plots/                 # Evaluation charts
│   │   ├── predictions/           # Evaluation prediction outputs
│   │   └── reports/               # Model and data-quality reports
│   ├── data/                      # Dataset loading and validation
│   ├── evaluation/                # Metrics and model analysis
│   ├── explainability/            # SHAP explanation utilities
│   ├── features/                  # Feature processing and leakage checks
│   ├── models/                    # Model wrappers and calibration
│   └── tests/                     # ML pipeline tests
├── paimana_dataset_v3/            # Clean snapshots and model-ready datasets
├── paimana_dataset/               # Earlier dataset package and audit outputs
├── raw_pdfs/                      # Source monitoring reports
├── docs/                          # Architecture and methodology documents
├── output/                        # Generated project reports
├── .env.example                   # Assistant configuration template
├── docker-compose.yml             # Backend and frontend orchestration
├── build_paimana_dataset_v3.py    # Current dataset build script
└── requirements_paimana.txt       # Dataset pipeline dependencies
```

## Documentation

Detailed documentation is available in [`docs/`](docs/), including the system architecture, API, risk scoring, data reliability, intervention priority, explainability, and deployment guidance.

The operational backend uses frozen model artifacts and does not retrain models or modify the packaged datasets during normal application use.
