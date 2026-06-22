# Use Cases

ATLAS is built around five distinct people, each with different needs from the
same underlying system.

| Role | What they need from ATLAS |
|---|---|
| **Service Delivery Manager (SDM)** | Visibility without noise; control over trust levels and automation thresholds; accountability for SLAs. |
| **L1 — Service Desk Engineer** | Fast, clear guidance across many simultaneous incidents, without needing deep expertise in every technology. |
| **L2 — Technical Support Engineer** | Full investigation context, instead of re-solving an incident a departed colleague already solved once. |
| **L3 — Deep Technical Architect** | Engagement only on genuinely novel or P1 incidents — their time and judgement preserved as institutional knowledge. |
| **The Atos Client** | A real-time view of what's happening in their own environment, without having to call the SDM to find out. |

---

## Onboarding to Resolution

=== "1 · Client Onboarding"

    **Who:** the SDM. **Before ATLAS:** a multi-week, bespoke integration
    project per client. **With ATLAS:** point at the client's CMDB webhook,
    fill in the thin [Layer 0 config](../architecture/overview.md#layer-0-client-configuration-layer),
    done — client #10 onboards as fast as client #2.

=== "2 · Normal Operations"

    **Who:** L1, passively. Specialist agents monitor continuously against
    seasonal baselines; nothing surfaces to a human unless a real deviation
    is detected.

=== "3 · Detection Before Users Notice"

    Detection tiers (Warning / Alert / Critical) fire on statistically real
    deviation — see [Detection Engine](../architecture/detection-engine.md) —
    often before a client's own users have filed a single support ticket.

=== "4 · L1 Handles a Known Pattern"

    L1 opens a two-sentence summary and a checklist, clicks **Approve**, and
    moves on. Average time: under 2 minutes per the
    [escalation chain](../escalation/human-workflow.md).

=== "5 · L2 Investigates a Complex Incident"

    L2 receives the full six-section briefing — blast radius, deployment
    correlation, historical match, ranked hypotheses, recommended action —
    and approves, modifies, or rejects with a reason.

=== "6 · L3 Handles a Novel Incident"

    L3 sees everything L2 sees plus cross-client anonymised patterns and the
    full confidence debug panel. Their resolution becomes permanent
    institutional knowledge, weighted 3× in the learning engine.

---

## Use Case — Auto-Resolved Incident (the Goal State)

**Setting:** RetailMax is at Trust Stage 2 (L1 Automation), with demonstrated
> 85% auto-resolution success. At 3 a.m., a Redis cache instance shows memory
pressure — a pattern ATLAS has resolved successfully six times before on this
client.

!!! success "Nobody wakes up"
    Confidence scores **0.91**. All 8 vetoes are checked: none fire — it's
    outside business hours, GDPR isn't triggered, no change freeze is active,
    no duplicate recent action exists. The action is Class 1. Threshold is
    met. ATLAS pre-validates, executes, confirms memory back to normal within
    **6 minutes**, writes the immutable audit record, auto-resolves the
    ServiceNow ticket with full notes, and updates the knowledge base.

    A manual response, starting only once an engineer became available, was
    estimated at 38 minutes. **The client sees** a resolved-incident entry on
    their transparency portal — timeline, action, outcome — without calling
    anyone. **The SDM sees** one more accuracy data point and updated trust
    progression metrics.

---

## Use Case — The Learning Loop Over Time

This is not a single use case — it is what makes ATLAS more valuable every day
it runs.

| Month | What happens |
|---|---|
| **1** | Observation Mode. 30 incidents processed; ATLAS recommends, humans execute. 84% confirmed-correct without modification → **Stage 1 unlocked.** |
| **2** | L1 triage time drops from ~35 minutes to under 3, working from ATLAS briefings instead of raw alerts. |
| **3** | 30 L1-assisted resolutions complete at 87% auto-resolution success → SDM enables **Stage 2**. First fully autonomous overnight resolution. |
| **4** | Three other clients on the same Java + PostgreSQL stack are warm-started from anonymised embedding centroids — they enter Stage 1 with stronger precedent than the first client ever had. |
| **6** | The L3 engineer who resolved nine novel incidents resigns. A new L3 engineer, with zero prior history on this client, joins. A novel incident appears resembling one resolved months earlier — ATLAS surfaces the prior resolution at high similarity. The new engineer reads it and executes it. |

!!! quote "The point"
    The departing engineer's expertise did not leave when they did. It is
    preserved as a graph node and a vector embedding, not as a memory in
    someone's head.

---

## Use Case — SDM Compliance Audit

**Before ATLAS:** two weeks of manually compiling evidence from ticket notes,
email threads, and engineers reconstructing what they did and when — often
taking longer than the incidents themselves took to resolve.

**With ATLAS:** the SDM opens the audit log, selects a date range, clicks
**Export**. The resulting package contains every incident in the period, every
action (automated or human-approved), every approver's sign-off timestamp and
cryptographic signature, the full reasoning chain behind every decision, every
rollback status, and the ServiceNow ticket correlation — in audit-ready format.

**Time to prepare a compliance audit package: under 10 minutes.**

---

## Knowledge Ownership — Where It Lives, Who Owns It

| Knowledge type | Before ATLAS | After ATLAS |
|---|---|---|
| Service topology | Wiki pages, frequently outdated | Neo4j graph, updated within seconds via CMDB webhook |
| Incident history | Unstructured ServiceNow ticket notes | Decision History DB + ChromaDB embeddings — queryable |
| Resolution expertise | In individual engineers' heads | Neo4j `Incident` nodes + weighted L3 correction signals — permanent |
| Compliance evidence | Manually compiled | Audit log, exportable on demand, cryptographically signed |
| Performance baselines | Static thresholds someone once configured | Self-updating seasonal rolling averages |
| Trust levels | Undefined, ad hoc | Evidence-gated stages, exposed to the client via API |
| Deployment risk | Disconnected from incident history | CMDB change records linked directly to `Incident` nodes |

!!! abstract "The principle"
    When an engineer joins, their decisions make the system smarter. When they
    leave, their decisions stay. ATLAS owns the knowledge — nobody can walk out
    the door with it.
