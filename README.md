# ATLAS

Autonomous Telemetry and Log Analysis System. A multi-agent AIOps platform built for managed service providers.

ATLAS detects failures before users notice, finds root cause in seconds using a live knowledge graph, routes decisions to the right human with complete evidence, executes pre-approved resolutions with automatic rollback, and gets smarter from every outcome.

---

## What it does

Five flows drive everything:

```
DETECT -> CORRELATE -> DECIDE -> ACT -> LEARN
```

- Specialist agents monitor Java, PostgreSQL, Node.js, and Redis services continuously
- A 7-node LangGraph orchestrator correlates signals, queries Neo4j, searches ChromaDB, and calls an LLM
- A pure-Python confidence engine scores every decision and checks 8 hard vetoes before acting
- Pre-approved playbooks execute with pre-validation, success monitoring, and auto-rollback
- Every outcome feeds back into the confidence engine and trust progression model

---

## Repository layout

```
Atlas/
  backend/          FastAPI application, all Python logic
    agents/         Specialist detection agents and detection models
    config/         Client YAML configs and registry
    database/       Neo4j, ChromaDB, and SQLite clients
    execution/      Playbook library and approval tokens
    ingestion/      Normaliser, CMDB enricher, event queue, adapters
    learning/       Decision history, recalibration, weight correction, trust
    llm/            Internal LLM reasoning server (runs as a separate process on port 8001)
    orchestrator/   LangGraph pipeline, 7 nodes, confidence engine
  data/
    fallbacks/      Pre-computed LLM responses for demo reliability
    fault_scripts/  Deterministic fault simulators for demo
    seed/           Cypher and JSON seed data for Neo4j and ChromaDB
    phase5_verify.py  Phase 5 integration verification script
    phase7_verify.py  Phase 7 pre-demo hardening verification script
  docs/             Architecture, plan, use cases, master spec
  frontend/         React 18 dashboard (primary UI, connects to live backend)
  ui-atlas/         React 19 presentation UI (standalone demo screens, no backend needed)
  scripts/          Setup, validation, and demo utility scripts
  test_progress.py  Full test suite
  requirements.txt  All Python dependencies, pinned
```

---

## Quick start

### Prerequisites

- Python 3.11
- Node.js 18 or 20
- Neo4j Aura Serverless instance (free tier at console.neo4j.io)
- ServiceNow Developer instance (free at developer.servicenow.com)
- Ollama running locally with `qwen3-coder:480b-cloud` pulled (primary LLM)
- Redis for the RetailMax playbook: `docker run -p 6379:6379 redis`

### Setup

```bash
# 1. Create virtual environment from the Atlas/ directory
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create .env from the example file and fill in your values
cp .env.example .env

# 4. Seed the databases
python scripts/seed_neo4j.py
python scripts/seed_chromadb.py

# 5. Validate similarity scores
python scripts/validate_similarity.py

# 6. Run the test suite
python test_progress.py

# 7. Start the LLM server (separate terminal, port 8001)
uvicorn backend.llm.cerebras_server:app --port 8001

# 8. Start the backend (separate terminal, port 8000)
uvicorn backend.main:app --reload --port 8000
```

---

## Environment variables

A `.env.example` file is included in the repository. Copy it and fill in your values:

```bash
cp .env.example .env
```

All variables in the required block must be set before the backend will start. The backend validates every variable at startup and refuses to run if any are missing.

```
# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password

# ServiceNow Developer Instance
SERVICENOW_INSTANCE_URL=https://devXXXXXX.service-now.com
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your-servicenow-password

# Security key (generate with: python -c "import secrets; print(secrets.token_hex(32))")
ATLAS_SECRET_KEY=your-64-char-hex-string-here

# LLM endpoint — points to cerebras_server.py running on port 8001
# Do NOT point this at port 8000 (the main backend). It must point at the LLM server.
ATLAS_LLM_ENDPOINT=http://localhost:8001/internal/llm/reason

# Database paths
CHROMADB_PATH=./data/chromadb
ATLAS_AUDIT_DB_PATH=./data/atlas_audit.db
ATLAS_DECISION_DB_PATH=./data/atlas_decisions.db
ATLAS_CHECKPOINT_DB_PATH=./data/atlas_checkpoints.db

# Ollama (primary LLM — start with: ollama serve)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-coder:480b-cloud
```

Optional variables (system works without them, with reduced capability):

```
# Anthropic Claude (fallback LLM if Ollama is unavailable)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI GPT-4o (secondary fallback)
OPENAI_API_KEY=sk-...

# Slack notifications for human review routing
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Frontend CORS origin (default: http://localhost:5173)
ATLAS_FRONTEND_ORIGIN=http://localhost:5173
```

---

## Two frontends

This repository contains two separate frontends. They serve different purposes.

`frontend/` is the primary operational dashboard. It connects to the live backend via WebSocket and shows real log streams, incident briefing cards, SHAP charts, and the approval flow. Use this for live demos with a running backend. Built with React 18.

`ui-atlas/` is a standalone presentation UI with pre-built demo screens. It does not require a live backend connection. Use this for presentations where a live backend is not available. Built with React 19.

```bash
# Primary dashboard (requires running backend on port 8000)
cd frontend
npm install
npm run dev    # starts on http://localhost:5173

# Standalone presentation UI (no backend required)
cd ui-atlas
npm install
npm run dev    # starts on http://localhost:5174
```

---

## Running the demo

```bash
# Terminal 1: LLM server
uvicorn backend.llm.cerebras_server:app --port 8001

# Terminal 2: backend
uvicorn backend.main:app --port 8000

# Terminal 3: frontend
cd frontend && npm run dev

# Terminal 4: inject the FinanceCore cascade fault
python data/fault_scripts/financecore_cascade.py

# Or use the end-to-end trigger script (instant replay, no sleep between events)
python scripts/trigger_financecore_e2e.py
```

After the fault is injected, the pipeline runs automatically. To approve the incident:

```bash
python scripts/test_resume.py
```

---

## Pre-demo health check

Run this immediately before presenting. It checks all external services, fallback files, and demo data in under 30 seconds.

```bash
python scripts/phase7_demo_check.py
```

Exit code 0 means green light. Exit code 1 means something needs fixing before you present. The script prints exactly what failed and how to fix it.

---

## Running tests

```bash
python test_progress.py
```

Tests cover: client registry, confidence scorer, all 8 vetoes, playbook library, audit database, decision history, approval tokens, state guards, normaliser, event queue, routing logic, adapters, base agent, and the full pipeline end-to-end.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| POST | /webhook/cmdb | ServiceNow change webhook, updates Neo4j |
| POST | /api/logs/ingest | Ingest log lines from fault scripts or adapters |
| POST | /api/incidents/approve | Human approval, resumes pipeline |
| POST | /api/incidents/reject | Human rejection with mandatory reason |
| POST | /api/incidents/modify | L2 parameter override approval |
| GET | /api/incidents/active | All active incidents |
| GET | /api/audit | Audit log query by client and date range |
| GET | /api/trust/{client_id} | Trust level and progression metrics |
| WS | /ws/logs/{client_id} | Live log stream |
| WS | /ws/incidents/{client_id} | Live incident state updates |
| WS | /ws/activity | Global activity feed |

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11, asyncio |
| Orchestration | LangGraph 0.2+ |
| LLM primary | Ollama (qwen3-coder:480b-cloud) |
| LLM fallback | Anthropic Claude, then GPT-4o |
| Time-series detection | Chronos-Bolt (HuggingFace) |
| Point anomaly | Isolation Forest + SHAP |
| Uncertainty | Conformal prediction |
| Knowledge graph | Neo4j Aura Serverless |
| Vector store | ChromaDB (namespaced per client) |
| ITSM | ServiceNow REST API |
| Audit / learning | SQLite WAL mode (3 separate databases) |
| Frontend (live) | React 18, Tailwind, Framer Motion, Recharts, React Force Graph 2D |
| Frontend (demo) | React 19, Tailwind, React Router |

---

## Multi-tenancy

Every data object is tagged with `client_id` at creation. Neo4j queries require `client_id` in every WHERE clause. ChromaDB uses separate namespaced collections per client. Cross-client learning uses federated embedding centroids only, with zero information leakage between clients. This is enforced architecturally, not by policy.

---

## Working directory

All scripts must be run from the `Atlas/` directory — the directory containing `backend/`, `data/`, `scripts/`, and `requirements.txt`. Running from a parent or child directory will cause `ModuleNotFoundError` because the backend package is resolved relative to this root.

```bash
# Correct
cd Atlas
python scripts/seed_neo4j.py

# Wrong — will fail with ModuleNotFoundError
cd Atlas/scripts
python seed_neo4j.py
```

---

## Docs

- `docs/ARCHITECTURE.md` — Full system design, all layers, all components
- `docs/MASTER.md` — Complete product specification
- `docs/USECASE.md` — User flows for every persona
- `docs/PLAN.md` — Build sequence and task breakdown
- `docs/STRUCTURE.md` — Every file, its purpose, its guardrails
