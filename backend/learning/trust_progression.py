"""
Trust progression engine for ATLAS.
Evaluates whether a client has met the criteria to advance to the next trust stage.
The ONLY component that can update trust_level in the client config.

Trust stages:
  Stage 0 — Observation:   default for new clients, all human
  Stage 1 — L1 Assistance: 30 incidents + >80% confirmed correct reasoning
  Stage 2 — L1 Automation: 30 more incidents + >85% auto-resolution success
  Stage 3 — L2 Assistance: demonstrated Stage 2 accuracy
  Stage 4 — L2 Automation: SDM explicit enablement required (criteria alone insufficient)

Hard constants (non-configurable):
  - Class 3 actions never auto-execute at any trust level. Ever.
  - Trust upgrades require SDM confirmation — never auto-upgraded.
  - Stage 4 requires explicit SDM action in addition to criteria being met.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from backend.config.client_registry import get_client, update_trust_level
from backend.database.audit_db import write_audit_record
from backend.learning.decision_history import (
    get_accuracy_rate,
    get_auto_resolution_rate,
    get_incident_count_for_client,
)

logger = structlog.get_logger(__name__)

# Stage gate thresholds — from ATLAS data contracts
_STAGE_1_MIN_INCIDENTS = 30
_STAGE_1_MIN_ACCURACY = 0.80
_STAGE_2_ADDITIONAL_INCIDENTS = 30
_STAGE_2_MIN_AUTO_RESOLUTION = 0.85


async def evaluate_progression(
    client_id: str,
    incident_id: str,
) -> dict[str, Any]:
    """
    Evaluate whether a client has met the criteria to advance to the next trust stage.
    Called after every resolved incident.

    If criteria are met:
      - Writes a trust upgrade recommendation to the audit trail with supporting evidence.
      - Returns the recommendation for SDM notification.
      - Does NOT automatically upgrade — SDM confirmation required.

    Args:
        client_id:   Client to evaluate — mandatory.
        incident_id: The just-resolved incident (for audit trail correlation).

    Returns:
        Dict with evaluation results and any recommendation.
    """
    if not client_id:
        raise ValueError("client_id is required for evaluate_progression.")

    client_config = get_client(client_id)
    current_stage = client_config["trust_level"]
    metrics = get_progression_metrics(client_id)

    result: dict[str, Any] = {
        "client_id": client_id,
        "current_stage": current_stage,
        "metrics": metrics,
        "recommendation": None,
        "criteria_met": False,
    }

    # Stage 4 requires explicit SDM action — criteria evaluation alone is insufficient
    if current_stage >= 4:
        logger.debug(
            "trust_progression.already_at_max_stage",
            client_id=client_id,
            current_stage=current_stage,
        )
        return result

    # Evaluate next stage criteria
    next_stage = current_stage + 1

    if next_stage == 1:
        criteria_met = _check_stage_1_criteria(metrics)
    elif next_stage == 2:
        criteria_met = _check_stage_2_criteria(metrics)
    elif next_stage == 3:
        # Stage 3 uses same accuracy bar as Stage 2 but for L2 patterns
        criteria_met = _check_stage_3_criteria(metrics)
    elif next_stage == 4:
        # Stage 4: criteria may be met but SDM explicit action is still required
        criteria_met = _check_stage_4_criteria(metrics)
    else:
        criteria_met = False

    result["criteria_met"] = criteria_met

    if criteria_met:
        recommendation = _build_recommendation(
            client_id=client_id,
            current_stage=current_stage,
            next_stage=next_stage,
            metrics=metrics,
        )
        result["recommendation"] = recommendation

        # Write recommendation to audit trail — never auto-upgrade
        write_audit_record({
            "client_id": client_id,
            "incident_id": incident_id,
            "action_type": "classification",
            "actor": "ATLAS_AUTO",
            "action_description": (
                f"Trust progression recommendation: client '{client_id}' has met criteria "
                f"for Stage {next_stage}. "
                f"Incident count: {metrics['total_incidents']}. "
                f"Accuracy rate: {metrics['overall_accuracy'] * 100:.1f}%. "
                f"Auto-resolution rate: {metrics['auto_resolution_rate'] * 100:.1f}%. "
                "SDM confirmation required before upgrade. No automatic change made."
            ),
            "confidence_score_at_time": metrics["overall_accuracy"],
            "outcome": "trust_upgrade_recommended",
            "servicenow_ticket_id": "",
            "rollback_available": False,
            "compliance_frameworks_applied": [],
            "reasoning_summary": (
                f"Stage {current_stage} → Stage {next_stage} criteria met. "
                "Awaiting SDM confirmation."
            ),
        })

        logger.info(
            "trust_progression.recommendation_written",
            client_id=client_id,
            current_stage=current_stage,
            next_stage=next_stage,
            total_incidents=metrics["total_incidents"],
            accuracy=round(metrics["overall_accuracy"], 4),
        )

    return result


def confirm_upgrade(
    client_id: str,
    new_stage: int,
    sdm_confirmed_by: str,
    incident_id: str = "",
) -> None:
    """
    Apply a trust level upgrade after SDM confirmation.
    This is the only path through which trust_level changes.

    Args:
        client_id:        Client to upgrade — mandatory.
        new_stage:        The new trust stage (must be current + 1).
        sdm_confirmed_by: Name/ID of the SDM who confirmed the upgrade.
        incident_id:      Optional incident ID for audit trail correlation.

    Raises:
        ValueError: If new_stage is not a valid progression from current stage.
        KeyError:   If client_id is not registered.
    """
    if not client_id:
        raise ValueError("client_id is required for confirm_upgrade.")
    if not sdm_confirmed_by:
        raise ValueError("sdm_confirmed_by is required — SDM confirmation is mandatory.")

    client_config = get_client(client_id)
    current_stage = client_config["trust_level"]

    if new_stage != current_stage + 1:
        raise ValueError(
            f"Invalid trust progression for client '{client_id}': "
            f"current stage is {current_stage}, requested stage is {new_stage}. "
            "Trust level can only advance one stage at a time."
        )

    # Delegate to client_registry — the only module that may write trust_level
    update_trust_level(client_id, new_stage, sdm_confirmed_by)

    write_audit_record({
        "client_id": client_id,
        "incident_id": incident_id or "sdm-confirmation",
        "action_type": "approval",
        "actor": sdm_confirmed_by,
        "action_description": (
            f"Trust level upgraded for client '{client_id}': "
            f"Stage {current_stage} → Stage {new_stage}. "
            f"SDM confirmation by: {sdm_confirmed_by}."
        ),
        "confidence_score_at_time": 1.0,
        "outcome": "trust_upgraded",
        "servicenow_ticket_id": "",
        "rollback_available": False,
        "compliance_frameworks_applied": [],
        "reasoning_summary": (
            f"Trust upgrade confirmed by SDM '{sdm_confirmed_by}'. "
            f"Stage {current_stage} → Stage {new_stage}."
        ),
    })

    logger.info(
        "trust_progression.upgrade_confirmed",
        client_id=client_id,
        from_stage=current_stage,
        to_stage=new_stage,
        sdm_confirmed_by=sdm_confirmed_by,
    )


def get_progression_metrics(client_id: str) -> dict[str, Any]:
    """
    Return current stage progression metrics for a client.
    Used by the frontend trust progress bar and by evaluate_progression.

    Args:
        client_id: Client scope — mandatory.

    Returns:
        Dict with: current_stage, total_incidents, overall_accuracy,
        auto_resolution_rate, auto_resolution_count,
        stage_1_criteria_met, stage_2_criteria_met,
        incidents_to_next_stage, accuracy_gap_to_next_stage.
    """
    if not client_id:
        raise ValueError("client_id is required for get_progression_metrics.")

    client_config = get_client(client_id)
    current_stage = client_config["trust_level"]

    total_incidents = get_incident_count_for_client(client_id)
    auto_resolution_rate, auto_resolution_count = get_auto_resolution_rate(client_id)

    # Overall accuracy: use a broad query across all patterns for this client
    # We approximate by averaging accuracy across all patterns weighted by record count
    from backend.learning.decision_history import get_all_patterns_for_client
    patterns = get_all_patterns_for_client(client_id)

    total_records = 0
    weighted_accuracy_sum = 0.0
    for pattern in patterns:
        accuracy, count = get_accuracy_rate(
            client_id,
            pattern["anomaly_type"],
            pattern["service_class"],
            pattern["recommended_action_id"],
        )
        weighted_accuracy_sum += accuracy * count
        total_records += count

    overall_accuracy = weighted_accuracy_sum / total_records if total_records > 0 else 0.0

    stage_1_met = _check_stage_1_criteria({
        "total_incidents": total_incidents,
        "overall_accuracy": overall_accuracy,
        "auto_resolution_rate": auto_resolution_rate,
        "auto_resolution_count": auto_resolution_count,
    })
    stage_2_met = _check_stage_2_criteria({
        "total_incidents": total_incidents,
        "overall_accuracy": overall_accuracy,
        "auto_resolution_rate": auto_resolution_rate,
        "auto_resolution_count": auto_resolution_count,
    })

    # Distance to next stage
    if current_stage == 0:
        incidents_needed = max(0, _STAGE_1_MIN_INCIDENTS - total_incidents)
        accuracy_gap = max(0.0, _STAGE_1_MIN_ACCURACY - overall_accuracy)
    elif current_stage == 1:
        incidents_needed = max(0, (_STAGE_1_MIN_INCIDENTS + _STAGE_2_ADDITIONAL_INCIDENTS) - total_incidents)
        accuracy_gap = max(0.0, _STAGE_2_MIN_AUTO_RESOLUTION - auto_resolution_rate)
    else:
        incidents_needed = 0
        accuracy_gap = 0.0

    return {
        "current_stage": current_stage,
        "total_incidents": total_incidents,
        "overall_accuracy": round(overall_accuracy, 4),
        "auto_resolution_rate": round(auto_resolution_rate, 4),
        "auto_resolution_count": auto_resolution_count,
        "stage_1_criteria_met": stage_1_met,
        "stage_2_criteria_met": stage_2_met,
        "incidents_to_next_stage": incidents_needed,
        "accuracy_gap_to_next_stage": round(accuracy_gap, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stage criteria checks
# ─────────────────────────────────────────────────────────────────────────────

def _check_stage_1_criteria(metrics: dict[str, Any]) -> bool:
    """Stage 1: 30 incidents + >80% confirmed correct reasoning."""
    return (
        metrics["total_incidents"] >= _STAGE_1_MIN_INCIDENTS
        and metrics["overall_accuracy"] > _STAGE_1_MIN_ACCURACY
    )


def _check_stage_2_criteria(metrics: dict[str, Any]) -> bool:
    """Stage 2: 30 more incidents (60 total) + >85% auto-resolution success."""
    return (
        metrics["total_incidents"] >= (_STAGE_1_MIN_INCIDENTS + _STAGE_2_ADDITIONAL_INCIDENTS)
        and metrics["auto_resolution_rate"] > _STAGE_2_MIN_AUTO_RESOLUTION
    )


def _check_stage_3_criteria(metrics: dict[str, Any]) -> bool:
    """Stage 3: demonstrated Stage 2 accuracy — same bar as Stage 2."""
    return _check_stage_2_criteria(metrics)


def _check_stage_4_criteria(metrics: dict[str, Any]) -> bool:
    """
    Stage 4: criteria may be met but SDM explicit action is still required.
    Criteria alone are not sufficient — this just determines if the recommendation
    should be sent to the SDM.
    """
    return _check_stage_2_criteria(metrics)


def _build_recommendation(
    client_id: str,
    current_stage: int,
    next_stage: int,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build the SDM notification payload for a trust upgrade recommendation."""
    stage_descriptions = {
        1: "L1 Assistance — ATLAS recommendations shown to L1 engineers for approval",
        2: "L1 Automation — Class 1 actions auto-execute for P3 incidents",
        3: "L2 Assistance — ATLAS recommendations shown to L2 engineers",
        4: "L2 Automation — Class 1 and Class 2 actions auto-execute (SDM explicit enablement required)",
    }
    return {
        "client_id": client_id,
        "recommended_at": datetime.now(timezone.utc).isoformat(),
        "current_stage": current_stage,
        "proposed_stage": next_stage,
        "proposed_stage_description": stage_descriptions.get(next_stage, "Unknown"),
        "supporting_evidence": {
            "total_incidents": metrics["total_incidents"],
            "overall_accuracy_pct": round(metrics["overall_accuracy"] * 100, 1),
            "auto_resolution_rate_pct": round(metrics["auto_resolution_rate"] * 100, 1),
            "auto_resolution_count": metrics["auto_resolution_count"],
        },
        "sdm_action_required": True,
        "note": (
            "This is a recommendation only. Trust level will not change until "
            "an SDM explicitly confirms via confirm_upgrade(). "
            "Class 3 actions remain permanently non-auto-executable regardless of trust level."
        ),
    }
