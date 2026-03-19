# ATLAS — TODO.md
## Complete End-to-End Task List: Setup to Production-Ready Demo

---

> READ THIS FIRST:
> - Do not start any task until the previous task's VERIFY condition is fully met
> - Read ROLE.md before touching any file
> - Read STRUCTURE.md section for a file before building that file
> - Read ARCHITECTURE.md before touching orchestration or graph logic
> - Sequence is law. Every layer depends on the one before it.
> - When told to build a file: build that file completely, to spec, production-ready, first write
> - Mark each task [ ] → [x] when its VERIFY condition is met — not before

---

## PHASE 0 — ENVIRONMENT & REPOSITORY SETUP

---

- [ ] **0.1 — Create external service accounts**
  - Create Neo4j Aura account at console.neo4j.io → create free Serverless instance → save URI, username, password immediately (shown once only)
  - Create ServiceNow Developer account at developer.servicenow.com → request personal developer instance → wait for provisioning email (up to 15 minutes) → save instance URL, admin username, admin password
  - Verify Anthropic API key is active and has available credits
  - Verify OpenAI API key is active (LiteLLM GPT-4o fallback)
  - Create HuggingFace account for Chronos-Bolt model tracking
  - Create Slack workspace and generate incoming webhook URL for approval notifications
  - VERIFY: Neo4j Browser opens at your URI. ServiceNow instance loads at devXXXXXX.service-now.com. Both API keys return 200 on a test call.

---

- [ ] **0.2 — Create repository and folder structure**
  - Create new Git repository named `atlas`
  - Create every folder from this exact list — no extras, no omissions:
    - `/backend`
    - `/backend/config`
    - `/backend/config/clients`
    - `/backend/ingestion`
    - `/backend/ingestion/adapters`
    - `/backend/agents`
    - `/backend/agents/detection`
    - `/backend/orchestrator`
    - `/backend/orchestrator/nodes`
    - `/backend/orchestrator/confidence`
    - `/backend/execution`
    - `/backend/execution/playbooks`
    - `/backend/learning`
    - `/backend/database`
    - `/data`
    - `/data/seed`
    - `/data/fault_scripts`
    - `/data/fallbacks`
    - `/frontend`
    - `/scripts`
  - Create `.gitignore` — include `.env`, `__pycache__`, `*.pyc`, `.DS_Store`, `node_modules`, `venv`, `*.egg-info`
  - Create `.env.example` with every variable name listed in STRUCTURE.md, all values blank
  - Create real `.env` with actual credentials — confirm `.env` is in `.gitignore`
  - Place `ROLE.md`, `ARCHITECTURE.md`, `STRUCTURE.md`, `PLAN.md`, `USECASE.md` in repo root
  - Create empty `test_progress.py` at repo root
  - Initial commit with structure only
  - VERIFY: `git status` is clean. Running `cat .gitignore | grep .env` shows `.env`. All folders exist. `.env` does not appear in `git status`.

---

- [ ] **0.3 — Create Python virtual environment and install dependencies**
  - Create Python 3.11 virtual environment: `python3.11 -m venv venv`
  - Activate venv
  - Create `requirements.txt` with every library from STRUCTURE.md, all versions pinned exactly — no `>=` or `~=`
  - Libraries required: fastapi, uvicorn[standard], websockets, langgraph, langchain-anthropic, langchain-openai, litellm, neo4j, chromadb, anthropic, chronos-forecasting, scikit-learn, shap, torch, numpy, pandas, python-dotenv, httpx, cryptography, pyyaml, aiofiles, structlog
  - Run `pip install -r requirements.txt`
  - Open Python shell and import every library individually to confirm zero errors
  - VERIFY: All imports succeed. `python --version` shows 3.11.x. `pip list` shows all packages at pinned versions.

---

- [ ] **0.4 — Set up frontend scaffold**
  - From the repo root: `npm create vite@latest frontend -- --template react`
  - cd into `/frontend`
  - Install: `npm install tailwindcss postcss autoprefixer framer-motion recharts react-force-graph-2d socket.io-client`
  - Initialise Tailwind: `npx tailwindcss init -p`
  - Configure Tailwind to scan `./src/**/*.{js,jsx}`
  - Start the dev server: `npm run dev`
  - VERIFY: Browser opens at localhost:5173 and shows the Vite + React default page. Zero console errors.

---

- [ ] **0.5 — Verify all external connections**
  - Load `.env` and run a test call to each service:
  - Neo4j: run `RETURN 1` in Neo4j Browser using your credentials → confirm result returns
  - ServiceNow: make GET request to `{your-instance}/api/now/table/incident?sysparm_limit=1` with basic auth → confirm JSON response with incident records
  - Anthropic: make a single messages API call with model claude-sonnet-4-6 and prompt "say hello" → confirm response
  - LiteLLM: configure LiteLLM with Claude as primary and GPT-4o as fallback → make one test completion call → confirm it routes to Claude
  - Slack: POST a test message to your webhook URL → confirm it appears in the Slack channel
  - VERIFY: All 5 connections return successful responses. Document exact response format from each.

---

## PHASE 1 — DATA FOUNDATION

> Do not proceed to Phase 2 until every task in Phase 1 has its VERIFY condition met.
> Bad data in Phase 1 breaks everything built on top. This phase gets the most care.

---

- [ ] **1.1 — Design FinanceCore knowledge graph on paper**
  - Draw every node with its properties on paper or whiteboard before writing any Cypher
  - Confirm the causal chain is coherent: Deployment CHG0089234 (3 days ago) → MODIFIED_CONFIG_OF → PaymentAPI (HikariCP maxPoolSize reduced from 100 to 40) → PaymentAPI DEPENDS_ON TransactionDB → TransactionDB had Incident INC-2024-0847 (4 months ago, same anomaly type, resolved successfully by restoring pool size)
  - List every relationship type that will exist: DEPENDS_ON, HOSTED_ON, MODIFIED_CONFIG_OF, DEPLOYED_TO, AFFECTED, CAUSED_BY, RESOLVED_BY, COVERED_BY, OWNED_BY, GOVERNED_BY
  - Confirm that running the deployment correlation Cypher query from ARCHITECTURE.md against this graph will return CHG0089234
  - Confirm that running the historical pattern Cypher query will return INC-2024-0847
  - VERIFY: Paper diagram is complete. Causal chain from CHG0089234 to today's incident is coherent. Every node has all required properties listed.

---

- [ ] **1.2 — Write and execute FinanceCore Cypher seed**
  - Create `/data/seed/financecore_graph.cypher` following the spec in STRUCTURE.md
  - Include all Service nodes: PaymentAPI, TransactionDB, AuthService, NotificationService, APIGateway — each with technology type, version, criticality, Kubernetes namespace or host
  - Include all Infrastructure nodes: EKS cluster, RDS primary instance, RDS replica, ALB
  - Include all Team nodes: payments-l2-team, dba-l2-team, platform-l3-team with tier and contact
  - Include 8 Deployment nodes — the critical one being CHG0089234 with these exact properties: change_id="CHG0089234", change_description containing "HikariCP maxPoolSize" and "40", timestamp 3 days before current date, cab_risk_rating="LOW", deployed_by="raj.kumar@atos.com"
  - Include 10 Incident nodes — the critical one being INC-2024-0847 with anomaly_type="CONNECTION_POOL_EXHAUSTED", root_cause mentioning HikariCP maxPoolSize, resolution mentioning restoring to 150, mttr_minutes=23
  - Include all SLA nodes, ComplianceRule nodes, all required relationships
  - Open Neo4j Browser → paste entire Cypher → execute
  - Run the 4 verification queries manually in Neo4j Browser:
    - Find CHG0089234: `MATCH (d:Deployment {change_id: 'CHG0089234', client_id: 'FINCORE_UK_001'}) RETURN d`
    - Confirm its relationship: `MATCH (d:Deployment {change_id: 'CHG0089234'})-[:MODIFIED_CONFIG_OF]->(s) RETURN d,s`
    - Run full deployment correlation query from ARCHITECTURE.md with affected_services=['PaymentAPI'] → confirm CHG0089234 in results
    - Run full historical pattern query with anomaly_type='CONNECTION_POOL_EXHAUSTED' → confirm INC-2024-0847 in results
  - VERIFY: All 4 verification queries return expected results. No missing nodes. No orphaned relationships.

---

- [ ] **1.3 — Write and execute RetailMax Cypher seed**
  - Create `/data/seed/retailmax_graph.cypher` following STRUCTURE.md spec
  - Include Service nodes: ProductAPI (Node.js), CartService (Node.js), Redis Cache, MongoDB, CDN
  - Include Deployment node DEP-20250316-003 with Redis maxmemory-policy change from allkeys-lru to noeviction, 2 days before current date
  - Include 6 Incident nodes — deliberately no incident with anomaly_type=REDIS_OOM (the absence is intentional)
  - Include all required relationships
  - Execute in Neo4j Browser
  - Run verification queries: confirm DEP-20250316-003 exists with MODIFIED_CONFIG_OF to Redis Cache. Confirm no REDIS_OOM incidents exist.
  - VERIFY: DEP-20250316-003 query returns the node. REDIS_OOM historical query returns empty results.

---

- [ ] **1.4 — Write historical incidents JSON**
  - Create `/data/seed/historical_incidents.json` following the schema in STRUCTURE.md
  - Write 10 FinanceCore incidents. For INC-2024-0847: write the description text carefully. It must include: service names TransactionDB and PaymentAPI, error codes HikariPool and maxPoolSize, root cause keywords pool exhaustion and configuration and deployment. This text must semantically match the fault scenario description when both are embedded.
  - Write 6 RetailMax incidents. None may have anomaly_type matching REDIS_OOM. Maximum semantic similarity to the Redis fault scenario must be under 0.70.
  - Every incident record must have: incident_id, client_id, service_name, anomaly_type, error_codes_observed, root_cause, resolution_steps, outcome, mttr_minutes, occurred_at
  - VERIFY: File is valid JSON. All 16 incidents present with all required fields.

---

- [ ] **1.5 — Build seed_chromadb.py script**
  - Read STRUCTURE.md section for `/scripts/seed_chromadb.py` before writing
  - Build the script per spec: creates collections for both clients if they don't exist, embeds every incident using the Claude embeddings API, stores in the correct collection with all metadata
  - Include rate limiting between embedding API calls
  - Run the script against the real ChromaDB instance
  - VERIFY: Script runs to completion with no errors. Both collections exist. Total document count matches incident count (10 + 6 = 16).

---

- [ ] **1.6 — Build and run validate_similarity.py**
  - Read STRUCTURE.md section for `/scripts/validate_similarity.py` before writing
  - Build the validation script per spec
  - The FinanceCore test query: "PaymentAPI and TransactionDB are experiencing connection pool exhaustion. HikariCP is reporting pool timeout errors. PostgreSQL connection count is at 94% of max_connections. Error pattern matches CONNECTION_POOL_EXHAUSTED. Deployment CHG0089234 modified HikariCP configuration."
  - The RetailMax test query: "Redis Cache OOM. Commands being rejected. maxmemory policy change. CartService latency spike from Redis rejections."
  - Run the script
  - If either test fails: rewrite the incident descriptions in historical_incidents.json, re-run seed_chromadb.py, re-run validate_similarity.py — repeat until both pass
  - VERIFY: Script outputs PASS for both tests. FinanceCore: INC-2024-0847 returns with score > 0.87. RetailMax: no result exceeds 0.70. Script exits with code 0.

---

- [ ] **1.7 — Write fault injection scripts**
  - Create `/data/fault_scripts/financecore_cascade.py` following STRUCTURE.md spec
  - Normal phase: 3 minutes of realistic INFO/DEBUG logs. Real Spring Boot format with real class names, thread names. Zero errors.
  - Fault phase: time-sequenced PostgreSQL connection count warnings starting at T+0, escalating every 30 seconds, first HikariCP ERROR at T+25, FATAL at T+35, Java HTTP 503 errors at T+45, Kubernetes pod restart events at T+60
  - All log lines must use real Java Spring Boot and PostgreSQL native log formats — no synthetic abbreviations
  - Create `/data/fault_scripts/retailmax_redis_oom.py` following the same approach for Redis OOM scenario
  - Run both scripts and confirm output looks realistic in terminal
  - VERIFY: Both scripts run without error. Output log lines look identical to production logs. Timing is documented in comments within each script.

---

- [ ] **1.8 — Pre-compute LLM fallback responses**
  - Assemble the complete reasoning prompt for the FinanceCore incident: evidence from agents, blast radius (PaymentAPI downstream services), deployment correlation (CHG0089234), historical match (INC-2024-0847 at 91% similarity), FinanceCore compliance profile
  - Make a real Claude API call using tool_use mode with the full output schema from ARCHITECTURE.md
  - Save the complete response to `/data/fallbacks/financecore_incident_response.json`
  - Validate the saved response: recommended_action_id must be "connection-pool-recovery-v2", all required fields must be present, explanation_for_engineer must be at least 100 words
  - Repeat for RetailMax: make a real call, save to `/data/fallbacks/retailmax_incident_response.json`
  - VERIFY: Both fallback files are valid JSON. Both recommended_action_id values match existing playbook IDs. Both explanation fields are at least 100 words.

---

## PHASE 2 — MATHEMATICAL CORE

> Build scorer.py and vetoes.py first. These are the mathematical foundation.
> Everything else in the confidence layer depends on them being correct.

---

- [ ] **2.1 — Build scorer.py**
  - Read STRUCTURE.md section for `/backend/orchestrator/confidence/scorer.py` before writing
  - Build the file per spec: four pure calculation functions, no I/O, no side effects, fully deterministic
  - Every function returns a value between 0.0 and 1.0 — validated with assertions
  - Update `test_progress.py` with assertions for known inputs: calculate_action_safety(3) must return 0.0, calculate_action_safety(1) must return 1.0, calculate_evidence_freshness with 25-minute-old timestamp must return 0.0, calculate_composite with all factors at 1.0 must return 1.0
  - Run `python test_progress.py`
  - VERIFY: All assertions pass. No import errors. Functions are deterministic on repeated calls with same inputs.

---

- [ ] **2.2 — Build vetoes.py**
  - Read STRUCTURE.md section for `/backend/orchestrator/confidence/vetoes.py` before writing
  - Build all 8 veto check functions per spec — each returns None (no veto) or a plain-English string (veto fired)
  - Build run_all_vetoes() which runs all checks and returns the complete list of fired vetoes
  - Update `test_progress.py`: test that check_action_class_three(3) returns a non-None string, check_action_class_three(1) returns None, run_all_vetoes with Class 3 action returns at least one veto
  - Run `python test_progress.py`
  - VERIFY: All new assertions pass. Veto explanations are complete English sentences suitable for display on a briefing card.

---

## PHASE 3 — DETECTION LAYER

---

- [ ] **3.1 — Build chronos_detector.py**
  - Read STRUCTURE.md section for `/backend/agents/detection/chronos_detector.py` before writing
  - Build per spec: loads Chronos-Bolt from HuggingFace, runs inference on metric time-series, supports fine-tuning on baseline data
  - Model loads asynchronously — never blocks the event loop
  - Fine-tuned model state stored per client_id per service_name — never shared
  - Fallback to z-score detection if model fails to load
  - Inference timeout: 500ms — use last known score if exceeded
  - Update `test_progress.py`: feed 60 flat readings at 5.0, confirm anomaly probability < 0.3. Feed 50 flat then 10 at 50.0, confirm probability rises above 0.6.
  - VERIFY: Both test cases pass. Model loads without error. Fallback activates when model is unavailable.

---

- [ ] **3.2 — Build isolation_forest.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: Isolation Forest with SHAP TreeExplainer wrapper, per-client per-service model isolation, 24-hour retraining in background thread
  - SHAP values always calculated for anomalous predictions — never suppressed
  - Minimum 100 training samples — falls back to z-score if fewer
  - Update `test_progress.py`: train on 100 synthetic normal observations, run on a normal observation (is_anomaly must be False), run on a 10x normal observation (is_anomaly must be True, shap_values dict must be non-empty, values must sum to approximately 100%)
  - VERIFY: All test cases pass. SHAP values present on every anomalous prediction.

---

- [ ] **3.3 — Build conformal.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: combines Chronos-Bolt and Isolation Forest scores using conformal prediction calibration
  - Fallback to simple threshold if calibration set has fewer than 50 samples — flagged in output
  - Output confidence_level is always the empirically calibrated value, never the nominal value
  - Combined score always between 0.0 and 1.0 — clipped if arithmetic produces otherwise
  - Update `test_progress.py`: test with calibration set of 50 samples (5% anomaly rate) → confirm combined_score and confidence_interval are both present in output. Test with 10 samples → confirm fallback flag is set.
  - VERIFY: Both test cases pass. Output structure is correct in both normal and fallback modes.

---

- [ ] **3.4 — Build base_agent.py**
  - Read STRUCTURE.md section before writing
  - Build abstract base class per spec: rolling seasonal baseline (168 slots: 7 days × 24 hours), EvidencePackage validator, bootstrap period enforcement, three detection tier thresholds
  - EvidencePackage validator must check every required field from the schema in STRUCTURE.md
  - Bootstrap enforcement: agent with no baseline data can only produce Warnings, never Alerts
  - Update `test_progress.py`: create a fresh agent instance with zero baseline data, attempt to trigger an Alert, confirm Warning is produced instead
  - VERIFY: Bootstrap enforcement confirmed. EvidencePackage validator rejects incomplete packages.

---

- [ ] **3.5 — Build java_agent.py**
  - Read STRUCTURE.md section before writing
  - Inherits from base_agent.py — do not duplicate any base class logic
  - Build per spec: Java/Spring Boot specific baselines, critical error code lookup table, hypothesis mapping
  - ECONNREFUSED from Java services must include target host in evidence package
  - Service silence for 5+ minutes emits Warning to activity feed
  - Update `test_progress.py`: feed 5 HikariCP exhaustion log lines to the agent, confirm it produces an EvidencePackage with anomaly_type CONNECTION_POOL_EXHAUSTED and severity P2
  - VERIFY: Test passes. EvidencePackage has all required fields from STRUCTURE.md schema.

---

- [ ] **3.6 — Build postgres_agent.py**
  - Read STRUCTURE.md section before writing
  - Inherits from base_agent.py
  - Build per spec: PostgreSQL-specific baselines, PANIC always produces P1, connection count thresholds (70%/85%/95%) not standard 2σ/3σ
  - max_connections value comes from CMDB-enriched event only — never hardcoded
  - Update `test_progress.py`: feed a PANIC log line, confirm EvidencePackage has severity P1 regardless of model confidence score
  - VERIFY: PANIC → P1 is unconditional. Test passes.

---

- [ ] **3.7 — Build nodejs_agent.py**
  - Read STRUCTURE.md section before writing
  - Inherits from base_agent.py
  - ECONNREFUSED must include target host — critical for cascade detection
  - Event loop lag metrics are optional — agent functions correctly without them
  - Update `test_progress.py`: feed ECONNREFUSED log line targeting "redis:6379", confirm the target host appears in the evidence package supporting_log_samples
  - VERIFY: Target host present in evidence. Test passes.

---

- [ ] **3.8 — Build redis_agent.py**
  - Read STRUCTURE.md section before writing
  - Inherits from base_agent.py
  - Any rejected command = Warning minimum — zero tolerance
  - Alert threshold: 85% memory (not 3σ — Redis memory is bounded)
  - Update `test_progress.py`: feed one Redis OOM log line, confirm EvidencePackage is produced with anomaly_type REDIS_OOM
  - VERIFY: OOM produces EvidencePackage. Test passes.

---

- [ ] **3.9 — Build event_queue.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: one asyncio queue per client_id, strict per-client isolation, queue depth metric, stale event flagging
  - No method that allows cross-client queue reading — enforced at the class level
  - Update `test_progress.py`: create queues for two different client_ids, write to queue A, confirm queue B remains empty
  - VERIFY: Client isolation confirmed. Test passes.

---

- [ ] **3.10 — Build normaliser.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: maps all three path formats to unified OTel schema, generates atlas_event_id, standardises timestamps, maps severity strings, preserves raw_payload
  - Events with missing client_id are rejected — never enter pipeline
  - raw_payload always preserved exactly — never modified
  - Update `test_progress.py`: feed a malformed event with no client_id, confirm it is rejected. Feed a valid Java log line, confirm all schema fields are present in output.
  - VERIFY: Both test cases pass. client_id rejection is enforced.

---

- [ ] **3.11 — Build java_adapter.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: parses Spring Boot log format, extracts error codes, handles multi-line stack traces, maps exception class names to ATLAS error taxonomy
  - Unparseable lines output with severity UNKNOWN and source_type java-unparseable — never silently dropped
  - Update `test_progress.py`: feed a real HikariCP log line, confirm error_code maps to CONNECTION_POOL_EXHAUSTED
  - VERIFY: HikariCP mapping correct. Unparseable line handling confirmed.

---

- [ ] **3.12 — Build postgres_adapter.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: parses PostgreSQL log format, maps SQLSTATE codes, extracts metrics where present
  - FATAL severity always outputs as ERROR in ATLAS schema — never downgraded
  - Update `test_progress.py`: feed a FATAL connection log line, confirm ATLAS severity is ERROR
  - VERIFY: FATAL → ERROR mapping confirmed. Test passes.

---

- [ ] **3.13 — Build cmdb_enricher.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: Neo4j lookup per source_system, 60-second TTL cache, graceful degradation when Neo4j is unavailable
  - Cache keys always include client_id — never serve one client's data to another
  - If Neo4j unavailable: serve from cache if available, flag event as enriched_from_cache, continue
  - Update `test_progress.py`: enrich an event for a known service, confirm ci_class and sla_breach_threshold_minutes are attached to the output
  - VERIFY: CMDB context attached to event. Test passes.

---

- [ ] **3.14 — Build correlation_engine.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: 90-second window per client_id, Neo4j DEPENDS_ON structural check (not temporal alone), deployment-correlated flag, early warning scan
  - Temporal proximity alone never sufficient for CASCADE classification — structural check is mandatory
  - If Neo4j unavailable for structural check: classify as ISOLATED_ANOMALY with structural_check_skipped flag — never block pipeline
  - Update `test_progress.py`: feed two EvidencePackages for DEPENDS_ON-connected services within 60 seconds → confirm CASCADE_INCIDENT. Feed two EvidencePackages for unconnected services → confirm two ISOLATED_ANOMALY packages.
  - VERIFY: Both test cases pass. CASCADE requires structural confirmation.

---

## PHASE 4 — DATABASE LAYER

---

- [ ] **4.1 — Build neo4j_client.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: connection pool, execute_query enforces client_id in params, 60-second result cache, automatic retry with exponential backoff
  - execute_query must validate client_id is in params before executing — hard enforcement
  - All queries are read transactions by default — write transactions require explicit request
  - Update `test_progress.py`: attempt to call execute_query without client_id in params → confirm it raises an error before executing
  - VERIFY: client_id enforcement confirmed. Connection to live Neo4j Aura succeeds.

---

- [ ] **4.2 — Build chromadb_client.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: creates client-namespaced collections on startup, embed_and_store, similarity_search, cross_client_search as separate method
  - similarity_search must only search the specified client's collection — never defaults to cross-client
  - Embedding model name stored as collection metadata — validated on every retrieval
  - Update `test_progress.py`: run similarity_search for FinanceCore fault scenario → confirm INC-2024-0847 is in top results
  - VERIFY: Correct similarity result confirmed using live ChromaDB with seeded data.

---

- [ ] **4.3 — Build audit_db.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: SQLite with audit_log table and decision_history table, write_audit_record, write is immutable (no update/delete methods), export functions
  - Every write is wrapped in a transaction
  - client_id always required — no record without it
  - Update `test_progress.py`: write one complete audit record, confirm it can be read back, confirm no update method exists on the class
  - VERIFY: Write and read confirmed. Immutability confirmed (no update method). Export to CSV returns valid CSV.

---

## PHASE 5 — ORCHESTRATION PIPELINE

> Build and test each node in complete isolation before connecting them.
> Test each node independently before running the full pipeline.

---

- [ ] **5.1 — Build state.py**
  - Read STRUCTURE.md section before writing
  - Build the complete LangGraph state TypedDict with every field from ARCHITECTURE.md
  - Mark immutable fields (client_id, incident_id, evidence_packages, mttr_start_time) with documentation
  - audit_trail is append-only — document this clearly
  - Update `test_progress.py`: instantiate a state with required fields → confirm it holds the correct values
  - VERIFY: State instantiates correctly. All fields typed. No missing fields from ARCHITECTURE.md spec.

---

- [ ] **5.2 — Build n1_classifier.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: ITIL priority assignment, SLA breach timer start, situation summary generation
  - P1 with breach under 15 minutes triggers immediate notification — not after orchestrator completes
  - SLA timer is immutable once started — no node may reset it
  - If all services have unknown criticality: default to P2 with criticality_uncertain flag — never default to P4
  - Update `test_progress.py`: feed CASCADE_INCIDENT with P1 service → confirm priority is P1. Feed with unknown criticality → confirm P2 with flag.
  - VERIFY: Both test cases pass.

---

- [ ] **5.3 — Build n2_itsm.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: real ServiceNow REST API call, INC ticket creation, retry with exponential backoff, graceful degradation if ServiceNow unavailable
  - Ticket must include atlas_incident_id in a custom field for correlation
  - If ServiceNow unavailable: set itsm_ticket_pending flag and continue pipeline — never halt
  - Make a real API call to the ServiceNow developer instance
  - Update `test_progress.py`: run n2 with valid incident state → confirm real ServiceNow ticket created and INC number returned in correct format
  - VERIFY: Real ServiceNow ticket visible in developer instance. INC number format is INC followed by 7 digits.

---

- [ ] **5.4 — Build n3_graph.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: three Cypher queries in parallel via asyncio.gather, 60-second result cache, query timeout of 5 seconds each
  - Every query enforces client_id filter at the query construction level — not just at runtime
  - If Neo4j completely unavailable: continue with empty results and graph_unavailable flag
  - Test each query independently with the FinanceCore demo scenario inputs before connecting to the pipeline:
    - Blast radius query with PaymentAPI → must return TransactionDB, AuthService, NotificationService
    - Deployment correlation query → must return CHG0089234
    - Historical pattern query with CONNECTION_POOL_EXHAUSTED → must return INC-2024-0847
  - Update `test_progress.py`: run n3 with FinanceCore demo inputs → confirm CHG0089234 in deployments and INC-2024-0847 in historical matches
  - VERIFY: All three queries return correct results from live Neo4j. Parallel execution confirmed via asyncio.

---

- [ ] **5.5 — Build n4_semantic.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: ChromaDB similarity search, double-confirmation logic, cross-client fallback for cold-start
  - similarity_search for the FinanceCore fault scenario must return INC-2024-0847 as top result above 0.87
  - Cross-client results must be flagged differently from client-specific results
  - Update `test_progress.py`: run n4 with FinanceCore fault scenario description → confirm INC-2024-0847 is top result with score above 0.87. Confirm double-confirmation flag fires when INC-2024-0847 also appears in graph results.
  - VERIFY: Correct similarity result. Double-confirmation logic confirmed.

---

- [ ] **5.6 — Build n5_reasoning.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: LiteLLM routing (Claude primary, GPT-4o fallback, Gemini tertiary), Claude tool_use mode, schema validation of output, fallback file loading
  - recommended_action_id from LLM output must be validated against playbook library before being accepted
  - Pre-computed fallback loads in under 200ms when live call fails or times out
  - Test the Claude tool_use call with mock inputs from the FinanceCore scenario — run it 10 times. Confirm valid JSON is returned 10/10 times.
  - Test the LiteLLM failover: disable Claude API key temporarily → confirm GPT-4o is used
  - Test the fallback: set timeout to 1 second → confirm fallback file loads correctly
  - Update `test_progress.py`: run n5 with FinanceCore mock context → confirm recommended_action_id is "connection-pool-recovery-v2"
  - VERIFY: 10/10 valid JSON. Failover confirmed. Fallback confirmed. recommended_action_id validated.

---

- [ ] **5.7 — Build n6_confidence.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: uses scorer.py and vetoes.py, queries decision_history for Factor 1, Class 3 check runs first
  - All 8 vetoes run and all active vetoes returned — not just the first
  - Insert 5 test decision records into decision_history: 4 successes and 1 failure for CONNECTION_POOL_EXHAUSTED on FINCORE_UK_001 with action connection-pool-recovery-v2 → confirm empirical accuracy = 0.80
  - Build FinanceCore demo scenario inputs: N5 output + graph context + client config. Run N6.
  - Confirm composite score is approximately 0.84. Confirm PCI-DSS + business hours veto fires. Confirm routing is L2_L3_ESCALATION.
  - Update `test_progress.py`: run N6 with FinanceCore demo inputs → confirm score ~0.84 and PCI veto active
  - VERIFY: Score approximately 0.84. PCI veto fires. Routing is L2_L3_ESCALATION. Cold-start veto fires when fewer than 5 records exist.

---

- [ ] **5.8 — Build n7_router.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: routes to AUTO_EXECUTE, L1_HUMAN_REVIEW, or L2_L3_ESCALATION based on routing_decision in state, LangGraph interrupt for human review paths, P1 always notifies SDM
  - LangGraph interrupt must persist state — if server restarts while waiting for human, state must be recoverable
  - Timeout on human review: SLA breach time minus 2 minutes → auto-escalate to next tier
  - Update `test_progress.py`: run full N7 with L2_L3_ESCALATION routing → confirm LangGraph interrupt fires at the correct node
  - VERIFY: Interrupt fires. State persists after simulated restart. Timeout escalation logic confirmed.

---

- [ ] **5.9 — Build pipeline.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: assembles all 7 nodes into the LangGraph StateGraph, defines all edges, adds conditional edge from N7
  - Every node transition writes a timestamped entry to audit_trail in state
  - Compile the graph and confirm it compiles without error
  - Update `test_progress.py`: compile the graph → confirm it compiles. Print the graph structure → confirm all 7 nodes are present.
  - VERIFY: Graph compiles. All 7 nodes shown. Interrupt configured on human-review node.

---

- [ ] **5.10 — Full pipeline end-to-end test**
  - Connect agents → correlation_engine → pipeline
  - Run the FinanceCore fault script
  - Watch the pipeline execute node by node — print state after each node to confirm correct updates
  - Confirm: ServiceNow ticket created, CHG0089234 in graph results, INC-2024-0847 in semantic results, confidence ~0.84, PCI veto fires, routed to L2
  - Simulate human approval via direct state update
  - Confirm graph resumes from interrupt
  - Run this test 5 consecutive times — all 5 must produce identical routing decisions
  - Update `test_progress.py`: run complete pipeline with FinanceCore fault scenario → confirm routing is L2_L3_ESCALATION with INC ticket created
  - VERIFY: 5/5 identical runs. All nodes execute correctly. ServiceNow ticket created each run.

---

## PHASE 6 — EXECUTION ENGINE AND LEARNING

---

- [ ] **6.1 — Build client_registry.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: loads YAML configs from /backend/config/clients/, validates all required fields, read-only after loading except via trust_progression designated method
  - auto_execute_threshold validated between 0.5 and 1.0 — reject outside this range
  - max_action_class must be 1 or 2 — value 3 rejected immediately
  - Unknown compliance frameworks rejected
  - Update `test_progress.py`: load FinanceCore config → confirm auto_execute_threshold is 0.92. Attempt to load a config with max_action_class=3 → confirm it raises an error.
  - VERIFY: FinanceCore config loads correctly. Class 3 rejection confirmed.

---

- [ ] **6.2 — Create financecore.yaml and retailmax.yaml**
  - Create `/backend/config/clients/financecore.yaml` with exact values from STRUCTURE.md spec
  - Create `/backend/config/clients/retailmax.yaml` with exact values from STRUCTURE.md spec
  - Load both through client_registry.py and confirm they parse without errors
  - VERIFY: Both configs load without errors. All required fields present. Compliance frameworks are valid known values.

---

- [ ] **6.3 — Build playbook_library.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: registry of all available playbooks with metadata, validate_action_id, semantic search for rejection reason matching
  - Class 3 playbooks marked auto_execute_eligible: false — execution engine checks this flag
  - Every playbook's rollback_playbook_id must point to a valid existing playbook — validated on startup
  - Update `test_progress.py`: call validate_action_id("connection-pool-recovery-v2") → confirm True. Call with a non-existent ID → confirm False.
  - VERIFY: validate_action_id works correctly. Rollback validation passes on startup.

---

- [ ] **6.4 — Build connection_pool_recovery_v2.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: pre-execution validation (HTTP call to PaymentAPI health endpoint), action execution (PATCH to update HikariCP config), success validation (poll error rate for recovery), auto-rollback on timeout
  - Every external HTTP call has a 10-second timeout
  - All target endpoints come from client config — never hardcoded
  - Set up a simple mock PaymentAPI Flask/FastAPI service in `/data/mock_services/` for the demo — it must have a /actuator/health endpoint and accept PATCH requests to update config
  - Test pre-execution validation failure: make the mock service unavailable → confirm playbook halts and escalates
  - Test auto-rollback: set success validation timeout to 10 seconds, do not trigger resolution signal → confirm rollback fires
  - VERIFY: Pre-validation halt confirmed. Auto-rollback confirmed. Audit record written in both success and rollback scenarios.

---

- [ ] **6.5 — Build redis_memory_policy_rollback_v1.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: connects to real Redis, pre-validation checks maxmemory-policy is noeviction, executes CONFIG SET, validates change
  - Start a local Redis instance via Docker: `docker run -d -p 6379:6379 redis`
  - Set Redis to noeviction mode manually
  - Run the playbook: confirm it detects noeviction, changes to allkeys-lru, verifies the change
  - Test pre-validation halt: set policy to allkeys-lru before running → confirm playbook halts with "assumed cause not present" message
  - VERIFY: Policy change confirmed in Redis. Pre-validation halt confirmed.

---

- [ ] **6.6 — Build approval_tokens.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: generate signed tokens, validate expiry, enforce one-time use via nonce store
  - Secret key comes from environment variables only — never defaults to a weak key
  - Test token expiry: generate token with 1-second expiry, wait 2 seconds, validate → confirm valid=False with expiry reason
  - Test one-time use: validate same valid token twice → confirm second validation returns valid=False with "already used" reason
  - VERIFY: Expiry confirmed. One-time use confirmed. Token generated without secret key raises error.

---

- [ ] **6.7 — Build decision_history.py (within audit_db.py)**
  - This may be part of audit_db.py or a separate file — follow STRUCTURE.md guidance
  - Build per spec: write_record, get_records_for_pattern, get_accuracy_rate, mark_recurrence
  - write_record is atomic — partial writes roll back
  - Records are immutable after writing — no update method exists
  - Update `test_progress.py`: write 5 records (4 success, 1 failure) for same pattern → confirm get_accuracy_rate returns 0.80
  - VERIFY: Accuracy rate calculation confirmed. Immutability confirmed.

---

- [ ] **6.8 — Build recalibration.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: recalculates Factor 1 after every resolution, updates in-memory cache, runs asynchronously
  - Minimum 5 records still required — cold-start veto lifted automatically when count reaches 5
  - Read-write lock on the cache — no reads during write
  - Update `test_progress.py`: insert 5th record for a previously cold-start pattern → confirm cold-start veto is lifted for subsequent confidence calculations
  - VERIFY: Cold-start veto lifts at 5 records. Async execution confirmed (does not block resolution confirmation).

---

- [ ] **6.9 — Build weight_correction.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: accumulates L2 modification diffs, updates defaults after 3x same direction, parses L3 rejection reasons, adjusts hypothesis weights
  - Parameter adjustments bounded at 50% from playbook default — beyond that, SDM review flagged
  - All adjustments logged to audit trail with supporting evidence
  - Update `test_progress.py`: record 3 L2 modifications all increasing maxPoolSize → confirm get_adjusted_default returns a value above the playbook default
  - VERIFY: Default updated after 3rd same-direction diff. Bounded at 50% confirmed.

---

- [ ] **6.10 — Build trust_progression.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: evaluates stage criteria after every incident, sends recommendation requiring SDM confirmation, updates trust_level via client_registry designated method only
  - No other module may call the trust_level update method
  - Stage 4 requires explicit SDM action beyond criteria being met
  - Update `test_progress.py`: insert 30 decision records for FINCORE_UK_001 all with human_action=approved and resolution_outcome=success → confirm get_progression_metrics shows Stage 1 criteria met and recommendation generated (not automatic upgrade)
  - VERIFY: Recommendation generated (not automatic upgrade). SDM confirmation required. Only trust_progression.py can change trust_level.

---

## PHASE 7 — API AND BACKEND INTEGRATION

---

- [ ] **7.1 — Build main.py**
  - Read STRUCTURE.md section before writing
  - Build per spec: FastAPI app, all HTTP routes, all WebSocket endpoints, startup validation, background tasks
  - On startup: check all required env vars, test Neo4j connection, test ChromaDB connection, test LLM API, start log generator, start agent monitoring tasks
  - If any required env var is missing: refuse to start, print exactly which variable is missing
  - CORS configured for frontend origin only — not wildcard
  - WebSocket disconnection handled gracefully — server never crashes on disconnect
  - Start the backend: `uvicorn backend.main:app --reload`
  - VERIFY: Server starts without error. All required env vars validated. `GET /api/incidents/active` returns 200. WebSocket connects at `ws://localhost:8000/ws/logs/FINCORE_UK_001`.

---

- [ ] **7.2 — Full backend integration test**
  - Start the complete backend
  - Start the log generator in normal mode for FinanceCore
  - Trigger the FinanceCore fault script
  - Watch the pipeline execute end-to-end without intervention until the human review pause
  - Confirm in sequence: both agents fire, correlation engine classifies CASCADE, N1 runs, N2 creates real ServiceNow ticket, N3 returns CHG0089234, N4 returns INC-2024-0847 at >0.87 similarity, N5 returns structured JSON, N6 produces ~0.84 score with PCI veto, graph suspends at human review
  - Call `POST /api/incidents/approve` with the incident_id
  - Confirm pipeline resumes, playbook executes, resolution signal fires, audit record written
  - Run this test 5 consecutive times — all 5 must produce identical outcomes
  - VERIFY: 5/5 identical runs. Real ServiceNow ticket created each run. Audit records in SQLite. Neo4j updated with new incident node after each run.

---

## PHASE 8 — FRONTEND

---

- [ ] **8.1 — Build useWebSocket hook**
  - Read STRUCTURE.md section for `/frontend/src/hooks/useWebSocket.js` before writing
  - Build per spec: manages WebSocket connections, automatic reconnect with exponential backoff, dispatches to state
  - Minimum 1 second between reconnect attempts, doubling up to 30 seconds maximum
  - Shows "Reconnecting..." state in UI when disconnected — never shows stale data silently
  - VERIFY: WebSocket connects to backend. Disconnecting backend shows reconnecting state. Reconnects automatically when backend restarts.

---

- [ ] **8.2 — Build three-panel layout and ActivityFeed**
  - Build three-panel layout: left panel (client roster), centre panel (active state), right panel (activity feed)
  - Build ClientRoster component: client cards with real health status from WebSocket, SLA uptime counter, compliance badges, trust level indicator
  - Build ActivityFeed component: timestamped entries from WS /ws/activity, colour-coded by entry type, last 100 entries
  - Connect both to live backend WebSocket endpoints
  - VERIFY: Left panel shows FinanceCore and RetailMax cards with real health status. Activity feed updates in real time when fault script is triggered.

---

- [ ] **8.3 — Build GraphViz component**
  - Read STRUCTURE.md section before writing
  - Build per spec: React Force Graph 2D with real Neo4j traversal path data, animated traversal sequence, hover tooltips showing real properties
  - Animation sequence driven by graph_traversal_path from incident state — not hardcoded
  - Pre-record the animation as a 15-second video file and implement fallback logic
  - VERIFY: Graph animates correctly using real FinanceCore incident data. Deployment node pulses first, then cascade traces to PaymentAPI. Hover tooltip shows CHG0089234 details. Pre-recorded fallback plays when component is disabled.

---

- [ ] **8.4 — Build BriefingCard component**
  - Read STRUCTURE.md section before writing
  - Build per spec: all 6 sections with real data, SLA countdown timer, similarity score from real ChromaDB value
  - SLA timer turns red under 5 minutes — automatic
  - Reject button requires minimum 20 characters in reason field before submit enables
  - VERIFY: All 6 sections populate with real data from running pipeline. SLA timer counts down live. Reject requires 20+ characters.

---

- [ ] **8.5 — Build SHAPChart component**
  - Build per spec: horizontal Recharts bar chart with real SHAP values, sorted by contribution, colour-coded by feature type
  - Values must sum to 100% — show warning banner if they do not
  - Show "Feature attribution unavailable" message when shap_values is empty
  - VERIFY: Chart shows real SHAP values from anomaly detection. Values sum to 100%.

---

- [ ] **8.6 — Build ApprovalFlow component**
  - Read STRUCTURE.md section before writing
  - Build per spec: L1 view (Approve/Escalate), L2 view (Approve/Modify/Reject), dual approval flow for PCI-DSS
  - Dual approval: primary approves → "Awaiting secondary" state → secondary crypto token confirmation → "Both approved"
  - Approve button disabled during dual approval pending state
  - Post-approval: shows "Executing..." then transitions to post-resolution view
  - VERIFY: Full approval flow works against running backend. Dual approval shows correct states. Approval click triggers real execution.

---

- [ ] **8.7 — Build post-resolution view and early warning card**
  - Post-resolution: real Recharts timeseries showing actual metric recovery from log stream, MTTR counter stopping with real elapsed seconds, Atlassian 43-minute benchmark line
  - Early warning card: appears when EarlyWarning signals present in incident state, shows real σ value from Chronos-Bolt inference
  - VERIFY: Post-resolution chart shows real metric recovery. MTTR counter stops at correct value. Early warning card appears during demo when AuthService shows 1.8σ deviation.

---

## PHASE 9 — HARDENING AND DEMO PREPARATION

---

- [ ] **9.1 — 20 consecutive complete system runs**
  - Start complete system: backend, frontend, both mock services, Redis, log generator
  - Run FinanceCore demo scenario 20 times consecutively
  - Document each run: detection timing (expected T+47 ±5s), confidence score (expected ~0.84), veto that fires (PCI-DSS), INC ticket created and visible in ServiceNow, MTTR under 5 minutes, audit record written, Neo4j updated with new incident node
  - If any run fails or produces different routing decision: find root cause, fix, restart count from zero
  - The count reaches 20 only when 20 consecutive runs produce identical correct outputs
  - VERIFY: 20 consecutive runs documented with consistent correct output. Zero failures.

---

- [ ] **9.2 — Test every fallback explicitly**
  - Fallback 1 — Claude API timeout: set timeout to 1 second, run demo → confirm fallback JSON loads in under 200ms, demo continues
  - Fallback 2 — LiteLLM failover: disable Claude API key, run demo → confirm GPT-4o is used automatically, output is valid
  - Fallback 3 — Neo4j unavailable: pause Neo4j connection mid-run → confirm cached results serve and pipeline continues with graph_unavailable flag
  - Fallback 4 — Graph animation failure: disable React Force Graph component → confirm pre-recorded video plays instead
  - Fallback 5 — WebSocket disconnection: kill backend WebSocket server mid-demo → confirm frontend shows "Reconnecting..." and reconnects automatically
  - VERIFY: All 5 fallbacks confirmed working. Each fallback is invisible or clearly communicated to the user. Document each test result.

---

- [ ] **9.3 — Technical depth verification for judge Q&A**
  - Prepare and rehearse each of these live demonstrations — each must be completable in under 60 seconds:
  - "Show me the actual graph query": open Neo4j Browser, paste deployment correlation Cypher, run live, show CHG0089234 in results
  - "Show me the ChromaDB similarity search": open Python REPL, import chromadb_client, run similarity search for FinanceCore scenario, show INC-2024-0847 at ~91% score
  - "Show me the audit log": open SQLite browser or run SQLite CLI, query audit_log table, show records from today's runs with all fields
  - "Show me the ServiceNow ticket": open ServiceNow developer instance, show INC ticket created by ATLAS, show all fields correctly populated
  - "Show me the confidence calculation": explain each of the four factors with actual values from the last demo run, show Factor 1 changing across multiple runs as decision history accumulates
  - VERIFY: All 5 demonstrations rehearsed. Each completable in under 60 seconds. Live data visible in each system.

---

- [ ] **9.4 — Presentation rehearsal**
  - Final build freeze: no code changes after this point
  - Rehearse the complete demo 10 times
  - Time each run: must be under 6 minutes
  - Practice three silence moments: 4 seconds during graph animation, 3 seconds after early warning card appears, 2 seconds after MTTR number displays
  - Every team member presents the demo at least twice — not just the designated presenter
  - Every team member answers these questions without notes: "How is this different from Dynatrace?", "How does the confidence score work?", "What stops it auto-executing something catastrophic?", "How does multi-tenancy work?", "What about legacy SAP systems?", "How does it learn?"
  - VERIFY: 10 rehearsal runs completed. All under 6 minutes. Every team member can answer all 6 questions from memory.

---

- [ ] **9.5 — Day-of preparation checklist**
  - The night before: run complete system one final time → if it works, stop, do not touch it
  - Morning of: charge all devices, close all applications except demo browser and one terminal, disable all notifications, set display to never sleep
  - Arrive early: set up 30 minutes before, run one full demo to confirm everything works in the actual physical location with actual network
  - Confirm open in separate browser tabs:
    - Neo4j Browser (logged in, test query pre-typed)
    - ServiceNow developer instance (logged in, incident list visible)
    - SQLite browser or terminal with SQLite CLI (database file open)
    - Python REPL with ChromaDB client ready to run
  - Confirm pre-computed fallback responses are loaded in the application
  - Confirm pre-recorded graph animation video file is accessible
  - Confirm Redis Docker container is running
  - Confirm mock PaymentAPI service is running
  - VERIFY: Complete system works in actual presentation location. All live-demo browser tabs open and tested. Fallbacks loaded and confirmed working.

---

## PROGRESS TRACKER

Mark tasks complete only when VERIFY condition is fully met.

| Phase | Tasks | Status |
|---|---|---|
| 0 — Environment | 0.1 → 0.5 | [ ] [ ] [ ] [ ] [ ] |
| 1 — Data Foundation | 1.1 → 1.8 | [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] |
| 2 — Math Core | 2.1 → 2.2 | [ ] [ ] |
| 3 — Detection | 3.1 → 3.14 | [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] |
| 4 — Database | 4.1 → 4.3 | [ ] [ ] [ ] |
| 5 — Orchestration | 5.1 → 5.10 | [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] |
| 6 — Execution + Learning | 6.1 → 6.10 | [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] |
| 7 — Backend Integration | 7.1 → 7.2 | [ ] [ ] |
| 8 — Frontend | 8.1 → 8.7 | [ ] [ ] [ ] [ ] [ ] [ ] [ ] |
| 9 — Hardening | 9.1 → 9.5 | [ ] [ ] [ ] [ ] [ ] |

---

## CRITICAL RULES — READ BEFORE EVERY SESSION

1. Read ROLE.md before writing any code in a session
2. Read the STRUCTURE.md section for a file before building that file — no exceptions
3. A task is not done until its VERIFY condition is fully met — not when the code runs once
4. The sequence is law — no phase starts until the previous phase's VERIFY conditions are all met
5. Never write mock data in production code paths
6. Never write a Cypher query without a client_id WHERE clause
7. Never allow Class 3 actions into the auto-execute path under any circumstances
8. Never commit `.env`
9. Build code only when explicitly told to — planning and reviewing are separate activities
10. When in doubt: check ARCHITECTURE.md first, STRUCTURE.md second, then choose the more defensive option

---

*TODO.md — Complete. Every task specified. Every verify condition defined. Follow in order. Win.*