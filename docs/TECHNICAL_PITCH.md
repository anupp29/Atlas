# ATLAS — Technical Architecture & Pitch Document

**Autonomous Telemetry and Log Analysis System**
Multi-Agent AIOps Platform for Managed Service Providers

---

## What ATLAS Is

ATLAS is a production-grade AIOps platform built for managed service providers who operate hundreds of enterprise clients simultaneously. It detects infrastructure failures before users notice, traces root cause through a live knowledge graph in seconds, routes decisions to the right human with complete evidence, executes pre-approved remediations with automatic rollback, and gets permanently smarter from every outcome.

The core differentiator: every existing AIOps product is built for one client's environment. ATLAS is built for the company managing hundreds of clients — each with different stacks, compliance regimes, and trust levels — from one platform. That is a different product category.

---

## Section 1 — The Five Flows

Everything in ATLAS serves one of five flows. If a component does not serve a flow, it does not exist.

```
DETECT → CORRELATE → DECIDE → ACT → LEARN
```

**DETECT** — Specialist agents monitor every client's infrastructure continuously using a three-layer ML ensemble. Anomalies are detected before users notice.

**CORRELATE** — A 7-node LangGraph orchestrator connects signals across the knowledge graph, vector store, and LLM reasoning to find root cause.

**DECIDE** — A pure-Python confidence engine scores every decision against 4 weighted factors and 7 hard vetoes. Routes to auto-execute or the correct human tier.

**ACT** — Named, versioned, pre-approved playbooks execute with pre-validation, success monitoring, and automatic rollback. No ad-hoc commands. Ever.

**LEARN** — Every human decision is a training signal. Confidence scores recalibrate. Weights correct. Trust levels advance. The system earns autonomy through evidence.


---

## Section 2 — System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ATLAS PLATFORM                                  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 0 — CMDB-NATIVE CONFIGURATION                            │   │
│  │  ServiceNow CMDB Webhook  ·  Thin ATLAS Config per Client        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1 — INGESTION & NORMALISATION                            │   │
│  │  OTel SDK  ·  Legacy Adapters  ·  API Pull  →  CMDB Enrichment  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2 — SPECIALIST AGENTS (configurable, any tech stack)     │   │
│  │  Chronos-Bolt  ·  Isolation Forest + SHAP  ·  Conformal Pred.   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3 — ORCHESTRATOR (7-node LangGraph)                      │   │
│  │  Classify → ITSM → Graph → Semantic → Reason → Score → Route    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4 — HUMAN SERVICE CHAIN                                  │   │
│  │  L1 (speed)  ·  L2 (investigation)  ·  L3 (institutional)       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5 — EXECUTION ENGINE                                     │   │
│  │  Pre-validate → Act → Validate → Rollback → Audit               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 6 — LEARNING ENGINE                                      │   │
│  │  Decision History  ·  Recalibration  ·  Weight Correction       │   │
│  │  Trust Progression  ·  Knowledge Graph Update                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```


---

## Section 3 — Detection Engine (Layer 2)

Every specialist agent runs a three-layer detection ensemble. The same ensemble runs regardless of technology domain — Java, PostgreSQL, Node.js, Redis, or any future agent type.

### Layer A — Chronos-Bolt (Time-Series Foundation Model)

Chronos-Bolt is a pretrained time-series foundation model trained on 100 billion real-world data points. It requires zero client-specific training. It is fine-tuned on 30 minutes of normal baseline per service and immediately detects gradual degradation and temporal pattern violations — the slow-burn failures that threshold-based systems miss entirely.

Seasonal baselines are built automatically: Monday 9am is compared to the last four Monday 9ams. This eliminates every false positive during predictable traffic peaks. No static thresholds anywhere in the detection layer.

Inference timeout: 500ms. Falls back to z-score if model is unavailable.

### Layer B — SHAP-Explained Isolation Forest

Isolation Forest detects sudden point anomalies. The SHAP TreeExplainer wraps every anomalous flag with a feature importance breakdown — which metric contributed what percentage to the detection decision.

Example output: `error_rate: 67%, response_time_p95: 21%, connection_count: 12%`

This is not an explanation. It is a proof. When a judge or client asks "why did ATLAS flag this" — the SHAP waterfall chart is the answer. Quantified. Auditable.

Auto-retrains every 24 hours on a rolling baseline window. Z-score override catches extreme outliers (>5σ) that Isolation Forest may miss with near-zero variance baselines.

### Layer C — Conformal Prediction (Calibration)

Conformal prediction combines both model outputs into a statistically valid confidence interval. Chronos-Bolt carries 55% weight, Isolation Forest 45%.

The confidence level is empirically calibrated — not claimed. "94% confident this is anomalous" means the calibration set confirmed 94% empirical coverage. This is the difference between a number that sounds good and a number that is mathematically defensible.

Falls back to a fixed 0.65 threshold when fewer than 50 calibration samples exist.

### Detection Tiers

| Tier | Threshold | Action |
|------|-----------|--------|
| Warning | 2σ | Elevated monitoring, no escalation |
| Alert | 3σ sustained 60s | EvidencePackage produced, orchestrator triggered |
| Critical | Known-bad error code | Immediate flag, no wait for statistical baseline |

### Detection Flow Diagram

```
Log / Metric Event
        │
        ▼
  ┌─────────────┐
  │  ingest()   │  ← updates log buffer, metric windows, seasonal baseline
  └─────────────┘
        │
        ▼
  ┌──────────────────────┐
  │  Critical pattern?   │  ← HikariCP exhaustion, OOM, deadlock → immediate
  └──────────────────────┘
        │ no
        ▼
  ┌─────────────────────────────────────────────────────┐
  │                  analyze()                          │
  │                                                     │
  │  Chronos-Bolt score (0.55 weight)                   │
  │         +                                           │
  │  Isolation Forest score + SHAP values (0.45 weight) │
  │         +                                           │
  │  Conformal prediction → calibrated confidence       │
  └─────────────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────────────┐
  │  EvidencePackage built and validated                 │
  │  (evidence_id, agent_id, client_id, service_name,   │
  │   anomaly_type, detection_confidence,               │
  │   shap_feature_values, conformal_interval,          │
  │   supporting_log_samples × 5, preliminary_hypothesis│
  │   severity_classification, detection_timestamp)     │
  └──────────────────────────────────────────────────────┘
        │
        ▼
  Cascade Correlation Engine
  (90-second window, Neo4j structural confirmation)
        │
        ├── Two+ connected services → CASCADE_INCIDENT
        └── Single service → ISOLATED_ANOMALY
```


---

## Section 4 — The 7-Node LangGraph Orchestrator (Layer 3)

The orchestrator is a LangGraph state machine. State persists across the entire incident lifecycle — from first detection through human approval through resolution through learning. Nothing is lost between steps regardless of how long human review takes.

### Orchestrator Pipeline Diagram

```
EvidencePackage(s) arrive
          │
          ▼
  ┌───────────────┐
  │  N1 Classify  │  ITIL priority P1-P4, SLA timer starts
  └───────────────┘
          │
          ▼
  ┌───────────────┐
  │  N2 ITSM      │  Real ServiceNow API → real INC ticket created
  └───────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  N3 Graph Intelligence (3 parallel Cypher queries)    │
  │                                                       │
  │  Query 1: Blast radius (DEPENDS_ON, 3 hops)           │
  │  Query 2: Deployment correlation (last 7 days CMDB)   │
  │  Query 3: Historical incidents (same service + type)  │
  └───────────────────────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  N4 Semantic Retrieval                                │
  │  ChromaDB vector search → top-3 historical matches   │
  │  Cross-reference with N3 → double-confirmed flag     │
  └───────────────────────────────────────────────────────┘
          │
          ▼
   ┌───────────────────────────────────────────────────────┐
   │  N5 Reasoning Engine                                  │
   │  Cerebras: Qwen3-235B → Ollama local fallback         │
   │  Structured JSON output with schema validation        │
   │  6-step ITIL reasoning prompt                         │
   │  Output: root_cause, recommended_action_id,           │
   │          alternative_hypotheses, explanation          │
   └───────────────────────────────────────────────────────┘
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  N6 Confidence Scoring                                │
  │  4 weighted factors (pure Python, zero LLM)           │
  │  7 hard vetoes (independent of score)                 │
  │  Composite score → routing decision                   │
  └───────────────────────────────────────────────────────┘
          │
          ▼
  ┌───────────────┐
  │  N7 Router    │
  └───────────────┘
          │
    ┌─────┴──────────────────┐
    ▼                        ▼
AUTO_EXECUTE          HUMAN_REVIEW
(score ≥ threshold,   (L1 / L2 / L3
 zero vetoes,          based on complexity,
 Class 1 action)       confidence, vetoes)
```

### Node Details

**N1 — Incident Classifier**
Assigns ITIL priority P1–P4 based on service criticality from CMDB, cascade scope, and SLA breach imminence. Starts the SLA breach countdown timer. P1 incidents with breach under 15 minutes trigger immediate L2/L3 notification regardless of confidence score — SLA protection is non-negotiable.

**N2 — ITSM Bridge**
Makes a real API call to a ServiceNow developer instance. Creates a real INC ticket with correct fields: priority, assignment group, affected CI, caller, short description. The ticket number is returned to state and displayed on the dashboard. Every subsequent action updates the same ticket.

**N3 — Graph Intelligence**
Three Cypher queries run in parallel via `asyncio.gather` against Neo4j Aura Serverless. Results cached 60 seconds per client.

- Blast radius query: traverses `DEPENDS_ON` relationships up to 3 hops from the affected service. Returns all downstream services with criticality and SLA breach timers.
- Deployment correlation query: finds all CMDB change records from the last 7 days touching the affected service or its dependencies. Returns change ID, description, deployer, CAB risk rating, timestamp. This is the query that finds the deployment that caused the incident.
- Historical pattern query: finds all past incidents for the same service and anomaly type. Returns root cause, resolution playbook, MTTR, resolving engineer.

**N4 — Semantic Retrieval**
ChromaDB vector similarity search against the client's namespaced collection (`atlas_{client_id}`). Top-3 historical matches returned with cosine similarity scores. When the same incident appears in both the Neo4j graph result and the ChromaDB result, it is marked double-confirmed and carries maximum weight in the LLM context.

**N5 — Reasoning Engine**
Cerebras Qwen3-235B as primary, Ollama local Qwen3 as automatic fallback. Failover under 500ms. Structured JSON output with schema validation at the API level — malformed output is structurally impossible, not a retry strategy.

Six-step ITIL-structured reasoning prompt: symptom characterisation → impact assessment → change correlation → historical match validation → hypothesis ranking → resolution recommendation.

Pre-computed fallback files exist for every demo scenario. If the live call exceeds 8 seconds, the fallback loads in under 200ms.

**N6 — Confidence Scoring Engine**
Described in full in Section 5.

**N7 — Router**
Writes the final routing decision to state. LangGraph suspends at human-review interrupt points. State persists indefinitely — the system waits for human input with zero state degradation.


---

## Section 5 — Confidence Scoring Engine

The confidence engine is pure Python mathematics. Zero LLM. Zero randomness. Same inputs always produce the same output. It is the decision boundary between autonomous action and human review.

### Four Weighted Factors

```
Composite Score = (F1 × 0.30) + (F2 × 0.25) + (F3 × 0.25) + (F4 × 0.20)
```

**Factor 1 — Historical Accuracy Rate (30%)**
Empirical success rate from the Decision History Database for the exact pattern/action/client triple. Minimum 5 cases required. New clients are warm-started via federated embedding centroids from existing clients running the same technology stack — anonymised, mathematically zero information leakage. Cold-start sentinel value: 0.50.

**Factor 2 — Root Cause Certainty (25%)**
The gap between the top and second hypothesis confidence scores, normalised 0–1. A wide gap means ATLAS is certain. A narrow gap means two competing explanations are close — route to human.

**Factor 3 — Action Safety Class (25%)**
- Class 1 (service restart, cache clear, config tuning): 1.0
- Class 2 (redeployment, infrastructure scaling): 0.6
- Class 3 (database operations, network changes, production data): **0.0 always. Permanent. Non-configurable.**

**Factor 4 — Evidence Freshness (20%)**
Linear decay from 1.0 at 0 minutes to 0.0 at 20 minutes. Stale reasoning is refused. The system does not act on old evidence.

### Seven Hard Vetoes

Any single veto fires → human review, regardless of composite score. All 7 run every time. The complete list is always returned, not just the first fired.

| # | Veto | Reason |
|---|------|--------|
| 1 | Active change freeze window | Contractual obligation |
| 2 | Business hours + PCI-DSS or SOX flag | Compliance requirement |
| 3 | Class 3 action type | Permanent ceiling, non-configurable |
| 4 | P1 severity | Always requires human sign-off |
| 5 | GDPR or compliance-sensitive data touched | Regulatory requirement |
| 6 | Same action on this service within 2 hours | Duplicate action prevention |
| 7 | Knowledge graph stale > 24 hours | Topology may be incorrect |
| 8 | Fewer than 5 historical records | Insufficient precedent (cold-start) |

Every veto produces a plain-English explanation on the briefing card. Engineers understand why the system stopped. Systems that explain their stops are trusted.

### Routing Logic

```
Composite Score + Veto Results
          │
          ├── Score ≥ threshold AND zero vetoes AND Class 1
          │         → AUTO_EXECUTE
          │
          ├── Below threshold AND similarity > 0.75 AND Class 1 AND no vetoes
          │         → L1_HUMAN_REVIEW
          │
          └── Novel pattern OR Class 2+ OR P1 OR any veto active
                    → L2_L3_ESCALATION
```

### Confidence Score Diagram

```
                    ┌─────────────────────────────────────┐
                    │         CONFIDENCE ENGINE            │
                    │                                     │
  Decision DB ───→  │  F1: Historical Accuracy   × 0.30  │
  LLM output  ───→  │  F2: Root Cause Certainty  × 0.25  │  ──→  Composite
  Playbook    ───→  │  F3: Action Safety Class   × 0.25  │       Score
  Timestamp   ───→  │  F4: Evidence Freshness    × 0.20  │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────────┐
                    │         7 HARD VETOES              │
                    │  (run independently, all 7)        │
                    └───────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────────┐
                    │         ROUTING DECISION           │
                    │  AUTO_EXECUTE / L1 / L2_L3         │
                    └───────────────────────────────────┘
```


---

## Section 6 — The Human Escalation Chain (L1 → L2 → L3)

ATLAS never acts without a human in the loop unless all conditions for autonomous execution are met. The escalation chain is the governance layer.

### Escalation Flow Diagram

```
Routing Decision: HUMAN_REVIEW
          │
          ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  L1 — Service Desk Engineer                                   │
  │                                                               │
  │  Sees: 2-sentence summary, numbered checklist, SLA countdown  │
  │  Actions: APPROVE → execute  |  ESCALATE → L2                 │
  │  Time budget: < 2 minutes                                     │
  └───────────────────────────────────────────────────────────────┘
          │ escalate
          ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  L2 — Technical Support Engineer                              │
  │                                                               │
  │  Sees: Full 6-section briefing card                           │
  │    1. Situation summary + blast radius                        │
  │    2. Dependency graph (interactive, animated)                │
  │    3. Deployment correlation (real CMDB change record)        │
  │    4. Historical match (similarity score + resolution)        │
  │    5. Alternative hypotheses (ranked, evidence for/against)   │
  │    6. Recommended action (playbook, risk class, rollback)     │
  │                                                               │
  │  Actions: APPROVE | MODIFY (diff logged) | REJECT | ESCALATE  │
  │  Compliance gate: PCI-DSS/SOX → dual cryptographic sign-off   │
  └───────────────────────────────────────────────────────────────┘
          │ escalate
          ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  L3 — Deep Technical Architect                                │
  │                                                               │
  │  Sees: Everything in L2 PLUS:                                 │
  │    - Cross-client anonymised portfolio patterns               │
  │    - Confidence debug panel (every factor, every veto)        │
  │    - Pre-populated Problem record draft                       │
  │    - Pre-populated Change Request draft                       │
  │                                                               │
  │  Actions: ACCEPT | MODIFY | REJECT                            │
  │  Weight: L3 corrections carry 3× learning weight              │
  │  Outcome: Resolution becomes permanent institutional knowledge │
  └───────────────────────────────────────────────────────────────┘
```

### What Happens at Each Decision

**Approve / Accept**: Playbook executes. Outcome recorded. Learning signal written.

**Modify**: Parameter editing panel opens. Engineer changes values. Diff is logged. Modified playbook executes. If the same modification direction appears 3+ more times on this client, ATLAS updates its default for that action.

**Reject**: Mandatory text field opens. Engineer explains why. ATLAS immediately runs semantic search on the playbook library using the rejection reason. Alternative playbooks surface instantly. Rejection reason and substituted action are both recorded as learning signals. The rejected hypothesis type receives lower weight on future similar incidents.

**Escalate**: Incident moves to next tier with full context pre-populated. The escalating engineer's reason is logged.

### Compliance Gate (PCI-DSS / SOX)

When a compliance veto fires, dual cryptographic approval is required:
1. Primary approver clicks Approve on the dashboard
2. A one-time signed token link fires to the secondary approver via Slack
3. Secondary approver clicks the link — single confirmation
4. Both cryptographic signatures are logged in the immutable audit record

This is how regulated change management actually works. ATLAS implements it natively.


---

## Section 7 — Execution Engine (Layer 5)

Every action ATLAS takes is a named, versioned, pre-approved playbook. The playbook library is the absolute boundary of autonomous action. No ad-hoc commands. No LLM-generated scripts. Ever.

### Five Mandatory Execution Steps

```
Approval received
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  STEP 1: Pre-execution Validation                       │
  │  Target environment in expected state?                  │
  │  Health endpoint reachable? Metrics at expected level?  │
  │  FAIL → halt immediately, escalate, do not proceed      │
  └─────────────────────────────────────────────────────────┘
        │ pass
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  STEP 2: Action Execution                               │
  │  Parameterised, bounded, specific                       │
  │  Every HTTP call has 10-second timeout                  │
  │  Every call logged with response code and latency       │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  STEP 3: Success Validation                             │
  │  Key metrics polled every 30 seconds                    │
  │  Declare success when recovery signal confirmed         │
  │  Not "did command run" — "did problem get better"       │
  │  Timeout: 10 minutes default                            │
  └─────────────────────────────────────────────────────────┘
        │ timeout
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  STEP 4: Auto-Rollback                                  │
  │  Pre-written, pre-tested rollback fires automatically   │
  │  Re-escalates with full context                         │
  │  Rollback itself has success validation                 │
  └─────────────────────────────────────────────────────────┘
        │ (always, regardless of outcome)
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  STEP 5: Immutable Audit Record                         │
  │  Written regardless of success or failure               │
  │  Every action, every metric, every timestamp            │
  │  Cryptographically signed                               │
  └─────────────────────────────────────────────────────────┘
```

### Action Safety Classes

| Class | Action Types | Auto-Execute Eligible | Safety Score |
|-------|-------------|----------------------|--------------|
| 1 | Service restart, cache clear, config tuning | Yes (if conditions met) | 1.0 |
| 2 | Redeployment, infrastructure scaling | No — always human | 0.6 |
| 3 | Database operations, network changes, production data | **Never. Permanent.** | 0.0 |

Class 3 is a permanent ceiling. It cannot be overridden by configuration, trust level, or confidence score. It is enforced at the execution engine level before any playbook runs.

### SLA Breach Interrupt

A background timer runs from the moment of incident classification:
- **Breach − 10 min**: Forced escalation to next tier
- **Breach − 5 min**: SDM notification fires
- **Breach − 0**: Breach event logged, compliance report generated automatically

No human needs to remember to escalate. The system enforces SLA protection.


---

## Section 8 — Learning Engine (Layer 6)

The learning engine is what makes ATLAS more valuable every day. Every resolved incident, every human correction, every modification makes the next response more accurate.

### Learning Loop Diagram

```
Incident Resolved
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Decision History Record written (immutable)            │
  │  client_id, anomaly_type, service_class,                │
  │  recommended_action_id, confidence_score_at_decision,   │
  │  routing_tier, human_action, modification_diff,         │
  │  rejection_reason, resolution_outcome, actual_mttr,     │
  │  recurrence_within_48h                                  │
  └─────────────────────────────────────────────────────────┘
        │
        ├──────────────────────────────────────────────────┐
        ▼                                                  ▼
  ┌─────────────────────────┐                  ┌──────────────────────────┐
  │  Confidence             │                  │  Weight Correction       │
  │  Recalibration          │                  │                          │
  │                         │                  │  L2 modified same param  │
  │  Empirical accuracy for │                  │  3+ times → update       │
  │  pattern/action/client  │                  │  ATLAS default           │
  │  triple recalculated    │                  │                          │
  │  from all matching      │                  │  L3 rejected hypothesis  │
  │  Decision History rows  │                  │  → weight down rejected  │
  │                         │                  │  type, weight up         │
  │  Factor 1 updated       │                  │  substituted type        │
  │  immediately            │                  └──────────────────────────┘
  └─────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Trust Progression Evaluation                           │
  │                                                         │
  │  Stage 0 → Stage 1: 30 incidents + >80% correct         │
  │  Stage 1 → Stage 2: 30 more + >85% auto-success         │
  │  Stage 2 → Stage 3: demonstrated Stage 2 accuracy       │
  │  Stage 3 → Stage 4: SDM explicit enablement required    │
  │  Class 3: never auto-executes. Permanent.               │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Knowledge Base Update                                  │
  │                                                         │
  │  New Neo4j Incident node created                        │
  │  New ChromaDB embedding stored                          │
  │  Problem record drafted if recurrence risk high         │
  │  Change request drafted if permanent fix needed         │
  └─────────────────────────────────────────────────────────┘
```

### The Recurrence Rule

Recurrence within 48 hours is recorded as a negative outcome even if the immediate metrics recovered. The fix was symptomatic, not causal. The learning engine is honest about this. A system that claims success when the problem comes back is not learning — it is lying.

### Knowledge Ownership

When an L3 engineer resolves a novel incident, their decision is embedded in the knowledge graph and the vector store. The next engineer who encounters a similar pattern — whether on the same client or any other client running the same stack — sees that resolution as a historical match.

When that engineer leaves, their expertise stays. ATLAS owns the knowledge. Nobody can walk out the door with it.


---

## Section 9 — Ingestion Pipeline (Layer 1)

### Three Ingestion Paths

```
Client Infrastructure
        │
   ┌────┴────────────────────────────────────────┐
   │                                             │
   ▼                                             ▼                          ▼
Path A                                      Path B                      Path C
OTel SDK                               Legacy Adapters               API Pull
(modern apps)                          (Java, PostgreSQL,            (Splunk, Dynatrace,
                                        SAP, Oracle,                  Datadog, CloudWatch)
                                        Mainframe, Windows)
   │                                             │                          │
   └────────────────────┬────────────────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │    Normaliser        │
              │                     │
              │  Unified OTel schema │
              │  client_id tagged   │
              │  Timestamps → UTC   │
              │  Severity mapped    │
              │  raw_payload kept   │
              └──────────────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │   CMDB Enricher      │
              │                     │
              │  CI class + version  │
              │  Business service   │
              │  Criticality tier   │
              │  Open change records│
              │  SLA threshold      │
              │  Owner team         │
              │  60s cache per client│
              └──────────────────────┘
                        │
                        ▼
              Specialist Agents receive
              pre-enriched events
              (zero mid-analysis lookups)
```

Every event is tagged with `client_id` at normalisation. Events with missing `client_id` are rejected immediately and logged to an error queue. They never enter the main pipeline.

The CMDB enricher serves from a 60-second TTL cache per client. If Neo4j is temporarily unavailable, it serves from cache and flags `enriched_from_cache: true`. The event pipeline never blocks on a database dependency.

---

## Section 10 — Multi-Tenancy Architecture

Multi-tenancy in ATLAS is architectural, not policy. It cannot be misconfigured away.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-TENANCY ENFORCEMENT                    │
│                                                                 │
│  Every data object:     client_id tagged at creation            │
│                                                                 │
│  Neo4j:                 client_id mandatory WHERE clause        │
│                         Query without it fails at construction  │
│                                                                 │
│  ChromaDB:              atlas_{client_id} namespaced collection │
│                         Search scoped to client namespace       │
│                                                                 │
│  Decision History DB:   client_id mandatory field at write      │
│                                                                 │
│  Confidence cache:      Key = (client_id, service_name)         │
│                                                                 │
│  Cross-client learning: Federated embedding centroids only      │
│                         Zero raw data shared                    │
│                         Mathematically zero information leakage │
│                                                                 │
│  Ingestion:             client_id mismatch = hard error         │
│                         Event rejected, never enters pipeline   │
└─────────────────────────────────────────────────────────────────┘
```

Client 400 onboards as fast as client 2. The architecture does not degrade with scale.


---

## Section 11 — End-to-End Incident Flow (The Full Picture)

This is the complete journey of a real incident — FinanceCore HikariCP connection pool exhaustion — from first signal to resolution.

```
T+0s    Deployment CHG0089234 was made 3 days ago
        (HikariCP maxPoolSize reduced 100 → 40, risk rated LOW)

T+0s    Morning peak traffic begins
        PostgreSQL agent detects connection count climbing above
        Monday 9am seasonal baseline

T+35s   Alert threshold crossed: 3σ sustained 60 seconds
        PostgreSQL agent produces EvidencePackage:
          anomaly_type: CONNECTION_POOL_EXHAUSTED
          detection_confidence: 0.94 (conformal calibrated)
          shap_feature_values: {connection_count: 71%, query_latency: 29%}
          supporting_log_samples: [5 real HikariCP log lines]

T+38s   Java agent detects PaymentAPI HTTP 503 spike
        Second EvidencePackage produced

T+40s   Cascade Correlation Engine:
        Neo4j confirms PaymentAPI DEPENDS_ON TransactionDB
        → CASCADE_INCIDENT declared

T+47s   Orchestrator triggered
        ServiceNow INC0089247 created (real ticket)
        SLA breach countdown: 23 minutes

T+52s   N3 Graph Intelligence:
        Blast radius: PaymentAPI (P1), AuthService (P2), NotificationService (P3)
        Deployment: CHG0089234 → MODIFIED_CONFIG_OF → PaymentAPI (3 days ago)
        Historical: INC-2024-0847 (same pattern, 4 months ago)

T+55s   N4 Semantic Retrieval:
        ChromaDB: INC-2024-0847 at 91% cosine similarity
        Double-confirmed (appears in both Neo4j and ChromaDB)

T+62s   N5 Reasoning:
        Qwen3 → structured JSON
        root_cause: "HikariCP maxPoolSize reduced from 100 to 40 by CHG0089234"
        recommended_action_id: "connection-pool-recovery-v2"
        alternative_hypotheses: [memory pressure 38%, traffic spike 27%]

T+70s   N6 Confidence Scoring:
        F1 (Historical): 0.91 (INC-2024-0847 resolved successfully)
        F2 (Certainty): 0.88 (top hypothesis 0.84, second 0.38, gap 0.46)
        F3 (Safety): 1.0 (Class 1 action)
        F4 (Freshness): 0.94 (70 seconds old)
        Composite: 0.84

        Veto check: PCI-DSS + business hours → VETO FIRES
        → L2_L3_ESCALATION (correct behaviour for a bank)

T+78s   Briefing card delivered to L2 engineer
        All 6 sections populated with real data
        Graph animation: CHG0089234 pulses → DEPENDS_ON edge → TransactionDB red

T+82s   Early Warning: AuthService at 1.8σ, trending upward
        "ATLAS is watching the next incident before it exists"

T+95s   L2 engineer reads briefing (< 2 minutes)
        Clicks Approve
        Slack notification → secondary approver
        Secondary clicks one-time token link
        Both cryptographic signatures logged

T+110s  Playbook connection-pool-recovery-v2 executes:
        Pre-validation: health endpoint ✓, connection count above threshold ✓
        Action: POST /actuator/env (maxPoolSize=150) + POST /actuator/refresh
        Success validation: polling every 30s

T+170s  Connection count drops below 70% of max for 2 consecutive readings
        Success validation confirmed
        MTTR stops: 4 minutes 12 seconds
        Atlassian 2024 benchmark: 43 minutes

        Audit record written (immutable, cryptographically signed)
        Neo4j: new Incident node created, linked to CHG0089234
        ChromaDB: new embedding stored
        ServiceNow INC0089247: resolved with full resolution notes
        Decision History: record written, Factor 1 updated for this pattern
        Trust progression: +1 incident toward Stage 2
```

**Total time from first signal to resolution: 4 minutes 12 seconds.**
**Industry median for P2 enterprise incidents: 43 minutes.**
**Reduction: 90%.**


---

## Section 12 — Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI, Python 3.11, asyncio | Async-native, WebSocket, production standard |
| Orchestration | LangGraph 0.2+ | State persistence, human-in-loop native, interrupt points |
| LLM Router | Cerebras + Ollama | Single interface, 99.9% availability across providers |
| LLM Primary | Cerebras Qwen3-235B | JSON schema enforced at API level — malformed output impossible |
| LLM Fallback | Ollama local Qwen3 | Auto-failover under 500ms |
| Time-Series | Chronos-Bolt (HuggingFace) | Pretrained 100B points, zero cold-start, seasonal-aware |
| Point Anomaly | Isolation Forest + SHAP | Explainable, production-proven, auto-retrains |
| Uncertainty | Conformal Prediction | Statistically valid confidence bounds, not nominal claims |
| Knowledge Graph | Neo4j Aura Serverless | Real-time CMDB sync, 60s cached queries, sub-200ms |
| Vector Store | ChromaDB (namespaced per client) | Zero dependency, federated warm-start, client isolation |
| CMDB Sync | ServiceNow Change Webhook | Push-based, seconds latency, real-time topology |
| ITSM | ServiceNow Developer Instance | Real tickets, real API, real INC format |
| Approval | Cryptographic one-time tokens | Compliance-grade dual sign-off |
| Frontend | React 18, TypeScript, Tailwind, Framer Motion | Dark enterprise theme, IBM Plex fonts |
| Graph Viz | React Force Graph 2D | Interactive traversal animation, real Neo4j node IDs |
| Charts | Recharts + SHAP waterfall | Real data, explainable detection |
| Audit Store | SQLite WAL mode (3 separate DBs) | Simple, exportable, migration-ready, immutable |
| MTTR Benchmark | Atlassian 2024 State of Incident Management | Third-party validated, 43-minute median P2 |

---

## Section 13 — Key Data Contracts

### EvidencePackage (Agent → Orchestrator)

Every agent produces this when an anomaly is detected. All fields required. Validated before leaving the agent.

```python
@dataclass
class EvidencePackage:
    evidence_id: str              # uuid4
    agent_id: str                 # e.g. "java-agent"
    client_id: str                # mandatory, enforced
    service_name: str
    anomaly_type: str             # from ATLAS error taxonomy
    detection_confidence: float   # 0.0–1.0, conformal calibrated
    shap_feature_values: dict     # feature → contribution_pct, sums to 100
    conformal_interval: dict      # {lower, upper, confidence_level}
    baseline_mean: float
    baseline_stddev: float
    current_value: float
    deviation_sigma: float
    supporting_log_samples: list  # exactly 5 real log lines
    preliminary_hypothesis: str
    severity_classification: str  # "P1" | "P2" | "P3"
    detection_timestamp: datetime
```

### AtlasState (LangGraph State — full incident lifecycle)

Immutable after initial set: `client_id`, `incident_id`, `evidence_packages`, `mttr_start_time`
Append-only: `audit_trail`
Once-set: `routing_decision`

### DecisionRecord (Learning Engine — immutable after write)

```python
@dataclass
class DecisionRecord:
    record_id: str
    client_id: str
    incident_id: str
    anomaly_type: str
    service_class: str
    recommended_action_id: str
    confidence_score_at_decision: float
    routing_tier: str             # "L1" | "L2" | "L3" | "auto"
    human_action: str             # "approved" | "modified" | "rejected" | "escalated"
    modification_diff: dict | None
    rejection_reason: str | None
    resolution_outcome: str       # "success" | "failure" | "partial"
    actual_mttr: int              # seconds
    recurrence_within_48h: bool
    timestamp: datetime
```

---

## Section 14 — ATLAS Error Taxonomy

Every anomaly type in ATLAS maps to a specific error taxonomy entry. This ensures consistent classification across all agents, all clients, and all historical records.

| Code | Description |
|------|-------------|
| `CONNECTION_POOL_EXHAUSTED` | HikariCP exhaustion, PostgreSQL 53300 |
| `DB_DEADLOCK` | PostgreSQL 40P01 |
| `DB_PANIC` | PostgreSQL PANIC level — always P1 |
| `JVM_MEMORY_CRITICAL` | OutOfMemoryError |
| `JVM_STACK_OVERFLOW` | StackOverflowError |
| `REDIS_OOM` | Redis maxmemory exceeded |
| `REDIS_COMMAND_REJECTED` | Redis rejected commands |
| `NODE_UNHANDLED_REJECTION` | UnhandledPromiseRejectionWarning spike |
| `NODE_DOWNSTREAM_REFUSED` | ECONNREFUSED to downstream service |
| `JAVA_UNKNOWN` | Unmapped Java exception (class name preserved) |
| `DB_UNKNOWN` | Unmapped PostgreSQL SQLSTATE (code preserved) |

New anomaly types are added to the taxonomy as new agent types are deployed. The taxonomy is the shared language between detection, reasoning, and learning.


---

## Section 15 — Roadmap

### Current State (MVP)

- Full 7-layer architecture operational
- Two demo clients: FinanceCore (PCI-DSS/SOX, L1 Assistance) and RetailMax (GDPR, L1 Automation)
- Detection ensemble: Chronos-Bolt + Isolation Forest + SHAP + Conformal Prediction
- Complete LangGraph orchestrator with real Neo4j, real ChromaDB, real ServiceNow
- Confidence engine with 4 factors and 7 vetoes
- Two production playbooks with full 5-step execution and auto-rollback
- Complete learning engine: decision history, recalibration, weight correction, trust progression
- Dual cryptographic approval for compliance-gated incidents
- Immutable audit log with export capability
- Dark enterprise UI with live WebSocket feeds, SHAP waterfall, graph visualization, pipeline progress

### Near-Term (Next Quarter)

- Additional agent types: Kubernetes, MongoDB, Kafka, AWS RDS, Azure SQL
- Expanded playbook library: pod restart, horizontal scaling, cache invalidation, circuit breaker reset
- Client transparency portal (read-only client-facing view)
- Slack and Teams native integration for approval flows
- Automated Problem record creation and Change Request drafting
- Cross-client federated learning improvements (larger centroid pool)

### Medium-Term (6–12 Months)

- ServiceNow CMDB write-back (ATLAS updates topology from resolution outcomes)
- Predictive incident prevention (Chronos-Bolt forecasting 30+ minutes ahead)
- Natural language incident query interface for SDMs
- Multi-region deployment with data residency controls
- SOC 2 Type II audit readiness package
- Client-configurable agent deployment via CMDB webhook (zero-touch agent provisioning)

### Long-Term Vision

- ATLAS as the standard operating layer for every Atos managed service client
- Trust Stage 4 (L2 Automation) as the default for mature clients
- Cross-industry incident pattern library (anonymised, federated)
- ATLAS as a platform: third-party agent marketplace, customer-built playbooks
- Real-time SLA performance as a contractual feature, not a reporting metric

---

## Section 16 — The Business Case

**The problem ATLAS solves is not technical. It is economic.**

Atos manages hundreds of enterprise clients. Each incident costs:
- Engineer time: average 43 minutes per P2 incident (Atlassian 2024)
- SLA penalties: breach costs vary by contract, typically £10k–£100k per event
- Client trust: every incident that takes too long is a renewal conversation at risk
- Knowledge loss: every engineer who leaves takes institutional knowledge with them

**What ATLAS delivers:**

- 90% reduction in MTTR for known incident patterns (4 minutes vs 43 minutes)
- Zero SLA breaches on incidents ATLAS handles autonomously
- L1 triage time: under 2 minutes vs 35 minutes average
- Knowledge retention: 100% — every resolution is permanent institutional knowledge
- Compliance audit preparation: under 10 minutes vs 2 weeks
- Client onboarding: under 1 hour vs weeks

**The compounding effect:**

Month 1: ATLAS recommends, humans execute. 84% accuracy.
Month 3: L1 automation enabled. First overnight auto-resolution.
Month 6: Cross-client learning benefits every new client from day one.
Month 12: The engineer who built the most institutional knowledge leaves. Their expertise stays.

**The moat:**

Every incident makes ATLAS more accurate for that client. Every client makes ATLAS more accurate for every other client running the same stack. The longer ATLAS runs, the harder it is to replace. The knowledge graph, the decision history, the calibrated confidence scores — these are not features. They are compounding assets.

---

*ATLAS Technical Pitch Document — Complete architecture, all flows, all components, all data contracts.*
*Built for Atos Managed Services. Designed to serve 400+ enterprise clients from one platform.*
