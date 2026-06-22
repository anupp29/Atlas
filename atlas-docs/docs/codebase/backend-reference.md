# Backend Reference — File by File

Every backend module, what it does, what it consumes, what it produces, and the
guardrail that keeps it safe. Organised by subsystem, matching
`backend/` exactly. For the cross-cutting *design* of each subsystem, see the
linked architecture page; this page is the implementation index.

!!! abstract "How to read this page"
    Each row is one source file. **Purpose** is what the file is responsible for.
    **Guardrail** is the single most important invariant the file enforces in
    code — not a summary of every check, but the one that matters most if you're
    modifying this file.

## Entry Point

| File | Purpose | Guardrail |
|---|---|---|
| `backend/main.py` | FastAPI application entry point. Registers every HTTP route and WebSocket endpoint (see [API Reference](../api/reference.md)), and starts background monitoring tasks per configured client on startup. | Refuses to start if any required environment variable, Neo4j connection, or ChromaDB connection is missing or unreachable — fails loudly rather than serving with a broken dependency. |

---

## :material-cog-outline: Configuration — Layer 0

| File | Purpose | Guardrail |
|---|---|---|
| `config/client_registry.py` | Loads and validates per-client YAML configuration. The single source of truth every other module reads client settings from. | `auto_execute_threshold` must be 0.5–1.0; `max_action_class` can never be 3 — Class 3 never auto-executes regardless of what a config file says. |
| `config/clients/financecore.yaml` | Live configuration for the FinanceCore demo client: PCI-DSS/SOX/ISO-27001, threshold `0.92`, weekday trading-hour freeze windows. | Not seed data — this is the operational config that actually governs ATLAS behaviour for this tenant. |
| `config/clients/retailmax.yaml` | Live configuration for RetailMax: GDPR only, threshold `0.82`, Trust Stage 2 (L1 Automation already enabled). | Deliberately different compliance posture from FinanceCore to prove per-client behaviour, not a global constant. |

[:octicons-arrow-right-24: Layer 0 design](../architecture/overview.md#layer-0-client-configuration-layer)

---

## :material-import: Ingestion — Layer 1

| File | Purpose | Guardrail |
|---|---|---|
| `ingestion/normaliser.py` | Converts raw events from all three ingestion paths into the unified OTel schema; assigns `atlas_event_id`; standardises timestamps to ISO-8601 UTC. | `raw_payload` is preserved byte-for-byte, always — it is the audit record of what actually arrived. Events with no `client_id` are rejected, never silently dropped. |
| `ingestion/cmdb_enricher.py` | Attaches CMDB context (criticality, owning team, SLA threshold, open changes) to every normalised event before any agent sees it. | 60-second per-client cache TTL. If Neo4j is briefly unavailable, serves from cache and flags `enriched_from_cache: true` — ingestion never blocks. |
| `ingestion/event_queue.py` | The async, per-client queue between ingestion and the specialist agents — the Kafka-pattern streaming backbone for the MVP. | Strict per-client isolation: no method exists that can read across client queues, even by mistake. |
| `ingestion/adapters/java_adapter.py` | Path B adapter: parses native Spring Boot log format, maps exception classes (e.g. `HikariPool*` → `CONNECTION_POOL_EXHAUSTED`) into the ATLAS error taxonomy. | Unparseable lines are output as-is with `severity: UNKNOWN` — never silently dropped. |
| `ingestion/adapters/postgres_adapter.py` | Path B adapter: parses native PostgreSQL logs, maps SQLSTATE codes (`53300` → `CONNECTION_POOL_EXHAUSTED`, `40P01` → `DB_DEADLOCK`) into the taxonomy. | `FATAL`-severity Postgres lines are always mapped to `ERROR` in ATLAS schema — never downgraded. |

[:octicons-arrow-right-24: Layer 1 design](../architecture/overview.md)

---

## :material-radar: Specialist Agents — Layer 2

| File | Purpose | Guardrail |
|---|---|---|
| `agents/base_agent.py` | Abstract base class defining the `ingest()` / `analyze()` / `get_evidence()` contract, the `EvidencePackage` schema, and the shared sliding-window / three-tier threshold logic every agent inherits. | An agent needs ≥ 30 minutes of baseline data before it can emit an Alert-level package; before that it can only emit Warnings. Every package is schema-validated before leaving the agent. |
| `agents/detection/chronos_detector.py` | Wraps the Chronos-Bolt pretrained time-series model — Layer A of the detection ensemble. Fine-tunes on 30 minutes of baseline per service. | If the model fails to load, falls back to statistical z-score detection and logs the fallback — detection never halts. Inference budget: 500ms. |
| `agents/detection/isolation_forest.py` | Wraps scikit-learn Isolation Forest (2% contamination) plus SHAP `TreeExplainer` — Layer B of the ensemble. | SHAP values are always computed for anomalous predictions; if SHAP itself fails, the anomaly is still reported with `shap_calculation_failed: true` rather than suppressed. |
| `agents/detection/conformal.py` | Combines Chronos-Bolt (weight `0.55`) and Isolation Forest (weight `0.45`) through conformal prediction calibration to produce a statistically valid confidence band. | The returned `confidence_level` is the empirically calibrated value, never the nominal claimed one — if real coverage is 87% against a 95% target, ATLAS reports 0.87. |
| `agents/java_agent.py` | Java/Spring Boot specialist: HTTP error rate, P95 latency, JVM heap, HikariCP/OOM/StackOverflow critical-pattern lookup. | If a service is silent for 5+ minutes, emits a Warning to the activity feed rather than waiting silently. |
| `agents/postgres_agent.py` | PostgreSQL specialist: connection count vs. `max_connections`, query latency, lock waits, replication lag. | A `PANIC:` log line always produces a P1 `EvidencePackage` immediately — no model calculation required for the most severe class of failure. |
| `agents/nodejs_agent.py` | Node.js specialist: unhandled-rejection rate, 5xx rate, request latency, event-loop lag. | `ECONNREFUSED` events must include the target host in evidence — required for the correlation engine to identify the failing downstream dependency. |
| `agents/redis_agent.py` | Redis specialist: memory usage, eviction rate, rejected commands, connected clients. | Any rejected command — even one — triggers at minimum a Warning; zero tolerance for silent command rejection. |
| `agents/correlation_engine.py` | Sits above all four agents. Maintains a 90-second per-client correlation window and confirms cascades structurally via Neo4j `DEPENDS_ON`, not temporal coincidence. | Structural confirmation is mandatory for a `CASCADE_INCIDENT` classification — two agents firing close in time is never sufficient on its own. |

[:octicons-arrow-right-24: Layer 2 design](../architecture/detection-engine.md)

---

## :material-graph-outline: Orchestrator — Layer 3

| File | Purpose | Guardrail |
|---|---|---|
| `orchestrator/state.py` | Defines `AtlasState`, the typed state object threaded through all nodes, plus `append_audit_entry()` and `guard_routing_decision()`. | Enforces three write disciplines in code: immutable-after-set fields, an append-only audit trail, and a once-set `routing_decision` — violations raise rather than silently overwrite. |
| `orchestrator/pipeline.py` | Builds the `StateGraph(AtlasState)`, wires all 9 nodes (`n1`–`n7`, `execute_playbook`, `n_learn`) and their edges, and runs/resumes incidents. | The graph suspends cleanly at any human-review point and resumes from exactly that point — no incident state is lost regardless of how long a human takes to respond. |
| `orchestrator/nodes/n1_classifier.py` | Assigns ITIL priority P1–P4 from service criticality, cascade scope, and SLA breach imminence; starts the MTTR/SLA timers. | A P1 with breach imminent in under 15 minutes forces immediate L2/L3 notification, independent of whatever the confidence engine later decides. |
| `orchestrator/nodes/n2_itsm.py` | Calls the real ServiceNow REST API and creates an `INC` ticket; writes the ticket number back to state for all downstream updates. | If ServiceNow is unavailable, sets `itsm_ticket_pending: true` and continues — incident processing is never blocked on the ITSM system being up. |
| `orchestrator/nodes/n3_graph.py` | Runs the three parallel Cypher queries (blast radius, deployment correlation, historical pattern) against Neo4j, cached 60s/client. | Sets `graph_unavailable: true` rather than failing the pipeline if Neo4j is unreachable — this flag is what later triggers Veto 7 (stale graph). |
| `orchestrator/nodes/n4_semantic.py` | Runs ChromaDB cosine-similarity search against the client's incident collection; warm-starts new clients from federated centroids of similar-stack clients. | A match also appearing in the Node 3 graph results is marked double-confirmed and given maximum weight in the Node 5 reasoning context. |
| `orchestrator/nodes/n5_reasoning.py` | Calls the LLM with the six-step ITIL reasoning prompt and validates the structured JSON response against schema. | Falls back to a pre-computed cached response if the live LLM call exceeds the latency budget, with `llm_unavailable: true` set — reasoning never silently hangs. |
| `orchestrator/nodes/n6_confidence.py` | Pure-Python confidence scoring and veto evaluation; produces the routing decision. Detailed in full on the [Confidence Engine page](../architecture/confidence-engine.md). | Class 3 actions short-circuit to `L2_L3_ESCALATION` before any factor math runs, with all 8 vetoes still evaluated for a complete audit record. |
| `orchestrator/nodes/n7_router.py` | Writes the final `routing_decision` exactly once and signals LangGraph to suspend for human input when required. | `routing_decision` is once-set at the state level — `n7` itself cannot be re-invoked to change a decision already made. |
| `orchestrator/confidence/scorer.py` | Pure scoring math for the four weighted factors and the composite score. No I/O, no side effects, fully deterministic. | Every factor function asserts its output is within `[0.0, 1.0]` before returning — an out-of-range score is a hard error, never silently clamped without logging. |
| `orchestrator/confidence/vetoes.py` | The 8 independent hard-veto checks plus `run_all_vetoes()`. | All 8 vetoes always run and are recorded, even after Class 3 fires first — the audit trail must show what *would* have fired, not just what stopped the action. |

[:octicons-arrow-right-24: Layer 3 design](../architecture/orchestrator.md) ·
[:octicons-arrow-right-24: Layer 4 design](../architecture/confidence-engine.md)

---

## :material-play-circle-outline: Execution — Layer 5

| File | Purpose | Guardrail |
|---|---|---|
| `execution/playbook_library.py` | The read-only-at-runtime registry of every action ATLAS may take. Defines `PlaybookMetadata` and the MVP playbooks. | `_register()` raises at import time if a Class 3 playbook is ever marked `auto_execute_eligible=True` — the constraint is structurally impossible to violate, not just policy. |
| `execution/playbooks/connection_pool_recovery_v2.py` | Restores HikariCP pool size via the Spring Boot Actuator management endpoint; polls connection count for recovery confirmation. | Auto-rolls back if recovery is not confirmed within 10 minutes; pre-validation re-confirms the issue is still active immediately before acting. |
| `execution/playbooks/redis_memory_policy_rollback_v1.py` | Reverts a `maxmemory-policy` misconfiguration and flushes memory pressure on a Redis instance. | Paired with its own dedicated rollback playbook, independently registered and independently validated. |
| `execution/approval_tokens.py` | Issues and validates the one-time cryptographic tokens used for dual sign-off on compliance-flagged actions. | A token is single-use and time-boxed; both signatures and both timestamps are written to the immutable audit record before execution is authorised. |

[:octicons-arrow-right-24: Layer 5 design](../architecture/execution-engine.md)

---

## :material-school-outline: Learning — Layer 6

| File | Purpose | Guardrail |
|---|---|---|
| `learning/decision_history.py` | Reads/writes `DecisionRecord`s and exposes `get_records_for_pattern()`, the query Factor 1 is built on. | Records are immutable after write — corrections are captured as *new* records, never edits to history. |
| `learning/recalibration.py` | Recomputes empirical accuracy for a pattern/action/client triple after every confirmed resolution and feeds it back into Factor 1. | `recurrence_within_48h` incidents are counted as failures for recalibration purposes even if immediate metrics looked recovered. |
| `learning/weight_correction.py` | Detects repeated L2 modification direction (3+ times) and parses L3 rejection reasons to re-weight hypothesis types. | Default updates require a *repeated* signal (3+ occurrences) — a single one-off human edit never changes a client's default. |
| `learning/trust_progression.py` | Evaluates Stage 0–4 advancement criteria and enforces one-stage-at-a-time progression. | Raises if asked to advance more than one stage at once, or past Stage 4; Stage 3→4 additionally requires explicit SDM confirmation, not just metric thresholds. |

[:octicons-arrow-right-24: Layer 6 design](../architecture/learning-engine.md)

---

## :material-database-outline: Database Clients

| File | Purpose | Guardrail |
|---|---|---|
| `database/neo4j_client.py` | Async Neo4j driver wrapper; runs the Layer 3 Cypher queries and Layer 0/6 graph writes. | Every query is parameterised and scoped by `client_id` — there is no helper method that can run an unscoped, cross-tenant query. |
| `database/chromadb_client.py` | Namespaced ChromaDB wrapper for semantic search and embedding storage, one collection per client. | Federated warm-start reads are explicitly opt-in and read-only against other clients' collections — never written to. |
| `database/audit_db.py` | SQLite-backed, production-schema, append-only audit log. | Every write is additive; the schema has no `UPDATE`/`DELETE` path exposed for incident records, by design. |

---

## :material-robot-outline: LLM Service

| File | Purpose | Guardrail |
|---|---|---|
| `llm/cerebras_server.py` | Internal reasoning endpoint (`POST /internal/llm/reason`) called by `n5_reasoning.py`. Can also run standalone (`uvicorn backend.llm.cerebras_server:app`). | Validates and repairs near-miss JSON from the model before it ever reaches orchestrator state — a malformed LLM response cannot propagate downstream. |

---

## :material-test-tube: Tests

| File | Purpose |
|---|---|
| `tests/test_incident_api_guards.py` | Exercises the FastAPI incident endpoints end-to-end with an in-process ASGI client, asserting guard conditions (auth, missing fields, invalid state transitions) are rejected correctly. |
| `tests/test_pipeline_resume_activity.py` | Verifies that a suspended LangGraph pipeline resumes correctly after a human-review interrupt, with no state loss or duplicate side effects. |
| `tests/test_pipeline_state_lookup.py` | Verifies `AtlasState` lookup and reconstruction by `thread_id`, the mechanism the frontend uses to fetch live incident detail. |

---

## Summary Table

| Subsystem | Files | Lines of responsibility |
|---|---|---|
| Configuration | 3 | Per-client thresholds, compliance posture, escalation routing |
| Ingestion | 5 | Three paths → one schema → enriched, queued events |
| Agents | 9 | Detection ensemble + 4 domain specialists + correlation |
| Orchestrator | 11 | 7-node reasoning pipeline + confidence engine |
| Execution | 4 | Playbook registry + 2 MVP playbooks + approval tokens |
| Learning | 4 | Decision history, recalibration, weight correction, trust |
| Database | 3 | Neo4j, ChromaDB, audit log clients |
| LLM | 1 | Internal reasoning service |
| Tests | 3 | API guard, pipeline resume, and state-lookup coverage |
| **Entry point** | 1 | FastAPI app, routes, startup/shutdown |

[:octicons-arrow-right-24: Frontend reference](frontend-reference.md){ .md-button .md-button--primary }
[:octicons-arrow-right-24: Scripts & seed data](scripts-and-data.md){ .md-button }
