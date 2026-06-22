# Scripts, Seed Data & Integration Utilities

Operational tooling that sits outside the request/response path of the backend
itself: environment validation, database seeding, fault injection for demos and
tests, and standalone integration utilities.

## `/scripts` — Operations & Validation

| Script | Purpose |
|---|---|
| `health_check.py` | Verifies every external service (Neo4j, ChromaDB, ServiceNow, LLM) is reachable before a demo or deployment. Supports `--wait` to poll until everything is up. |
| `endpoint_probe.py` | Validates core backend HTTP endpoints against their expected status-code contracts — a fast smoke test independent of full integration tests. |
| `seed_neo4j.py` | **Idempotent.** Executes the Cypher seed files for both demo clients and verifies critical nodes exist afterward. Safe to re-run at any time. |
| `seed_chromadb.py` | One-time embed of every historical incident in `historical_incidents.json` into ChromaDB, rate-limited against the embedding model. |
| `validate_similarity.py` | A validation gate: confirms ChromaDB semantic search returns the expected matches before the detection layer is considered ready. Exits non-zero on failure — intended to block a build. |
| `check_checkpoints.py` | Inspects LangGraph checkpoint state for debugging suspended pipelines. |
| `trigger_financecore_e2e.py` | Fires the FinanceCore fault scenario through `/api/logs/ingest` in replay mode (no artificial delay) and prints the resulting incident state once the pipeline suspends for human review — the fastest way to exercise the full pipeline locally. |
| `test_servicenow.py` | Standalone check that the configured ServiceNow developer instance credentials and API are working. |
| `test_ollama_qwen3.py` / `test_ollama_atlas_integration.py` | Verify the local Ollama fallback model works in isolation, then verify it is correctly wired into `/internal/llm/reason`. |
| `test_resume.py` / `test_resume_direct.py` | Exercise LangGraph pipeline-suspend-and-resume behaviour directly, outside the test suite. |

## `/data` — Seed Data & Fault Scenarios

=== "Seed (`data/seed/`)"

    | File | Contents |
    |---|---|
    | `financecore_graph.cypher` | Initial Neo4j graph for FinanceCore: services, infrastructure, SLAs, teams, compliance rules, and historical incidents/deployments. |
    | `retailmax_graph.cypher` | Equivalent seed graph for RetailMax, with a different topology and a GDPR-only compliance posture. |
    | `historical_incidents.json` | The historical incident corpus embedded into ChromaDB by `seed_chromadb.py` — what gives Layer 3's semantic search something real to match against from day one. |

=== "Fault scripts (`data/fault_scripts/`)"

    | File | Scenario |
    |---|---|
    | `financecore_cascade.py` | Simulates the HikariCP connection-pool exhaustion cascading into a PaymentAPI outage — the trace used throughout this documentation. |
    | `financecore_instant.py` | A faster, non-cascading variant of the FinanceCore fault for quick demos. |
    | `retailmax_redis_oom.py` | Simulates Redis memory exhaustion on RetailMax's cache cluster. |

=== "Fallbacks (`data/fallbacks/`)"

    | File | Purpose |
    |---|---|
    | `financecore_incident_response.json` | Pre-computed LLM reasoning output for the FinanceCore scenario, loaded automatically if the live LLM call exceeds its latency budget — see [Node 5](../architecture/orchestrator.md#node-5-reasoning-engine). |
    | `retailmax_incident_response.json` | Equivalent fallback for the RetailMax scenario. |

## `/IntegrationScripts` — Standalone Integration Utilities

A separate set of production-grade utilities for log monitoring and source-control
synchronisation, usable independently of the core ATLAS pipeline:

| File | Purpose |
|---|---|
| `log_monitor.py` | Structured log ingestion and monitoring with SQLite persistence. |
| `log_processor.py` | Batch processing and transformation of ingested log records. |
| `github_integration.py` / `github_repo_sync.py` | GitHub repository synchronisation — pulling change history relevant to deployment correlation. |
| `platform_integration.py` / `platform_adapters.py` | Adapters for connecting ATLAS to additional external platforms beyond the MVP set. |
| `integration_orchestrator.py` / `integration_api.py` | Coordinates multiple integration adapters behind a single internal API surface. |
| `test_runner.py` | Standalone test runner for the integration scripts package. |

See `IntegrationScripts/INTEGRATION_GUIDE.md` in the repository for setup
instructions specific to this package.

## Top-Level Operational Files

| File | Purpose |
|---|---|
| `start_atlas.sh` / `start_atlas.ps1` | One-command local startup for macOS/Linux and Windows respectively — starts backend, frontend, and verifies dependencies. |
| `Dockerfile.backend` | Production container build for the FastAPI backend. |
| `render.yaml` | Render.com deployment manifest (see [Deployment Guide](../deployment/guide.md)). |
| `test_progress.py` | Lightweight root-level smoke script for pipeline progress reporting. |
