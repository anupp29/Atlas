# ATLAS Deployment Guide

## Short answer

- Frontend: Vercel is a good fit.
- Backend: Do not deploy this backend on Vercel serverless.

## Why Vercel is not a fit for this backend

ATLAS backend in [backend/main.py](../backend/main.py) is a long-running stateful service:

- Uses WebSocket endpoints for continuous streams:
  - /ws/logs/{client_id}
  - /ws/incidents/{client_id}
  - /ws/activity
- Starts background monitoring loops at app startup in lifespan.
- Keeps active incident and connection state in memory.

These requirements conflict with serverless execution model constraints.

## Recommended production split

- Frontend on Vercel from [ui](../ui).
- Backend on a container platform (Render, Railway, Fly.io, ECS, AKS, etc).

This repo includes:

- Backend container file: [Dockerfile.backend](../Dockerfile.backend)
- Render manifest: [render.yaml](../render.yaml)
- Vercel config for UI: [ui/vercel.json](../ui/vercel.json)

## Deploy backend on Render

1. Create a new Render Web Service from this repository.
2. Render auto-detects [render.yaml](../render.yaml).
3. Set secret env vars in Render dashboard:
   - NEO4J_URI
   - NEO4J_USERNAME
   - NEO4J_PASSWORD
   - SERVICENOW_INSTANCE_URL
   - SERVICENOW_USERNAME
   - SERVICENOW_PASSWORD
   - ATLAS_SECRET_KEY
   - CEREBRAS_API_KEY
4. Optional LLM vars:
   - CEREBRAS_MODEL (default: qwen-3-235b-a22b-instruct-2507)
   - OLLAMA_BASE_URL and OLLAMA_MODEL (only if you want local fallback)
5. Set CORS origin after frontend URL is known:
   - ATLAS_FRONTEND_ORIGIN=https://your-ui-domain.vercel.app
6. Deploy and verify health path:
   - /api/playbooks

## Deploy frontend on Vercel

1. Import repository into Vercel.
2. Set Root Directory to ui.
3. Build command: npm run build
4. Output directory: dist
5. Set frontend env vars:
   - VITE_ATLAS_API_BASE_URL=https://your-backend-domain
   - VITE_ATLAS_WS_BASE_URL=wss://your-backend-domain
   - VITE_ATLAS_DEFAULT_CLIENT_ID=FINCORE_UK_001
6. Deploy.

## Post-deploy smoke checks

Run from repo root:

```bash
python scripts/health_check.py --backend-url https://your-backend-domain --frontend-url https://your-ui-domain --client-id FINCORE_UK_001
```

Expected:

- Critical backend checks pass.
- Optional checks may warn if mock services are intentionally offline.

## Current known blocker in local smoke script

The script [test_progress.py](../test_progress.py) is an integration smoke check and now flushes logs immediately for deterministic reads. It may still fail if dependent local fixtures are missing; it should not be used as the only production gate.
