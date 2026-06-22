# Glossary

Key terms used throughout this documentation — ordered alphabetically.

**Action Class**
: A safety rating assigned to every playbook: Class 1 (low-risk, auto-execute
eligible if all conditions are met), Class 2 (medium-risk, always requires human
approval), Class 3 (high-risk — database, network, or production-data operations —
permanently excluded from autonomous execution). Enforced structurally in
`playbook_library.py`.

**AtlasState**
: The typed LangGraph state object threaded through all 7 orchestrator nodes for
the entire lifecycle of an incident, from first evidence to final audit record.
Three write disciplines are enforced in code: immutable-after-set fields,
append-only audit trail, and a once-set routing decision.

**Auto-Execute Threshold**
: The minimum composite confidence score below which ATLAS will not act
autonomously, set per client in their configuration YAML. Must be between 0.5 and
1.0. Default for a PCI-DSS/SOX-regulated client: 0.92.

**CAB Risk Rating**
: Change Advisory Board risk rating attached to a CMDB deployment record —
carried through to the Neo4j `Deployment` node and surfaced in the L2/L3 briefing.

**Cascade Correlation Engine**
: The component above the four specialist agents that determines whether multiple
anomaly signals represent structurally connected, causally related services
(`CASCADE_INCIDENT`) or temporal coincidence (`ISOLATED_ANOMALY`). Confirmation
requires a Neo4j `DEPENDS_ON` graph traversal — temporal proximity alone is never
sufficient.

**Cerebras**
: The primary hosted LLM inference provider used for Node 5 reasoning. Default
model: `qwen-3-235b-a22b-instruct-2507`.

**ChromaDB**
: The vector store used for semantic incident matching in Node 4. Collections are
namespaced per client; new clients are warm-started from federated embedding
centroids of clients on the same technology stack.

**Chronos-Bolt**
: A time-series foundation model from HuggingFace, pretrained on 100 billion
real-world data points. Layer A of the two-layer detection ensemble, weight 0.55.
Catches gradual degradation and temporal pattern violations that static thresholds
miss.

**CMDB**
: Configuration Management Database — ServiceNow is the CMDB source of truth for
all clients. ATLAS reads service topology, CIs, and change records from it via
push-based webhooks (not polling), keeping the knowledge graph seconds-fresh.

**Compliance Gate**
: The dual cryptographic sign-off process that fires when a PCI-DSS or SOX veto
is active. Requires two independent approvers, both with logged timestamps and
cryptographic signatures, before any production configuration change executes.

**Conformal Prediction**
: The statistical calibration framework that turns raw model scores into
statistically valid confidence bands. Used in `agents/detection/conformal.py` to
combine Chronos-Bolt and Isolation Forest outputs. The confidence value returned is
empirically calibrated — not the nominal claim.

**DecisionRecord**
: The immutable learning-engine record written after every incident resolution —
the ledger that Factor 1 (Historical Accuracy) is built from. Immutable after
write; corrections are new records, never edits.

**EvidencePackage**
: The strongly-typed output of every specialist agent — the data structure that
carries anomaly details, SHAP explanations, log samples, and hypothesis text from
Layer 2 into the Layer 3 orchestrator.

**Factor 1 / F1 — Historical Accuracy**
: 30% of the composite confidence score. The empirical success rate for this exact
pattern / action / client triple, derived from all matching `DecisionRecord`s.
Updated by the learning engine after every confirmed resolution.

**GraphRAG**
: Retrieval-Augmented Generation using a knowledge graph — the technique used in
Node 3, where structured Cypher queries over Neo4j provide the structural reasoning
layer on top of the LLM's text understanding.

**INC**
: The ServiceNow incident record format. ATLAS creates a real `INC` ticket in Node
2 on every incident and keeps it updated through resolution.

**Isolation Forest**
: The scikit-learn anomaly detection model used as Layer B of the detection
ensemble (weight 0.45). Every flag is wrapped with SHAP `TreeExplainer`
feature-contribution values — no flag is unexplained.

**LangGraph**
: The orchestration library that implements the 7-node state machine. Chosen
specifically for its native support for human-in-the-loop interrupts and durable
state persistence — a suspended graph resumes with zero state loss regardless of
how long human review takes.

**Layer 0–6**
: The seven architectural layers of ATLAS, numbered from client configuration (0)
through ingestion (1), detection (2), orchestration (3), confidence scoring (4),
execution (5), and continuous learning (6). See [Architecture Overview](architecture/overview.md).

**MTTR**
: Mean Time To Resolve. ATLAS measures this from the first `EvidencePackage`
received to the final audit record written. Compared against the Atlassian 2024
State of Incident Management Report benchmark of 43 minutes for P2 enterprise
incidents.

**Neo4j**
: The graph database used for the ATLAS knowledge graph. Stores the structural
relationships between services, infrastructure, deployments, incidents, and
compliance rules. Queried by Node 3 via Cypher.

**Ollama**
: The local LLM inference server used as the offline fallback if Cerebras is
unreachable. Default model: `qwen3-coder:480b-cloud`.

**OTel / OpenTelemetry**
: The unified schema all ingested events are normalised into by `normaliser.py`,
regardless of which of the three ingestion paths they arrived through.

**Playbook**
: A named, versioned, pre-approved action registered in `playbook_library.py`.
The playbook library is the absolute boundary of autonomous action — no LLM
output can cause a command to run outside this registry.

**SHAP**
: SHapley Additive exPlanations — the technique used to wrap the Isolation Forest
with feature-contribution scores. Every anomaly detection in ATLAS is
accompanied by a SHAP breakdown of which metric contributed what percentage.

**SLA Breach Timer**
: The background countdown started at Node 1 classification. Triggers forced
escalation at breach − 10 minutes, SDM notification at breach − 5 minutes, and
an automatic compliance report at breach − 0.

**Trust Stage**
: The five-stage progression (0 = Observation through 4 = L2 Automation) that
determines what ATLAS is permitted to do autonomously for a given client.
Advancement is gated by evidence-based thresholds; stages can only advance one at
a time; Stage 4 requires explicit SDM confirmation. Class 3 actions are excluded
at every stage.

**Veto**
: One of the 8 hard, independent checks in the confidence engine that forces
human review regardless of the composite confidence score. All 8 run and are
recorded on every decision, even after one has already fired.
