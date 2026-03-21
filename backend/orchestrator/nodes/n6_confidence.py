"""
Node 6 — Confidence Scoring Engine.

Pure Python confidence calculation. Completely independent of the LLM.
Calculates the composite score, checks all 8 vetoes, and produces the
routing decision.

Factor weights: Historical Accuracy 30%, Root Cause Certainty 25%,
                Action Safety Class 25%, Evidence Freshness 20%.

Inputs:  all N1–N5 state fields
Outputs: composite_confidence_score, active_veto_conditions, routing_decision,
         factor_scores, audit_trail entry
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from backend.config.client_registry import get_client
from backend.execution.playbook_library import get_playbook
from backend.learning import decision_history
from backend.orchestrator.confidence.scorer import (
    calculate_action_safety,
    calculate_composite,
    calculate_evidence_freshness,
    calculate_historical_accuracy,
    calculate_root_cause_certainty,
)
from backend.orchestrator.confidence.vetoes import run_all_vetoes
from backend.orchestrator.state import (
    AtlasState,
    append_audit_entry,
    guard_routing_decision,
)

logger = structlog.get_logger(__name__)

# Fixed floor for L1_HUMAN_REVIEW routing — not configurable via client config
_L1_REVIEW_SCORE_FLOOR: float = 0.75
_L1_REVIEW_SIMILARITY_FLOOR: float = 0.75


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 6: Calculate composite confidence score and determine routing.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with confidence scores, vetoes, and routing decision.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    evidence_packages: list[dict] = state["evidence_packages"]
    recommended_action_id: str = state.get("recommended_action_id", "")
    alternative_hypotheses: list[dict] = state.get("alternative_hypotheses", [])
    semantic_matches: list[dict] = state.get("semantic_matches", [])

    logger.info(
        "n6_confidence.started",
        client_id=client_id,
        incident_id=incident_id,
        recommended_action=recommended_action_id,
    )

    client_config = get_client(client_id)

    # ── Resolve action class ──────────────────────────────────────────────────
    action_class = _resolve_action_class(recommended_action_id)

    # ── Class 3 check FIRST — skip all other calculations if fires ────────────
    if action_class == 3:
        logger.warning(
            "n6_confidence.class3_immediate_escalation",
            client_id=client_id,
            incident_id=incident_id,
            action_id=recommended_action_id,
        )
        # Still run all vetoes for complete audit record
        all_vetoes = _run_vetoes(state, client_config, action_class)
        routing = "L2_L3_ESCALATION"
        updates = _build_updates(
            state=state,
            composite=0.0,
            factor_scores={"f1": 0.0, "f2": 0.0, "f3": 0.0, "f4": 0.0},
            vetoes=all_vetoes,
            routing=routing,
            reason="Class 3 action — permanent ceiling, never auto-executes",
        )
        guard_routing_decision(state, updates)
        return updates

    # ── Factor 1: Historical Accuracy (30%) ───────────────────────────────────
    anomaly_type = _primary_anomaly_type(evidence_packages)
    service_class = _primary_service_class(evidence_packages)
    historical_records = decision_history.get_records_for_pattern(
        client_id=client_id,
        anomaly_type=anomaly_type,
        service_class=service_class,
        action_id=recommended_action_id,
    )
    f1 = calculate_historical_accuracy(historical_records)
    historical_count = len(historical_records)

    # ── Factor 2: Root Cause Certainty (25%) ──────────────────────────────────
    f2 = calculate_root_cause_certainty(alternative_hypotheses)

    # ── Factor 3: Action Safety Class (25%) ───────────────────────────────────
    f3 = calculate_action_safety(action_class)

    # ── Factor 4: Evidence Freshness (20%) ────────────────────────────────────
    most_recent_ts = _most_recent_evidence_timestamp(evidence_packages)
    f4 = calculate_evidence_freshness(most_recent_ts)

    # ── Composite score ───────────────────────────────────────────────────────
    composite = calculate_composite(f1, f2, f3, f4)
    factor_scores = {"f1": round(f1, 4), "f2": round(f2, 4), "f3": round(f3, 4), "f4": round(f4, 4)}

    logger.info(
        "n6_confidence.factors_calculated",
        client_id=client_id,
        incident_id=incident_id,
        f1_historical=round(f1, 4),
        f2_certainty=round(f2, 4),
        f3_safety=round(f3, 4),
        f4_freshness=round(f4, 4),
        composite=round(composite, 4),
    )

    # ── Run all 8 vetoes ──────────────────────────────────────────────────────
    all_vetoes = _run_vetoes(state, client_config, action_class, historical_count)

    # ── Determine routing ─────────────────────────────────────────────────────
    auto_execute_threshold: float = float(client_config.get("auto_execute_threshold", 0.92))
    top_similarity = semantic_matches[0]["similarity_score"] if semantic_matches else 0.0

    routing = _determine_routing(
        composite=composite,
        vetoes=all_vetoes,
        action_class=action_class,
        auto_execute_threshold=auto_execute_threshold,
        top_similarity=top_similarity,
    )

    logger.info(
        "n6_confidence.routing_determined",
        client_id=client_id,
        incident_id=incident_id,
        routing=routing,
        composite=round(composite, 4),
        vetoes_count=len(all_vetoes),
        threshold=auto_execute_threshold,
    )

    updates = _build_updates(
        state=state,
        composite=composite,
        factor_scores=factor_scores,
        vetoes=all_vetoes,
        routing=routing,
        reason=f"composite={composite:.4f}, vetoes={len(all_vetoes)}, action_class={action_class}",
    )
    guard_routing_decision(state, updates)
    return updates


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_action_class(action_id: str) -> int:
    """Look up action class from playbook library. Default to 2 (safe) if unknown."""
    if not action_id:
        return 2
    playbook = get_playbook(action_id)
    if playbook is None:
        logger.warning("n6_confidence.unknown_playbook", action_id=action_id)
        return 2
    return playbook.action_class


def _primary_anomaly_type(evidence_packages: list[dict]) -> str:
    """Return the anomaly type from the highest-confidence evidence package."""
    if not evidence_packages:
        return ""
    best = max(evidence_packages, key=lambda p: p.get("detection_confidence", 0.0))
    return best.get("anomaly_type", "")


def _primary_service_class(evidence_packages: list[dict]) -> str:
    """Return the service name from the highest-confidence evidence package."""
    if not evidence_packages:
        return ""
    best = max(evidence_packages, key=lambda p: p.get("detection_confidence", 0.0))
    return best.get("service_name", "")


def _most_recent_evidence_timestamp(evidence_packages: list[dict]) -> datetime:
    """Return the most recent detection_timestamp from all evidence packages."""
    timestamps: list[datetime] = []
    for pkg in evidence_packages:
        ts = pkg.get("detection_timestamp")
        if isinstance(ts, datetime):
            timestamps.append(ts)
        elif isinstance(ts, str):
            try:
                timestamps.append(datetime.fromisoformat(ts))
            except ValueError:
                pass
    if not timestamps:
        return datetime.now(timezone.utc)
    return max(timestamps)


def _run_vetoes(
    state: AtlasState,
    client_config: dict[str, Any],
    action_class: int,
    historical_count: int = 0,
) -> list[str]:
    """Run all 8 vetoes and return the complete list of fired explanations."""
    evidence_packages: list[dict] = state["evidence_packages"]
    incident_priority: str = state.get("incident_priority", "P3")
    client_id: str = state["client_id"]
    recommended_action_id: str = state.get("recommended_action_id", "")

    # Determine service name for duplicate action check
    service_name = _primary_service_class(evidence_packages)

    # Graph freshness: use graph_unavailable flag and the n3 query timestamp from audit trail.
    # DECISION: We cannot know when Neo4j data was last written from the state alone.
    # The correct signal is whether n3_graph reported graph_unavailable=True (stale/unreachable)
    # or whether no graph queries have run at all. We use the n3 audit entry timestamp
    # as the "last graph update" time — this is when we last successfully read from the graph.
    # If graph_unavailable is True, we pass None to trigger the staleness veto.
    graph_unavailable: bool = state.get("graph_unavailable", False)
    last_graph_update: datetime | None = None
    if not graph_unavailable:
        # Find the n3_graph audit entry timestamp as the last successful graph read
        audit_trail: list[dict] = state.get("audit_trail", [])
        for entry in reversed(audit_trail):
            if entry.get("node") == "n3_graph":
                ts_str = entry.get("timestamp")
                if ts_str:
                    try:
                        last_graph_update = datetime.fromisoformat(ts_str)
                    except ValueError:
                        pass
                break

    # Recent actions for duplicate check (from audit trail)
    # audit_trail already fetched above when graph_unavailable is False;
    # fetch it here unconditionally to cover the graph_unavailable=True path.
    audit_trail_entries: list[dict] = state.get("audit_trail", [])
    recent_actions = [
        {"client_id": client_id, "action_id": recommended_action_id, "service_name": service_name}
        for entry in audit_trail_entries
        if entry.get("action") == "playbook_executed"
        and entry.get("action_id") == recommended_action_id
    ]

    return run_all_vetoes(
        client_config=client_config,
        current_time=datetime.now(timezone.utc),
        action_class=action_class,
        incident_priority=incident_priority,
        evidence_packages=evidence_packages,
        client_id=client_id,
        action_id=recommended_action_id,
        service_name=service_name,
        last_2_hours_actions=recent_actions,
        last_graph_update_timestamp=last_graph_update,
        historical_record_count=historical_count,
    )


def _determine_routing(
    composite: float,
    vetoes: list[str],
    action_class: int,
    auto_execute_threshold: float,
    top_similarity: float,
) -> str:
    """
    Apply routing rules from ARCHITECTURE.md.

    AUTO_EXECUTE:    composite >= threshold AND no vetoes AND Class 1
    L1_HUMAN_REVIEW: composite >= 0.75 AND similarity >= 0.75 AND Class 1 AND no vetoes
    L2_L3_ESCALATION: all other cases
    """
    has_vetoes = len(vetoes) > 0

    if composite >= auto_execute_threshold and not has_vetoes and action_class == 1:
        return "AUTO_EXECUTE"

    if (
        composite >= _L1_REVIEW_SCORE_FLOOR
        and top_similarity >= _L1_REVIEW_SIMILARITY_FLOOR
        and action_class == 1
        and not has_vetoes
    ):
        return "L1_HUMAN_REVIEW"

    return "L2_L3_ESCALATION"


def _build_updates(
    state: AtlasState,
    composite: float,
    factor_scores: dict,
    vetoes: list[str],
    routing: str,
    reason: str,
) -> dict[str, Any]:
    """Build the state update dict for N6."""
    return {
        "composite_confidence_score": round(composite, 4),
        "active_veto_conditions": vetoes,
        "routing_decision": routing,
        "factor_scores": factor_scores,
        "audit_trail": append_audit_entry(state, {
            "node": "n6_confidence",
            "actor": "ATLAS_AUTO",
            "action": "confidence_scored",
            "composite_score": round(composite, 4),
            "factor_scores": factor_scores,
            "vetoes_fired": vetoes,
            "routing_decision": routing,
            "routing_reason": reason,
        }),
    }
