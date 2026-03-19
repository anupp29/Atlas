# ATLAS — PLAN.md
## Complete Task Breakdown: What to Do, In What Order, With What Instructions

---

> This is your execution guide. Every task is listed in the exact order it must be done.
> No code is written here. Each task has: what to do, what to verify, what the done condition is.
> Do not start a new task until the current task's done condition is fully met.
> Sequence is not optional. Every layer depends on the one before it.

---

## PHASE 0 — ENVIRONMENT SETUP
### Complete this entirely before writing a single application file

---

### Task 0.1 — Create all external accounts

**What to do:**
- Create a Neo4j Aura account at console.neo4j.io. Create a free Serverless instance. Copy the connection URI, username, and password immediately — they are only shown once. Save them securely.
- Create a ServiceNow Developer account at developer.servicenow.com. Request a developer instance. This takes up to 15 minutes to provision. Note the instance URL (format: devXXXXXX.service-now.com), admin username, and admin password.
- Confirm your Anthropic API key is active. Test it with a single curl call to the messages endpoint.
- Confirm your OpenAI API key is active. This is the LiteLLM fallback.
- Create a HuggingFace account if you do not have one. The Chronos-Bolt model download does not require authentication but having an account allows you to track model versions.

**Done condition:** All four API credentials are saved. ServiceNow developer instance URL is accessible in a browser. Neo4j Browser is accessible at the URI.

---

### Task 0.2 — Set up the repository

**What to do:**
- Create a new Git repository named `atlas`
- Create the complete folder structure from STRUCTURE.md: `/backend`, `/backend/config`, `/backend/config/clients`, `/backend/ingestion`, `/backend/ingestion/adapters`, `/backend/agents`, `/backend/agents/detection`, `/backend/orchestrator`, `/backend/orchestrator/nodes`, `/backend/orchestrator/confidence`, `/backend/execution`, `/backend/execution/playbooks`, `/backend/learning`, `/backend/database`, `/data`, `/data/seed`, `/data/fault_scripts`, `/data/fallbacks`, `/frontend`, `/scripts`
- Create the `.env.example` file with all variable names from STRUCTURE.md, all values blank
- Create the `.env` file with your real values — immediately add `.env` to `.gitignore`
- Commit the empty structure with `.env.example` and `.gitignore`

**Done condition:** `git status` shows a clean repo. `.env` is in `.gitignore` and does not appear in `git status`. All folders exist.

---

### Task 0.3 — Install all dependencies

**What to do:**
- Create `requirements.txt` with every library listed in STRUCTURE.md, all versions pinned
- Run `pip install -r requirements.txt` in a Python 3.11 virtual environment
- After installation completes: open a Python shell and import every library one by one. The list to test: fastapi, uvicorn, langgraph, langchain_anthropic, litellm, neo4j, chromadb, anthropic, chronos, sklearn, shap, torch, numpy, pandas, dotenv, httpx, cryptography
- For the frontend: run `npm create vite@latest frontend -- --template react` inside the frontend directory, then install: tailwindcss, framer-motion, recharts, react-force-graph-2d, socket.io-client

**Done condition:** Every import succeeds without error in Python. The Vite dev server starts successfully. Zero dependency errors.

---

### Task 0.4 — Verify external connections

**What to do:**
- Load your `.env` file and test each connection:
- Neo4j: open Neo4j Browser, paste the URI, confirm you can run `RETURN 1` and get a result
- ServiceNow: log into your developer instance. Navigate to Incident module. Confirm you can see the incident list. Confirm the REST API is accessible by making a GET request to `{instance}/api/now/table/incident?sysparm_limit=1`
- Anthropic: make a single test API call with a simple prompt. Confirm you get a response.
- LiteLLM: install and configure LiteLLM pointing at both Claude and GPT-4o. Make one test call through LiteLLM routing to Claude.

**Done condition:** All four external connections verified with actual successful calls. Document the response from each test call.

---

---

## PHASE 1 — DATA FOUNDATION
### Do not start Phase 2 until every task in Phase 1 has its done condition met

---

### Task 1.1 — Design the FinanceCore graph on paper first

**What to do:**
- Before writing any Cypher, draw the complete FinanceCore graph on paper or a whiteboard
- List every node you will create with its properties
- List every relationship and confirm it makes logical sense
- Verify the detective story is coherent: CHG0089234 (3 days ago) → MODIFIED_CONFIG_OF → PaymentAPI (reducing maxPoolSize). PaymentAPI → DEPENDS_ON → TransactionDB. TransactionDB → had → INC-2024-0847 (4 months ago, same pattern, same cause, resolved successfully).
- The graph traversal during the demo must follow this exact path and surface CHG0089234 as the deployment correlation. Verify this is achievable before writing any Cypher.

**Done condition:** Paper diagram complete. Causal chain confirmed as coherent. Every node and relationship documented.

---

### Task 1.2 — Write and execute the FinanceCore Cypher seed

**What to do:**
- Write `financecore_graph.cypher` using your paper design
- Include every node and relationship from STRUCTURE.md
- Include the critical CHG0089234 deployment node with exact properties: change_id, deployed_by, change_description mentioning HikariCP maxPoolSize reduction, timestamp set to 3 days before the demo date, cab_risk_rating LOW
- Include the critical INC-2024-0847 incident node with exact properties: anomaly_type CONNECTION_POOL_EXHAUSTED, root_cause text mentioning HikariCP maxPoolSize, resolution mentioning restoring pool size to 150, mttr_minutes 23
- Open Neo4j Browser and paste the Cypher directly. Execute it.
- After execution, run these verification queries manually in Neo4j Browser:
  - Query: find CHG0089234 and confirm its MODIFIED_CONFIG_OF relationship to PaymentAPI exists
  - Query: find INC-2024-0847 and confirm its AFFECTED relationship to TransactionDB exists and its anomaly_type is correct
  - Query: run the full deployment correlation Cypher query from ARCHITECTURE.md with affected_services = PaymentAPI and confirm CHG0089234 is in the results
  - Query: run the full historical pattern Cypher query with anomaly_type CONNECTION_POOL_EXHAUSTED and confirm INC-2024-0847 is in the results

**Done condition:** All four verification queries return the expected results. Zero unexpected nodes or missing relationships.

---

### Task 1.3 — Write and execute the RetailMax Cypher seed

**What to do:**
- Write `retailmax_graph.cypher` following the same approach
- Include DEP-20250316-003 with the Redis maxmemory-policy change from 2 days before the demo
- Ensure no historical incident node has anomaly_type REDIS_OOM — the absence of a strong historical match is intentional for the RetailMax demo scenario
- Execute in Neo4j Browser and verify: DEP-20250316-003 exists and has MODIFIED_CONFIG_OF relationship to Redis Cache

**Done condition:** Verification query confirms DEP-20250316-003 exists. Verification query for REDIS_OOM historical pattern returns empty results.

---

### Task 1.4 — Write the historical incidents JSON and seed ChromaDB

**What to do:**
- Write `historical_incidents.json` with 10 FinanceCore incidents and 6 RetailMax incidents following the schema in STRUCTURE.md
- For INC-2024-0847: write the description carefully. Include the service name (TransactionDB, PaymentAPI), the error codes (HikariCP, connection_pool, maxPoolSize), the root cause keywords (pool exhaustion, configuration, deployment). The description must semantically match the FinanceCore fault scenario description when both are embedded.
- Write the FinanceCore fault scenario description as a separate test string: "PaymentAPI and TransactionDB are experiencing connection pool exhaustion. HikariCP is reporting pool timeout errors. PostgreSQL connection count is at 94% of max_connections. Error pattern matches CONNECTION_POOL_EXHAUSTED. Related deployment CHG0089234 modified HikariCP configuration."
- Run `seed_chromadb.py` to embed all incidents
- Immediately run `validate_similarity.py`

**Done condition:** `validate_similarity.py` outputs PASS for both tests. FinanceCore fault scenario returns INC-2024-0847 with score above 0.87. RetailMax fault scenario returns nothing above 0.70. If either test fails: rewrite the incident descriptions until both pass. Do not move to the next task until validation passes.

---

### Task 1.5 — Write the fault scripts

**What to do:**
- Write `financecore_cascade.py` as a sequence of log lines with timing offsets
- Start with 3 minutes of normal logs (no errors)
- At T+0: begin inserting PostgreSQL connection count warning messages. Frequency: 1 per 30 seconds initially.
- At T+25: increase frequency to 1 per 10 seconds. Insert first HikariCP timeout message.
- At T+35: insert FATAL connection pool message. This should trigger the PostgreSQL agent.
- At T+45: insert Java Spring Boot HTTP 503 error messages. This should trigger the Java agent.
- At T+60: insert Kubernetes pod restart events.
- Run the fault script against the log generator manually and watch the terminal output. Confirm the timing and log format look realistic.
- Write `retailmax_redis_oom.py` following the same pattern for Redis OOM.

**Done condition:** Both fault scripts produce realistic-looking log output. Timing is documented (T+0 through T+75 for FinanceCore).

---

### Task 1.6 — Pre-compute LLM fallback responses

**What to do:**
- Write the exact reasoning prompt you will use in n5_reasoning.py: include the FinanceCore incident context (evidence from agents, blast radius from Neo4j, deployment from Neo4j, historical match from ChromaDB, client compliance profile)
- Make a real Claude API call with this prompt in tool_use mode with the required output schema
- Save the complete response to `data/fallbacks/financecore_incident_response.json`
- Verify the saved response: confirm recommended_action_id is connection-pool-recovery-v2, confirm all required fields are present, confirm explanation_for_engineer is at least 100 words
- Make a similar call for RetailMax and save to `data/fallbacks/retailmax_incident_response.json`

**Done condition:** Both fallback files exist with valid content. All required fields present. recommended_action_id values match existing playbook IDs.

---

---

## PHASE 2 — DETECTION LAYER
### Do not start until Phase 1 done conditions are all met

---

### Task 2.1 — Build the confidence and scoring utilities first

**What to do:**
- Build `scorer.py` with the four pure calculation functions
- Build `vetoes.py` with all eight veto check functions
- Test every function with known inputs and expected outputs before connecting to anything else
- Test cases to verify: calculate_action_safety(3) must return 0.0. calculate_evidence_freshness with a 25-minute-old timestamp must return 0.0. check_action_class_three with class=3 must return a non-None string. run_all_vetoes must return all fired vetoes, not just the first one.

**Done condition:** All test cases pass. Functions return correct values for edge cases. Zero logic errors in the mathematical core.

---

### Task 2.2 — Build the Chronos-Bolt detector

**What to do:**
- Build `chronos_detector.py` following the spec in STRUCTURE.md
- Load the Chronos-Bolt model. If the download takes time, do it now — not later when you are time-pressured.
- Run a basic test: feed it 60 readings of a normal metric (flat at 5.0), confirm it returns a low anomaly probability. Then feed it 50 normal readings followed by 10 readings at 50.0. Confirm the anomaly probability increases significantly for the spike readings.
- Test the baseline fine-tuning: generate 30 minutes of synthetic normal data at realistic values. Run the fine-tune method. Confirm the model's expected range for normal data is narrower after fine-tuning.

**Done condition:** Model loads successfully. Normal data produces anomaly probability below 0.3. Spike data produces anomaly probability above 0.7. Fine-tuning completes without error.

---

### Task 2.3 — Build the Isolation Forest with SHAP

**What to do:**
- Build `isolation_forest.py` following the spec
- Train on 100 synthetic normal baseline observations
- Run detection on a normal observation: confirm is_anomaly is False
- Run detection on an anomalous observation (all metrics at 10x normal): confirm is_anomaly is True and shap_values dict is populated with percentages summing to 100%
- Verify the per-client isolation: create two instances with different client_ids. Confirm that training one does not affect the other.

**Done condition:** Isolation Forest detects the test anomaly. SHAP values produced. Values sum to 100%. Per-client isolation confirmed.

---

### Task 2.4 — Build the conformal prediction wrapper

**What to do:**
- Build `conformal.py` following the spec
- Test with a calibration set of 50 samples where 5% are known anomalies. Confirm the combined score and confidence interval are produced.
- Test the fallback: call with a calibration set of only 10 samples. Confirm it falls back to simple threshold and flags the fallback.

**Done condition:** Conformal prediction produces valid confidence intervals. Fallback activates correctly when calibration set is small.

---

### Task 2.5 — Build base_agent.py

**What to do:**
- Build `base_agent.py` with the abstract class and all shared logic
- Implement the rolling seasonal baseline: a data structure that stores (mean, stddev) per (hour_of_day, day_of_week) slot — 168 slots per metric
- Implement the EvidencePackage validator: checks all required fields are present and of correct types before allowing the package to be sent
- Test the bootstrap period enforcement: create a fresh agent instance with no baseline data. Attempt to trigger an Alert. Confirm it produces only a Warning (not Alert) until 30 minutes of baseline data exist.

**Done condition:** Base class validates EvidencePackage schema correctly. Bootstrap enforcement works. Seasonal baseline structure stores and retrieves correctly.

---

### Task 2.6 — Build the four specialist agents

**What to do:**
- Build `java_agent.py`, `postgres_agent.py`, `nodejs_agent.py`, `redis_agent.py` — all inheriting from base_agent.py
- For each agent: confirm the critical error code patterns are mapped correctly to the ATLAS error taxonomy. Java: HikariCP → CONNECTION_POOL_EXHAUSTED. PostgreSQL: SQLSTATE 53300 → CONNECTION_POOL_EXHAUSTED. Redis: OOM → REDIS_OOM.
- Run each agent against its fault script in isolation. Feed the fault script output line by line and confirm the agent detects the anomaly at approximately the right point.
- Verify the EvidencePackage from each agent contains real SHAP values, a real conformal confidence interval, and all required fields.

**Done condition:** All four agents detect their respective fault scenarios. EvidencePackages pass schema validation. SHAP values are present in every package.

---

### Task 2.7 — Build the correlation engine and early warning

**What to do:**
- Build `correlation_engine.py` following the spec
- Test the cascade classification: simulate the FinanceCore scenario where both PostgreSQL agent and Java agent fire within 60 seconds. Confirm CASCADE_INCIDENT is produced.
- Test the structural check: confirm the correlation engine queries Neo4j before classifying as cascade. Test with two agents firing for services that are NOT connected in the graph — confirm it produces two ISOLATED_ANOMALY packages, not a CASCADE.
- Test the deployment-correlated flag: confirm it is added when a recent change record exists for a service in the cascade chain.
- Test early warning: add a synthetic 1.8σ reading for AuthService. Confirm the early warning scan detects it and produces an EarlyWarning signal.

**Done condition:** Cascade correctly classified when services are graph-connected. ISOLATED correctly classified when services are not connected. Deployment-correlated flag fires correctly. Early warning detects the 1.8σ synthetic signal.

---

---

## PHASE 3 — ORCHESTRATION PIPELINE
### Build each node in isolation. Test it. Connect it. Only then move to the next node.

---

### Task 3.1 — Define the state and build the pipeline skeleton

**What to do:**
- Build `state.py` with the complete TypedDict including all fields from STRUCTURE.md
- Build the skeleton of `pipeline.py`: create the StateGraph, add placeholder nodes, define all edges, compile the graph
- Verify the graph compiles without error by calling the compile method
- Confirm the interrupt is correctly configured on the human-review node

**Done condition:** Graph compiles. LangGraph shows all 7 nodes when the graph is printed. Interrupt node is correctly identified.

---

### Task 3.2 — Build and test Node 2 (ITSM Bridge) in isolation

**Why Node 2 first:** ServiceNow can be slow. Get it working early so you have time to debug it.

**What to do:**
- Build `n2_itsm.py`
- Make a real API call to your ServiceNow developer instance to create a test incident
- Confirm: ticket is created, INC number is returned in the correct format, ticket is visible in the ServiceNow incident list
- Test the retry logic: temporarily use an invalid endpoint, confirm it retries 3 times with backoff, then sets itsm_ticket_pending flag
- Test the graceful degradation: confirm the pipeline continues even when ServiceNow is unavailable

**Done condition:** Real ServiceNow ticket visible in your developer instance. INC number in correct format. Graceful degradation confirmed.

---

### Task 3.3 — Build and test Node 3 (Graph Intelligence) in isolation

**What to do:**
- Build `n3_graph.py`
- Build `neo4j_client.py` first — Node 3 depends on it
- Test each of the three Cypher queries independently with hardcoded test inputs that match the FinanceCore demo scenario
- Blast radius query with service=PaymentAPI, client_id=FINCORE_UK_001: must return TransactionDB, AuthService, NotificationService
- Deployment correlation query with affected_services=[PaymentAPI], client_id=FINCORE_UK_001: must return CHG0089234
- Historical pattern query with service=TransactionDB, anomaly_type=CONNECTION_POOL_EXHAUSTED, client_id=FINCORE_UK_001: must return INC-2024-0847
- Test the 60-second cache: run the blast radius query twice within 60 seconds. Confirm the second call does not make a new Neo4j connection (check query execution count).
- Test the client_id enforcement: attempt to run a query without client_id in the parameters. Confirm it is rejected before execution.

**Done condition:** All three queries return correct results for the FinanceCore scenario. Cache confirmed working. client_id enforcement confirmed.

---

### Task 3.4 — Build and test Node 4 (Semantic Retrieval) in isolation

**What to do:**
- Build `n4_semantic.py`
- Build `chromadb_client.py` first
- Run a similarity search using the FinanceCore fault scenario description as the query
- Confirm: INC-2024-0847 is the top result with score above 0.87
- Test the double-confirmation logic: simulate a case where INC-2024-0847 appears in both the graph results (from N3) and the vector results (from N4). Confirm it is marked double-confirmed.
- Test the cross-client fallback: temporarily use a client with an empty collection. Confirm cross-client search activates and results are flagged as cross_client_anonymised.

**Done condition:** Correct similarity search result. Double-confirmation logic works. Cross-client fallback activates correctly.

---

### Task 3.5 — Build and test Node 5 (Reasoning Engine) in isolation

**What to do:**
- Build `n5_reasoning.py` and `litellm_router.py` (if separate)
- Assemble the complete reasoning prompt with mock inputs: use the blast_radius, deployments, and historical matches you would expect from Nodes 3 and 4 for the FinanceCore scenario
- Run the Claude API call in tool_use mode with the output schema
- Confirm: all required output fields are present, recommended_action_id is connection-pool-recovery-v2, alternative_hypotheses has at least 2 entries each with evidence_for and evidence_against
- Test the fallback: set the API timeout to 1 second and confirm the pre-computed fallback loads within 200ms
- Test the LiteLLM failover: disable the Claude API key and confirm the call routes to GPT-4o
- Run the Claude call 10 times with the same prompt. Confirm valid JSON is returned all 10 times. If any run returns invalid JSON, update the schema enforcement in the prompt.

**Done condition:** 10/10 runs return valid JSON. Fallback confirmed working. LiteLLM failover confirmed working. recommended_action_id matches a real playbook.

---

### Task 3.6 — Build and test Node 6 (Confidence Scorer) in isolation

**What to do:**
- Build `n6_confidence.py` using the already-built `scorer.py` and `vetoes.py`
- Test with the FinanceCore demo scenario inputs: insert 5 historical records into decision_history with this pattern showing 4 successes and 1 failure (accuracy = 0.80). Use the N5 output from Task 3.5 as input. Manually calculate the expected composite score.
- Confirm: composite score is approximately 0.84 for FinanceCore. The PCI-DSS + business hours veto fires. The routing decision is L2_L3_ESCALATION.
- Test the cold-start veto: delete the decision_history records so count is below 5. Confirm cold-start veto fires and routing is L2_L3_ESCALATION.
- Test Class 3 blocking: use a playbook with action_class=3. Confirm routing is immediately L2_L3_ESCALATION regardless of other factors.

**Done condition:** FinanceCore scenario produces composite score ~0.84. PCI-DSS veto fires. Routing decision is correct. Cold-start veto confirmed. Class 3 blocking confirmed.

---

### Task 3.7 — Connect the full pipeline end-to-end

**What to do:**
- Connect all nodes in `pipeline.py`
- Run the full pipeline with a real CASCADE_INCIDENT package from the correlation engine
- Watch each node execute in sequence. Print the state after each node to confirm it is being updated correctly.
- Confirm the LangGraph interrupt fires at the human-review node and the graph suspends
- Simulate a human approval: call the approval API endpoint with the incident_id. Confirm the graph resumes from the interrupt point.
- Confirm the routing decision, confidence score, and ServiceNow ticket number are all in the final state.

**Done condition:** Full pipeline runs. State is correct after each node. Interrupt fires correctly. Graph resumes after simulated approval. Run 5 times — identical outcomes every time.

---

---

## PHASE 4 — EXECUTION ENGINE AND LEARNING

---

### Task 4.1 — Build the audit database

**What to do:**
- Build `audit_db.py` with the audit_log and decision_history tables
- Test write_audit_record with a complete mock record
- Test write is immutable: confirm no update method exists. Try to update a record directly — the method should not exist.
- Test export_as_csv: write 5 records and export them. Confirm all fields are present in the CSV.

**Done condition:** Audit records written and readable. CSV export works. No update method exists.

---

### Task 4.2 — Build the playbook library and connection pool recovery playbook

**What to do:**
- Build `playbook_library.py` with the registry containing both MVP playbooks
- Build `connection_pool_recovery_v2.py` following the spec in STRUCTURE.md
- For the pre-execution validation step: make a real HTTP call to the PaymentAPI health endpoint in your simulated environment. The FinanceCore demo uses a simulated Java application — set up a simple Flask or FastAPI mock that acts as PaymentAPI with a /actuator/health endpoint.
- For the action step: make a real PATCH call to update a configuration value on the mock PaymentAPI. Confirm the mock receives and processes the request.
- For success validation: connect to the log generator and confirm error rate is decreasing. The resolution signal from the playbook should cause the fault script to taper off.
- Test auto-rollback: set the success validation timeout to 10 seconds and do not trigger the resolution signal. Confirm rollback executes after 10 seconds.

**Done condition:** Pre-validation, action, success validation, and auto-rollback all confirmed working. Audit record written after both success and rollback scenarios.

---

### Task 4.3 — Build the Redis memory policy rollback playbook

**What to do:**
- Build `redis_memory_policy_rollback_v1.py`
- Set up a real Redis instance for the demo (Docker is the fastest option: `docker run -p 6379:6379 redis`). Configure it with maxmemory-policy set to noeviction to simulate the fault state.
- Test pre-execution validation: connect to Redis and read the current maxmemory-policy. Confirm it detects noeviction as the problematic state.
- Test action: run CONFIG SET maxmemory-policy allkeys-lru. Confirm it succeeds. Read the policy back with CONFIG GET to verify.
- Test the pre-validation halt: set the policy to allkeys-lru before running the playbook (policy already correct). Confirm the playbook halts with the message "assumed cause not present."

**Done condition:** Full playbook runs successfully against real Redis. Pre-validation halt confirmed. Auto-rollback tested.

---

### Task 4.4 — Build the approval token system

**What to do:**
- Build `approval_tokens.py`
- Generate a test token. Decode it manually to confirm it contains the expected fields (incident_id, approver_role, expiry).
- Validate the token: confirm valid=True is returned.
- Test expiry: generate a token with 1-second expiry, wait 2 seconds, validate it. Confirm valid=False with reason "token expired."
- Test one-time use: validate the same token twice. Confirm the second validation returns valid=False with reason "token already used."

**Done condition:** Token generation, validation, expiry, and one-time-use all confirmed working.

---

### Task 4.5 — Build the learning engine

**What to do:**
- Build `decision_history.py` (if not already built in Task 4.1 — merge with audit_db.py or keep separate per STRUCTURE.md)
- Build `recalibration.py`: write 5 decision records for the FinanceCore pattern. Run recalibration. Confirm Factor 1 is updated in the confidence engine's cache.
- Build `weight_correction.py`: write 3 L2 modification diffs all increasing maxPoolSize. Run weight correction. Confirm the adjusted default for this action on this client is now above the playbook default.
- Build `trust_progression.py`: insert 30 decision records for FinanceCore all with human_action=approved and resolution_outcome=success. Run the progression check. Confirm it produces a Stage 1 upgrade recommendation (not an automatic upgrade — a recommendation requiring SDM confirmation).

**Done condition:** Recalibration updates Factor 1. Weight correction updates the parameter default after 3 diffs. Trust progression produces a recommendation (not an automatic upgrade) after 30 successful resolutions.

---

---

## PHASE 5 — BACKEND INTEGRATION

---

### Task 5.1 — Build main.py and all API routes

**What to do:**
- Build `main.py` with all routes and WebSocket endpoints from STRUCTURE.md
- Start the server. Confirm it starts without error and all required environment variables are validated on startup.
- Test each route with a REST client (curl or Postman):
  - POST /webhook/cmdb: send a mock ServiceNow change event. Confirm it updates Neo4j.
  - POST /api/incidents/approve: send a mock approval. Confirm the LangGraph graph resumes.
  - GET /api/incidents/active: confirm it returns the current active incident list.
  - GET /api/audit: confirm it returns real audit records from SQLite.
- Test WebSocket connections: connect to WS /ws/logs/FINCORE_UK_001. Start the log generator. Confirm log lines appear in real time.

**Done condition:** Server starts successfully. All routes return expected responses. WebSocket streams real log data. Environment validation rejects start when variables are missing.

---

### Task 5.2 — Full backend integration test

**What to do:**
- Start the full backend
- Start the log generator in normal mode for FinanceCore
- Trigger the fault script
- Watch the entire pipeline execute end-to-end without any manual intervention until the human review pause
- Confirm in sequence: both agents fire, correlation engine classifies CASCADE, N1 runs, N2 creates real ServiceNow ticket, N3 returns CHG0089234, N4 returns INC-2024-0847 at correct similarity, N5 returns structured JSON with correct action, N6 produces ~0.84 score with PCI veto, graph suspends at human review
- Simulate approval through the API endpoint. Confirm execution engine runs. Confirm resolution signal returns metrics to normal. Confirm audit record written.
- Run this full test 5 times. All 5 must produce identical outcomes.

**Done condition:** 5 consecutive full backend runs with identical correct outcomes. Real ServiceNow ticket created each run. Real audit records in SQLite after each run.

---

---

## PHASE 6 — FRONTEND

---

### Task 6.1 — Build the three-panel layout and WebSocket connections

**What to do:**
- Build the three-panel layout in React
- Connect to the backend WebSocket endpoints using `useWebSocket.js`
- Confirm the left panel shows the FinanceCore and RetailMax client cards with real health status updating from the WebSocket
- Confirm the centre panel shows the real log stream scrolling in real time
- Confirm the right panel shows the activity feed with real entries from the backend

**Done condition:** All three panels show real data from the real backend. Health indicators update when the fault script is triggered.

---

### Task 6.2 — Build the ATLAS briefing card

**What to do:**
- Build `BriefingCard/` component with all six sections
- Connect each section to the real incident state data from the backend
- Test with the FinanceCore scenario running: confirm all six sections populate with real data when the orchestrator produces its output
- Confirm the SLA countdown timer counts down in real time and turns red under 5 minutes
- Confirm the historical match similarity score shows the actual ChromaDB score (e.g. 91%)
- Confirm the deployment correlation section shows the real CHG0089234 details from Neo4j

**Done condition:** All six sections show real data. SLA timer works. Similarity score is real. Deployment correlation is real.

---

### Task 6.3 — Build the graph visualisation

**What to do:**
- Build `GraphViz/` component using React Force Graph 2D
- Feed it the real graph_traversal_path from the incident state
- Implement the animation sequence: deployment node first, then edges, then affected services
- Test the animation plays correctly and follows the real traversal path
- Implement hover tooltips showing real node properties
- Create the pre-recorded animation video fallback: screen-record the animation working correctly, save as a local video file, implement the fallback logic in the component

**Done condition:** Animation plays correctly using real Neo4j data. Hover tooltips show real properties. Pre-recorded fallback plays when the component is disabled.

---

### Task 6.4 — Build the approval flow

**What to do:**
- Build `ApprovalFlow/` component with L1 and L2 views
- Implement the Reject mandatory text field: submit button disabled until 20+ characters
- Implement the Modify panel: show current values, allow editing, show diff before submit
- Implement the dual approval flow: after primary approval, show awaiting secondary state, update to complete when secondary token is validated
- Test the full approval flow against the running backend: click Approve on the briefing card, confirm the backend API call fires, confirm the LangGraph graph resumes, confirm the execution engine runs

**Done condition:** Approve, Modify, and Reject all work against the real backend. Dual approval flow shows correct states. Reject requires minimum 20 characters.

---

### Task 6.5 — Build all remaining components

**What to do:**
- Build `SHAPChart/` with real shap_feature_values from the incident state
- Build `ActivityFeed/` with real-time entries from WS /ws/activity
- Build post-resolution view: real Recharts timeseries showing metric recovery, MTTR counter stopping, Atlassian benchmark line at 43 minutes
- Build the early warning card component: shown when EarlyWarning signals are present in incident state
- Build the L1 interface view (simplified, switchable from L2 view for the demo)

**Done condition:** SHAP chart shows real values. Activity feed shows real backend events. Post-resolution chart shows real metric recovery. Early warning card appears when the backend sends the signal.

---

---

## PHASE 7 — HARDENING AND DEMO PREPARATION

---

### Task 7.1 — 20 consecutive full-system runs

**What to do:**
- Start the complete system: backend, frontend, log generator
- Run the FinanceCore demo scenario 20 consecutive times
- For each run, document: detection timing (should be T+47 ±5s), confidence score (should be ~0.84), veto that fires (PCI-DSS), INC ticket created (check in ServiceNow each time), MTTR (should be under 5 minutes), audit record written (check SQLite), Neo4j updated with new incident node
- Any run that fails or produces different output: find root cause, fix, restart the count from zero
- The count only reaches 20 when 20 consecutive runs produce identical correct outputs

**Done condition:** 20 consecutive runs documented. All 20 consistent. Zero failures.

---

### Task 7.2 — Test every fallback

**What to do:**
- Fallback 1 — LLM failure: disable the Claude API key mid-run. Confirm LiteLLM routes to GPT-4o. Re-enable Claude. Confirm it routes back.
- Fallback 2 — LLM timeout: set the timeout to 1 second. Confirm the pre-computed fallback loads in under 200ms.
- Fallback 3 — Neo4j unavailable: pause the Neo4j connection mid-run. Confirm cached results serve correctly and pipeline continues with graph_unavailable flag.
- Fallback 4 — Graph animation failure: disable the React Force Graph component. Confirm the pre-recorded video plays instead.
- Fallback 5 — WebSocket disconnection: kill the backend WebSocket server mid-demo. Confirm the frontend shows "Reconnecting..." and reconnects automatically.

**Done condition:** All 5 fallbacks tested. All 5 confirmed invisible or clearly communicated to the user. Document the test result for each fallback.

---

### Task 7.3 — Technical depth verification

**What to do:**
- For each of these judge challenges, prepare a live demonstration:
  - "Show me the actual Neo4j graph" → open Neo4j Browser, run the deployment correlation Cypher query live, show CHG0089234 in the results
  - "Show me the ChromaDB similarity search" → open Python REPL, run the similarity search manually, show the similarity score
  - "Show me the audit log" → open SQLite browser, run a SQL query on the audit_log table, show records from today's runs
  - "Show me the ServiceNow ticket" → open the ServiceNow developer instance, show the INC ticket created by ATLAS, show all fields correctly populated
  - "Show me the confidence calculation" → explain each of the four factors with the actual values from the last demo run
- Practice each of these until they can be done in under 60 seconds

**Done condition:** Each live demonstration rehearsed and confirmed working in under 60 seconds.

---

### Task 7.4 — Final demo freeze and rehearsal

**What to do:**
- At this point: no new features. No code changes.
- Rehearse the complete demo presentation 10 times
- Time each run: must be under 6 minutes
- Practice the three silence moments: 4 seconds during graph animation, 3 seconds after early warning card appears, 2 seconds after MTTR number appears
- Each team member presents the demo at least twice — not just the designated presenter
- Each team member answers the 8 judge questions from ARCHITECTURE.md without looking at notes

**Done condition:** 10 rehearsal runs completed. All under 6 minutes. Every team member can answer all 8 judge questions from memory.

---

### Task 7.5 — Day-of preparation checklist

**What to do:**
- The night before: run the complete system one final time. If it works: stop. Do not touch it.
- The morning of: charge all devices. Close all applications except the demo browser and one terminal. Disable all notifications and screen sleep.
- Arrive early: set up 30 minutes before. Run one full demo to confirm everything is working in the actual physical location (network, power, display).
- Have ready in separate browser tabs: Neo4j Browser (for live query demo), ServiceNow developer instance (for live ticket demo), SQLite browser (for live audit demo)
- Have pre-computed fallback responses confirmed loaded in the application
- Have the pre-recorded graph animation video file accessible

**Done condition:** Complete system works in the actual presentation location. All live-demo tabs open and verified. Fallbacks loaded and confirmed.

---

---

## QUICK REFERENCE — DONE CONDITIONS SUMMARY

| Phase | Task | Done Condition |
|---|---|---|
| 0 | 0.1 | All accounts created, connections verified |
| 0 | 0.2 | Repo structure created, .env gitignored |
| 0 | 0.3 | Every library imports without error |
| 0 | 0.4 | All four external connections verified with real calls |
| 1 | 1.1 | Paper graph design complete, causal chain confirmed |
| 1 | 1.2 | All 4 Neo4j verification queries pass |
| 1 | 1.3 | RetailMax graph verified, no REDIS_OOM historical matches |
| 1 | 1.4 | validate_similarity.py outputs PASS for both clients |
| 1 | 1.5 | Fault scripts produce realistic output, timing documented |
| 1 | 1.6 | Both fallback files valid, action IDs match real playbooks |
| 2 | 2.1 | All scorer/veto test cases pass |
| 2 | 2.2 | Chronos-Bolt detects synthetic spike |
| 2 | 2.3 | Isolation Forest detects anomaly with SHAP values |
| 2 | 2.4 | Conformal prediction produces valid intervals |
| 2 | 2.5 | Base agent bootstrap enforcement confirmed |
| 2 | 2.6 | All 4 agents detect their fault scenarios |
| 2 | 2.7 | Cascade/isolated classification confirmed, early warning confirmed |
| 3 | 3.1 | LangGraph graph compiles, interrupt configured |
| 3 | 3.2 | Real ServiceNow ticket created |
| 3 | 3.3 | All 3 Cypher queries correct for FinanceCore |
| 3 | 3.4 | Correct similarity result, double-confirmation works |
| 3 | 3.5 | 10/10 valid JSON runs, fallback and failover confirmed |
| 3 | 3.6 | Correct score ~0.84, PCI veto fires, routing correct |
| 3 | 3.7 | Full pipeline 5/5 identical runs, approval resumes graph |
| 4 | 4.1 | Audit records immutable, CSV export works |
| 4 | 4.2 | Full connection pool playbook including auto-rollback confirmed |
| 4 | 4.3 | Redis playbook confirmed against real Redis instance |
| 4 | 4.4 | Token expiry and one-time-use confirmed |
| 4 | 4.5 | Recalibration, weight correction, trust recommendation all confirmed |
| 5 | 5.1 | All routes work, WebSocket streams real data |
| 5 | 5.2 | 5 consecutive full backend runs, identical outcomes |
| 6 | 6.1 | Three panels show real data |
| 6 | 6.2 | All 6 briefing sections show real data |
| 6 | 6.3 | Graph animation from real data, fallback video ready |
| 6 | 6.4 | Full approval flow against real backend |
| 6 | 6.5 | All remaining components with real data |
| 7 | 7.1 | 20 consecutive full-system runs documented |
| 7 | 7.2 | All 5 fallbacks tested and confirmed |
| 7 | 7.3 | All live demonstrations rehearsed under 60 seconds |
| 7 | 7.4 | 10 presentation rehearsals, all under 6 minutes |
| 7 | 7.5 | System confirmed working in actual presentation location |

---

*PLAN.md — Every task listed. Every done condition specified. No code. Execute in order. Win.*