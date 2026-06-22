# Local Development Setup

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Backend runtime |
| Node.js 18+ | Frontend build (`ui/`) |
| A Neo4j Aura Serverless instance | Free tier at [console.neo4j.io](https://console.neo4j.io) |
| A ServiceNow Developer instance | Free at [developer.servicenow.com](https://developer.servicenow.com) |
| A Cerebras API key | Free developer tier — primary LLM reasoning provider |
| *(Optional)* Ollama installed locally | Offline LLM fallback |

## 1. Clone and Configure

```bash
git clone https://github.com/YOUR-ORG/Atlas.git
cd Atlas
cp .env.example .env
```

Fill in `.env`. The backend **refuses to start** if any required variable is
missing — this is intentional, not a bug, and the startup log will name exactly
which variable is absent.

=== "Required"

    ```bash
    NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=

    SERVICENOW_INSTANCE_URL=https://devXXXXXX.service-now.com
    SERVICENOW_USERNAME=admin
    SERVICENOW_PASSWORD=

    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    ATLAS_SECRET_KEY=

    CEREBRAS_API_KEY=
    CEREBRAS_MODEL=qwen-3-235b-a22b-instruct-2507
    ```

=== "Optional"

    ```bash
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=qwen3-coder:480b-cloud

    ANTHROPIC_API_KEY=
    OPENAI_API_KEY=
    SLACK_WEBHOOK_URL=
    ATLAS_FRONTEND_ORIGIN=http://localhost:5173
    ```

## 2. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd ui && npm install && cd ..
```

## 3. Seed the Databases

```bash
python scripts/seed_neo4j.py       # idempotent — safe to re-run
python scripts/seed_chromadb.py    # one-time embedding of historical incidents
python scripts/validate_similarity.py   # confirms ChromaDB returns expected matches
```

## 4. Start Everything

=== "macOS / Linux"

    ```bash
    ./start_atlas.sh
    ```

=== "Windows"

    ```powershell
    ./start_atlas.ps1
    ```

=== "Manually"

    ```bash
    # Terminal 1 — backend
    uvicorn backend.main:app --reload --port 8000

    # Terminal 2 — frontend
    cd ui && npm run dev
    ```

## 5. Verify

```bash
python scripts/health_check.py --wait
```

Then exercise the full pipeline without manually waiting for a real anomaly:

```bash
python scripts/trigger_financecore_e2e.py
```

This replays the FinanceCore connection-pool-exhaustion scenario through
`/api/logs/ingest` and prints the incident state once the pipeline suspends for
human review — the fastest path from a clean checkout to seeing the entire
[end-to-end data flow](../architecture/data-flow.md) execute.

## Running Tests

=== "Backend"

    ```bash
    pytest backend/tests/
    ```

=== "Frontend (unit)"

    ```bash
    cd ui && npm run test
    ```

=== "Frontend (E2E)"

    ```bash
    cd ui && npx playwright test
    ```

## Common Troubleshooting

| Symptom | Likely cause |
|---|---|
| Backend refuses to start, names a missing variable | `.env` incomplete — see Required variables above |
| Backend starts but `health_check.py` reports Neo4j unreachable | Aura instance paused (free tier auto-pauses on inactivity) — open the Neo4j console to wake it |
| `/internal/llm/reason` times out | `CEREBRAS_API_KEY` invalid/missing, or rate limited — confirm with `scripts/test_ollama_qwen3.py` whether the local fallback works as a stopgap |
| WebSocket closes immediately with code `4403` | `client_id` in the URL doesn't match a configured client in `backend/config/clients/` |

[:octicons-arrow-right-24: Production deployment](../deployment/guide.md){ .md-button .md-button--primary }
