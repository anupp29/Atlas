"""
ATLAS LangGraph state definition.

The single data structure that carries everything from incident detection
through human approval through resolution and learning. Every node reads
from and writes to this state.

Immutable fields (set once, never overwritten):
    client_id, incident_id, evidence_packages, mttr_start_time

routing_decision: once set to a non-empty string, cannot be changed.
audit_trail: append-only — use append_audit_entry(), never direct assignment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from typing_extensions import TypedDict

import structlog

logger = structlog.get_logger(__name__)

# Fields that are immutable after their initial (non-None/non-empty) set
_IMMUTABLE_FIELDS: frozenset[str] = frozenset({
    "client_id",
    "incident_id",
    "evidence_packages",
    "mttr_start_time",
})


class ImmutableStateError(RuntimeError):
    """Raised when a node attempts to overwrite an immutable state field."""


class AtlasState(TypedDict, total=False):
    """
    Complete LangGraph state for one ATLAS incident lifecycle.

    Fields marked [IMMUTABLE] cannot be overwritten after initial set.
    Fields marked [APPEND-ONLY] must be extended, never replaced.
    """

    # ── Core identity ─────────────────────────────────────────────────────────
    client_id: str                          # [IMMUTABLE] set by pipeline entry point
    incident_id: str                        # [IMMUTABLE] uuid4 assigned at pipeline start
    evidence_packages: list[dict]           # [IMMUTABLE] raw EvidencePackage dicts from agents
    thread_id: str                          # injected by pipeline after run_incident, for frontend

    # ── Classification (N1) ───────────────────────────────────────────────────
    correlation_type: str                   # "CASCADE_INCIDENT" | "ISOLATED_ANOMALY"
    incident_priority: str                  # "P1" | "P2" | "P3" | "P4"
    situation_summary: str                  # plain-English briefing for L1/L2
    sla_breach_time: str                    # ISO-8601 UTC string of SLA breach time
    criticality_uncertain: bool             # True if CMDB enrichment failed

    # ── ITSM (N2) ─────────────────────────────────────────────────────────────
    servicenow_ticket_id: str               # INC number e.g. "INC0001234"
    itsm_ticket_pending: bool               # True if ServiceNow was unavailable

    # ── Graph intelligence (N3) ───────────────────────────────────────────────
    blast_radius: list[dict]                # downstream services with criticality + SLA
    recent_deployments: list[dict]          # CMDB change records last 7 days
    historical_graph_matches: list[dict]    # past incidents same service + anomaly type
    graph_traversal_path: list[dict]        # ordered nodes/edges visited (for frontend viz)
    graph_unavailable: bool                 # True if Neo4j was unreachable

    # ── Semantic retrieval (N4) ───────────────────────────────────────────────
    semantic_matches: list[dict]            # top-3 ChromaDB results with similarity scores
    no_historical_precedent: bool           # True if nothing above 0.50 similarity

    # ── Reasoning (N5) ────────────────────────────────────────────────────────
    root_cause: str
    recommended_action_id: str             # must match a playbook in the library
    alternative_hypotheses: list[dict]     # ranked, each with evidence_for/evidence_against
    explanation_for_engineer: str          # L2-level explanation, min 50 chars
    technical_evidence_summary: str
    confidence_factors: dict               # raw factor breakdown from LLM
    llm_unavailable: bool                  # True if all LLM calls failed

    # ── Confidence scoring (N6) ───────────────────────────────────────────────
    composite_confidence_score: float      # 0.0–1.0 weighted composite
    active_veto_conditions: list[str]      # plain-English veto explanations
    routing_decision: str                  # [ONCE-SET] "AUTO_EXECUTE" | "L1_HUMAN_REVIEW" | "L2_L3_ESCALATION"
    factor_scores: dict                    # {f1, f2, f3, f4} for audit/debug

    # ── Routing + execution (N7 + execution engine) ───────────────────────────
    execution_status: str                  # "pending" | "executing" | "success" | "rollback" | "failed"
    execution_result: dict                 # PlaybookResult fields

    # ── Human review ──────────────────────────────────────────────────────────
    human_action: str                      # "approved" | "modified" | "rejected" | "escalated"
    human_modifier: str                    # engineer name
    human_rejection_reason: str
    human_modified_parameters: dict        # parameter overrides from L2 Modify

    # ── MTTR tracking ─────────────────────────────────────────────────────────
    mttr_start_time: str                   # [IMMUTABLE] ISO-8601 UTC, set in N1, never changed
    mttr_seconds: int                      # filled on resolution

    # ── Resolution ────────────────────────────────────────────────────────────
    resolution_outcome: str                # "success" | "failure" | "partial"
    recurrence_check_due_at: str           # ISO-8601 UTC, 48h after resolution

    # ── Early warning ─────────────────────────────────────────────────────────
    early_warning_signals: list[dict]      # services between 1.5σ–2.5σ

    # ── Audit trail ───────────────────────────────────────────────────────────
    audit_trail: list[dict]                # [APPEND-ONLY] every node transition logged


# ─────────────────────────────────────────────────────────────────────────────
# State helpers — used by every node
# ─────────────────────────────────────────────────────────────────────────────

def guard_immutable_fields(current: AtlasState, updates: dict[str, Any]) -> None:
    """
    Raise ImmutableStateError if any update attempts to overwrite an immutable field
    that already has a value in the current state.

    Call this at the top of every node function before returning state updates.

    Args:
        current: The current state dict.
        updates: The dict slice the node intends to return.

    Raises:
        ImmutableStateError: If any immutable field would be overwritten.
    """
    for field in _IMMUTABLE_FIELDS:
        if field not in updates:
            continue
        existing = current.get(field)
        if existing is None or existing == [] or existing == "":
            continue  # first write is allowed
        if existing != updates[field]:
            raise ImmutableStateError(
                f"Attempted to overwrite immutable state field '{field}'. "
                f"Existing value: {existing!r}. "
                "Create a new incident to re-route."
            )


def guard_routing_decision(current: AtlasState, updates: dict[str, Any]) -> None:
    """
    Raise ImmutableStateError if routing_decision is already set and the update
    attempts to change it to a different value.

    Args:
        current: The current state dict.
        updates: The dict slice the node intends to return.

    Raises:
        ImmutableStateError: If routing_decision would be changed.
    """
    if "routing_decision" not in updates:
        return
    existing = current.get("routing_decision", "")
    if not existing:
        return  # first write allowed
    if existing != updates["routing_decision"]:
        raise ImmutableStateError(
            f"routing_decision is already set to '{existing}' and cannot be changed. "
            "Create a new incident for re-routing."
        )


def append_audit_entry(current: AtlasState, entry: dict[str, Any]) -> list[dict]:
    """
    Return a new audit_trail list with the entry appended.
    Never replaces the existing trail — always extends it.

    Args:
        current: The current state dict.
        entry:   The new audit entry to append. 'timestamp' is added automatically.

    Returns:
        New list to assign to state["audit_trail"].
    """
    existing: list[dict] = list(current.get("audit_trail") or [])
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    existing.append(entry)
    return existing


def build_initial_state(
    client_id: str,
    incident_id: str,
    evidence_packages: list[dict],
    correlation_type: str,
    early_warning_signals: list[dict] | None = None,
) -> AtlasState:
    """
    Construct the initial state dict for a new incident.
    Sets all immutable fields. All other fields default to safe empty values.

    Args:
        client_id:            Mandatory. Multi-tenancy key.
        incident_id:          UUID4 string.
        evidence_packages:    List of EvidencePackage dicts from correlation engine.
        correlation_type:     "CASCADE_INCIDENT" | "ISOLATED_ANOMALY"
        early_warning_signals: Optional early warning signals from correlation engine.

    Returns:
        Fully initialised AtlasState dict.
    """
    if not client_id:
        raise ValueError("client_id is required to build initial state.")
    if not incident_id:
        raise ValueError("incident_id is required to build initial state.")
    if not evidence_packages:
        raise ValueError("evidence_packages cannot be empty.")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    return AtlasState(
        # Immutable identity
        client_id=client_id,
        incident_id=incident_id,
        evidence_packages=evidence_packages,
        mttr_start_time=now_iso,
        thread_id="",  # injected by pipeline after run_incident

        # Classification defaults
        correlation_type=correlation_type,
        incident_priority="",
        situation_summary="",
        sla_breach_time=now_iso,
        criticality_uncertain=False,

        # ITSM defaults
        servicenow_ticket_id="",
        itsm_ticket_pending=False,

        # Graph defaults
        blast_radius=[],
        recent_deployments=[],
        historical_graph_matches=[],
        graph_traversal_path=[],
        graph_unavailable=False,

        # Semantic defaults
        semantic_matches=[],
        no_historical_precedent=False,

        # Reasoning defaults
        root_cause="",
        recommended_action_id="",
        alternative_hypotheses=[],
        explanation_for_engineer="",
        technical_evidence_summary="",
        confidence_factors={},
        llm_unavailable=False,

        # Confidence defaults
        composite_confidence_score=0.0,
        active_veto_conditions=[],
        routing_decision="",
        factor_scores={},

        # Execution defaults
        execution_status="pending",
        execution_result={},

        # Human review defaults
        human_action="",
        human_modifier="",
        human_rejection_reason="",
        human_modified_parameters={},

        # MTTR
        mttr_seconds=0,

        # Resolution defaults
        resolution_outcome="",
        recurrence_check_due_at=now_iso,

        # Early warning
        early_warning_signals=early_warning_signals or [],

        # Audit trail — first entry records incident creation
        audit_trail=[{
            "timestamp": now.isoformat(),
            "node": "pipeline_entry",
            "actor": "ATLAS_AUTO",
            "action": "incident_created",
            "incident_id": incident_id,
            "client_id": client_id,
            "correlation_type": correlation_type,
            "evidence_count": len(evidence_packages),
        }],
    )
