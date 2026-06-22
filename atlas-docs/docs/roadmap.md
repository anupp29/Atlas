# Roadmap

The roadmap is structured in **build phases** — each phase has hard done-conditions
that gate the next. Nothing advances until the current phase is provably complete.

## Current State — Phases 0–7 Shipped

| Phase | Name | Status |
|---|---|---|
| **0** | Environment & data foundation setup | ✅ Complete |
| **1** | Data foundation — graphs, vectors, fault scenarios | ✅ Complete |
| **2** | Detection layer — four agents + ensemble + correlation | ✅ Complete |
| **3** | Orchestration pipeline — all 7 nodes + state machine | ✅ Complete |
| **4** | Execution engine + learning engine | ✅ Complete |
| **5** | Backend integration — full API surface + WebSockets | ✅ Complete |
| **6** | Frontend — all role views, graph viz, approval flows | ✅ Complete |
| **7** | Hardening + demo preparation | ✅ Complete |

---

## Immediate Enhancements

The following items are scoped and sequenced — each builds on a confirmed
foundation, not an assumed one.

### Additional Specialist Agents

The detection-layer architecture is designed for new agents to be added with
no changes to the orchestrator or downstream pipeline. Next agents in the
queue (in order of client demand):

1. **Kubernetes agent** — pod restart rate, pending pods, node memory pressure
2. **Oracle DB agent** — tablespace exhaustion, redo-log waits, buffer-cache hit rate
3. **SAP agent** — work-process saturation, dialog-instance overload, spool overflow

### Trust Stage 4 as the Default for Mature Clients

Stage 4 (L2 Automation — service redeployment and infrastructure scaling without
human approval for high-confidence cases) is architecturally complete but disabled
by default. Enabling it for production requires:

- Sustained Stage 3 track record across a statistically significant incident count
- Explicit per-client SDM enablement (this check already exists in code)
- Class 3 ceiling is permanent and never part of Stage 4 scope

### Class 2 Action Playbooks

Current MVP ships Class 1 playbooks only. Class 2 (service redeployment,
infrastructure scaling) playbooks are the next execution-layer work. Class 3
actions — database operations, network changes, production data — are a
permanent ceiling and are not on the roadmap for any autonomous path.

---

## Medium Term

### CMDB Beyond ServiceNow
Jira Service Management and Freshservice adapter support — the same thin config
model, different webhook format.

### Cross-Client Federated Learning
Currently, cross-client knowledge flows only via embedding warm-starts. A richer
federated learning signal — anonymised anomaly patterns weighted by resolution
success rate — would accelerate Stage 0 → Stage 1 progression for new clients.

### Structured Compliance Export Formats
The audit log already captures everything needed. Next step: rendering that data
into the specific XML/CSV schemas required by PCI-DSS v4, SOX, and ISO 27001
auditors, removing the formatting step from audit preparation entirely.

---

## What Is Never on the Roadmap

!!! danger "Permanent design ceilings — not configuration options"
    - Class 3 actions (database operations, network changes, production data)
      auto-executing — **ever**, at any trust stage, for any client.
    - An LLM generating a script or command that executes directly against
      production — the playbook library is the only boundary of autonomous
      action, always.
    - Skipping a trust stage — progression is always one stage at a time,
      evidence-gated, non-negotiable.

These are architectural constants enforced in code (`_register()`, Class 3
veto, `trust_progression.py` stage-gate logic), not policy decisions that can
be revisited.
