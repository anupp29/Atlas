# orchestrator

LangGraph state machine. Seven nodes. State persists across the entire incident lifecycle from detection through human approval through resolution through learning.

---

## Files

| File | What it does |
|------|-------------|
| `pipeline.py` | Assembles all 7 nodes, compiles the graph, manages the SQLite checkpointer. Public interface: `run_incident()`, `resume_after_approval()`, `get_incident_state()`. |
| `state.py` | `AtlasState` TypedDict. Immutable field guards. Append-only audit trail. `build_initial_state()`. |

---

## nodes/

| File | Inputs | Outputs |
|------|--------|---------|
| `n1_classifier.py` | evidence_packages, correlation_type | incident_priority, situation_summary, sla_breach_time |
| `n2_itsm.py` | incident_priority, situation_summary | servicenow_ticket_id, itsm_ticket_pending |
| `n3_graph.py` | evidence_packages | blast_radius, recent_deployments, historical_graph_matches, graph_traversal_path |
| `n4_semantic.py` | evidence_packages, historical_graph_matches | semantic_matches, no_historical_precedent |
| `n5_reasoning.py` | all N1-N4 fields | root_cause, recommended_action_id, alternative_hypotheses, explanation_for_engineer |
| `n6_confidence.py` | all N1-N5 fields | composite_confidence_score, active_veto_conditions, routing_decision, factor_scores |
| `n7_router.py` | routing_decision | raises NodeInterrupt for human paths, continues for AUTO_EXECUTE |

---

## confidence/

| File | What it does |
|------|-------------|
| `scorer.py` | Pure math functions for the four confidence factors. No I/O. Deterministic. |
| `vetoes.py` | Eight independent veto check functions. `run_all_vetoes()` returns the complete list of fired vetoes. |

---

## Pipeline flow

```
run_incident(evidence_packages, client_id)
    -> N1: classify priority, start SLA timer
    -> N2: create ServiceNow ticket (real API call)
    -> N3: three Neo4j queries in parallel (blast radius, deployments, history)
    -> N4: ChromaDB similarity search, cross-reference with N3 for double-confirmation
    -> N5: LLM reasoning (Claude primary, GPT-4o fallback, pre-computed fallback)
    -> N6: confidence score (4 factors) + 8 veto checks -> routing decision
    -> N7: AUTO_EXECUTE continues, human paths raise NodeInterrupt

# Graph suspends here for human review
# State persists in SQLite checkpointer indefinitely

resume_after_approval(
    thread_id=thread_id,
    human_action="approved",       # "approved" | "modified" | "rejected" | "escalated"
    modifier="engineer.name",      # engineer who acted
    rejection_reason="",           # required if human_action == "rejected"
    modified_parameters={},        # parameter overrides if human_action == "modified"
)
    -> execute_playbook: pre-validation, action, success validation, auto-rollback
    -> n_learn: write decision history, recalibrate Factor 1, check trust progression
```

---

## Confidence scoring (N6)

Four weighted factors:

| Factor | Weight | Source |
|--------|--------|--------|
| Historical Accuracy Rate | 30% | Decision History DB, empirical success rate for this pattern/action/client triple |
| Root Cause Certainty | 25% | Gap between top and second hypothesis confidence scores |
| Action Safety Class | 25% | Class 1 = 1.0, Class 2 = 0.6, Class 3 = 0.0 |
| Evidence Freshness | 20% | Linear decay from 1.0 at 0 minutes to 0.0 at 20 minutes |

Seven hard vetoes (independent of composite score):
1. Active change freeze window
2. Business hours + PCI-DSS or SOX
3. Class 3 action type
4. P1 severity
5. Compliance-sensitive data touched
6. Same action on this service within 2 hours
7. Knowledge graph stale over 24 hours

Plus a cold-start veto (veto 8): fewer than 5 historical records for this pattern.

Any single veto fires -> human review, regardless of composite score. All 8 vetoes always run — `run_all_vetoes()` returns the complete list, never just the first.

Three routing paths:
- `AUTO_EXECUTE`: score >= threshold, zero vetoes, Class 1
- `L1_HUMAN_REVIEW`: below threshold, known pattern (similarity > 0.75), Class 1
- `L2_L3_ESCALATION`: novel pattern, Class 2+, P1, or any veto

---

## State (AtlasState)

The TypedDict that carries everything. Key rules:

- `client_id`, `incident_id`, `evidence_packages`, `mttr_start_time` are immutable after initial set. `guard_immutable_fields()` enforces this.
- `routing_decision` is once-set. `guard_routing_decision()` enforces this.
- `audit_trail` is append-only. Always use `append_audit_entry()`, never direct assignment.

```python
# Build initial state
state = build_initial_state(
    client_id="FINCORE_UK_001",
    incident_id=str(uuid.uuid4()),
    evidence_packages=[...],
    correlation_type="CASCADE_INCIDENT",
)

# Append to audit trail (returns new list, does not mutate)
new_trail = append_audit_entry(state, {"node": "n1", "action": "classified"})
```

---

## LLM routing (N5)

N5 calls the internal ATLAS LLM endpoint (`ATLAS_LLM_ENDPOINT`). 8-second timeout. On timeout or error, loads a pre-computed fallback from `data/fallbacks/{client_id}_incident_response.json`. Fallback loads in under 200ms.

LLM output is validated against a required schema before any downstream code sees it. If validation fails, the fallback is tried. If both fail, the incident is routed to L2/L3 with `llm_unavailable=True`.

---

## Human-in-the-loop

N7 raises `NodeInterrupt` for human review paths. LangGraph suspends the graph at this point. State is persisted by the SQLite checkpointer. The graph waits indefinitely.

When the human submits their decision via `POST /api/incidents/approve` or `POST /api/incidents/reject`, `resume_after_approval()` calls `graph.aupdate_state()` to inject the human decision, then `graph.astream(None)` to resume from the interrupt point.
