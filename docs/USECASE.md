# ATLAS — Use Cases & Complete User Flow
## From Client Onboarding to Incident Resolution to Knowledge Ownership

---

## Who Uses ATLAS

There are five people who interact with ATLAS. Understanding each one is critical to understanding why the system is designed the way it is.

**The Atos Delivery Manager (SDM)**
Owns the client relationship. Accountable for SLAs. Gets called when things go badly wrong. Wants visibility without noise. Makes decisions about trust levels and automation thresholds.

**The L1 Service Desk Engineer**
First contact for every incident. Manages many incidents simultaneously. Needs fast, clear guidance. Does not have deep technical expertise in every technology. Gets burned out doing the same investigations over and over.

**The L2 Technical Support Engineer**
Deeper technical skills. Investigates what L1 couldn't resolve. Spends most of their time on incidents that were actually solved before by a colleague who has since left. This is the primary pain point ATLAS addresses.

**The L3 Deep Technical Architect**
Expert-level. Gets involved only for novel or P1 incidents. Their knowledge is the most valuable institutional asset and the most at risk of being lost when they leave.

**The Atos Client**
The company Atos is managing services for. Wants to know what is happening in their environment. Currently has to call the SDM to find out. With ATLAS, they have a real-time view they can access themselves.

---

## Use Case 1 — Client Onboarding

### Who does this
The Atos Delivery Manager.

### What used to happen
Onboarding a new client meant weeks of work. Setting up monitoring tools. Configuring alert thresholds. Documenting the client's architecture. Training the L1/L2 teams on the client's specific environment. Knowledge lived in a Confluence page that nobody kept updated.

### What happens with ATLAS

**Step 1 — Point ATLAS at the client's ServiceNow CMDB**
The client already has a ServiceNow instance. Their IT team has already documented their services, infrastructure, and dependencies in the CMDB. ATLAS reads this directly. No re-documentation required. The SDM configures a CMDB webhook so every new change record in ServiceNow automatically flows into ATLAS in real time.

**Step 2 — Fill the thin ATLAS config**
The SDM fills one configuration file with ATLAS-specific settings only. This takes about 20 minutes:
- What auto-execute confidence threshold does this client want? (Default: 0.88)
- What compliance frameworks apply? (PCI-DSS, SOX, GDPR, etc.)
- Who gets notified at L1, L2, L3 for each priority level?
- What are the change freeze windows?
- What are the SLA breach thresholds per service?

**Step 3 — ATLAS self-configures**
ATLAS reads the CMDB and automatically:
- Builds the client's knowledge graph in Neo4j from their existing CI relationships
- Deploys the correct specialist agents based on the technology stack declared in CMDB (Java services → Java agent. PostgreSQL → PostgreSQL agent. And so on.)
- Seeds the ChromaDB vector store with anonymised incident patterns from existing clients running the same technology — giving the new client warm-started intelligence from day one

**Step 4 — Trust level starts at Observation Mode**
For the first 30 incidents, ATLAS watches, detects, and recommends — but humans execute everything. This is deliberate. ATLAS has not yet demonstrated accuracy on this client's specific environment. It earns the right to do more by being right more often.

**What the SDM sees:**
A new client card appears in the ATLAS dashboard. Green health indicators. Compliance badges. Trust level: Stage 0 — Observation. Agent deployment status: active for all detected technology types.

**Time from "start onboarding" to "ATLAS is monitoring":** Under one hour.

---

## Use Case 2 — Normal Operations Monitoring

### Who experiences this
Every team member sees this in the background at all times.

### What happens

Every application log, metric, and trace from the client's environment flows into ATLAS continuously. All three ingestion paths are active:
- Modern applications send data via OpenTelemetry
- Legacy systems like SAP or Oracle send data through purpose-built adapters
- Existing tools like Splunk or CloudWatch have their data pulled via API

All of this data gets enriched with CMDB context automatically. When a log line arrives from PaymentAPI, ATLAS already knows: this is a P1 service, it supports the FinanceCore core banking business service, it depends on TransactionDB, it was last deployed three days ago, its SLA requires 99.95% uptime.

Four specialist agents are running continuously. Each one knows what "normal" looks like for its specific technology domain — not based on a generic threshold someone configured, but based on the actual behaviour of that specific service in that specific client environment over the last four weeks, calibrated by time of day and day of week.

**What the team sees:**
A live dashboard with health indicators for each client. A real-time log stream. An activity feed showing ATLAS monitoring heartbeats. Everything green. Nothing to do.

---

## Use Case 3 — Incident Detection (Before Users Notice)

### Who experiences this
The detection happens automatically. The L1 engineer is the first human to see it.

### The scenario
A deployment was made three days ago to FinanceCore's PaymentAPI. The change reduced the HikariCP connection pool size from 100 to 40 as a cost optimisation measure. The risk was rated LOW on the change ticket. Nobody connected this change to a potential problem.

Today, during morning peak hours, transaction volume is higher than average. The connection pool starts getting exhausted.

### What happens

**T+0: The anomaly begins developing**
The PostgreSQL agent detects that TransactionDB's connection count is climbing above its Monday 9am baseline. Not yet at alert level. Warning level. ATLAS notes it and increases monitoring frequency.

**T+35 seconds: Alert threshold crossed**
Connection count crosses 3 standard deviations above baseline and stays there for 60 seconds. The PostgreSQL agent packages an EvidencePackage: the exact error codes appearing, the deviation magnitude, the SHAP breakdown showing connection_count contributed 71% and query_latency contributed 29% to the detection, the conformal prediction interval saying "94% confident this is anomalous."

Simultaneously, the Java agent detects PaymentAPI's HTTP 5xx error rate spiking. Two agents, both firing, services structurally connected in the Neo4j graph via DEPENDS_ON. Cascade correlation engine confirms: `CASCADE_INCIDENT`.

**T+47 seconds: Orchestrator triggered**
Both EvidencePackages packaged together. Sent to the seven-node LangGraph orchestrator. A ServiceNow incident ticket INC0089247 is created automatically in the correct format with the correct assignment group and affected CI. The SLA breach timer starts: 23 minutes until breach.

The ATLAS activity feed in the dashboard updates in real time: "09:23:47 — PostgreSQL Agent: connection pool anomaly detected, conformal confidence 94%, SHAP: connection_count 71%, query_latency 29%." "09:24:01 — Cascade confirmed via CMDB topology. Orchestrator triggered."

**T+78 seconds: Reasoning complete**
The orchestrator has:
- Traversed the Neo4j graph and found Deployment CHG0089234 from three days ago that modified PaymentAPI's HikariCP configuration
- Found historical Incident INC-2024-0847 from four months ago in ChromaDB at 91% similarity — same pattern, same service, resolved by restoring pool size to 150
- Called Claude with all this context and received structured reasoning output
- Calculated a composite confidence score of 0.84

The PCI-DSS veto fires: production database configuration changes during business hours require human sign-off per compliance policy. Routed to L2 human review.

**What nobody did:**
No human detected this. No alert fired after a user complained. No ticket was manually created. ATLAS found it before any customer noticed, traced it to a three-day-old deployment, matched it to a four-month-old historical fix, and had a complete briefing ready for an engineer — all in 78 seconds.

---

## Use Case 4 — L1 Handling a Known Incident

### Who does this
The L1 Service Desk Engineer.

### When this happens
ATLAS routed the incident to L1 human review because: the confidence score was below threshold, but the historical similarity is above 0.75, it is a Class 1 action, and no compliance vetoes fired. This is a known pattern with a known fix. L1 can handle it.

### What the L1 engineer sees

A notification fires — on the dashboard and via the configured channel (Slack or Teams). The L1 engineer opens the ATLAS L1 interface. It shows:

```
INCIDENT: RetailMax — Redis Cache Issue
Priority: P2
SLA Breach: 18 minutes remaining

WHAT IS HAPPENING:
Redis memory at 96%. Commands being rejected.
Response time on CartService increased 4x baseline.

ATLAS RECOMMENDS:
1. Rollback Redis maxmemory-policy to allkeys-lru
2. Flush expired keys
3. Monitor memory for recovery over next 5 minutes

[APPROVE]    [ESCALATE TO L2]
```

No graph. No reasoning chains. No alternative hypotheses. Just: what is happening, what to do, two buttons.

### What the L1 engineer does

The engineer reads the two-line summary. Recognises the checklist matches the recommended action. Clicks **Approve**.

ATLAS executes the playbook. The engineer watches the confirmation appear. Done.

**Time spent by L1 engineer:** Under 2 minutes.
**What would have happened without ATLAS:** L1 searches KB with keywords "Redis slow." Gets 47 results. Spends 20 minutes reading them. Escalates to L2. L2 spends 40 minutes investigating. Total time: 60+ minutes.

### Learning signal captured
L1 approved ATLAS's recommendation. Outcome: success. Decision History Database records: pattern/action/client triple for this incident, approved at L1, successful resolution, 4-minute MTTR. Factor 1 of the confidence engine for this pattern on RetailMax just got one more positive data point.

---

## Use Case 5 — L2 Handling a Complex Incident

### Who does this
The L2 Technical Support Engineer.

### When this happens
The FinanceCore HikariCP incident was routed to L2 because of the PCI-DSS compliance veto — not because ATLAS was uncertain, but because the compliance rules require a human sign-off for this type of change on this client.

### What the L2 engineer sees

The full ATLAS briefing card. Six sections:

**Section 1 — Situation Summary**
"PaymentAPI is experiencing HTTP 503 errors at 340% above Monday morning baseline. TransactionDB shows HikariCP connection pool at 94% capacity. AuthService and NotificationService are showing early signs of degradation (1.8σ above baseline). SLA breach in 21 minutes. Business impact: estimated 2,400 transactions per minute affected."

**Section 2 — Blast Radius (interactive graph)**
The dependency graph animates on screen. The deployment node from three days ago pulses yellow. An arrow traces from the deployment to TransactionDB (orange). Another arrow traces from TransactionDB to PaymentAPI (red). AuthService and NotificationService glow amber in the background — not yet affected but in the blast zone.

The engineer can hover over any node to see its details. Click on the deployment node: "CHG0089234 — Reduced HikariCP maxPoolSize from 100 to 40 — Cost optimisation — Deployed by raj.kumar@atos.com — CAB risk rating: LOW."

**Section 3 — Historical Match**
"ATLAS matched Incident INC-2024-0847 from November 2024 (91% similarity). That incident was caused by Deployment CHG0071892 which also reduced maxPoolSize. Resolved in 23 minutes by restoring pool size to 150 and restarting connection manager. Resolution was successful. Permanent fix applied: pool_size floor validation added to deployment pipeline."

A link opens the full historical incident record. The engineer can read the exact resolution steps that worked last time.

**Section 4 — Alternative Hypotheses**
- "Memory pressure on RDS instance (38% confidence) — Evidence against: memory metrics within normal range for this time of day"
- "Traffic spike causing natural exhaustion (27% confidence) — Evidence against: request rate 12% above baseline, insufficient to explain 94% pool utilisation with original pool size of 100"

The engineer can see ATLAS considered and eliminated these alternatives. This is not a black box.

**Section 5 — Recommended Action**
"Execute Playbook: connection-pool-recovery-v2. Restore HikariCP maxPoolSize to 150. Restart connection manager pod. Estimated resolution: 4-6 minutes. Risk class: P2 (reversible). Rollback: connection-pool-restore-v2 is pre-tested and available."

**Section 6 — Compliance Note**
"PCI-DSS: This action modifies production database connection configuration during business hours. Dual engineer sign-off required per compliance policy. Rejection reason has been pre-populated with: 'CHG0089234 config rollback — HikariCP pool exhaustion.'"

### What the L2 engineer does

The engineer reads the briefing in under 2 minutes. Agrees with the assessment. Clicks **Approve**.

A notification fires to the secondary approver (the SDM or L2 lead, configured in the client registry). They receive a Slack message with a one-time signed token link. They click it. Single confirmation.

Both cryptographic signatures logged. Playbook executes.

**What the engineer modified (this time: nothing)**
They approved as recommended. That approval is logged. One more positive data point in the Decision History Database.

**What if the engineer had modified it?**
If the engineer changed the pool size from 150 to 200 before approving, the diff is logged: `{parameter: 'maxPoolSize', recommended: 150, approved: 200, direction: 'increased'}`. If this pattern appears three more times — L2 consistently increases the pool size beyond ATLAS's recommendation on this client — ATLAS updates its default recommendation for this client to 200. It learned from the engineer's judgment without anyone configuring it.

**What if the engineer had rejected it?**
The rejection text field opens. The engineer types: "Wrong root cause — this is actually a Redis connection leak from the new caching layer, not HikariCP config." ATLAS immediately runs semantic search on the playbook library matching "Redis connection leak." Surfaces two alternative playbooks. The engineer selects one. The execution and outcome are recorded. The rejected hypothesis type receives lower weight for future similar incidents on this client. The substituted hypothesis receives higher weight.

---

## Use Case 6 — L3 Handling a Novel Incident

### Who does this
The L3 Deep Technical Architect.

### When this happens
ATLAS detects an incident pattern it has never seen before on this client — or anywhere in the portfolio. Similarity score on best historical match: 0.58. Below the 0.75 threshold for known patterns. Routed directly to L3.

### What the L3 engineer sees

Everything in the L2 interface plus:

**Cross-client pattern panel**
"ATLAS found 3 similar incidents across the Atos portfolio (anonymised). All involved Java services on AWS EKS during Kubernetes node autoscaling events. Two were resolved by adjusting pod disruption budgets. One required manual pod recreation."

**Confidence debug panel**
"Factor 1 (Historical Accuracy): 0.50 — insufficient precedent (3 cases). Factor 2 (Root Cause Certainty): 0.61 — two competing hypotheses within 15% of each other. Factor 3 (Action Safety): 0.60 — Class 2 action required. Factor 4 (Evidence Freshness): 0.95. Composite: 0.68. Threshold: 0.92. Gap: 0.24. Routing: L3 direct."

**Problem record draft (pre-populated)**
ATLAS has already written the first draft of a Problem record from the incident data. Title, affected services, observed symptoms, preliminary root cause, service impact. The L3 engineer reviews, corrects where needed, and submits with one click. What used to take two hours of documentation takes five minutes.

**Change request draft (if applicable)**
If the resolution requires an infrastructure change — a new Kubernetes configuration, a new network rule — ATLAS drafts the change request from the incident context. The L3 engineer reviews and submits to CAB.

### What the L3 engineer does

The engineer investigates using the briefing as a starting point rather than a blank screen. Uses their expertise to identify the actual root cause — in this case, a Kubernetes pod disruption budget misconfiguration introduced in a recent cluster upgrade.

Selects the correct playbook. Approves. Resolution executes.

### What happens after L3 resolution

This L3 decision carries 3× weight in the learning engine. The new incident class is created in Neo4j as a first-class Incident node. The resolution is embedded in ChromaDB. The next time this pattern appears — whether on this client or any other client running the same stack — ATLAS has a strong precedent to reason from. The L3 engineer's expertise is now permanent institutional knowledge. It does not leave when they do.

---

## Use Case 7 — Auto-Resolved Incident (The Goal State)

### When this happens
RetailMax is on Trust Level: Stage 2 — L1 Automation. ATLAS has demonstrated above 85% auto-resolution success on this client. P3 incidents with Class 1 actions can auto-execute when confidence conditions are met and no vetoes are active.

### The scenario
At 3am, a Redis cache instance on RetailMax starts showing memory pressure. The same pattern ATLAS has now resolved successfully six times before on this client. Confidence: 0.91. Zero vetoes: it is 3am (outside business hours), GDPR not triggered, no change freeze, no recent duplicate action. Class 1 action. Threshold met.

### What happens

Nobody wakes up.

ATLAS detects the anomaly. Runs the orchestrator. Scores 0.91 confidence. Checks all seven vetoes: none fire. Routes to auto-execute. Pre-execution validation confirms the Redis instance is in expected state. Playbook executes. Success validation confirms memory returning to normal within 6 minutes. Immutable audit record written. ServiceNow ticket created and auto-resolved with full resolution notes. Knowledge base updated.

The L1 engineer starts their morning shift and sees: one auto-resolved incident overnight. Resolution time: 6 minutes. If it had been handled manually starting when the first alert fired and an engineer was available: estimated 38-minute resolution.

**The client sees:** On their transparency portal, a resolved incident entry appears with the timeline, the action taken, and the outcome — all visible without calling the SDM.

**The SDM sees:** One more data point in FinanceCore's accuracy record. Trust progression metrics updated. They are now 12 incidents away from being eligible for Stage 2 automation themselves.

---

## Use Case 8 — The Learning Loop Over Time

### This is not a single use case — it is what makes ATLAS more valuable every day

**Month 1 — FinanceCore**
ATLAS is in Observation Mode. 30 incidents are processed. ATLAS recommends. Humans execute. 84% of the time, L2 confirms ATLAS's recommendation was correct without modification. Stage 1 trust unlocked. L1 Assistance enabled.

**Month 2 — FinanceCore**
L1 engineers now work from ATLAS briefings. Triage time drops from average 35 minutes to under 3 minutes. 12 incidents are auto-escalated by L1 instead of being investigated from scratch. L2 resolves them faster because they receive a complete briefing rather than a raw alert.

**Month 3 — FinanceCore**
30 L1-assisted resolutions completed. Auto-resolution success rate: 87%. SDM enables Stage 2 — L1 Automation for P3 incidents. First auto-executed incident: Redis cache flush at 2am. Nobody woke up.

**Month 4 — Cross-client learning**
Three other Atos clients running Java + PostgreSQL stacks benefit automatically. The anonymised embedding centroids from FinanceCore's four months of incident history warm-start their ChromaDB collections. They enter Stage 1 with much stronger historical precedent than FinanceCore had at the same point.

**Month 6 — The engineer leaves**
Priya Sharma, the L3 engineer who personally resolved nine novel incidents and contributed the most training signals to the system, resigns. Her last day is Friday.

On Monday morning, a new L3 engineer joins. They have never worked on FinanceCore before.

At 10am, a novel incident appears on FinanceCore — a pattern similar to one Priya resolved in March.

ATLAS surfaces her resolution at 89% similarity. Her reasoning, her diagnosis, her exact fix — preserved in the knowledge graph. The new engineer reads it. Executes it. 

Priya's expertise did not leave when she did.

---

## Use Case 9 — SDM Compliance Audit

### Who does this
The Atos SDM preparing for a quarterly PCI-DSS compliance audit for FinanceCore.

### What used to happen
The SDM spent two weeks manually compiling evidence: pulling ticket notes from ServiceNow, checking email threads for approval records, asking engineers to reconstruct what they did and when. The audit report took longer to prepare than the incidents themselves took to resolve.

### What happens with ATLAS

The SDM navigates to the ATLAS audit log for FinanceCore. Selects the date range for the audit period. Clicks Export.

A PDF downloads containing: every incident in the period, every action taken (automated or human-approved), every approver with their sign-off timestamp and cryptographic signature, every reasoning chain showing what evidence supported each decision, every rollback status, every ServiceNow ticket correlation. In the format the PCI-DSS auditor requires.

**Time to prepare the compliance audit package:** Under 10 minutes.

---

## The Complete User Flow — End to End

```
DAY 1: NEW CLIENT
SDM configures CMDB webhook + thin config
        ↓
ATLAS reads CMDB, builds Neo4j graph, deploys agents
        ↓
Trust Level: Stage 0 — Observation Mode
        ↓
ATLAS monitors silently, recommends, humans execute

ONGOING: EVERY INCIDENT
Log stream flows in continuously
        ↓
Agents detect anomaly (Chronos-Bolt + SHAP Isolation Forest)
        ↓
Cascade correlation confirms structural connection (Neo4j)
        ↓
ServiceNow ticket auto-created (real INC format)
        ↓
Orchestrator runs (Neo4j graph + ChromaDB vector + Claude reasoning)
        ↓
Confidence scored (pure Python, 4 factors + 7 vetoes)
        ↓
    ┌───────────────────────────────┐
    ↓                               ↓
Auto-Execute                   Human Review
(if all conditions met)        (L1 / L2 / L3 based on complexity)
    ↓                               ↓
    └──────────────┬────────────────┘
                   ↓
         Playbook executes
         (pre-validated, with auto-rollback)
                   ↓
         Success validation confirms recovery
                   ↓
         Audit record written (immutable)
         Neo4j updated (new Incident node)
         ChromaDB updated (new embedding)
         ServiceNow ticket resolved
         Client transparency portal updated
                   ↓
         Learning loop runs:
         - Factor 1 recalibrated
         - Weight corrections applied
         - Trust progression evaluated
         - Problem record drafted if recurring

OVER TIME: TRUST PROGRESSION
30 incidents + 80% accuracy → Stage 1 (L1 Assistance)
30 more + 85% auto-success → Stage 2 (L1 Automation)
Continued accuracy → Stage 3 (L2 Assistance)
SDM explicit enablement → Stage 4 (L2 Automation)
Class 3 actions: never auto. Permanent.
```

---

## Knowledge Ownership — Where It Lives and Who Owns It

| Knowledge Type | Before ATLAS | After ATLAS |
|---|---|---|
| Service topology | Confluence pages, outdated | Neo4j graph, updated in seconds via CMDB webhook |
| Incident history | ServiceNow ticket notes, unstructured | Decision History DB + ChromaDB embeddings, queryable |
| Resolution expertise | In engineers' heads | Neo4j Incident nodes + L3 correction signals, permanent |
| Compliance evidence | Manual compilation | Audit log, exportable on demand, cryptographically signed |
| Performance baselines | Static thresholds someone configured | Chronos-Bolt + seasonal rolling averages, self-updating |
| Trust levels | Undefined, ad hoc | Evidence-gated stages, visible to client via API |
| Deployment risk | Not connected to incidents | CMDB change records linked to Incident nodes in graph |

**The knowledge ownership principle:**
When an engineer joins ATLAS, their decisions make the system smarter. When they leave, their decisions stay. ATLAS owns the knowledge. Nobody can walk out the door with it.

---

*ATLAS Use Cases v3.0 — Every flow described. Every person accounted for. Every scenario covered.*