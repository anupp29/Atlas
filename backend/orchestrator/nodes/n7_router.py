"""
Node 7 — Router.

Takes the routing_decision from N6 and dispatches the incident to the
correct destination. Sends Slack briefing cards for human review paths.
Triggers LangGraph interrupt for human-in-the-loop paths.

Inputs:  routing_decision, all prior state fields
Outputs: audit_trail entry (routing destination + timestamp)

Note: The LangGraph interrupt is triggered by raising NodeInterrupt from
      langgraph.errors — the graph suspends here and waits for human input.
      State is persisted by the SqliteSaver checkpointer in pipeline.py.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from langgraph.errors import NodeInterrupt

from backend.config.client_registry import get_client
from backend.execution.playbook_library import get_playbook
from backend.orchestrator.state import AtlasState, append_audit_entry

logger = structlog.get_logger(__name__)

_HTTP_TIMEOUT: float = 5.0


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 7: Route the incident to AUTO_EXECUTE, L1_HUMAN_REVIEW, or L2_L3_ESCALATION.

    For human review paths: sends Slack briefing card, then raises NodeInterrupt
    to suspend the graph. The graph resumes when the human submits their decision
    via the /api/incidents/approve or /api/incidents/reject endpoint.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with updated audit_trail.

    Raises:
        NodeInterrupt: For L1_HUMAN_REVIEW and L2_L3_ESCALATION paths.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    routing: str = state.get("routing_decision", "L2_L3_ESCALATION")
    priority: str = state.get("incident_priority", "P3")

    logger.info(
        "n7_router.started",
        client_id=client_id,
        incident_id=incident_id,
        routing=routing,
        priority=priority,
    )

    client_config = get_client(client_id)

    # ── P1: always notify SDM regardless of routing path ─────────────────────
    if priority == "P1":
        await _notify_channel(
            client_id=client_id,
            incident_id=incident_id,
            state=state,
            client_config=client_config,
            tier="sdm",
            routing=routing,
        )

    audit_entry: dict[str, Any] = {
        "node": "n7_router",
        "actor": "ATLAS_AUTO",
        "action": "routing_dispatched",
        "routing_decision": routing,
        "priority": priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if routing == "AUTO_EXECUTE":
        # Pipeline continues directly to execution — no interrupt
        logger.info(
            "n7_router.auto_execute",
            client_id=client_id,
            incident_id=incident_id,
            action_id=state.get("recommended_action_id"),
        )
        audit_entry["destination"] = "execution_engine"
        return {
            "audit_trail": append_audit_entry(state, audit_entry),
        }

    # ── Human review paths — send briefing and interrupt ─────────────────────
    tier = _determine_tier(routing, priority)
    await _notify_channel(
        client_id=client_id,
        incident_id=incident_id,
        state=state,
        client_config=client_config,
        tier=tier,
        routing=routing,
    )

    audit_entry["destination"] = f"human_review_{tier}"
    audit_entry["sla_breach_time"] = state.get("sla_breach_time", "").isoformat() if isinstance(
        state.get("sla_breach_time"), datetime
    ) else str(state.get("sla_breach_time", ""))

    logger.info(
        "n7_router.suspending_for_human_review",
        client_id=client_id,
        incident_id=incident_id,
        tier=tier,
        routing=routing,
    )

    # DECISION: LangGraph NodeInterrupt must be raised — it does NOT return.
    # The audit entry is embedded in the interrupt payload so it is captured
    # by the checkpointer as part of the interrupt value. The state update
    # (audit_trail) is included in the interrupt dict and applied by the
    # pipeline's astream handler before the graph suspends.
    # Raising NodeInterrupt IS the return — no code after this executes.
    raise NodeInterrupt(
        {
            "incident_id": incident_id,
            "client_id": client_id,
            "routing": routing,
            "tier": tier,
            "priority": priority,
            "situation_summary": state.get("situation_summary", ""),
            "recommended_action_id": state.get("recommended_action_id", ""),
            "composite_confidence_score": state.get("composite_confidence_score", 0.0),
            "active_veto_conditions": state.get("active_veto_conditions", []),
            "sla_breach_time": str(state.get("sla_breach_time", "")),
            # Embed the audit update so the checkpointer captures it
            "_state_update": {"audit_trail": append_audit_entry(state, audit_entry)},
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _determine_tier(routing: str, priority: str) -> str:
    """Map routing decision + priority to the correct human tier."""
    if routing == "L1_HUMAN_REVIEW":
        return "l1"
    # L2_L3_ESCALATION: P1 → L3, P2/P3 → L2
    if priority == "P1":
        return "l3"
    return "l2"


async def _notify_channel(
    client_id: str,
    incident_id: str,
    state: AtlasState,
    client_config: dict[str, Any],
    tier: str,
    routing: str,
) -> None:
    """
    Send a Slack briefing card to the appropriate channel.
    Failure is logged but never blocks the pipeline.
    """
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not slack_url or slack_url == "https://hooks.slack.com/services/placeholder":
        logger.warning(
            "n7_router.slack_not_configured",
            client_id=client_id,
            incident_id=incident_id,
        )
        return

    escalation_matrix: dict = client_config.get("escalation_matrix", {})
    tier_config: dict = escalation_matrix.get(tier, {})
    contact = tier_config.get("contact", tier.upper())

    composite = state.get("composite_confidence_score", 0.0)
    vetoes = state.get("active_veto_conditions", [])
    action_id = state.get("recommended_action_id", "")
    priority = state.get("incident_priority", "P3")
    situation = state.get("situation_summary", "")
    sla_breach = state.get("sla_breach_time")

    # Playbook details
    playbook = get_playbook(action_id) if action_id else None
    playbook_name = playbook.name if playbook else action_id or "Unknown"
    action_class = playbook.action_class if playbook else "?"

    sla_str = sla_breach.isoformat() if isinstance(sla_breach, datetime) else str(sla_breach or "")

    veto_text = "\n".join(f"• {v}" for v in vetoes) if vetoes else "None"

    emoji = ":rotating_light:" if priority == "P1" else ":warning:"
    tier_label = tier.upper()

    payload = {
        "text": (
            f"{emoji} *ATLAS — {priority} Incident Requires {tier_label} Review* {emoji}\n"
            f"*Client:* {client_config.get('client_name', client_id)}\n"
            f"*Incident ID:* `{incident_id}`\n"
            f"*Routing:* {routing}\n"
            f"*Confidence Score:* {composite:.0%}\n"
            f"*Recommended Action:* {playbook_name} (Class {action_class})\n"
            f"*SLA Breach:* {sla_str}\n"
            f"*Active Vetoes:*\n{veto_text}\n\n"
            f"*Summary:* {situation}\n\n"
            f"*Assigned to:* {contact}\n"
            f"Review at: {os.environ.get('ATLAS_FRONTEND_ORIGIN', 'http://localhost:5173')}"
            f"/incidents/{incident_id}"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(slack_url, json=payload)
            logger.info(
                "n7_router.slack_sent",
                client_id=client_id,
                incident_id=incident_id,
                tier=tier,
                status=resp.status_code,
            )
    except Exception as exc:
        logger.error(
            "n7_router.slack_failed",
            client_id=client_id,
            incident_id=incident_id,
            tier=tier,
            error=str(exc),
        )
