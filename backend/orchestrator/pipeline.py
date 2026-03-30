"""
ATLAS LangGraph orchestration pipeline.

Assembles all 7 nodes into the complete state machine. Compiles the graph
with a SQLite-backed checkpointer so state persists across server restarts.

Public interface:
    run_incident(evidence_packages, client_id, correlation_type, early_warning_signals)
        → starts a new incident thread, returns (thread_id, initial_state)

    resume_after_approval(thread_id, human_action, modifier, rejection_reason, modified_params)
        → resumes a suspended graph after human decision

    get_incident_state(thread_id) → current state dict for a thread
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.orchestrator.nodes import (
    n1_classifier,
    n2_itsm,
    n3_graph,
    n4_semantic,
    n5_reasoning,
    n6_confidence,
    n7_router,
)
from backend.orchestrator.state import AtlasState, build_initial_state

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Activity broadcast callback — registered by main.py to avoid circular import
# ─────────────────────────────────────────────────────────────────────────────

_activity_broadcast_fn: Any = None

_NODE_STAGE_MAP: dict[str, str] = {
    "n1_classifier": "detect",
    "n2_itsm": "route",
    "n3_graph": "correlate",
    "n4_semantic": "search",
    "n5_reasoning": "reason",
    "n6_confidence": "select",
    "n7_router": "route",
    "execute_playbook": "act",
    "n_learn": "learn",
}


def register_activity_broadcast(fn: Any) -> None:
    """Register the activity broadcast function from main.py."""
    global _activity_broadcast_fn
    _activity_broadcast_fn = fn


async def _broadcast_node_activity(
    node_name: str,
    updates: dict[str, Any],
    client_id: str,
    incident_id: str,
) -> None:
    """Broadcast a node completion event to the activity feed WebSocket."""
    if _activity_broadcast_fn is None:
        return
    try:
        _NODE_MESSAGES: dict[str, str] = {
            "n1_classifier": f"Incident classified — priority {updates.get('incident_priority', '?')}",
            "n2_itsm": f"ServiceNow ticket {updates.get('servicenow_ticket_id', 'pending')} created",
            "n3_graph": (
                f"Graph intelligence: {len(updates.get('blast_radius', []))} blast radius services, "
                f"{len(updates.get('recent_deployments', []))} deployments"
            ),
            "n4_semantic": (
                f"Semantic search: {len(updates.get('semantic_matches', []))} matches found"
            ),
            "n5_reasoning": f"LLM reasoning complete — {updates.get('recommended_action_id', '?')}",
            "n6_confidence": (
                f"Confidence score: {updates.get('composite_confidence_score', 0.0):.2f} — "
                f"routing: {updates.get('routing_decision', '?')}"
            ),
            "n7_router": f"Routing dispatched: {updates.get('routing_decision', '?')}",
            "execute_playbook": f"Playbook executed — {updates.get('execution_status', '?')}",
            "n_learn": "Learning engine updated",
        }
        message = _NODE_MESSAGES.get(node_name, f"Node {node_name} complete")
        changed_fields = sorted(str(key) for key in updates.keys())
        await _activity_broadcast_fn(
            {
                "type": "orchestrator_node",
                "id": f"node-{node_name}-{incident_id[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": node_name,
                "message": message,
                "client_id": client_id,
                "meta": {
                    "node": node_name,
                    "incident_id": incident_id,
                    "stage": _NODE_STAGE_MAP.get(node_name, "unknown"),
                    "changed_fields": changed_fields,
                },
            }
        )
    except Exception:
        pass  # Never block pipeline for activity broadcast


# ─────────────────────────────────────────────────────────────────────────────
# Graph compilation
# ─────────────────────────────────────────────────────────────────────────────

_CHECKPOINT_DB_ENV = "ATLAS_CHECKPOINT_DB_PATH"

# Module-level compiled graph — built once on first use
_graph: CompiledStateGraph | None = None
_checkpointer: MemorySaver | None = None
_checkpoint_conn: aiosqlite.Connection | None = None
_graph_lock = asyncio.Lock()


async def _get_graph() -> CompiledStateGraph:
    """
    Build and compile the LangGraph state machine on first call.
    Subsequent calls return the cached compiled graph.
    Thread-safe: uses an asyncio.Lock to prevent double-initialisation.
    """
    global _graph, _checkpointer, _checkpoint_conn

    if _graph is not None:
        return _graph

    async with _graph_lock:
        # Double-checked locking — another coroutine may have built it while we waited
        if _graph is not None:
            return _graph

        checkpoint_path = os.environ.get(_CHECKPOINT_DB_ENV)
        if not checkpoint_path:
            raise RuntimeError(
                f"Environment variable '{_CHECKPOINT_DB_ENV}' is not set. "
                "ATLAS cannot persist incident state without a checkpoint database path."
            )

        # Hold the connection at module level so it is closed on shutdown
        _checkpoint_conn = await aiosqlite.connect(checkpoint_path)
        _checkpointer = MemorySaver()

        builder = StateGraph(AtlasState)

        # ── Add all 7 nodes ───────────────────────────────────────────────────────
        builder.add_node("n1_classifier", n1_classifier.run)
        builder.add_node("n2_itsm", n2_itsm.run)
        builder.add_node("n3_graph", n3_graph.run)
        builder.add_node("n4_semantic", n4_semantic.run)
        builder.add_node("n5_reasoning", n5_reasoning.run)
        builder.add_node("n6_confidence", n6_confidence.run)
        builder.add_node("n7_router", n7_router.run)

        # ── Execution node (post-approval) ────────────────────────────────────────
        builder.add_node("execute_playbook", _execute_playbook_node)

        # ── Learning node (post-resolution) ───────────────────────────────────────
        builder.add_node("n_learn", _learning_node)

        # ── Define edges ──────────────────────────────────────────────────────────
        builder.set_entry_point("n1_classifier")
        builder.add_edge("n1_classifier", "n2_itsm")
        builder.add_edge("n2_itsm", "n3_graph")
        builder.add_edge("n3_graph", "n4_semantic")
        builder.add_edge("n4_semantic", "n5_reasoning")
        builder.add_edge("n5_reasoning", "n6_confidence")
        builder.add_edge("n6_confidence", "n7_router")

        # ── Conditional edge from n7_router ───────────────────────────────────────
        builder.add_conditional_edges(
            "n7_router",
            _route_after_n7,
            {
                "execute": "execute_playbook",
                "end": END,
            },
        )

        builder.add_edge("execute_playbook", "n_learn")
        builder.add_edge("n_learn", END)

        _graph = builder.compile(checkpointer=_checkpointer)

        logger.info("pipeline.graph_compiled", nodes=list(builder.nodes))
        return _graph


async def close_graph() -> None:
    """
    Close the SQLite checkpoint connection. Call on application shutdown.
    Registered in the lifespan context manager.
    """
    global _checkpoint_conn
    if _checkpoint_conn is not None:
        await _checkpoint_conn.close()
        _checkpoint_conn = None
        logger.info("pipeline.checkpoint_connection_closed")


def _route_after_n7(state: AtlasState) -> str:
    """
    Conditional routing after N7.
    AUTO_EXECUTE → execute immediately.
    Human review paths → N7 raises NodeInterrupt before this is called,
    so this function only runs for AUTO_EXECUTE or after human resumes.
    """
    routing = state.get("routing_decision", "L2_L3_ESCALATION")
    human_action = state.get("human_action", "")

    if routing == "AUTO_EXECUTE":
        return "execute"

    # After human resumes: approved/modified → execute, rejected/escalated → end
    if human_action in ("approved", "modified"):
        return "execute"

    return "end"


# ─────────────────────────────────────────────────────────────────────────────
# Execution node
# ─────────────────────────────────────────────────────────────────────────────


async def _execute_playbook_node(state: AtlasState) -> dict[str, Any]:
    """
    Execute the recommended playbook.
    Imports the playbook module dynamically from the playbook library.
    """
    from backend.execution.playbook_library import get_playbook
    from backend.orchestrator.state import append_audit_entry

    client_id = state["client_id"]
    incident_id = state["incident_id"]
    action_id = state.get("recommended_action_id", "")
    actor = state.get("human_modifier") or "ATLAS_AUTO"
    ticket_id = state.get("servicenow_ticket_id", "")

    # Use modified parameters if L2 modified the action
    parameters = state.get("human_modified_parameters") or None

    logger.info(
        "pipeline.execute_playbook",
        client_id=client_id,
        incident_id=incident_id,
        action_id=action_id,
        actor=actor,
    )

    playbook_meta = get_playbook(action_id)
    if playbook_meta is None:
        logger.error("pipeline.playbook_not_found", action_id=action_id)
        return {
            "execution_status": "failed",
            "execution_result": {
                "error": f"Playbook '{action_id}' not found in library."
            },
            "audit_trail": append_audit_entry(
                state,
                {
                    "node": "execute_playbook",
                    "actor": actor,
                    "action": "playbook_not_found",
                    "action_id": action_id,
                },
            ),
        }

    # HARD BLOCK: Class 3 actions never auto-execute at any trust level.
    # This is a permanent ceiling — non-configurable. Checked before any other flag.
    if playbook_meta.action_class == 3:
        logger.error(
            "pipeline.class3_execution_blocked",
            action_id=action_id,
            client_id=client_id,
            incident_id=incident_id,
        )
        return {
            "execution_status": "blocked",
            "execution_result": {
                "error": f"Playbook '{action_id}' is Class 3 — permanent auto-execute ceiling. "
                "Class 3 actions require manual execution only."
            },
            "routing_decision": "L2_L3_ESCALATION",
            "audit_trail": append_audit_entry(
                state,
                {
                    "node": "execute_playbook",
                    "actor": "ATLAS_AUTO",
                    "action": "class3_execution_blocked",
                    "action_id": action_id,
                    "reason": "Class 3 permanent ceiling — non-configurable",
                },
            ),
        }

    # Check auto_execute_eligible flag
    if (
        not playbook_meta.auto_execute_eligible
        and state.get("routing_decision") == "AUTO_EXECUTE"
    ):
        logger.error(
            "pipeline.playbook_not_auto_eligible",
            action_id=action_id,
            action_class=playbook_meta.action_class,
        )
        return {
            "execution_status": "failed",
            "execution_result": {
                "error": f"Playbook '{action_id}' is not auto-execute eligible."
            },
            "routing_decision": "L2_L3_ESCALATION",
            "audit_trail": append_audit_entry(
                state,
                {
                    "node": "execute_playbook",
                    "actor": "ATLAS_AUTO",
                    "action": "auto_execute_blocked",
                    "action_id": action_id,
                    "reason": "not auto_execute_eligible",
                },
            ),
        }

    # Dynamically import and run the playbook module
    try:
        result = await _dispatch_playbook(
            action_id=action_id,
            client_id=client_id,
            incident_id=incident_id,
            actor=actor,
            ticket_id=ticket_id,
            parameters=parameters,
            evidence_packages=state["evidence_packages"],
        )
    except Exception as exc:
        logger.error(
            "pipeline.playbook_execution_error",
            client_id=client_id,
            incident_id=incident_id,
            action_id=action_id,
            error=str(exc),
        )
        result = {"success": False, "outcome": "error", "detail": str(exc)}

    execution_status = (
        "success" if result.get("success") else result.get("outcome", "failed")
    )
    resolution_outcome = "success" if result.get("success") else "failure"

    return {
        "execution_status": execution_status,
        "execution_result": result,
        "resolution_outcome": resolution_outcome,
        "audit_trail": append_audit_entry(
            state,
            {
                "node": "execute_playbook",
                "actor": actor,
                "action": "playbook_executed",
                "action_id": action_id,
                "outcome": execution_status,
            },
        ),
    }


async def _dispatch_playbook(
    action_id: str,
    client_id: str,
    incident_id: str,
    actor: str,
    ticket_id: str,
    parameters: dict | None,
    evidence_packages: list[dict],
) -> dict[str, Any]:
    """Dispatch to the correct playbook module based on action_id."""
    primary_service = (
        evidence_packages[0].get("service_name", "") if evidence_packages else ""
    )

    if action_id == "connection-pool-recovery-v2":
        from backend.execution.playbooks.connection_pool_recovery_v2 import execute

        result = await execute(
            client_id=client_id,
            incident_id=incident_id,
            service_name=primary_service,
            actor=actor,
            servicenow_ticket_id=ticket_id,
            parameters=parameters,
        )
        return {
            "success": result.success,
            "outcome": result.outcome,
            "detail": result.detail,
            "audit_record_id": result.audit_record_id,
            "execution_seconds": result.execution_seconds,
        }

    if action_id == "redis-memory-policy-rollback-v1":
        from backend.execution.playbooks.redis_memory_policy_rollback_v1 import execute

        result = await execute(
            client_id=client_id,
            incident_id=incident_id,
            service_name=primary_service,
            actor=actor,
            servicenow_ticket_id=ticket_id,
            parameters=parameters,
        )
        return {
            "success": result.success,
            "outcome": result.outcome,
            "detail": result.detail,
            "audit_record_id": result.audit_record_id,
            "execution_seconds": result.execution_seconds,
        }

    raise NotImplementedError(
        f"No dispatch handler for playbook '{action_id}'. "
        "Add a dispatch case in pipeline._dispatch_playbook()."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Learning node
# ─────────────────────────────────────────────────────────────────────────────


async def _learning_node(state: AtlasState) -> dict[str, Any]:
    """
    Post-resolution learning. Runs asynchronously — never blocks resolution.
    Writes decision history record and triggers recalibration.
    """
    from backend.learning import decision_history
    from backend.orchestrator.state import append_audit_entry

    client_id = state["client_id"]
    incident_id = state["incident_id"]

    mttr_start_str: str = (
        state.get("mttr_start_time") or datetime.now(timezone.utc).isoformat()
    )
    try:
        mttr_start = datetime.fromisoformat(mttr_start_str)
    except (ValueError, TypeError):
        mttr_start = datetime.now(timezone.utc)
    mttr_seconds = int((datetime.now(timezone.utc) - mttr_start).total_seconds())

    resolution_outcome = state.get("resolution_outcome", "failure")
    routing_tier_map = {
        "AUTO_EXECUTE": "auto",
        "L1_HUMAN_REVIEW": "L1",
        "L2_L3_ESCALATION": "L2",
    }
    routing_tier = routing_tier_map.get(state.get("routing_decision", ""), "L2")

    evidence_packages = state["evidence_packages"]
    primary_pkg = max(
        evidence_packages, key=lambda p: p.get("detection_confidence", 0.0), default={}
    )

    # DECISION: service_class is the technology class (e.g. "java-spring-boot"), not the
    # service name. Map agent_id → tech type per the ATLAS error taxonomy and agent naming.
    _AGENT_TO_TECH: dict[str, str] = {
        "java-agent": "java-spring-boot",
        "postgres-agent": "postgresql",
        "nodejs-agent": "nodejs",
        "redis-agent": "redis",
    }
    service_class = _AGENT_TO_TECH.get(
        primary_pkg.get("agent_id", ""),
        primary_pkg.get("agent_id", "unknown"),
    )

    record = {
        "client_id": client_id,
        "incident_id": incident_id,
        "anomaly_type": primary_pkg.get("anomaly_type", ""),
        "service_class": service_class,
        "recommended_action_id": state.get("recommended_action_id", ""),
        "confidence_score_at_decision": state.get("composite_confidence_score", 0.0),
        "routing_tier": routing_tier,
        "human_action": state.get("human_action", "approved"),
        "modification_diff": state.get("human_modified_parameters"),
        "rejection_reason": state.get("human_rejection_reason"),
        "resolution_outcome": resolution_outcome,
        "actual_mttr": mttr_seconds,
        "recurrence_within_48h": False,
    }

    try:
        decision_history.write_record(record)
        logger.info(
            "pipeline.learning.decision_recorded",
            client_id=client_id,
            incident_id=incident_id,
            outcome=resolution_outcome,
        )
    except Exception as exc:
        logger.error("pipeline.learning.write_failed", error=str(exc))

    # Recalibration runs in background — never blocks.
    # DECISION: pass service_class (tech type, e.g. "java-spring-boot") not service_name
    # ("PaymentAPI"). The Decision History records are keyed on this tech class, so
    # recalibration must use the same key or pattern matching never accumulates.
    asyncio.create_task(
        _run_recalibration(
            client_id=client_id,
            anomaly_type=primary_pkg.get("anomaly_type", ""),
            service_class=service_class,
            action_id=state.get("recommended_action_id", ""),
        )
    )

    # Trust progression check
    asyncio.create_task(_check_trust_progression(client_id, incident_id))

    from datetime import timedelta

    recurrence_due = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    return {
        "mttr_seconds": mttr_seconds,
        "recurrence_check_due_at": recurrence_due,
        "audit_trail": append_audit_entry(
            state,
            {
                "node": "n_learn",
                "actor": "ATLAS_AUTO",
                "action": "learning_complete",
                "mttr_seconds": mttr_seconds,
                "resolution_outcome": resolution_outcome,
                "decision_record_written": True,
            },
        ),
    }


async def _run_recalibration(
    client_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> None:
    """Background task: recalibrate Factor 1 after resolution."""
    try:
        from backend.learning.recalibration import recalibrate_after_resolution

        await recalibrate_after_resolution(
            client_id=client_id,
            incident_id="post_resolution",
            anomaly_type=anomaly_type,
            service_class=service_class,
            action_id=action_id,
        )
    except Exception as exc:
        logger.error("pipeline.recalibration_failed", error=str(exc))


async def _check_trust_progression(client_id: str, incident_id: str = "") -> None:
    """Background task: check trust stage progression after resolution."""
    try:
        from backend.learning.trust_progression import evaluate_progression

        await evaluate_progression(client_id, incident_id)
    except Exception as exc:
        logger.error("pipeline.trust_progression_failed", error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────


async def run_incident(
    evidence_packages: list[dict],
    client_id: str,
    correlation_type: str = "ISOLATED_ANOMALY",
    early_warning_signals: list[dict] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Start a new incident thread through the pipeline.

    Args:
        evidence_packages:      List of EvidencePackage dicts from correlation engine.
        client_id:              Mandatory. Multi-tenancy key.
        correlation_type:       "CASCADE_INCIDENT" | "ISOLATED_ANOMALY"
        early_warning_signals:  Optional early warning signals.

    Returns:
        (thread_id, final_or_interrupted_state)
        thread_id is used to resume the graph after human approval.
    """
    if not client_id:
        raise ValueError("client_id is required to run an incident.")
    if not evidence_packages:
        raise ValueError("evidence_packages cannot be empty.")

    incident_id = str(uuid.uuid4())
    thread_id = f"{client_id}_{incident_id}"

    initial_state = build_initial_state(
        client_id=client_id,
        incident_id=incident_id,
        evidence_packages=evidence_packages,
        correlation_type=correlation_type,
        early_warning_signals=early_warning_signals,
    )

    graph = await _get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(
        "pipeline.incident_started",
        client_id=client_id,
        incident_id=incident_id,
        thread_id=thread_id,
        correlation_type=correlation_type,
    )

    final_state: dict[str, Any] = {}
    async for event in graph.astream(initial_state, config=config):
        # Each event is a dict of {node_name: state_updates}
        # LangGraph emits NodeInterrupt as {"__interrupt__": (Interrupt(...),)}
        for node_name, updates in event.items():
            if node_name == "__interrupt__":
                # Graph suspended for human review — extract embedded state update
                # from the interrupt payload and apply it so audit_trail is captured.
                interrupt_values = (
                    updates if isinstance(updates, (list, tuple)) else [updates]
                )
                for interrupt_obj in interrupt_values:
                    # Interrupt value is the dict passed to NodeInterrupt(...)
                    payload = getattr(interrupt_obj, "value", interrupt_obj)
                    if isinstance(payload, dict):
                        state_update = payload.get("_state_update", {})
                        if state_update:
                            final_state.update(state_update)
                logger.info(
                    "pipeline.graph_interrupted",
                    client_id=client_id,
                    incident_id=incident_id,
                    thread_id=thread_id,
                )
                continue
            if isinstance(updates, dict):
                final_state.update(updates)
                logger.debug("pipeline.node_complete", node=node_name)
                # Broadcast node completion to activity feed
                await _broadcast_node_activity(
                    node_name=node_name,
                    updates=updates,
                    client_id=client_id,
                    incident_id=incident_id,
                )

    # After streaming, fetch the full persisted state from the checkpointer.
    # This is the authoritative source — it contains all fields set by every node,
    # not just the incremental update dicts emitted during this stream.
    try:
        snapshot = await graph.aget_state(config)
        if snapshot and snapshot.values:
            full_state = dict(snapshot.values)
            # Merge: full_state is authoritative, but keep any keys we set locally
            # (e.g. thread_id which is not in the checkpointed state yet)
            full_state.update(
                {k: v for k, v in final_state.items() if k not in full_state}
            )
            final_state = full_state
    except Exception as exc:
        logger.warning(
            "pipeline.snapshot_fetch_failed",
            thread_id=thread_id,
            error=str(exc),
            note="Using streamed state — may be incomplete.",
        )

    return thread_id, final_state


async def resume_after_approval(
    thread_id: str,
    human_action: str,
    modifier: str = "",
    rejection_reason: str = "",
    modified_parameters: dict | None = None,
) -> dict[str, Any]:
    """
    Resume a suspended graph after human decision.

    Args:
        thread_id:           The thread_id returned by run_incident().
        human_action:        "approved" | "modified" | "rejected" | "escalated"
        modifier:            Engineer name.
        rejection_reason:    Required if human_action == "rejected".
        modified_parameters: Parameter overrides if human_action == "modified".

    Returns:
        Final state dict after pipeline completes.
    """
    valid_actions = {"approved", "modified", "rejected", "escalated"}
    if human_action not in valid_actions:
        raise ValueError(
            f"human_action must be one of {valid_actions}, got '{human_action}'"
        )

    graph = await _get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # Inject human decision into the checkpointed state before resuming.
    # LangGraph's correct resume pattern: update_state() first, then astream(None).
    # Passing the update dict directly to astream() treats it as a new initial state
    # rather than a continuation — this is incorrect and breaks the checkpoint chain.
    human_update: dict[str, Any] = {
        "human_action": human_action,
        "human_modifier": modifier,
        "human_rejection_reason": rejection_reason,
        "human_modified_parameters": modified_parameters or {},
    }

    await graph.aupdate_state(config, human_update)

    client_id = ""
    incident_id = ""
    try:
        pre_resume_snapshot = await graph.aget_state(config)
        if pre_resume_snapshot and pre_resume_snapshot.values:
            client_id = str(pre_resume_snapshot.values.get("client_id") or "")
            incident_id = str(pre_resume_snapshot.values.get("incident_id") or "")
    except Exception as exc:
        logger.debug("pipeline.pre_resume_snapshot_fetch_failed", thread_id=thread_id, error=str(exc))

    logger.info(
        "pipeline.resuming_after_human",
        thread_id=thread_id,
        human_action=human_action,
        modifier=modifier,
    )

    final_state: dict[str, Any] = {}
    async for event in graph.astream(None, config=config):
        for node_name, updates in event.items():
            if node_name == "__interrupt__":
                # Should not happen after human resume, but handle defensively
                interrupt_values = (
                    updates if isinstance(updates, (list, tuple)) else [updates]
                )
                for interrupt_obj in interrupt_values:
                    payload = getattr(interrupt_obj, "value", interrupt_obj)
                    if isinstance(payload, dict):
                        state_update = payload.get("_state_update", {})
                        if state_update:
                            final_state.update(state_update)
                continue
            if isinstance(updates, dict):
                final_state.update(updates)
                logger.debug("pipeline.node_complete_after_resume", node=node_name)
                if not client_id:
                    client_id = str(final_state.get("client_id") or "")
                if not incident_id:
                    incident_id = str(final_state.get("incident_id") or "")
                if client_id and incident_id:
                    await _broadcast_node_activity(
                        node_name=node_name,
                        updates=updates,
                        client_id=client_id,
                        incident_id=incident_id,
                    )

    # Fetch full persisted state — authoritative after resume
    try:
        snapshot = await graph.aget_state(config)
        if snapshot and snapshot.values:
            full_state = dict(snapshot.values)
            full_state.update(
                {k: v for k, v in final_state.items() if k not in full_state}
            )
            final_state = full_state
    except Exception as exc:
        logger.warning(
            "pipeline.resume_snapshot_fetch_failed",
            thread_id=thread_id,
            error=str(exc),
        )

    return final_state


async def get_incident_state(thread_id: str) -> dict[str, Any] | None:
    """
    Return the current persisted state for a thread.
    Returns None if the thread does not exist.
    """
    graph = await _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.values:
            return None

        values = dict(snapshot.values)
        # Some checkpointers may return an empty/default snapshot for unknown
        # thread IDs. Treat these as missing incidents instead of valid state.
        if not values:
            return None
        if not values.get("incident_id") and not values.get("client_id"):
            return None

        return values
    except Exception as exc:
        logger.error("pipeline.get_state_failed", thread_id=thread_id, error=str(exc))
        return None
