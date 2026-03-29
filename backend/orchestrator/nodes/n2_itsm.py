"""
Node 2 — ITSM Bridge.

Creates a real ServiceNow incident ticket and returns the INC number to state.
Retries 3 times with exponential backoff. Degrades gracefully if ServiceNow
is unavailable — sets itsm_ticket_pending and continues the pipeline.

Inputs:  client_id, incident_id, incident_priority, situation_summary (from state)
Outputs: servicenow_ticket_id, itsm_ticket_pending, audit_trail entry
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
import structlog

from backend.config.client_registry import get_client
from backend.orchestrator.state import AtlasState, append_audit_entry

logger = structlog.get_logger(__name__)

_HTTP_TIMEOUT: float = 10.0
_MAX_RETRIES: int = 3
_RETRY_BASE_SECONDS: float = 2.0

# ServiceNow priority mapping: ATLAS P1–P4 → ServiceNow 1–4
_PRIORITY_MAP: dict[str, str] = {
    "P1": "1",
    "P2": "2",
    "P3": "3",
    "P4": "4",
}

# ServiceNow anomaly type → category/subcategory mapping
_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "CONNECTION_POOL_EXHAUSTED": ("Software", "Application"),
    "DB_DEADLOCK":               ("Software", "Database"),
    "DB_PANIC":                  ("Software", "Database"),
    "JVM_MEMORY_CRITICAL":       ("Software", "Application"),
    "JVM_STACK_OVERFLOW":        ("Software", "Application"),
    "REDIS_OOM":                 ("Software", "Application"),
    "REDIS_COMMAND_REJECTED":    ("Software", "Application"),
    "NODE_UNHANDLED_REJECTION":  ("Software", "Application"),
    "NODE_DOWNSTREAM_REFUSED":   ("Network", "Connectivity"),
}


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 2: Create a ServiceNow incident ticket.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with servicenow_ticket_id or itsm_ticket_pending flag.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    priority: str = state.get("incident_priority", "P3")
    situation_summary: str = state.get("situation_summary", "ATLAS detected an anomaly.")
    evidence_packages: list[dict] = state["evidence_packages"]

    logger.info(
        "n2_itsm.started",
        client_id=client_id,
        incident_id=incident_id,
        priority=priority,
    )

    client_config = get_client(client_id)
    ticket_id, pending = await _create_ticket(
        client_id=client_id,
        incident_id=incident_id,
        priority=priority,
        situation_summary=situation_summary,
        evidence_packages=evidence_packages,
        client_config=client_config,
    )

    if ticket_id:
        logger.info(
            "n2_itsm.ticket_created",
            client_id=client_id,
            incident_id=incident_id,
            ticket_id=ticket_id,
        )
    else:
        logger.warning(
            "n2_itsm.ticket_pending",
            client_id=client_id,
            incident_id=incident_id,
            reason="ServiceNow unavailable after retries",
        )

    return {
        "servicenow_ticket_id": ticket_id or "",
        "itsm_ticket_pending": pending,
        "audit_trail": append_audit_entry(state, {
            "node": "n2_itsm",
            "actor": "ATLAS_AUTO",
            "action": "servicenow_ticket_created" if ticket_id else "servicenow_ticket_pending",
            "ticket_id": ticket_id or "PENDING",
            "priority": priority,
            "atlas_incident_id": incident_id,
        }),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ServiceNow API
# ─────────────────────────────────────────────────────────────────────────────

async def _create_ticket(
    client_id: str,
    incident_id: str,
    priority: str,
    situation_summary: str,
    evidence_packages: list[dict],
    client_config: dict[str, Any],
) -> tuple[str | None, bool]:
    """
    Attempt to create a ServiceNow incident with retries.

    Returns:
        (ticket_id, is_pending)
        ticket_id is None and is_pending is True if all retries failed.
    """
    instance_url = os.environ.get("SERVICENOW_INSTANCE_URL", "")
    username = os.environ.get("SERVICENOW_USERNAME", "")
    password = os.environ.get("SERVICENOW_PASSWORD", "")

    for var, val in (
        ("SERVICENOW_INSTANCE_URL", instance_url),
        ("SERVICENOW_USERNAME", username),
        ("SERVICENOW_PASSWORD", password),
    ):
        if not val:
            logger.error("n2_itsm.missing_env_var", var=var)
            return None, True

    payload = _build_payload(
        client_id=client_id,
        incident_id=incident_id,
        priority=priority,
        situation_summary=situation_summary,
        evidence_packages=evidence_packages,
        client_config=client_config,
    )

    url = f"{instance_url.rstrip('/')}/api/now/table/incident"

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=float(os.environ.get("SERVICENOW_HTTP_TIMEOUT", str(_HTTP_TIMEOUT)))) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    auth=(username, password),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )

            if resp.status_code == 201:
                data = resp.json()
                ticket_id: str = data.get("result", {}).get("number", "")
                if ticket_id:
                    return ticket_id, False
                logger.error(
                    "n2_itsm.ticket_number_missing",
                    client_id=client_id,
                    response=str(data)[:200],
                )
                return None, True

            logger.warning(
                "n2_itsm.unexpected_status",
                client_id=client_id,
                attempt=attempt,
                status=resp.status_code,
                body=resp.text[:200],
            )

        except httpx.RequestError as exc:
            logger.warning(
                "n2_itsm.request_error",
                client_id=client_id,
                attempt=attempt,
                error=str(exc),
            )

        if attempt < _MAX_RETRIES:
            wait = float(os.environ.get("SERVICENOW_RETRY_SLEEP", str(_RETRY_BASE_SECONDS * (2 ** (attempt - 1)))))
            logger.info("n2_itsm.retry", attempt=attempt, wait_seconds=wait)
            await asyncio.sleep(wait)

    return None, True


def _build_payload(
    client_id: str,
    incident_id: str,
    priority: str,
    situation_summary: str,
    evidence_packages: list[dict],
    client_config: dict[str, Any],
) -> dict[str, Any]:
    """Build the ServiceNow incident creation payload."""
    snow_priority = _PRIORITY_MAP.get(priority, "3")

    # Determine category from first evidence package anomaly type
    anomaly_type = evidence_packages[0].get("anomaly_type", "") if evidence_packages else ""
    category, subcategory = _CATEGORY_MAP.get(anomaly_type, ("Software", "Application"))

    # Affected CI: primary service from first evidence package
    affected_ci = evidence_packages[0].get("service_name", "") if evidence_packages else ""

    # Assignment group from escalation matrix
    # YAML keys are uppercase (L1, L2, L3, SDM) — must match exactly
    escalation_matrix: dict = client_config.get("escalation_matrix", {})
    tier_key = "L1" if priority in ("P3", "P4") else "L2"
    assignment_group = escalation_matrix.get(tier_key, {}).get("group", "IT Operations")

    # Short description: max 160 chars for ServiceNow
    short_desc = f"[ATLAS {priority}] {situation_summary}"[:160]

    return {
        "short_description": short_desc,
        "description": (
            f"ATLAS Incident ID: {incident_id}\n"
            f"Client: {client_config.get('client_name', client_id)}\n"
            f"Anomaly Type: {anomaly_type}\n"
            f"Affected Services: {', '.join(p.get('service_name', '') for p in evidence_packages)}\n\n"
            f"{situation_summary}"
        ),
        "priority": snow_priority,
        "category": category,
        "subcategory": subcategory,
        "assignment_group": assignment_group,
        "cmdb_ci": affected_ci,
        "caller_id": os.environ.get("SERVICENOW_CLIENT_ID", "atlas-service-account"),
        # Custom field to correlate back to ATLAS
        "u_atlas_incident_id": incident_id,
    }
