"""
Node 1 — Incident Classifier.

Assigns ITIL priority P1–P4, starts the SLA breach countdown timer,
generates a plain-English situation summary, and notifies SDM immediately
for P1 incidents.

Inputs:  evidence_packages, correlation_type, client_id (from state)
Outputs: incident_priority, situation_summary, sla_breach_time,
         mttr_start_time (already set), criticality_uncertain, audit_trail entry
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

from backend.config.client_registry import get_client
from backend.orchestrator.state import (
    AtlasState,
    append_audit_entry,
    guard_immutable_fields,
)

logger = structlog.get_logger(__name__)

_HTTP_TIMEOUT: float = 5.0

# Priority rules: (min_criticality_tier, cascade_required) → priority
# Criticality tiers from CMDB: "P1" > "P2" > "P3" > "P4"
_PRIORITY_RULES: list[tuple[str, bool, str]] = [
    ("P1", True,  "P1"),   # P1 service + cascade → P1 incident
    ("P1", False, "P2"),   # P1 service alone → P2 incident
    ("P2", True,  "P2"),   # P2 services in cascade → P2 incident
    ("P2", False, "P3"),   # P2 service isolated → P3 incident
    ("P3", True,  "P3"),   # P3 services in cascade → P3 incident
    ("P3", False, "P3"),
    ("P4", True,  "P4"),
    ("P4", False, "P4"),
]

# SLA breach thresholds by incident priority (minutes) — fallback if not in client config
_DEFAULT_SLA_MINUTES: dict[str, int] = {
    "P1": 15,
    "P2": 30,
    "P3": 120,
    "P4": 480,
}


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 1: Classify the incident, start SLA timer, notify SDM if P1.

    LangGraph node function — receives full state, returns a dict slice
    of fields to update. Never mutates state in place.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with classification results and updated audit_trail.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    evidence_packages: list[dict] = state["evidence_packages"]
    correlation_type: str = state.get("correlation_type", "ISOLATED_ANOMALY")

    logger.info(
        "n1_classifier.started",
        client_id=client_id,
        incident_id=incident_id,
        evidence_count=len(evidence_packages),
        correlation_type=correlation_type,
    )

    client_config = get_client(client_id)
    is_cascade = correlation_type == "CASCADE_INCIDENT"

    # ── Determine highest criticality tier among affected services ────────────
    highest_tier, criticality_uncertain = _resolve_highest_criticality(
        evidence_packages, client_config
    )

    # ── Assign ITIL priority ──────────────────────────────────────────────────
    priority = _assign_priority(highest_tier, is_cascade)

    # ── Start SLA breach countdown ────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    sla_minutes = _get_sla_minutes(client_config, priority)
    sla_breach_time = now + timedelta(minutes=sla_minutes)

    # ── Generate situation summary ────────────────────────────────────────────
    situation_summary = _build_situation_summary(
        evidence_packages, priority, correlation_type, sla_minutes, client_config
    )

    logger.info(
        "n1_classifier.classified",
        client_id=client_id,
        incident_id=incident_id,
        priority=priority,
        sla_breach_time=sla_breach_time.isoformat(),
        criticality_uncertain=criticality_uncertain,
    )

    # ── P1: immediate SDM notification ───────────────────────────────────────
    if priority == "P1":
        await _notify_sdm_p1(client_id, incident_id, situation_summary, client_config)

    # ── Build updates ─────────────────────────────────────────────────────────
    updates: dict[str, Any] = {
        "incident_priority": priority,
        "situation_summary": situation_summary,
        "sla_breach_time": sla_breach_time.isoformat(),
        "criticality_uncertain": criticality_uncertain,
        "audit_trail": append_audit_entry(state, {
            "node": "n1_classifier",
            "actor": "ATLAS_AUTO",
            "action": "incident_classified",
            "priority": priority,
            "sla_breach_time": sla_breach_time.isoformat(),
            "sla_minutes": sla_minutes,
            "criticality_uncertain": criticality_uncertain,
            "correlation_type": correlation_type,
        }),
    }

    guard_immutable_fields(state, updates)
    return updates


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_highest_criticality(
    evidence_packages: list[dict],
    client_config: dict[str, Any],
) -> tuple[str, bool]:
    """
    Find the highest criticality tier among all affected services.

    Returns:
        (highest_tier, criticality_uncertain)
        criticality_uncertain is True if no service had a known criticality.
    """
    tier_order = ["P1", "P2", "P3", "P4"]
    applications: list[dict] = client_config.get("applications", [])
    app_criticality: dict[str, str] = {
        app["name"]: app.get("criticality", "P4")
        for app in applications
    }

    found_tiers: list[str] = []
    for pkg in evidence_packages:
        service = pkg.get("service_name", "")
        tier = app_criticality.get(service)
        if tier:
            found_tiers.append(tier)
        else:
            # Also check severity_classification from the evidence package itself
            sev = pkg.get("severity_classification", "")
            if sev in tier_order:
                found_tiers.append(sev)

    if not found_tiers:
        logger.warning(
            "n1_classifier.criticality_unknown",
            services=[p.get("service_name") for p in evidence_packages],
        )
        return "P2", True  # Default to P2, flag as uncertain

    # Return the highest (lowest index in tier_order)
    best = min(found_tiers, key=lambda t: tier_order.index(t) if t in tier_order else 99)
    return best, False


def _assign_priority(highest_tier: str, is_cascade: bool) -> str:
    """Map (highest_criticality_tier, is_cascade) → ITIL incident priority."""
    for tier, cascade_req, result_priority in _PRIORITY_RULES:
        if highest_tier == tier and is_cascade == cascade_req:
            return result_priority
    return "P3"  # safe default


def _get_sla_minutes(client_config: dict[str, Any], priority: str) -> int:
    """Return SLA breach threshold in minutes for this priority from client config."""
    thresholds: dict = client_config.get("sla_breach_thresholds", {})
    return int(thresholds.get(priority, _DEFAULT_SLA_MINUTES.get(priority, 120)))


def _build_situation_summary(
    evidence_packages: list[dict],
    priority: str,
    correlation_type: str,
    sla_minutes: int,
    client_config: dict[str, Any],
) -> str:
    """
    Generate a plain-English situation summary for the L1/L2 briefing card.
    Written at L1 engineer level — clear, specific, actionable.
    """
    services = list({p.get("service_name", "unknown") for p in evidence_packages})
    anomaly_types = list({p.get("anomaly_type", "UNKNOWN") for p in evidence_packages})
    client_name = client_config.get("client_name", "Unknown Client")

    incident_type = "cascade incident" if correlation_type == "CASCADE_INCIDENT" else "isolated anomaly"
    service_list = ", ".join(services) if services else "unknown services"
    anomaly_list = ", ".join(anomaly_types) if anomaly_types else "unknown anomaly"

    # Business impact from highest severity evidence
    max_confidence = max((p.get("detection_confidence", 0.0) for p in evidence_packages), default=0.0)

    summary = (
        f"{priority} {incident_type} detected on {client_name}. "
        f"Affected services: {service_list}. "
        f"Anomaly type: {anomaly_list}. "
        f"Detection confidence: {max_confidence:.0%}. "
        f"SLA breach in {sla_minutes} minutes. "
    )

    # Add preliminary hypothesis from highest-confidence package
    best_pkg = max(evidence_packages, key=lambda p: p.get("detection_confidence", 0.0), default={})
    hypothesis = best_pkg.get("preliminary_hypothesis", "")
    if hypothesis:
        summary += f"Initial hypothesis: {hypothesis}"

    return summary.strip()


async def _notify_sdm_p1(
    client_id: str,
    incident_id: str,
    situation_summary: str,
    client_config: dict[str, Any],
) -> None:
    """
    Send immediate Slack notification to SDM for P1 incidents.
    Failure is logged but never blocks the pipeline.
    """
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not slack_url or slack_url == "https://hooks.slack.com/services/placeholder":
        logger.warning(
            "n1_classifier.sdm_notify_skipped",
            reason="SLACK_WEBHOOK_URL not configured",
            client_id=client_id,
            incident_id=incident_id,
        )
        return

    escalation_matrix: dict = client_config.get("escalation_matrix", {})
    sdm_contact = escalation_matrix.get("sdm", {}).get("contact", "SDM")

    payload = {
        "text": (
            f":rotating_light: *P1 INCIDENT — ATLAS* :rotating_light:\n"
            f"*Client:* {client_config.get('client_name', client_id)}\n"
            f"*Incident ID:* {incident_id}\n"
            f"*Summary:* {situation_summary}\n"
            f"*SDM:* {sdm_contact} — immediate attention required."
        )
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(slack_url, json=payload)
            logger.info(
                "n1_classifier.sdm_notified",
                client_id=client_id,
                incident_id=incident_id,
                status=resp.status_code,
            )
    except Exception as exc:
        logger.error(
            "n1_classifier.sdm_notify_failed",
            client_id=client_id,
            incident_id=incident_id,
            error=str(exc),
        )
