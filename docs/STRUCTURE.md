# ATLAS — STRUCTURE.md
## File-by-File Description: What Every File Does, What It Delivers, What Guardrails It Enforces

---

> This document describes every file in the ATLAS repository.
> No code is written here. This is the specification each file must meet.
> Every file has: a purpose, a list of responsibilities, its inputs, its outputs, and its guardrails.
> Build each file to satisfy this spec exactly.

---

## Repository Root

---

### `.env.example`
**Purpose:** Template showing every environment variable the system needs. Nobody commits real credentials. This file is committed. The real `.env` is not.

**Must contain entries for:**
- Cerebras API key
- Ollama base URL
- Neo4j connection URI, username, password
- ServiceNow developer instance URL, username, password, client ID
- Slack webhook URL for approval notifications
- Secret key for cryptographic approval token generation
- Environment flag (development / production)

**Guardrails:**
- `.env` must be in `.gitignore` — never committed
- All secrets loaded via environment variables only — never hardcoded in any file
- On startup, the application checks all required variables are present and fails immediately with a clear error message if any are missing

---

### `requirements.txt`
**Purpose:** Pins every Python dependency to an exact version. Prevents "works on my machine" failures.

**Must include:**
- fastapi, uvicorn, websockets
- langgraph
- neo4j (official Python driver)
- chromadb
- cerebras (LLM API)
- ollama (local LLM)
- chronos-forecasting (HuggingFace)
- scikit-learn, shap, torch
- numpy, pandas
- python-dotenv
- httpx (async HTTP client for ServiceNow calls)
- cryptography (approval token signing)
- sqlite3 is part of Python stdlib — no pip entry needed

**Guardrails:**
- Every version pinned exactly — no floating versions like `>=`
- Tested on Python 3.11 only — document this clearly

---

### `README.md`
**Purpose:** The first file any team member or judge reads. Sets up the project, explains what it is, how to run it.

**Must contain:**
- One paragraph explaining what ATLAS is and who it is for
- Prerequisites list (Python 3.11, Node 18, Neo4j Aura account, ServiceNow developer instance, API keys)
- Step-by-step setup instructions from zero to running demo
- How to seed the databases (Neo4j and ChromaDB)
- How to run the backend
- How to run the frontend
- How to trigger the demo fault scenario
- Link to ARCHITECTURE.md and USECASE.md for deep reading

---

---

## `/backend`

---

### `/backend/main.py`
**Purpose:** The entry point of the entire backend. Creates the FastAPI application, registers all routes, mounts WebSocket endpoints, and starts the background services that run continuously.

**Responsibilities:**
- Create and configure the FastAPI app instance
- Register the following HTTP routes: POST /webhook/cmdb (receives ServiceNow change webhooks), POST /api/incidents/approve (human approval submission), POST /api/incidents/reject (human rejection with reason), GET /api/incidents/active (all active incidents for dashboard), GET /api/audit (audit log query), GET /api/trust/{client_id} (trust level and progression for a client)
- Register WebSocket routes: WS /ws/logs/{client_id} (live log stream per client), WS /ws/incidents/{client_id} (live incident state updates per client), WS /ws/activity (global ATLAS activity feed)
- On startup: verify all environment variables are present, test Neo4j connection, test ChromaDB connection, test LLM API connectivity, start the log generator background task, start the agent monitoring background tasks for each configured client
- On shutdown: gracefully close all connections and background tasks

**Guardrails:**
- If any required environment variable is missing on startup: application must refuse to start and print exactly which variable is missing
- If Neo4j or ChromaDB connections fail on startup: application must refuse to start
- All WebSocket connections must handle disconnection gracefully without crashing the server
- CORS configured to allow only the frontend origin — not wildcard in production

---

### `/backend/config/client_registry.py`
**Purpose:** Loads and validates the thin ATLAS configuration for every client. This is the single source of client-specific behavior settings. All other modules read client config from here.

**Responsibilities:**
- Load client configuration from a YAML or JSON file per client (one file per client in `/backend/config/clients/`)
- Validate that every required field is present when a config is loaded — fail loudly if any field is missing
- Expose a simple interface: given a client_id, return the full config object for that client
- Hold the following per client: client_id, client_name, auto_execute_threshold (float 0-1), max_action_class (1, 2, or 3), compliance_frameworks (list: PCI-DSS, SOX, GDPR, etc.), escalation_matrix (L1/L2/L3 contacts and channels), sla_breach_thresholds (per criticality tier in minutes), change_freeze_windows (list of time windows), trust_level (current stage 0-4), business_hours (start and end time with timezone)
- Expose a method to update trust_level when the learning engine determines a stage upgrade is warranted

**Guardrails:**
- auto_execute_threshold must be between 0.5 and 1.0 — reject any value outside this range
- max_action_class must be 1 or 2 — value 3 is never permitted, Class 3 actions never auto-execute regardless of what is in the config
- compliance_frameworks must be a known list — reject unknown framework names
- If a client_id is requested that does not exist in the registry: raise a clear error, never silently return empty config
- All config values are read-only after loading — no module may modify them except trust_progression.py through its designated method

---

### `/backend/config/clients/financecore.yaml`
**Purpose:** The real ATLAS configuration for the FinanceCore demo client. This is not seed data — this is the live operational configuration that governs all ATLAS behavior for this client.

**Must contain:**
- client_id: FINCORE_UK_001
- client_name: FinanceCore Ltd
- region: UK
- auto_execute_threshold: 0.92
- max_action_class: 1
- compliance_frameworks: PCI-DSS, SOX, ISO-27001
- business_hours: Monday-Friday 08:00-18:00 GMT
- change_freeze_windows: weekdays 09:00-17:00 (trading hours), December 24 through January 2
- sla_breach_thresholds: P1=15min, P2=30min, P3=120min, P4=480min
- escalation_matrix: L1 contact, L2 contact, L3 contact, SDM contact, all with channel (slack/email)
- trust_level: 1 (L1 Assistance for demo — shows human-in-loop working)
- applications: list of PaymentAPI, TransactionDB, AuthService, NotificationService, APIGateway with their technology types and criticality

---

### `/backend/config/clients/retailmax.yaml`
**Purpose:** The real ATLAS configuration for the RetailMax demo client. Deliberately different from FinanceCore in compliance profile and trust level to demonstrate ATLAS behaving differently per client.

**Must contain:**
- client_id: RETAILMAX_EU_002
- client_name: RetailMax EU
- region: EU
- auto_execute_threshold: 0.82
- max_action_class: 1
- compliance_frameworks: GDPR
- business_hours: Monday-Friday 08:00-20:00 CET
- trust_level: 2 (L1 Automation — P3 Class 1 actions auto-execute)
- applications: ProductAPI, CartService, Redis Cache, MongoDB, CDN with their types and criticality

---

---

## `/backend/ingestion`

---

### `/backend/ingestion/normaliser.py`
**Purpose:** Takes raw log events from any of the three ingestion paths and converts them into the unified ATLAS OTel schema. Every event that enters the system passes through here.

**Responsibilities:**
- Accept raw events from Path A (already OTel-formatted), Path B (adapter output), and Path C (pulled from external tools)
- Map every incoming event to the unified schema fields: atlas_event_id, client_id, timestamp, source_system, source_type, severity, error_code, message, raw_payload, deployment_id
- Generate a unique atlas_event_id for every event
- Parse and standardise timestamps to ISO-8601 UTC
- Map severity strings from various formats (FATAL, CRITICAL, ERROR, WARN, WARNING, INFO, DEBUG) to the four ATLAS tiers (ERROR, WARN, INFO, DEBUG)
- Preserve the original raw_payload without modification — this is the audit record of what actually arrived
- Tag every event with client_id before it leaves this module — this tag is immutable from this point forward

**Guardrails:**
- Events with missing client_id must be rejected and logged to an error queue — never allowed into the main pipeline
- Events with unparseable timestamps must use the arrival timestamp with a flag indicating the original was invalid — never silently dropped
- The raw_payload field must always be preserved exactly — never modified, truncated, or summarised
- Maximum event size enforced — events over 1MB are flagged and sampled, not fully stored, with the flag recorded in the event
- client_id once set cannot be overwritten by any downstream module

---

### `/backend/ingestion/cmdb_enricher.py`
**Purpose:** Attaches CMDB context to every normalised event before agents see it. Agents never perform their own CMDB lookups — all context is pre-attached here.

**Responsibilities:**
- For every normalised event, look up the source_system in the Neo4j knowledge graph for the event's client_id
- Attach the following fields to the event: ci_class, ci_version, business_service_name, criticality_tier, open_change_records (list of change IDs active against this service), sla_breach_threshold_minutes, owner_team
- Cache CMDB lookups with a 60-second TTL to reduce Neo4j load — the graph updates via webhooks, so 60 seconds is acceptably fresh
- If a service is not found in the graph: attach a flag `cmdb_enrichment_status: not_found` and continue — never block the event pipeline for a missing CI

**Guardrails:**
- Cache must be per client_id — never serve one client's CMDB data to another client's events
- If Neo4j is temporarily unavailable: serve from cache if available, flag the event as `enriched_from_cache: true`, continue pipeline — never block ingestion
- The client_id field on the event must match the client_id used for the Neo4j query — a mismatch is a critical error that must be logged and the event rejected

---

### `/backend/ingestion/event_queue.py`
**Purpose:** The in-memory async queue that sits between ingestion and the specialist agents. Decouples ingestion speed from processing speed. Simulates Kafka behaviour for the MVP.

**Responsibilities:**
- Maintain one queue per client_id — events from different clients never mix in the same queue
- Accept enriched events from cmdb_enricher.py
- Expose a method for each specialist agent to read events from its designated queue
- Maintain a queue depth metric per client — if queue depth exceeds a threshold, emit a warning to the activity feed
- Events that have been in the queue for more than 5 minutes without being consumed are flagged as stale

**Guardrails:**
- Strict per-client queue isolation — no method that allows reading across client queues
- Queue size capped per client — if cap is reached, oldest events are dropped and the drop is logged (prevents memory exhaustion)
- No event is modified after entering the queue — read-only access for consumers

---

### `/backend/ingestion/adapters/java_adapter.py`
**Purpose:** Reads Java Spring Boot application logs in their native format and converts them to the unified ATLAS schema. This is the Path B adapter for Java services.

**Responsibilities:**
- Parse Java Spring Boot log format: timestamp, log level, thread name, logger name, message, exception (if present)
- Extract ATLAS-relevant fields: error code (mapped from exception class names), stack trace (preserved but not required for schema), response time (if present in MDC fields), service version (from startup logs)
- Map Java exception class names to ATLAS error taxonomy: HikariPool exceptions map to CONNECTION_POOL_EXHAUSTED, OutOfMemoryError maps to JVM_MEMORY_CRITICAL, etc.
- Handle multi-line log entries (stack traces span multiple lines) — reassemble them into a single event
- Output normalised event ready for cmdb_enricher.py

**Guardrails:**
- If a log line cannot be parsed: output it as-is with severity UNKNOWN and source_type java-unparseable — never silently drop
- Stack trace reassembly has a maximum line count — prevent a runaway stack trace from consuming memory
- Exception class name mapping to error codes must be a maintained lookup table — unknown exception classes get error_code JAVA_UNKNOWN with the class name preserved

---

### `/backend/ingestion/adapters/postgres_adapter.py`
**Purpose:** Reads PostgreSQL server logs in their native format and converts to ATLAS unified schema.

**Responsibilities:**
- Parse PostgreSQL log format: timestamp, severity, error code (SQLSTATE), message, detail, context, location
- Map PostgreSQL SQLSTATE codes and error message patterns to ATLAS error taxonomy: 53300 (too_many_connections) maps to CONNECTION_POOL_EXHAUSTED, 40P01 (deadlock_detected) maps to DB_DEADLOCK, etc.
- Extract metrics where present in log lines: connection count from status messages, query duration from slow query logs, lock wait time from lock log entries
- Output normalised event

**Guardrails:**
- SQLSTATE codes not in the known mapping table get error_code DB_UNKNOWN with the SQLSTATE preserved — never dropped
- Log lines with FATAL severity are always output as ERROR in the ATLAS schema — never downgraded
- The raw PostgreSQL log line is always preserved in raw_payload regardless of whether parsing succeeded

---

---

## `/backend/agents`

---

### `/backend/agents/base_agent.py`
**Purpose:** The abstract base class that every specialist agent inherits from. Defines the contract every agent must satisfy. Enforces that all agents behave consistently regardless of technology domain.

**Responsibilities:**
- Define the three required methods every agent must implement: ingest(event), analyze(), get_evidence()
- Define the EvidencePackage data structure that every agent must produce — all fields, all types
- Implement the sliding window logic that is common to all agents: maintain a rolling time-series of metric values per service per client, calculate current values per window
- Implement the three detection tier thresholds: Warning (2σ), Alert (3σ sustained 60s), Critical (known-bad code immediate)
- Implement the output method that sends a completed EvidencePackage to the correlation engine
- Maintain a health status for each agent — is it actively monitoring, is its baseline established, when did it last fire

**EvidencePackage fields every agent must produce:**
- evidence_id (unique)
- agent_id
- client_id
- service_name
- anomaly_type (from ATLAS taxonomy)
- detection_confidence (float 0-1, from conformal prediction)
- shap_feature_values (dict: feature name → contribution percentage)
- conformal_interval (lower bound, upper bound, confidence level)
- baseline_mean and baseline_stddev for the primary metric
- current_value of the primary metric
- deviation_sigma (how many standard deviations above baseline)
- supporting_log_samples (exactly 5 log lines — no more, no less)
- preliminary_hypothesis (string from domain rule mapping)
- severity_classification (P1, P2, or P3)
- detection_timestamp

**Guardrails:**
- No agent may produce an EvidencePackage without a valid client_id — enforced in the base class send method
- No agent may read another client's baseline data — each agent instance is scoped to one client
- An agent must have at least 30 minutes of baseline data before it can produce Alert-level EvidencePackages — in the bootstrap period it can only produce Warnings
- The supporting_log_samples field must contain exactly 5 samples — if fewer are available, the evidence package is held until 5 samples exist or the agent is in Critical mode (Critical mode sends with however many samples are available, minimum 1)
- Every EvidencePackage must be validated against the schema before being sent to the correlation engine — schema validation failure is logged and the package is held, not sent

---

### `/backend/agents/detection/chronos_detector.py`
**Purpose:** Wraps the Chronos-Bolt pretrained time-series foundation model. Provides the temporal pattern detection capability for every agent. This is Layer A of the two-layer ensemble.

**Responsibilities:**
- Load the Chronos-Bolt model from HuggingFace on first use and cache it in memory
- Accept a time-series of metric values (list of floats with timestamps) as input
- Run inference and return an anomaly probability score (float 0-1) for the most recent data point
- Fine-tune on 30 minutes of normal baseline data when a new service is first monitored — store the fine-tuned model state per client per service
- Return not just a score but a prediction interval (the model's expected range) — the deviation from this interval is what gets fed to the conformal wrapper
- Expose a method to update the baseline: add new normal data points to the rolling 4-week seasonal window

**Guardrails:**
- Model loading must happen asynchronously on first use — never block the main event loop during model load
- Fine-tuned model state is stored per client_id per service_name — never shared across clients
- If the model fails to load (HuggingFace unavailable, corrupt model file): fall back to statistical z-score detection for that service, log the fallback, continue operating — never halt
- Inference must complete within 500ms — if it takes longer, use the last known score and flag the timeout in the evidence package
- Minimum data points required before producing meaningful output: 10 consecutive readings — before this threshold, output a neutral score of 0.5

---

### `/backend/agents/detection/isolation_forest.py`
**Purpose:** Wraps the scikit-learn Isolation Forest model with SHAP explainability. Provides the point anomaly detection capability. This is Layer B of the two-layer ensemble.

**Responsibilities:**
- Train an Isolation Forest model on the baseline feature set per service per client: contamination parameter set to 0.02 (assumes 2% of observations are anomalies)
- Features used: error_rate, response_time_p95, resource_utilisation, error_code_frequency (top 5 error codes as individual features)
- On each new observation, run inference and return: anomaly score (float, more negative = more anomalous), is_anomaly (boolean, based on the contamination threshold)
- Run SHAP TreeExplainer on every anomalous prediction to produce feature contribution values
- Return the SHAP values as a dict: feature_name → contribution_percentage, summing to 100%
- Retrain the model every 24 hours on the rolling baseline window — not just at startup

**Guardrails:**
- SHAP values must always be calculated for anomalous predictions — never send an anomaly flag without explainability
- Model training must happen in a background thread — never block the ingestion or detection pipeline during retraining
- Per-client per-service model isolation — models are never shared across clients
- If SHAP calculation fails for any reason: return the anomaly flag with shap_values set to an empty dict and a flag `shap_calculation_failed: true` — never suppress the anomaly because SHAP failed
- Minimum training samples: 100 observations. If fewer are available, the model is not used and detection falls back to z-score only, flagged accordingly

---

### `/backend/agents/detection/conformal.py`
**Purpose:** Wraps both the Chronos-Bolt score and the Isolation Forest score in a conformal prediction framework. Produces statistically valid confidence intervals on every combined anomaly score. This is what allows ATLAS to say "94% confident this is anomalous" with mathematical backing.

**Responsibilities:**
- Accept the Chronos-Bolt score and the Isolation Forest score as inputs
- Combine them using a weighted ensemble: Chronos-Bolt weight 0.55 (better at temporal patterns), Isolation Forest weight 0.45 (better at point anomalies) — these weights are configurable in the client config
- Apply conformal prediction calibration: using a held-out calibration set from the baseline period, calculate the nonconformity scores and produce valid prediction intervals at the configured confidence level (default 95%)
- Return: combined_score (float 0-1), confidence_level (float, e.g. 0.94), lower_bound (float), upper_bound (float), is_anomalous (boolean)
- The is_anomalous flag is only set to True when the combined score exceeds the conformal threshold at the specified confidence level

**Guardrails:**
- If the calibration set has fewer than 50 samples: conformal prediction is not applied, fall back to simple threshold, flag the fallback in the output
- The confidence_level returned must always be the empirically calibrated value, never a claimed value — if calibration data suggests 87% actual coverage at the nominal 95% level, return 0.87 not 0.95
- Combined score must always be between 0.0 and 1.0 — clip if arithmetic produces values outside this range and log the clipping

---

### `/backend/agents/java_agent.py`
**Purpose:** The specialist agent for Java Spring Boot services. Knows what normal looks like for Java applications and what the critical failure patterns are. Inherits from base_agent.py.

**Responsibilities:**
- Consume normalised enriched events from the event queue for Java services (source_type = java-spring-boot)
- Maintain the rolling seasonal baseline for: HTTP error rate (errors per minute), HTTP 5xx rate (percentage of total requests), response time P95 (milliseconds), JVM heap usage percentage, active thread count
- Maintain a critical error code lookup table specific to Java: HikariPool exhaustion patterns, OutOfMemoryError, StackOverflowError, ClassNotFoundException, connection refused patterns — any of these triggers immediate Critical-level detection regardless of statistical baseline
- Produce preliminary hypotheses mapped from error patterns: HikariCP errors → "Connection pool exhaustion — possible connection leak or misconfigured pool size." OOM → "JVM heap exhaustion — possible memory leak or undersized heap configuration."
- When Alert or Critical level triggered: call both detection layers (Chronos-Bolt and Isolation Forest), combine with conformal wrapper, produce full EvidencePackage

**Guardrails:**
- The critical error code lookup table must be reviewed and updated — it is not set-and-forget. A process for adding new critical patterns must be documented.
- JVM heap metrics are optional (only available if JMX is exposed) — the agent must function correctly when JVM metrics are absent, using only the log-derivable metrics
- If the service sends no events for more than 5 minutes: emit a Warning-level signal to the activity feed indicating the service may be down or logging may have stopped — do not silently wait

---

### `/backend/agents/postgres_agent.py`
**Purpose:** Specialist agent for PostgreSQL databases. Inherits from base_agent.py.

**Responsibilities:**
- Consume events from the queue for PostgreSQL services (source_type = postgresql)
- Maintain baseline for: active connection count, connection count as percentage of max_connections (derived from CMDB-enriched max_connections value), query latency P95, lock wait events per minute, replication lag seconds (if replica)
- Critical pattern lookup: "FATAL: remaining connection slots are reserved" → immediate CONNECTION_POOL_EXHAUSTED, "ERROR: deadlock detected" → immediate DB_DEADLOCK, "PANIC:" → immediate DB_PANIC (highest severity, always P1)
- Preliminary hypothesis mapping: connection count above 85% of max → "Connection pool approaching exhaustion — likely upstream traffic spike or connection leak or misconfigured pool size." Lock waits spiking → "Lock contention detected — likely long-running transaction or missing index."
- The max_connections value comes from the CMDB-enriched event (attached by cmdb_enricher.py) — the agent does not query the database directly

**Guardrails:**
- PANIC-level PostgreSQL events must always produce P1 severity EvidencePackages regardless of confidence score — no model calculation needed, PANIC always means immediate human escalation
- Replication lag detection only activates when the service is identified as a replica in CMDB — never produce replication alerts for primary instances
- Connection count threshold for Warning is 70% of max_connections — Alert is 85% — Critical is 95% (these differ from the standard 2σ/3σ because connection count has a hard ceiling unlike most metrics)

---

### `/backend/agents/nodejs_agent.py`
**Purpose:** Specialist agent for Node.js services. Inherits from base_agent.py.

**Responsibilities:**
- Consume events for Node.js services (source_type = nodejs)
- Maintain baseline for: unhandled rejection rate per minute, HTTP 5xx rate, request latency P95, event loop lag (if available from Node.js metrics endpoint)
- Critical patterns: "UnhandledPromiseRejectionWarning" spike (more than 10 in 60 seconds) → immediate flag, ECONNREFUSED to downstream services → immediate flag for cascade detection
- Hypothesis mapping: rejection spike → "Unhandled promise rejections — likely downstream service failure or uncaught async error." ECONNREFUSED → "Downstream connection refused — check dependency health."

**Guardrails:**
- ECONNREFUSED errors must include the target host in the evidence package supporting logs — this is critical for cascade correlation to identify which downstream service is failing
- Event loop lag metrics are optional — agent must function without them

---

### `/backend/agents/redis_agent.py`
**Purpose:** Specialist agent for Redis cache instances. Inherits from base_agent.py.

**Responsibilities:**
- Consume events for Redis services (source_type = redis)
- Maintain baseline for: memory usage percentage, eviction rate per minute, rejected commands per minute, connected clients count
- Critical patterns: "OOM command not allowed when used memory > maxmemory" → immediate REDIS_OOM flag, "MISCONF Redis is configured to save RDB snapshots" → immediate flag, rejected commands above zero (any rejection is a degraded state)
- Hypothesis mapping: OOM → "Redis memory exhaustion — maxmemory policy may have changed or memory growth is exceeding capacity." Eviction rate spiking → "Redis evicting keys — check if maxmemory-policy is appropriate for workload."

**Guardrails:**
- Any rejected commands must trigger at minimum a Warning — zero tolerance for silent rejection of commands (this directly impacts application behaviour)
- Memory percentage threshold for Alert is 85% (not 3σ) because Redis memory is bounded and 85% is operationally critical regardless of historical baseline

---

### `/backend/agents/correlation_engine.py`
**Purpose:** Sits above all four agents. Collects EvidencePackages from all agents for a given client and determines whether they represent an isolated anomaly or a cascade incident. This is the component that understands structure, not just signals.

**Responsibilities:**
- Maintain a 90-second correlation window per client_id — a sliding buffer of EvidencePackages
- When a new EvidencePackage arrives: check if any other EvidencePackage for the same client has arrived in the last 90 seconds
- If yes: query Neo4j to confirm whether the affected services are structurally connected via DEPENDS_ON relationships within 3 hops — this is the structural confirmation step
- If structurally connected: classify as CASCADE_INCIDENT and package all related EvidencePackages together
- If not structurally connected (temporal coincidence, not causal): classify each as ISOLATED_ANOMALY and process separately
- Check CMDB change records for the affected services: if any service in the cascade chain has an open change record from the last 7 days, add a deployment_correlated flag to the combined package
- Run Chronos-Bolt early warning scan on all services within the blast radius (DEPENDS_ON neighbours not yet flagged): flag any service between 1.5σ and 2.5σ as an EarlyWarning signal
- Send the classified incident package to the orchestrator

**Guardrails:**
- The Neo4j structural check is mandatory for CASCADE classification — temporal proximity alone is never sufficient to declare a cascade
- The 90-second window is per client — a cascade for Client A never picks up signals from Client B
- The correlation engine must not wait indefinitely for more signals — after 90 seconds, whatever is in the window is processed and the window clears
- If Neo4j is temporarily unavailable for the structural check: classify as ISOLATED_ANOMALY with a flag `structural_check_skipped: true` — never block incident processing because graph is temporarily unavailable
- Early warning scan runs only after CASCADE classification is determined — never delays the primary incident package being sent to the orchestrator

---

---

## `/backend/orchestrator`

---

### `/backend/orchestrator/state.py`
**Purpose:** Defines the complete LangGraph state object. This is the single data structure that carries everything from incident detection through human approval through resolution and learning. Every node reads from and writes to this state.

**Responsibilities:**
- Define every field in the state with its type, default value, and description
- Fields must include everything listed in ARCHITECTURE.md: client_id, incident_id, evidence_packages, correlation_type, blast_radius, recent_deployments, historical_graph_matches, semantic_matches, root_cause, recommended_action_id, alternative_hypotheses, composite_confidence_score, active_veto_conditions, routing_decision, servicenow_ticket_id, execution_status, audit_trail (list of timestamped entries), mttr_start_time, mttr_seconds, sla_breach_time, early_warning_signals, human_action, human_modifier, human_rejection_reason, resolution_outcome, recurrence_check_due_at

**Guardrails:**
- State fields that are set once and must never be overwritten (client_id, incident_id, evidence_packages, mttr_start_time) must be marked as immutable after their initial setting — any attempt to overwrite them must raise an error
- routing_decision once set to AUTO_EXECUTE or HUMAN_REVIEW must not be changeable — if re-routing is needed, a new incident must be created
- audit_trail is append-only — entries can be added but never modified or deleted

---

### `/backend/orchestrator/pipeline.py`
**Purpose:** Assembles the seven LangGraph nodes into the complete state machine. Defines the flow between nodes. This is the top-level orchestration file.

**Responsibilities:**
- Import all seven node functions from the nodes/ directory
- Create the LangGraph StateGraph using the state defined in state.py
- Add all seven nodes to the graph
- Define the edges between nodes: N1 → N2 → N3 → N4 → N5 → N6 → N7
- From N7: conditional edge to AUTO_EXECUTE path or HUMAN_REVIEW path based on routing_decision
- HUMAN_REVIEW path: LangGraph interrupt — graph suspends and waits for human input
- After human input received: graph resumes, execution proceeds
- After execution: N_LEARN node runs to update the learning engine
- Compile the graph and expose a single run_incident(evidence_package) function that external callers use

**Guardrails:**
- The interrupt for human review must persist state — if the server restarts between the interrupt and the human responding, the state must be recoverable
- Timeout on human review: if no human response within the SLA breach time minus 2 minutes, the graph automatically escalates to the next tier — does not wait indefinitely
- Every node transition must write a timestamped entry to the audit_trail in state — the audit trail must reflect every step the pipeline took

---

### `/backend/orchestrator/nodes/n1_classifier.py`
**Purpose:** First node in the pipeline. Takes raw evidence packages and assigns ITIL priority, starts SLA timer, assesses initial business impact.

**Responsibilities:**
- Assign ITIL priority based on: highest criticality tier among affected services (from CMDB enrichment), cascade vs. isolated classification, number of affected services, SLA breach imminence
- Priority assignment rules: any P1 service affected + cascade = P1 incident. Any P1 service affected alone = P2 incident. P2 services in cascade = P2 incident. P2/P3 services isolated = P3 incident. P4 services only = P4 incident.
- Start the SLA breach countdown timer: look up the SLA threshold for the incident priority from the client config
- Generate a plain-English situation summary for the briefing card: which services, what symptoms, estimated user impact in business terms (not just technical)
- Write classification result and SLA timer to state

**Guardrails:**
- A P1 incident classification must immediately trigger a notification to the SDM and L3 contacts in the escalation matrix — regardless of what happens downstream in the pipeline
- SLA timer is immutable once started — no node may reset or extend it
- If all services have unknown criticality (CMDB enrichment failed): default to P2 and flag as `criticality_uncertain: true` — never default to P4 which would suppress notifications

---

### `/backend/orchestrator/nodes/n2_itsm.py`
**Purpose:** Second node. Creates a real ServiceNow incident ticket and returns the ticket number to state.

**Responsibilities:**
- Call the ServiceNow REST API to create an incident record
- Populate: priority (mapped from ITIL P1-P4 to ServiceNow 1-4), assignment_group (from client config escalation matrix), affected_ci (from CMDB CI name), short_description (from N1 situation summary), caller_id (configured service account), category and subcategory (from anomaly type mapping)
- Return the INC ticket number (format: INC followed by 7 digits) and store in state
- Write the ticket URL to the audit trail

**Guardrails:**
- If ServiceNow is unavailable: continue the pipeline with a flag `itsm_ticket_pending: true` and retry ticket creation in the background every 30 seconds — never halt incident processing because ServiceNow is down
- The ServiceNow API call must use a retry with exponential backoff — maximum 3 retries before marking as pending
- Ticket creation must use the credentials from environment variables — never hardcoded
- The ticket must include a reference back to the ATLAS incident_id in a custom field — to allow correlation when humans look at the ticket in ServiceNow

---

### `/backend/orchestrator/nodes/n3_graph.py`
**Purpose:** Third node. Runs the three Neo4j Cypher queries in parallel to retrieve blast radius, deployment correlations, and historical patterns. This is the structural intelligence node.

**Responsibilities:**
- Run all three Cypher queries in parallel using asyncio.gather
- Blast radius query: traverse DEPENDS_ON from all affected services up to 3 hops, return all downstream services with criticality and SLA threshold
- Deployment correlation query: find CMDB change records from last 7 days touching affected services or their direct dependencies, return change_id, change_description, deployed_by, timestamp, cab_risk_rating
- Historical pattern query: find past incidents for the same services with the same anomaly type, return root_cause, resolution_playbook, mttr_minutes, resolved_by
- Store all results in state
- Store the graph_traversal_path (ordered list of nodes and edges visited) in state — this is what gets visualised in the frontend
- Apply 60-second result caching per client per query — identical queries within 60 seconds return cached results

**Guardrails:**
- Every Cypher query must include client_id as a mandatory filter — no query may execute without it, enforced at the query construction level not just at runtime
- Query timeout of 5 seconds per query — if any query exceeds this, return partial results with a timeout flag and continue pipeline
- If Neo4j is completely unavailable: continue pipeline with empty graph results and a flag `graph_unavailable: true` — the pipeline degrades gracefully, it does not halt
- The blast_radius list must never include services from a different client — validated against client_id after retrieval

---

### `/backend/orchestrator/nodes/n4_semantic.py`
**Purpose:** Fourth node. Runs ChromaDB vector similarity search to find historically similar incidents.

**Responsibilities:**
- Construct the search query by embedding the current incident's anomaly description: service names, error codes, anomaly type, preliminary hypotheses from agents
- Run similarity search against the client's namespaced ChromaDB collection
- Return top-3 results with their cosine similarity scores
- Cross-reference with N3 graph results: if any historical incident appears in both the graph query results and the vector search results, mark it as double-confirmed and assign it maximum context weight
- If the client has fewer than 5 incidents in their collection (cold start): also run against the cross-client federated collection for the same technology stack, with results clearly flagged as `source: cross_client_anonymised`

**Guardrails:**
- ChromaDB search must use the client_id namespaced collection — never query across collections without explicit cross-client federation logic
- Cross-client results must be flagged differently from client-specific results — the LLM reasoning prompt must differentiate between direct historical matches and cross-client analogues
- If no results above 0.50 similarity are found: return empty results with a flag `no_historical_precedent: true` — this contributes to the cold-start veto in N6
- Embedding of the search query must use the same model as was used for the stored embeddings — a mismatch produces meaningless similarity scores

---

### `/backend/orchestrator/nodes/n5_reasoning.py`
**Purpose:** Fifth node. The LLM reasoning call. Takes all structured context from N3 and N4 and produces structured reasoning output. This is the only node that calls an external LLM.

**Responsibilities:**
- Assemble the complete reasoning prompt: current evidence summary, blast radius, deployment correlations, historical matches (client-specific first, cross-client second), client compliance profile, ITIL 6-step reasoning instruction
- Route the call through Cerebras: Qwen3-235B primary, Ollama local fallback
- Use structured JSON output to enforce the schema at the API level
- Load pre-computed fallback response from `/data/fallbacks/{client_id}_incident_response.json` if the live call exceeds 8 seconds or fails after retries
- Parse the structured JSON output and validate every required field is present before writing to state
- Required output fields: root_cause (string), confidence_factors (dict), recommended_action_id (string matching a playbook in the library), alternative_hypotheses (list with evidence_for and evidence_against for each), explanation_for_engineer (string, written at L2 level), technical_evidence_summary (string)

**Guardrails:**
- The recommended_action_id must be validated against the actual playbook library — if the LLM returns an action ID that does not exist in the library, the output is rejected and the fallback is used
- Maximum prompt length enforced — if the assembled context exceeds the model's context window, the least-recent historical matches are dropped first, then cross-client results, then graph results are summarised — never truncate the current evidence
- Both LLM models must be tested and confirmed working before demo day — failure of the primary does not mean failure of the demo
- If both LLM calls fail and no fallback exists: route directly to HUMAN_REVIEW with the raw evidence, with a flag `llm_unavailable: true` — the incident is never dropped because the LLM is down
- The explanation_for_engineer field must be validated for length — if it is less than 50 characters, the output is rejected as likely truncated

---

### `/backend/orchestrator/nodes/n6_confidence.py`
**Purpose:** Sixth node. Pure Python confidence calculation. Completely independent of the LLM. Calculates the composite score and checks all seven vetoes. Produces the routing decision.

**Responsibilities:**
- Calculate Factor 1 (Historical Accuracy Rate, 30%): query the Decision History Database for all records matching this pattern/action/client triple. If fewer than 5 records exist, return 0.50 and flag cold-start-veto. If 5 or more exist, return the empirical success rate.
- Calculate Factor 2 (Root Cause Certainty, 25%): take alternative_hypotheses from N5 output, find the gap between highest and second-highest confidence scores, normalise to 0-1.
- Calculate Factor 3 (Action Safety Class, 25%): look up the recommended_action_id in the playbook library to find its safety class. Class 1 = 1.0. Class 2 = 0.6. Class 3 = 0.0 (immediately triggers a Class3 veto — Class 3 actions never auto-execute, do not even calculate other factors for routing decision if this fires).
- Calculate Factor 4 (Evidence Freshness, 20%): calculate time in seconds since the most recent EvidencePackage timestamp. Decay linearly from 1.0 at 0 seconds to 0.0 at 1200 seconds (20 minutes).
- Calculate composite score: weighted sum of all four factors.
- Check all seven vetoes in order. Any veto that fires: add it to active_veto_conditions with its plain-English explanation.
- Determine routing: if composite >= client threshold AND active_veto_conditions is empty AND action class is 1 → AUTO_EXECUTE. If composite >= 0.75 AND similarity score from N4 >= 0.75 AND action class is 1 AND no vetoes → L1_HUMAN_REVIEW. All other cases → L2_L3_ESCALATION.
- Write all scores, veto results, and routing decision to state.

**Guardrails:**
- Class 3 action check must run first before any other calculation — if it fires, skip all other calculations and route immediately to L2_L3_ESCALATION
- The seven vetoes must all be checked regardless of whether earlier ones fired — the active_veto_conditions list must be complete, not just the first veto found
- composite_confidence_score must be between 0.0 and 1.0 — if arithmetic produces a value outside this range, clamp it and log the anomaly
- The routing decision must be logged to the audit trail with the exact score and all active vetoes — a human must be able to audit exactly why ATLAS routed the way it did
- auto_execute_threshold from client config is used for AUTO_EXECUTE routing — the 0.75 threshold for L1_HUMAN_REVIEW is hardcoded and cannot be changed via config (this is intentional — L1 routing has a fixed floor)

---

### `/backend/orchestrator/nodes/n7_router.py`
**Purpose:** Seventh and final orchestration node. Takes the routing decision from N6 and sends the incident to the correct destination.

**Responsibilities:**
- Read routing_decision from state
- For AUTO_EXECUTE: send incident package to the execution engine, do not interrupt the graph
- For L1_HUMAN_REVIEW: send the briefing card data to the L1 notification channel (Slack or Teams, per client config), trigger LangGraph interrupt to pause the graph and wait for human input
- For L2_L3_ESCALATION: determine whether L2 or L3 based on incident priority (P1 → L3, P2 → L2, P3 → L2), send full briefing card to appropriate channel, trigger LangGraph interrupt
- Write the routing destination and timestamp to audit trail
- For P1 incidents regardless of routing: also notify the SDM immediately

**Guardrails:**
- LangGraph interrupt must be configured to persist state across server restarts — if the server goes down while waiting for human approval, the incident must be recoverable on restart
- Timeout on human review: if SLA breach time minus 2 minutes is reached with no human response, auto-escalate to the next tier — this is mandatory and cannot be disabled via config
- The graph must never be left in a permanently suspended state — every interrupt has a maximum wait time equal to the SLA breach threshold for that incident priority

---

---

## `/backend/orchestrator/confidence`

---

### `/backend/orchestrator/confidence/scorer.py`
**Purpose:** The actual mathematical implementation of the four-factor confidence calculation. Called by n6_confidence.py. Pure functions only — no I/O, no database calls. Takes inputs, returns scores.

**Responsibilities:**
- calculate_historical_accuracy(records: list) → float: given a list of Decision History records for this pattern/action/client triple, return the empirical success rate
- calculate_root_cause_certainty(hypotheses: list) → float: given ranked hypotheses with confidence scores, return the normalised gap between top and second
- calculate_action_safety(action_class: int) → float: lookup table: 1→1.0, 2→0.6, 3→0.0
- calculate_evidence_freshness(evidence_timestamp: datetime) → float: linear decay function
- calculate_composite(f1, f2, f3, f4) → float: weighted sum with defined weights
- All functions are pure — no side effects, fully testable, deterministic

**Guardrails:**
- All factor functions must return values between 0.0 and 1.0 — validated with assertions
- composite must be between 0.0 and 1.0 — clamp and log if arithmetic produces otherwise
- These functions must be unit tested with known inputs and expected outputs before any other part of the system is built — they are the mathematical core

---

### `/backend/orchestrator/confidence/vetoes.py`
**Purpose:** Checks all seven hard veto conditions. Called by n6_confidence.py. Each veto is a pure function that returns either None (no veto) or a plain-English explanation string (veto fired).

**Responsibilities:**
- check_change_freeze_window(client_config, current_time) → str or None
- check_business_hours_compliance(client_config, current_time, action_class) → str or None: fires only if compliance_frameworks includes PCI-DSS or SOX AND current_time is within business_hours
- check_action_class_three(action_class) → str or None: fires if action_class == 3, always
- check_p1_severity(incident_priority) → str or None: fires if priority is P1
- check_compliance_data_touched(evidence_packages, client_config) → str or None: fires if any evidence involves services flagged as compliance-sensitive in client config
- check_duplicate_action(client_id, action_id, last_2_hours_actions) → str or None: fires if the same action was attempted on the same service in the last 2 hours
- check_graph_freshness(last_graph_update_timestamp) → str or None: fires if graph has not been updated in more than 24 hours
- check_cold_start(historical_record_count) → str or None: fires if fewer than 5 historical records exist for this pattern
- run_all_vetoes(…) → list: runs all checks and returns the list of fired veto explanations (empty list = no vetoes)

**Guardrails:**
- Each veto function must be independently testable — no shared state between veto checks
- The check_action_class_three veto must run first in run_all_vetoes — if it fires, the rest still run (complete veto list must be returned, not just the first)
- Plain-English explanations must be specific enough to display directly on the L2 briefing card without modification — they are user-facing text

---

---

## `/backend/execution`

---

### `/backend/execution/playbook_library.py`
**Purpose:** The registry of all available playbooks. Knows which playbooks exist, their safety classes, their expected inputs, and their estimated resolution times. The boundary of what ATLAS can autonomously do.

**Responsibilities:**
- Maintain the playbook registry: a dictionary mapping playbook_id to playbook metadata (name, description, action_class, estimated_resolution_minutes, pre_validation_checks, success_metrics, rollback_playbook_id)
- Expose: get_playbook(playbook_id) → playbook object, list_playbooks() → all available playbooks, validate_action_id(action_id) → boolean
- The library is read-only at runtime — no playbook is added or removed while the system is running
- Semantic search method: given a free-text query (from L2 rejection reason), return the top-3 playbooks by semantic similarity to the query text

**Guardrails:**
- If a playbook_id is requested that does not exist: return None and log — never raise an unhandled exception, never guess
- Class 3 playbooks may exist in the library for documentation purposes but must be marked `auto_execute_eligible: false` — the execution engine checks this flag before running any playbook
- The rollback_playbook_id for every Class 1 and Class 2 playbook must point to a valid, existing playbook — validated on startup

---

### `/backend/execution/playbooks/connection_pool_recovery_v2.py`
**Purpose:** The real playbook for resolving HikariCP connection pool exhaustion on Java Spring Boot services. This is not a mock. It executes real actions against real (simulated) infrastructure.

**Responsibilities:**
- Pre-execution validation: verify that the target PaymentAPI service endpoint is reachable, verify that the current connection count is above the alert threshold (confirm the issue still exists before acting), verify that no other ATLAS action has been taken on this service in the last 10 minutes
- Action execution: send a real PATCH request to the PaymentAPI actuator endpoint to update the HikariCP maxPoolSize configuration to 150, then send a real restart signal to the connection manager component
- Success validation: poll the connection count metric from the log stream every 30 seconds for up to 10 minutes, declare success when connection count drops below 70% of max_connections for two consecutive readings
- Auto-rollback: if success validation does not confirm recovery within 10 minutes, send a PATCH request to restore maxPoolSize to its previous value and trigger re-escalation
- Write detailed execution log to audit trail: every HTTP call made, every response received, every metric check result

**Guardrails:**
- Pre-execution validation failure must halt execution and escalate — never proceed on a service that is not in the expected state
- The target endpoint URL, authentication, and parameter values come from the client config and the playbook parameters — never hardcoded
- Maximum execution time is enforced: if the total playbook runtime (validation + action + first success check) exceeds 15 minutes, auto-rollback triggers regardless of validation state
- Every external call (PATCH request, status check) must have a timeout of 10 seconds — no call may block indefinitely
- The audit trail entry for this playbook must include the exact URL called (redacted of credentials), the response code, and the metric values at each validation check

---

### `/backend/execution/playbooks/redis_memory_policy_rollback_v1.py`
**Purpose:** The real playbook for resolving Redis OOM caused by maxmemory-policy misconfiguration. Executes real Redis CLI commands against the demo Redis instance.

**Responsibilities:**
- Pre-execution validation: connect to Redis, verify memory usage is above 85%, verify that maxmemory-policy is currently set to noeviction (confirm the suspected cause is present)
- Action execution: execute CONFIG SET maxmemory-policy allkeys-lru against the Redis instance, then execute a controlled DEBUG SLEEP 0 (harmless flush trigger), verify the policy change took effect via CONFIG GET maxmemory-policy
- Success validation: poll memory usage every 30 seconds, declare success when usage drops below 75% for two consecutive readings
- Auto-rollback: if success validation fails, set maxmemory-policy back to noeviction (preserving the problematic state for L2 investigation rather than guessing at an alternative) and escalate

**Guardrails:**
- Redis connection credentials come from environment variables — never hardcoded
- The pre-validation check for current policy is mandatory — if the policy is already allkeys-lru when the playbook runs, the playbook must halt and report to the orchestrator that the assumed cause is not present (the hypothesis was wrong)
- Never execute FLUSHALL or FLUSHDB — these are destructive and are not in the playbook library at any action class

---

### `/backend/execution/approval_tokens.py`
**Purpose:** Generates and validates cryptographic one-time approval tokens for dual sign-off on compliance-flagged actions. This is the mechanism that makes PCI-DSS dual approval real, not theatrical.

**Responsibilities:**
- generate_approval_token(incident_id, approver_role, expiry_minutes=30) → signed token string: create a time-limited signed token encoding the incident ID, the approver role, a nonce, and an expiry timestamp. Sign with the secret key from environment variables.
- validate_approval_token(token) → (valid: bool, incident_id: str, approver_role: str): verify signature, verify not expired, verify nonce has not been used before (one-time use)
- store_nonce(nonce): add used nonce to the nonce store so the token cannot be replayed
- Expose an endpoint that accepts a token via URL (the link sent to the secondary approver) and validates it, then records the approval in the audit database

**Guardrails:**
- Tokens expire after 30 minutes — an approver cannot approve an incident that is already resolved or past its SLA breach
- Nonces are single-use — the same token cannot be used twice even within its validity window
- If the secret key is not set in environment variables: token generation must fail with a clear error — never generate tokens with a weak or default key
- The token must encode the incident_id — a token generated for incident A cannot be used to approve incident B

---

---

## `/backend/learning`

---

### `/backend/learning/decision_history.py`
**Purpose:** The SQLite database that stores every human and automated decision made in ATLAS. This is the memory that makes the confidence engine smarter over time.

**Responsibilities:**
- Create and maintain the decision_history table with all fields from ARCHITECTURE.md
- write_record(record): insert a new record after every incident resolution
- get_records_for_pattern(client_id, anomaly_type, service_class, action_id) → list: query all matching records for confidence scoring
- get_accuracy_rate(client_id, anomaly_type, service_class, action_id) → float: calculate empirical success rate from matching records
- mark_recurrence(incident_id): called 48 hours after resolution if the same incident pattern appears again, marks the original resolution as `recurrence_within_48h: true`
- Export all records for a client and date range as JSON or CSV: used for compliance audit exports

**Guardrails:**
- Every write must be atomic — partial writes that would leave the record in an inconsistent state must roll back
- client_id is always a required field — no record can be written without it
- Records are immutable after writing — no update or delete methods exist. Corrections are made by writing a new record referencing the original.
- The database file path comes from environment variables — not hardcoded

---

### `/backend/learning/recalibration.py`
**Purpose:** Recalculates Factor 1 (Historical Accuracy Rate) in the confidence engine after every resolved incident. Ensures the next similar incident is scored with up-to-date accuracy data.

**Responsibilities:**
- After every incident resolution: query decision_history for all records matching the resolved incident's pattern/action/client triple
- Calculate the new empirical accuracy rate
- Update the in-memory accuracy cache that n6_confidence.py reads from
- Write a recalibration event to the audit trail: "Factor 1 for pattern X on client Y updated from A% to B% based on N records"
- Expose a method to force-recalculate all accuracy rates: used on system startup to rebuild the cache from the full history

**Guardrails:**
- Recalibration runs asynchronously after resolution — never block the resolution confirmation waiting for recalibration
- Minimum record count of 5 still applies after recalibration — if the update brings the count to 5 for the first time, the cold-start veto is automatically lifted for future incidents of this type
- The in-memory cache must not be read while a recalibration write is in progress — use a read-write lock

---

### `/backend/learning/weight_correction.py`
**Purpose:** Applies weight corrections based on accumulated L2 modification diffs and L3 rejection signals. Gradually adjusts ATLAS's recommendations toward what experienced engineers actually prefer.

**Responsibilities:**
- After every L2 Modify action: store the parameter diff (what was changed, in what direction, by how much) in a diffs table
- After accumulating 3 or more diffs in the same direction for the same action on the same client: calculate the adjusted default parameter value and store it in a defaults table
- After every L2 Reject or L3 Override action: parse the rejection reason text to identify which hypothesis type was rejected and what was substituted
- Maintain a hypothesis_weight table per client: tracks adjustments to the weight given to each hypothesis type
- Expose: get_adjusted_default(client_id, action_id, parameter_name) → adjusted value or None (None means use playbook default), get_hypothesis_weights(client_id) → dict of adjustments

**Guardrails:**
- Weight adjustments must be bounded — no single parameter default can be moved more than 50% from the playbook default value through automatic adjustment. Beyond that threshold, a human review is flagged.
- Rejection reason parsing is best-effort — if the reason text cannot be meaningfully parsed, the record is stored but no weight adjustment is made
- All weight adjustments are logged to the audit trail with the evidence that triggered them (number of diffs, direction, magnitude)

---

### `/backend/learning/trust_progression.py`
**Purpose:** Evaluates whether a client has met the criteria to advance to the next trust stage. The only component that can update the trust_level in the client config.

**Responsibilities:**
- After every resolved incident: recalculate stage progression metrics for the relevant client
- Stage 1 criteria check: has this client had 30 incidents processed AND is the confirmed-correct rate above 80%?
- Stage 2 criteria check: has Stage 1 been active for at least 30 more incidents AND is the auto-resolution success rate above 85%?
- If criteria are met: write a trust upgrade recommendation to the audit trail with the supporting evidence (incident count, accuracy rate), send a notification to the SDM for explicit approval — do not automatically upgrade without SDM confirmation
- After SDM confirmation: update trust_level in the client config via the designated method in client_registry.py
- Expose: get_progression_metrics(client_id) → current stage, incident count, accuracy rates, distance to next stage

**Guardrails:**
- Trust level can only go up through this module — no other module may change trust_level
- Trust downgrade (if accuracy drops significantly after an upgrade) must be treated as a separate process requiring SDM notification — automatic downgrade is not implemented, it requires human decision
- Stage 4 (L2 Automation) requires explicit SDM action in addition to criteria being met — criteria alone are not sufficient
- Class 3 actions are never added to any auto-execute eligibility regardless of trust level — this is a hard constant, not a config value

---

---

## `/backend/database`

---

### `/backend/database/neo4j_client.py`
**Purpose:** All Neo4j database interactions go through this module. No other module connects to Neo4j directly. Handles connection, query execution, caching, and graceful degradation.

**Responsibilities:**
- Maintain a connection pool to the Neo4j Aura Serverless instance
- Expose execute_query(cypher, params, client_id) → results: runs a Cypher query, enforces that client_id is in the params, returns results
- Implement 60-second result caching per (query_hash, client_id) pair
- Handle connection errors with automatic retry (3 retries, exponential backoff)
- On persistent failure: return None with a clear error flag — never raise unhandled exceptions to callers
- Expose a health_check() method that confirms the connection is live — used on startup

**Guardrails:**
- The execute_query method must validate that client_id is present in params before executing — prevents accidental cross-client queries
- Cache keys must include client_id as a component — prevents one client's cached results serving another client
- All queries are executed as read transactions by default — write transactions must be explicitly requested via a separate method, and only specific modules are permitted to call write transactions (neo4j_client.py enforces this via an allowed_writers list)

---

### `/backend/database/chromadb_client.py`
**Purpose:** All ChromaDB interactions go through this module. Manages collections, embeddings, and search.

**Responsibilities:**
- On startup: create collections for all configured clients if they do not exist, using naming convention `atlas_{client_id}`
- embed_and_store(incident_record, client_id): generate embedding using the configured model, store in the client's collection with full metadata
- similarity_search(query_text, client_id, n_results=3) → list of results with scores: embed the query, search the client's collection
- cross_client_search(query_text, tech_stack: list, exclude_client_id) → list: search across all collections for clients running the same technology stack, exclude the requesting client, return anonymised results
- Health check method

**Guardrails:**
- Collection names must always be derived from client_id — no hardcoded collection names
- similarity_search must only search the specified client's collection — cross_client_search is a separate, explicitly named method to prevent accidental cross-client search
- Embeddings must always use the same model for both storage and retrieval — model name stored as collection metadata and validated on every retrieval operation
- cross_client results must have all client-identifying metadata stripped before being returned

---

### `/backend/database/audit_db.py`
**Purpose:** Manages the SQLite audit database. Every action ATLAS takes — automated or human-approved — produces an immutable audit record here.

**Responsibilities:**
- Create and maintain the audit_log table and the decision_history table
- write_audit_record(record): insert an immutable audit record. Fields: record_id, incident_id, client_id, timestamp, action_type (detection/classification/approval/execution/rollback/resolution), actor (ATLAS_AUTO or engineer name), action_description, confidence_score_at_time, reasoning_summary, outcome, servicenow_ticket_id, rollback_available, compliance_frameworks_applied
- query_audit(client_id, date_from, date_to) → list: for compliance exports
- export_as_csv(client_id, date_from, date_to) → CSV file path
- export_as_json(client_id, date_from, date_to) → JSON file path

**Guardrails:**
- Audit records are write-once — no update or delete methods
- Every write is wrapped in a transaction — partial writes roll back
- The audit database file is append-only in filesystem terms if possible — backup before any maintenance
- client_id is always required — no audit record without it

---

---

## `/data`

---

### `/data/seed/financecore_graph.cypher`
**Purpose:** The complete Cypher script that creates the FinanceCore knowledge graph in Neo4j. Run once during setup. This is real seed data — every node and relationship must be accurate and internally consistent.

**Must contain:**
- All Service nodes with real properties (technology type, version, Kubernetes namespace, health endpoint, max_connections for DB)
- All Infrastructure nodes (EKS cluster details, RDS instance class)
- All Team nodes with tier and contact
- All Deployment nodes — especially CHG0089234 from 3 days ago with the HikariCP config change
- All historical Incident nodes — especially INC-2024-0847 from 4 months ago with the matching pattern
- All DEPENDS_ON, HOSTED_ON, MODIFIED_CONFIG_OF, AFFECTED, CAUSED_BY relationships
- SLA nodes linked to each service
- ComplianceRule nodes for PCI-DSS and SOX linked to financial services

**Guardrails:**
- Every Deployment node must have a corresponding MODIFIED_CONFIG_OF or DEPLOYED_TO relationship — orphan deployment nodes are not useful
- Every Incident node must have an AFFECTED relationship to at least one Service — orphan incidents cannot be queried by the graph node
- The CHG0089234 deployment node must have a direct MODIFIED_CONFIG_OF relationship to PaymentAPI — this is the causal link the demo depends on
- The INC-2024-0847 incident node must have anomaly_type matching the demo fault script's anomaly type — this is what the historical pattern query uses

---

### `/data/seed/retailmax_graph.cypher`
**Purpose:** Complete Cypher script for the RetailMax knowledge graph.

**Must contain:**
- Service nodes for ProductAPI, CartService, Redis Cache, MongoDB, CDN
- Deployment node DEP-20250316-003 with the Redis maxmemory-policy change
- Historical incidents — deliberately no close match to Redis OOM pattern (maximum 0.65 similarity when searched)
- DEPENDS_ON relationships: CartService depends on Redis, ProductAPI depends on MongoDB

---

### `/data/seed/historical_incidents.json`
**Purpose:** The source data for all historical incidents that get embedded into ChromaDB. Each incident in this file becomes one vector embedding in the client's ChromaDB collection.

**Must contain for FinanceCore:**
- 10 incidents, each with: incident_id, client_id, service_name, anomaly_type, error_codes_observed, root_cause, resolution_steps, outcome, mttr_minutes, occurred_at
- INC-2024-0847 must be written so that its composite description (service + error codes + root cause keywords) produces cosine similarity above 0.87 when compared to the FinanceCore fault scenario description
- The other 9 incidents must be varied enough that they are not false positives (similarity below 0.70 when the fault scenario is searched)

**Must contain for RetailMax:**
- 6 incidents, none with high similarity to the Redis OOM pattern — maximum similarity 0.65

**Guardrails:**
- After writing this file and seeding ChromaDB, run the validation script to confirm similarity scores are in expected ranges — do not proceed to build detection layer until validation passes

---

### `/data/fault_scripts/financecore_cascade.py`
**Purpose:** The deterministic fault injection script for the FinanceCore demo. When triggered, emits exactly the right log lines at exactly the right timing to produce reliable detection at second 47 of every run.

**Must contain:**
- Normal phase log lines (first 3 minutes of operation): realistic mix of INFO, DEBUG, occasional WARN, zero errors
- Escalation phase (T+0 to T+90): HikariCP warning messages starting at T+0, frequency increasing every 30 seconds, PostgreSQL connection count messages rising, first ERROR at T+35, FATAL at T+60, cascade into Kubernetes pod restart events at T+75
- All log lines in real Java Spring Boot and PostgreSQL log format — no synthetic or abbreviated formats
- Timing calibrated so that: PostgreSQL agent fires at T+47, Java agent fires at T+52, cascade correlation confirmed at T+55

**Guardrails:**
- The fault script must produce identical output on every run — no randomness in timing or log content
- After writing the script, run it 10 times and confirm agent detection fires at T+47 ±5 seconds every time — adjust timing if necessary
- The error codes and messages in this script must match the error_code mappings in postgres_adapter.py and java_adapter.py — mismatches will cause detection to fail silently

---

### `/data/fault_scripts/retailmax_redis_oom.py`
**Purpose:** Deterministic fault injection for RetailMax Redis OOM scenario.

**Must contain:**
- Normal phase: healthy Redis log lines
- Fault phase: Redis memory warning messages, then OOM command rejections, then Node.js CartService errors caused by Redis rejections
- Timing: Redis agent fires at T+40, Node.js agent fires at T+55, cascade confirmed at T+60

---

### `/data/fallbacks/financecore_incident_response.json`
**Purpose:** Pre-computed LLM response for the FinanceCore demo scenario. Used as fallback if the live LLM call fails or exceeds 8 seconds.

**Must contain:**
- A real LLM response captured from a real API call during development
- All required fields: root_cause, confidence_factors, recommended_action_id (must be connection-pool-recovery-v2), alternative_hypotheses with evidence, explanation_for_engineer
- The explanation_for_engineer must be written at L2 engineer level — readable, specific, actionable

**Guardrails:**
- This file must be generated from a real API call — never manually written to fake an LLM response
- The recommended_action_id in this file must be connection-pool-recovery-v2 — validate this before saving
- Update this file whenever the prompt structure changes — a stale fallback that doesn't match the current schema will cause validation failure in n5_reasoning.py

---

---

## `/frontend/src`

---

### `/frontend/src/components/ClientRoster/`
**Purpose:** The left panel of the three-panel dashboard. Shows all configured clients with their real-time health status. Always visible — even when an incident is active in the centre panel.

**Responsibilities:**
- Display one card per client: client name, technology stack icons, compliance badges (PCI-DSS, SOX, GDPR)
- Show real-time health indicator: green (all services healthy), yellow (warning signals active), red (incident active). Updates via WebSocket.
- Show SLA uptime counter: real percentage calculated from resolved and missed SLA events in the audit log, updating live
- Show current trust level with a progress bar toward the next stage
- Show active incident count for each client
- Clicking a client card switches the centre panel focus to that client

**Guardrails:**
- Health status must come from the real backend WebSocket — never hardcoded or simulated in the frontend
- Trust level must reflect the actual value from client_registry.py — not a display-only value

---

### `/frontend/src/components/BriefingCard/`
**Purpose:** The centrepiece of the L2 interface. Shows the complete ATLAS reasoning output for an active incident. Every field shows real data from the live pipeline.

**Responsibilities:**
- Section 1 — Situation Summary: affected services list, business impact statement, SLA countdown timer (counting down in real time from the SLA breach time calculated in N1)
- Section 2 — Blast Radius: placeholder for the GraphViz component, list of affected downstream services with their criticality
- Section 3 — Deployment Correlation: CHG number, change description, deployed by, timestamp, CAB risk rating — all from the real Neo4j query result
- Section 4 — Historical Match: similarity score badge (e.g. 91%), incident ID, root cause summary, resolution summary, MTTR from last resolution, link to full record
- Section 5 — Alternative Hypotheses: ranked list with evidence for and against each, showing ATLAS considered multiple possibilities
- Section 6 — Recommended Action: playbook name, action description, estimated resolution time, risk class badge, rollback availability status
- Approve / Modify / Reject buttons at the bottom

**Guardrails:**
- The similarity score badge must show the actual cosine similarity value from ChromaDB — not a rounded or approximated display value
- The SLA countdown timer must turn red when under 5 minutes remaining — automatic, not manually triggered
- The Reject button must open a mandatory text field — the submit button for rejection must be disabled until at least 20 characters are entered in the reason field

---

### `/frontend/src/components/GraphViz/`
**Purpose:** The interactive dependency graph visualisation. Shows the actual Neo4j traversal path for the current incident. This is the visual centrepiece of the demo.

**Responsibilities:**
- Render the FinanceCore service dependency graph using React Force Graph 2D
- Node data comes from the blast_radius and recent_deployments in the incident state — real Neo4j node IDs
- Animate the traversal sequence: deployment node pulses yellow first (3 seconds), then the MODIFIED_CONFIG_OF edge animates, then TransactionDB turns orange (2 seconds), then the DEPENDS_ON edge to PaymentAPI animates, then PaymentAPI turns red
- Nodes are interactive: hover shows the node's properties (service name, version, criticality, last deployment date)
- Clicking the deployment node shows the full change record (CHG number, what changed, who deployed)
- The full graph remains visible after the animation so judges can explore it

**Guardrails:**
- The animation sequence must be driven by the actual graph_traversal_path stored in state — not a hardcoded animation
- Pre-recorded animation fallback: if React Force Graph fails to render, load the pre-recorded 15-second video of the animation — this is a critical fallback for demo day
- The graph must clearly distinguish between: normal services (grey), warning services (amber), affected services (orange/red), deployment nodes (yellow), and historical incident nodes (purple)

---

### `/frontend/src/components/ActivityFeed/`
**Purpose:** The right panel. Shows every action ATLAS is taking in real time. Every LangGraph node transition, every agent detection, every decision — logged here as it happens.

**Responsibilities:**
- Display timestamped feed entries received via the WS /ws/activity WebSocket
- Each entry shows: timestamp, component name (which agent, which orchestrator node), action taken, key values (confidence score, similarity score, veto name if fired)
- Entries are prepended (newest at top), scrollable, last 100 entries kept
- Different entry types styled differently: agent detection (orange), orchestrator node (blue), human action (green), veto fired (red), resolution (teal)

**Guardrails:**
- Every entry must come from the real backend WebSocket — no synthetic entries generated in the frontend
- The feed must never block the main UI thread — rendered in a separate scrollable container with virtualization if needed

---

### `/frontend/src/components/SHAPChart/`
**Purpose:** Displays the SHAP feature importance values from the anomaly detection as a horizontal bar chart. Shows exactly which metrics triggered the detection and by how much.

**Responsibilities:**
- Receive shap_feature_values dict from the incident state: feature_name → contribution_percentage
- Render as a horizontal bar chart using Recharts
- Features sorted by contribution (highest at top)
- Bars colour-coded by feature type: error-related (red), latency-related (orange), resource-related (yellow)
- Shows the percentage value at the end of each bar

**Guardrails:**
- Values must sum to 100% — validate on display, show warning if they do not (this indicates a SHAP calculation issue upstream)
- If shap_values is empty (SHAP calculation failed): show a text message "Feature attribution unavailable — SHAP calculation failed" rather than an empty chart

---

### `/frontend/src/components/ApprovalFlow/`
**Purpose:** The approval buttons and dual sign-off flow. Handles all human interaction with the incident decision.

**Responsibilities:**
- L1 view: Approve button, Escalate button — both large, clearly labelled
- L2 view: Approve button, Modify button (opens parameter editor), Reject button (opens reason text field, submit disabled until 20+ characters)
- Dual approval flow: after primary Approve click, show "Awaiting secondary approval" state with the secondary approver's name and a status indicator. Update to "Both approvals received" when the secondary confirms.
- Modification panel: for Modify action, show editable parameter fields pre-filled with ATLAS's recommended values, show the diff (what changed from recommendation) before final submit
- Post-approval: show "Playbook executing..." status, then transition to post-resolution view when success validation confirms

**Guardrails:**
- The Approve button must be disabled during the SLA check — if the SLA has already breached, approval is still possible but a warning banner appears: "SLA already breached — escalate for incident review"
- The dual approval "Awaiting secondary" state must timeout after 30 minutes with an alert if the secondary has not responded — matches the token expiry in approval_tokens.py
- After any human action (approve/modify/reject): the buttons must be disabled immediately to prevent double-submission

---

### `/frontend/src/hooks/useWebSocket.js`
**Purpose:** Custom React hook that manages WebSocket connections to the backend. Used by all components that need live data.

**Responsibilities:**
- Create and maintain WebSocket connections to the three backend endpoints: logs, incidents, activity
- Handle disconnection with automatic reconnect (exponential backoff, maximum 10 retries)
- Parse incoming messages and dispatch to the appropriate state updates
- Expose connection status so components can show "Reconnecting..." states

**Guardrails:**
- WebSocket connections must be created per client_id — never share a single connection across clients
- Reconnect must not flood the server — minimum 1 second between reconnect attempts, doubling up to 30 seconds maximum
- If the server is unreachable after 10 retries: show a clear "Backend disconnected" banner in the UI — never silently show stale data

---

---

## `/scripts`

---

### `/scripts/seed_neo4j.py`
**Purpose:** One-time setup script. Reads the .cypher seed files and executes them against the Neo4j instance. Verifies the graph was created correctly.

**Responsibilities:**
- Connect to Neo4j using credentials from environment variables
- Execute financecore_graph.cypher and retailmax_graph.cypher
- After execution: run verification queries to confirm that the critical nodes exist (CHG0089234 for FinanceCore, DEP-20250316-003 for RetailMax, INC-2024-0847 for FinanceCore)
- Print a clear success or failure summary: which nodes were created, which verification queries passed

**Guardrails:**
- Must check if data already exists before inserting — idempotent execution (running twice does not duplicate data)
- If any verification query fails: print the specific failure and exit with a non-zero status code — the system must not be considered ready until all verifications pass

---

### `/scripts/seed_chromadb.py`
**Purpose:** One-time setup script. Reads historical_incidents.json and creates embeddings using a local embedding model, then stores them in ChromaDB.

**Responsibilities:**
- Connect to ChromaDB
- Create collections for FinanceCore and RetailMax if they do not exist
- For each incident in historical_incidents.json: generate embedding using local model, store in the correct collection with all metadata fields
- After seeding: run the similarity validation test for both clients and print the results

**Guardrails:**
- Embedding generation must be rate-limited — add a small delay between calls if needed
- If any embedding call fails: retry once, then skip and log the skipped incident — do not fail the entire seeding process for one bad embedding

---

### `/scripts/validate_similarity.py`
**Purpose:** Validation script run after seeding. Confirms that ChromaDB similarity search returns the expected results for both demo fault scenarios. Must pass before building the detection layer.

**Responsibilities:**
- Embed the FinanceCore fault scenario description and run similarity search: print the top-3 results with similarity scores. INC-2024-0847 must appear as top result with score above 0.87.
- Embed the RetailMax fault scenario description and run similarity search: print the top-3 results. No result should exceed 0.70 similarity.
- Print PASS or FAIL for each test with the actual score
- Exit with non-zero status code if either test fails

**Guardrails:**
- This script must be run and must pass before any other development work proceeds — it is a gate, not an optional check

---

*STRUCTURE.md — Every file described. Every guardrail specified. No code. Build to this spec.*