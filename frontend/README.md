# PAIMANA Sentinel Phase 3 Frontend

React/Vite frontend for the frozen Phase 2 FastAPI backend. It contains no model code and does not read or modify dataset files.

## Run locally

Start the existing backend from the repository root:

```bash
uvicorn backend.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. For another deployment, set
`VITE_API_BASE_URL`. The existing `VITE_API_URL` name remains supported for
backward compatibility.

## Verify

```bash
npm test
npm run build
```

The portfolio endpoints are intentionally granular. The client caches responses and uses bounded parallel trajectory loading. Project detail enrichment is limited to visible explorer rows.
