# ATLAS — System Architecture
## Autonomous Telemetry & Log Analysis System

---

## What ATLAS Is

ATLAS is a multi-agent AIOps platform built for managed service providers. It sits above every tool Atos already uses. It reads service topology from ServiceNow CMDB, detects failures before users notice them, reasons over a live knowledge graph to find root cause in seconds, manages the L1→L2→L3 service chain with governed automation, and gets permanently smarter from every human decision made inside it.

**The single differentiator:** Every existing AIOps product is built for one client. ATLAS is built for the company that manages hundreds of clients simultaneously — each with different stacks, compliance regimes, and trust levels — from one platform.

---

## The Five Core Flows

```
DETECT → CORRELATE → DECIDE → ACT → LEARN
```

Every component in the architecture serves one of these five flows. Nothing exists outside them.

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — CMDB-NATIVE CONFIGURATION                           │
│  ServiceNow CMDB Webhook → Thin ATLAS Config Layer             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — INGESTION & NORMALISATION                           │
│  Path A (OTel SDK) + Path B (Adapters) + Path C (API Pull)     │
│  → Unified OTel Schema → CMDB Enrichment → Event Queue         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — SPECIALIST AGENT DETECTION                          │
│  Java Agent | PostgreSQL Agent | Node.js Agent | Redis Agent   │
│  Chronos-Bolt + SHAP Isolation Forest + Conformal Prediction   │
│  → Cascade Correlation Engine → EvidencePackage                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — MASTER ORCHESTRATOR + GRAPHRAG                      │
│  7-Node LangGraph State Machine                                │
│  Node 1: Classify → Node 2: ITSM → Node 3: Graph Intel        │
│  Node 4: Semantic → Node 5: Reason → Node 6: Score → Node 7: Route │
└─────────────────────────────────────────────────────────────────┘
                              ↓
           ┌──────────────────┴──────────────────┐
           ↓                                      ↓
┌──────────────────────┐              ┌───────────────────────┐
│  AUTO-EXECUTE PATH   │              │  HUMAN REVIEW PATH    │
│  Score ≥ Threshold   │              │  Score < Threshold    │
│  Zero Vetoes         │              │  OR Any Veto Active   │
│  Class 1 Only        │              │  L1 / L2 / L3         │
└──────────────────────┘              └───────────────────────┘
           ↓                                      ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — EXECUTION ENGINE                                    │
│  Pre-Validation → Playbook Run → Success Validation            │
│  Auto-Rollback if needed → Immutable Audit Record              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6 — CONTINUOUS LEARNING ENGINE                          │
│  Decision History DB → Confidence Recalibration                │
│  Weight Correction → Trust Progression → KB Update            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 0 — CMDB-Native Configuration

### What it does
Reads service topology, CI relationships, change records, and business criticality directly from ServiceNow CMDB via **push-based Change Webhooks** — not polling. Every change record fires a webhook to ATLAS in real time. The knowledge graph is never more than seconds stale.

### The thin ATLAS config layer
Holds only what CMDB cannot provide:

| Setting | Purpose |
|---|---|
| `auto_execute_threshold` | Score required before ATLAS acts autonomously |
| `max_action_class` | Highest action class eligible for automation |
| `compliance_rules` | PCI-DSS, SOX, GDPR behavioral constraints |
| `escalation_matrix` | Who gets notified at L1/L2/L3 and via what channel |
| `sla_breach_thresholds` | Time-to-breach per service criticality |
| `change_freeze_windows` | Periods where no automation is permitted |

### Client onboarding
Point ATLAS at the client's CMDB webhook → fill thin config → done. Client 400 onboards as fast as client 2.

---

## Layer 1 — Ingestion and Normalisation

### Three ingestion paths

**Path A — Modern Apps (OTel SDK)**
Applications instrumented with OpenTelemetry emit logs, metrics, and traces directly. OTel Collector runs as sidecar or host agent. Structured JSON in OTel semantic conventions. Zero adapter needed.

**Path B — Legacy Systems (Purpose-Built Adapters)**
Each adapter is a versioned standalone Python module that reads the native format and outputs to the unified schema. Build once, deploy to every client running that technology.

Adapters for MVP: Java/Spring Boot, PostgreSQL.
Adapters specified for production: SAP ABAP, Oracle EBS, IBM Mainframe z/OS, Windows Event Log.

**Path C — Existing Observability Tools (API Pull)**
Reads from Splunk, Dynatrace, Datadog, CloudWatch via their APIs. Zero rip-and-replace. Clients keep existing investments.

### Normalisation
All three paths converge into one unified OTel schema:

```
atlas_event_id       — unique event identifier
client_id            — mandatory, tagged at creation
timestamp            — ISO-8601
source_system        — service name
source_type          — technology class
severity             — ERROR / WARN / INFO / DEBUG
error_code           — ATLAS internal taxonomy
message              — normalised description
raw_payload          — original log line preserved
deployment_id        — linked to CMDB change record if available
```

### CMDB enrichment
After normalisation, every event receives CMDB context attached before agents ever see it:
- CI class and version
- Business service it supports
- Criticality tier (P1/P2/P3/P4)
- Open change records against this service
- SLA breach threshold
- Owner team

Agents receive pre-enriched events. Zero mid-analysis lookups required.

### Multi-tenant isolation (architectural, not policy)
- Every data object tagged `client_id` at creation
- Neo4j queries: `client_id` mandatory WHERE clause
- ChromaDB: separate namespaced collections per client
- Cross-client learning: federated embedding centroids only — zero information leakage, mathematically guaranteed

---

## Layer 2 — Specialist Agent Detection

### Four agents
Each agent is a stateless Python class with three methods: `ingest(event)`, `analyze()`, `get_evidence()`.

| Agent | Monitors | Critical Patterns |
|---|---|---|
| Java/Spring Boot | Error rate, response time P95, JVM heap | HikariCP exhaustion, OOM, StackOverflow |
| PostgreSQL | Connection count, query latency, lock waits | FATAL: connection slots reserved, deadlock detected |
| Node.js | Unhandled rejection rate, request latency | Promise rejection spikes, 5xx rate |
| Redis | Memory usage, eviction rate, rejected commands | OOM, maxmemory threshold breach |

### Two-layer detection ensemble

**Layer A — Chronos-Bolt (Time-Series Foundation Model)**
- Pretrained on 100 billion real-world time-series data points
- Zero client-specific training required
- Fine-tuned on 30 minutes of normal baseline per service
- Catches gradual degradation and temporal pattern violations
- Eliminates the "where is your training data from?" challenge completely

**Layer B — SHAP-Explained Isolation Forest (Point Anomaly Detection)**
- Isolation Forest detects sudden spikes
- SHAP TreeExplainer wraps every flag with feature importance breakdown
- Output: "error_rate contributed 67%, response_time 21%, connection_count 12%"
- Every detection is explainable. Not a black box.

**Ensemble with conformal prediction**
Both model outputs combined using conformal prediction intervals. Every anomaly score carries a statistically valid confidence band. "94% confident this is anomalous" — calibrated, not claimed.

### Seasonal baselines
Same-hour same-day-of-week rolling 4-week average. Monday 9am compared to last four Monday 9ams. Eliminates false positives during predictable traffic peaks. No static thresholds anywhere.

### Three detection tiers

| Tier | Threshold | Action |
|---|---|---|
| Warning | 2σ | Elevated monitoring only |
| Alert | 3σ sustained 60s | Trigger EvidencePackage |
| Critical | Known-bad error code | Immediate flag, no wait |

### EvidencePackage schema
```
agent_id
client_id
service_name
anomaly_type
detection_confidence       — composite score
shap_feature_values        — per-metric contribution
conformal_interval         — statistical confidence band
supporting_log_samples     — 5 real log lines
preliminary_hypothesis     — domain-specific rule mapping
severity_classification    — P1 / P2 / P3
timestamp
```

### Cascade correlation engine
- 90-second window per client
- Two or more agents firing for structurally connected services (confirmed via Neo4j DEPENDS_ON, not temporal proximity alone) = `CASCADE_INCIDENT`
- Single agent alone = `ISOLATED_ANOMALY`
- CMDB change records checked at correlation time — deployment-correlated flag attached immediately if a recent change touches any service in the cascade chain

### Proactive early warning
While processing the current incident, Chronos-Bolt runs inference on all blast-radius-adjacent services. Services between 1.5σ and 2.5σ (below alert threshold but trending upward) surface as Early Warning cards. ATLAS identifies the next incident before it becomes one.

---

## Layer 3 — Master Orchestrator + GraphRAG

### LangGraph state machine
Seven nodes. State persists across the entire incident lifecycle. Nothing lost between steps regardless of how long human review takes.

#### State object
```
client_id
incident_id
evidence_packages          — from all agents
correlation_type           — CASCADE or ISOLATED
blast_radius               — from Node 3
recent_deployments         — from Node 3
historical_graph_matches   — from Node 3
semantic_matches           — from Node 4
root_cause                 — from Node 5
recommended_action_id      — from Node 5
alternative_hypotheses     — from Node 5
composite_confidence_score — from Node 6
active_veto_conditions     — from Node 6
routing_decision           — from Node 7
servicenow_ticket_id       — from Node 2
execution_status
audit_trail
mttr_seconds
```

---

### Node 1 — Incident Classifier
- Assigns ITIL priority P1-P4 based on service criticality, cascade scope, SLA breach imminence
- SLA breach countdown timer starts here
- P1 with breach under 15 minutes: immediate L2/L3 notification regardless of confidence score

---

### Node 2 — ITSM Bridge
- Real ServiceNow developer instance
- Real REST API call
- Real INC ticket created: priority, assignment group, affected CI, caller, short description all populated
- Ticket number returned to state and displayed on dashboard
- All subsequent actions update the same ticket

---

### Node 3 — Graph Intelligence

Three Cypher queries run in parallel via asyncio. Results cached 60 seconds per client.

**Query 1 — Blast Radius**
```cypher
MATCH (s:Service {name: $service_name, client_id: $client_id})
MATCH (s)-[:DEPENDS_ON*1..3]-(connected:Service)
OPTIONAL MATCH (connected)-[:COVERED_BY]->(sla:SLA)
RETURN connected.name, connected.criticality, sla.breach_threshold_minutes
```

**Query 2 — Deployment Correlation**
```cypher
MATCH (d:Deployment {client_id: $client_id})
WHERE d.timestamp > datetime() - duration('P7D')
MATCH (d)-[:MODIFIED_CONFIG_OF|DEPLOYED_TO]->(s:Service)
WHERE s.name IN $affected_services
RETURN d.change_id, d.change_description, d.deployed_by,
       d.timestamp, d.cab_risk_rating
ORDER BY d.timestamp DESC
```

**Query 3 — Historical Pattern**
```cypher
MATCH (i:Incident {client_id: $client_id})-[:AFFECTED]->(s:Service)
WHERE s.name IN $affected_services
AND i.anomaly_type = $anomaly_type
RETURN i.incident_id, i.root_cause, i.resolution,
       i.mttr_minutes, i.resolution_playbook, i.resolved_by
ORDER BY i.timestamp DESC LIMIT 5
```

Graph traversal path stored in state — every node and edge visited in order. Displayed in frontend as proof of structural reasoning, not keyword matching.

---

### Node 4 — Semantic Retrieval
- ChromaDB vector similarity search against client's incident collection
- New clients warm-started via federated embedding centroids from existing clients on same tech stack
- Top-3 historical matches returned with cosine similarity scores
- Cross-reference with Node 3 results: same incident in both = double-confirmed, maximum weight in LLM context

---

### Node 5 — Reasoning Engine

**Cerebras Inference API:**
```
Model:     llama3.1-70b (ultra-fast inference)
Fallback:  Ollama local (qwen2.5-coder:7b)
```

Cerebras provides free API access for developers with structured output support. JSON schema validation ensures consistent output format — malformed responses are structurally impossible.

**Six-step ITIL reasoning prompt:**
1. Symptom characterisation
2. Impact assessment
3. Change correlation
4. Historical match validation
5. Hypothesis ranking
6. Resolution recommendation

**Structured JSON output:**
```json
{
  "root_cause": "string",
  "confidence_factors": {},
  "recommended_action_id": "string",
  "alternative_hypotheses": [
    {
      "hypothesis": "string",
      "evidence_for": "string",
      "evidence_against": "string",
      "confidence": 0.0
    }
  ],
  "explanation_for_engineer": "string",
  "technical_evidence_summary": "string"
}
```

Pre-computed fallback for every demo scenario: real API response captured during testing, loaded in 200ms if live call exceeds 8 seconds.

---

### Node 6 — Confidence Scoring Engine

Pure Python math. Zero LLM involvement.

**Four weighted factors:**

| Factor | Weight | Source | Description |
|---|---|---|---|
| Historical Accuracy Rate | 30% | Decision History DB | Empirical success rate for this pattern/action/client triple |
| Root Cause Certainty | 25% | LLM output | Gap between top and second hypothesis, normalised 0-1 |
| Action Safety Class | 25% | Playbook library | Class 1=1.0, Class 2=0.6, Class 3=0.0 |
| Evidence Freshness | 20% | Timestamp delta | Linear decay: 1.0 at 0 min → 0.0 at 20 min |

**Action safety classes:**

| Class | Examples | Auto-execute eligible |
|---|---|---|
| Class 1 | Service restart, cache clear, config parameter tuning | Yes (if threshold met) |
| Class 2 | Service redeployment, infrastructure scaling | No — always human |
| Class 3 | Database operations, network changes, production data | Never — permanent ceiling |

**Seven hard vetoes — independent of composite score:**
Any single veto fires → human review regardless of score.

| Veto | Condition |
|---|---|
| 1 | Active change freeze window |
| 2 | Business hours + PCI-DSS or SOX flag |
| 3 | Class 3 action type |
| 4 | P1 severity |
| 5 | GDPR or compliance-sensitive data touched |
| 6 | Same action on this service within 2 hours |
| 7 | Knowledge graph stale > 24 hours |

Cold-start veto: fewer than 5 historical cases for this pattern → insufficient-precedent veto fires, routes to human, captures decision as seed data.

Every veto produces a plain-English explanation on the briefing card.

**Three routing paths:**

| Path | Conditions |
|---|---|
| Auto-execute | Score ≥ client threshold AND zero vetoes AND Class 1 action |
| L1 human review | Below threshold AND known pattern (similarity > 0.75) AND Class 1 |
| L2/L3 direct | Novel pattern OR Class 2+ OR P1 OR any veto active |

---

### Node 7 — Router
Writes final routing decision. LangGraph suspends at human-review node. State persists indefinitely. System waits for human with zero state degradation.

---

## Layer 4 — L1/L2/L3 Service Chain

### L1 Interface — speed under pressure
- Two-sentence incident summary
- Numbered step-by-step checklist
- Approve button
- Escalate to L2 button
- SLA countdown in large numbers
- Nothing else

### L2 Interface — investigation grade

Six-section briefing card:

| Section | Content |
|---|---|
| 1. Situation Summary | Affected services, business impact, SLA time remaining |
| 2. Blast Radius | Graph visualization with downstream services |
| 3. Deployment Correlation | The change that caused this, from real CMDB data |
| 4. Historical Match | Real similarity score, link to full historical record |
| 5. Alternative Hypotheses | Ranked, evidence for and against each |
| 6. Recommended Action | Playbook details, risk class, rollback availability |

Three action buttons:
- **Approve** — executes as recommended
- **Modify** — parameter editing, diff logged, default updated after 3x same direction
- **Reject** — mandatory free-text reason, parsed as correction signal, semantic playbook search triggered

### L3 Interface — institutional knowledge
Everything in L2 plus:
- Cross-client pattern panel (anonymised portfolio matches)
- Problem record draft pre-populated for one-click submission
- Change request draft if permanent fix requires infrastructure change
- Confidence debug panel: every factor score, every veto check, full reasoning chain

L3 corrections carry 3× weight in the learning engine.

### Compliance gate — dual cryptographic approval
PCI-DSS and SOX: dual sign-off required for production configuration changes.
1. Primary engineer approves on dashboard
2. Slack message fires to secondary approver with one-time signed token link
3. Secondary clicks link — single confirmation
4. Both cryptographic signatures logged in audit record with timestamps
5. Execution begins only after both confirmations

---

## Layer 5 — Execution Engine

### Playbook library
Every action is a named, versioned, pre-approved playbook. No ad-hoc commands. No LLM-generated scripts. The library is the absolute boundary of autonomous action.

**MVP playbooks:**
- `connection-pool-recovery-v2` — HikariCP pool restoration + connection manager restart
- `redis-memory-policy-rollback-v1` — maxmemory-policy revert + memory flush

Each playbook has five mandatory components:

```
1. Pre-execution validation   — target environment in expected state
2. Action execution           — parameterised, bounded, specific
3. Success validation         — key metrics monitored for recovery signal
4. Auto-rollback              — fires automatically if timeout exceeded
5. Immutable audit record     — written regardless of outcome
```

### Severity-tiered execution

| Priority | Approval required | Notes |
|---|---|---|
| P3 | None (auto-execute) | When score + veto conditions met |
| P2 | One-click (dashboard or Slack) | Single approver |
| P1 | Dual cryptographic sign-off | Two approvers, both timestamps |

### SLA breach interrupt
Background timer from incident classification:
- Breach − 10 min: forced escalation to next tier
- Breach − 5 min: SDM notification fires
- Breach − 0: breach event logged, compliance report generated

### MTTR benchmark
Atlassian 2024 State of Incident Management Report: 43-minute median MTTR for P2 enterprise IT incidents. Third-party published. Used as comparison benchmark.

---

## Layer 6 — Continuous Learning Engine

### Decision History Database

One record per incident resolution:

```
client_id
anomaly_type
service_class
recommended_action_id
confidence_score_at_decision
routing_tier               — L1 / L2 / L3 / auto
human_action               — approved / modified / rejected / escalated
modification_diff          — what parameter changed and in what direction
rejection_reason           — free text, parsed for weight corrections
resolution_outcome         — success / failure / partial
actual_mttr
recurrence_within_48h      — boolean: symptomatic fix detection
```

Recurrence within 48 hours = fix was symptomatic not causal. Recorded as negative outcome even if immediate metrics recovered.

### Confidence recalibration
After every confirmed resolution: empirical accuracy rate for that pattern/action/client triple recalculated from all matching Decision History records. Flows back into Factor 1 immediately. The next identical incident has a more accurate confidence score.

### Weight correction
- L2 modifications: same parameter direction 3+ times on same client → ATLAS updates default for that action on that client
- L3 rejections: reason text parsed → rejected hypothesis type weighted down, substituted hypothesis weighted up

### Trust progression

Evidence-gated stages. Non-negotiable thresholds.

| Stage | Name | Requirement |
|---|---|---|
| 0 | Observation | Default for new clients |
| 1 | L1 Assistance | 30 incidents + >80% confirmed correct reasoning |
| 2 | L1 Automation | 30 more incidents + >85% auto-resolution success |
| 3 | L2 Assistance | Demonstrated Stage 2 accuracy |
| 4 | L2 Automation | SDM explicit enablement required |
| — | Class 3 ceiling | Never auto-executes. Permanent. Non-configurable. |

Trust level exposed via read-only API endpoint. Clients integrate it into their own dashboards.

### Knowledge base update after every resolution
- New Neo4j Incident node created with full resolution details
- New ChromaDB embedding stored
- Problem record draft generated if recurrence risk high
- Change request draft generated if permanent fix requires infrastructure change

---

## The Five Outputs

| Output | Description |
|---|---|
| A — Auto-Resolved Incident | Service restored, metrics confirmed, ticket closed, KB updated |
| B — Human Approval Briefing | Six-section ITIL briefing, complete reasoning, complete evidence |
| C — Immutable Audit Log | Every action, approver, reasoning chain, outcome. Exportable JSON/CSV/PDF |
| D — Client Transparency Portal | Real-time status, SLA, MTTR trends, trust level, read-only API |
| E — Knowledge Base Record | New Neo4j node, new ChromaDB embedding, problem record, change request |

---

## Complete Tech Stack

| Component | Technology | Reason |
|---|---|---|
| Backend | FastAPI Python 3.11 | Async, WebSocket, production-grade |
| Orchestration | LangGraph 0.2+ | State persistence, human-in-loop native |
| LLM Primary | Cerebras llama3.1-70b | Free API, ultra-fast inference |
| LLM Fallback | Ollama local (qwen2.5-coder) | Zero-cost, offline capable |
| Time-Series Detection | Chronos-Bolt (HuggingFace) | Pretrained 100B points, zero cold-start |
| Point Anomaly | Isolation Forest + SHAP | Explainable, production-proven |
| Uncertainty | Conformal Prediction | Statistically valid confidence bounds |
| Knowledge Graph | Neo4j Aura Serverless | Real-time CMDB sync, cached queries |
| Vector Store | ChromaDB namespaced | Zero dependency, federated warm-start |
| CMDB Sync | ServiceNow Change Webhook | Push-based, seconds latency |
| ITSM | ServiceNow Developer Instance | Real tickets, real API, real INC format |
| Approval | Cryptographic one-time tokens | Compliance-grade dual sign-off |
| Frontend | React 18 + Tailwind + Framer Motion | Clean, animated, professional |
| Graph Viz | React Force Graph 2D | Interactive traversal animation |
| Charts | Recharts + SHAP waterfall | Real data, explainable detection |
| Audit Store | SQLite production schema | Simple, exportable, migration-ready |
| MTTR Benchmark | Atlassian 2024 Report | Third-party validated |

---

## Neo4j Graph Schema

### Node types
```
Service        {name, client_id, tech_type, version, criticality, namespace}
Infrastructure {name, client_id, type, provider, region}
Deployment     {change_id, client_id, deployed_by, change_description,
                timestamp, cab_approved_by, risk_rating}
Incident       {incident_id, client_id, title, occurred_at, root_cause,
                resolution, mttr_minutes, resolved_by, playbook_used}
Problem        {problem_id, client_id, title, root_cause, permanent_fix}
SLA            {service_name, client_id, breach_threshold_minutes, tier}
Team           {name, client_id, tier, contact}
ComplianceRule {framework, client_id, rule_description, enforcement}
```

### Relationship types
```
DEPENDS_ON          (Service → Service, weight: criticality)
HOSTED_ON           (Service → Infrastructure)
MODIFIED_CONFIG_OF  (Deployment → Service)
DEPLOYED_TO         (Deployment → Infrastructure)
AFFECTED            (Incident → Service)
CAUSED_BY           (Incident → Deployment)
RESOLVED_BY         (Incident → Resolution)
COVERED_BY          (Service → SLA)
OWNED_BY            (Service → Team)
GOVERNED_BY         (Service → ComplianceRule)
```

---

## Repository Structure

```
atlas/
├── backend/
│   ├── main.py                    # FastAPI app, WebSocket endpoints
│   ├── config/
│   │   └── client_registry.py    # Thin ATLAS config per client
│   ├── ingestion/
│   │   ├── normaliser.py         # OTel schema normalisation
│   │   ├── cmdb_enricher.py      # CMDB context attachment
│   │   ├── adapters/
│   │   │   ├── java_adapter.py
│   │   │   └── postgres_adapter.py
│   │   └── event_queue.py        # Async event queue
│   ├── agents/
│   │   ├── base_agent.py         # Abstract base
│   │   ├── java_agent.py
│   │   ├── postgres_agent.py
│   │   ├── nodejs_agent.py
│   │   ├── redis_agent.py
│   │   ├── detection/
│   │   │   ├── chronos_detector.py
│   │   │   ├── isolation_forest.py
│   │   │   └── conformal.py
│   │   └── correlation_engine.py
│   ├── orchestrator/
│   │   ├── state.py              # LangGraph state TypedDict
│   │   ├── pipeline.py           # 7-node LangGraph graph
│   │   ├── nodes/
│   │   │   ├── n1_classifier.py
│   │   │   ├── n2_itsm.py
│   │   │   ├── n3_graph.py
│   │   │   ├── n4_semantic.py
│   │   │   ├── n5_reasoning.py
│   │   │   ├── n6_confidence.py
│   │   │   └── n7_router.py
│   │   └── confidence/
│   │       ├── scorer.py         # Pure Python confidence math
│   │       └── vetoes.py         # 7 hard veto conditions
│   ├── execution/
│   │   ├── playbook_library.py
│   │   ├── playbooks/
│   │   │   ├── connection_pool_recovery_v2.py
│   │   │   └── redis_memory_policy_rollback_v1.py
│   │   └── approval_tokens.py   # Cryptographic token generation
│   ├── learning/
│   │   ├── decision_history.py   # SQLite Decision History DB
│   │   ├── recalibration.py      # Factor 1 update after resolution
│   │   ├── weight_correction.py  # L2 diff accumulation, L3 override
│   │   └── trust_progression.py  # Stage gate evaluation
│   └── database/
│       ├── neo4j_client.py
│       ├── chromadb_client.py
│       └── audit_db.py           # SQLite audit records
├── data/
│   ├── seed/
│   │   ├── financecore_graph.cypher
│   │   ├── retailmax_graph.cypher
│   │   └── historical_incidents.json
│   └── fault_scripts/
│       ├── financecore_cascade.py
│       └── retailmax_redis_oom.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ClientRoster/
│   │   │   ├── BriefingCard/
│   │   │   ├── GraphViz/         # React Force Graph 2D
│   │   │   ├── ActivityFeed/
│   │   │   ├── SHAPChart/
│   │   │   ├── ApprovalFlow/
│   │   │   ├── L1Interface/
│   │   │   ├── L2Interface/
│   │   │   └── EarlyWarning/
│   │   └── hooks/
│   │       ├── useWebSocket.js
│   │       └── useIncident.js
└── scripts/
    ├── seed_neo4j.py
    ├── seed_chromadb.py
    └── validate_similarity.py
```

---

## Data Flow Diagram

```
ServiceNow CMDB
      │ Webhook (push, real-time)
      ↓
ATLAS Config Layer
      │
      ├── Application Logs (OTel SDK)
      ├── Legacy Logs (Adapters)        → Normaliser → CMDB Enricher → Event Queue
      └── Existing Tools (API Pull)
                                                              │
                              ┌───────────────────────────────┤
                              │                               │
                         Java Agent                    PostgreSQL Agent
                         Node.js Agent                 Redis Agent
                              │                               │
                              └────────────┬──────────────────┘
                                           │
                                  Correlation Engine
                                  (90s window, Neo4j structural check)
                                           │
                                    CASCADE_INCIDENT
                                           │
                              ┌────────────▼────────────┐
                              │   LangGraph Pipeline    │
                              │  N1→N2→N3→N4→N5→N6→N7  │
                              └────────────┬────────────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         ↓                 ↓                  ↓
                   Auto-Execute       L1 Review          L2/L3 Review
                         │                │                   │
                         └────────────────┴───────────────────┘
                                          │
                                   Execution Engine
                                          │
                              ┌───────────┴───────────┐
                              ↓                       ↓
                         Resolved                Auto-Rollback
                              │
                    ┌─────────┴─────────┐
                    ↓                   ↓
               Audit Record        Learning Update
               Neo4j Update        ChromaDB Update
               Portal Update       Confidence Recalibration
```

---

*ATLAS Architecture v3.0 — Built to win.*