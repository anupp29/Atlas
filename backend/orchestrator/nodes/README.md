# nodes

The seven LangGraph nodes. Each node is an async function that receives the full `AtlasState`, does one thing, and returns a dict slice of fields to update.

---

## Files

| File | Node | What it does |
|------|------|-------------|
| `n1_classifier.py` | N1 | Assigns ITIL priority P1-P4. Starts SLA breach countdown. Generates situation summary. Notifies SDM immediately for P1. |
| `n2_itsm.py` | N2 | Creates a real ServiceNow incident ticket via REST API. 3 retries with exponential backoff. Degrades gracefully if ServiceNow is unavailable. |
| `n3_graph.py` | N3 | Runs three Cypher queries in parallel: blast radius, deployment correlation, historical pattern. Builds traversal path for frontend animation. |
| `n4_semantic.py` | N4 | ChromaDB similarity search. Cross-references with N3 results for double-confirmation. Falls back to cross-client federated search on cold start. |
| `n5_reasoning.py` | N5 | Calls the internal LLM endpoint with 6-step ITIL reasoning context. Falls back to pre-computed response on timeout. Validates output schema. |
| `n6_confidence.py` | N6 | Calculates composite confidence score (4 factors). Runs all 8 vetoes. Determines routing decision. |
| `n7_router.py` | N7 | Sends Slack briefing card for human review paths. Raises `NodeInterrupt` to suspend the graph. Continues directly for AUTO_EXECUTE. |

---

## Node contract

Every node function:
- Is `async`
- Receives the full `AtlasState`
- Returns a `dict[str, Any]` slice of fields to update
- Never mutates the state object in place
- Calls `append_audit_entry()` to add to the audit trail
- Handles its own failures gracefully (logs and continues with safe defaults)

---

## N1 - Incident Classifier

Priority rules based on service criticality from CMDB and cascade scope:
- P1 service + cascade -> P1 incident
- P1 service alone -> P2 incident
- P2 services in cascade -> P2 incident
- P2 service isolated -> P3 incident

P1 incidents trigger immediate SDM notification via HTTP regardless of confidence score. SLA breach countdown starts here using thresholds from client config.

---

## N2 - ITSM Bridge

Makes a real POST to `{SERVICENOW_INSTANCE_URL}/api/now/table/incident`. Maps ATLAS priority to ServiceNow priority (P1->1, P2->2, etc.). Maps anomaly types to ServiceNow categories. Returns the INC number (e.g. INC0089247) to state.

If ServiceNow is unavailable after 3 retries, sets `itsm_ticket_pending=True` and continues. The pipeline never blocks on ITSM.

---

## N3 - Graph Intelligence

Three Cypher queries run in parallel via `asyncio.gather()`:

1. Blast radius: traverse DEPENDS_ON up to 3 hops from affected service
2. Deployment correlation: find CMDB change records from last 7 days touching affected services
3. Historical pattern: find past incidents with same service and anomaly type

Results are cached 60 seconds per client by the Neo4j client. If Neo4j is unavailable, sets `graph_unavailable=True` and continues with empty lists.

---

## N4 - Semantic Retrieval

Builds a query text from service names, anomaly types, preliminary hypotheses, and first log sample. Searches the client's ChromaDB collection. Filters results below 0.50 similarity.

Double-confirmation: if an incident appears in both N3 graph results and N4 vector results, it is marked `double_confirmed=True` with `context_weight="maximum"`. This carries the highest weight in the N5 reasoning prompt.

Cold start (fewer than 5 incidents in collection): supplements with cross-client federated search, results flagged as `source="cross_client_anonymised"`.

---

## N5 - Reasoning Engine

Assembles the full context payload and POSTs to `ATLAS_LLM_ENDPOINT` with an 8-second timeout. The payload includes evidence summary, blast radius, deployments, historical matches, semantic matches, and compliance profile.

Fallback chain:
1. Live LLM call (8s timeout)
2. Pre-computed fallback from `data/fallbacks/{client_id}_incident_response.json` (loads in <200ms)
3. If both fail: sets `llm_unavailable=True`, forces `routing_decision="L2_L3_ESCALATION"`

Output validation: checks all required fields, validates `recommended_action_id` against the playbook library, checks `explanation_for_engineer` is at least 50 characters.

---

## N6 - Confidence Scoring

Pure Python. Zero LLM. Deterministic.

Reads historical accuracy from the recalibration cache (no I/O). Calculates all four factors. Runs all 8 vetoes. Determines routing.

Class 3 check runs first. If it fires, routing is immediately `L2_L3_ESCALATION` and other factors are still calculated for the audit record.

---

## N7 - Router

For `AUTO_EXECUTE`: returns immediately, pipeline continues to execution.

For human review paths:
1. Sends Slack briefing card to the appropriate tier channel
2. Raises `NodeInterrupt` with the full incident context embedded in the payload
3. LangGraph suspends here, state persists in SQLite checkpointer

The graph resumes when `resume_after_approval()` is called from the API endpoint.
