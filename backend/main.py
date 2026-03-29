"""
ATLAS Backend — FastAPI application entry point.

Registers all HTTP routes, WebSocket endpoints, and background services.
Validates all required environment variables on startup — refuses to start
if any are missing or if Neo4j/ChromaDB connections fail.

Routes:
    POST /webhook/cmdb              — ServiceNow change webhook
    POST /api/incidents/approve     — human approval submission
    POST /api/incidents/reject      — human rejection with reason
    GET  /api/incidents/active      — all active incidents for dashboard
    GET  /api/audit                 — audit log query
    GET  /api/trust/{client_id}     — trust level and progression

WebSockets:
    WS /ws/logs/{client_id}         — live log stream per client
    WS /ws/incidents/{client_id}    — live incident state updates per client
    WS /ws/activity                 — global ATLAS activity feed
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

# Load .env before any env-var reads — must happen before module-level code
# that reads os.environ (e.g. structlog config, client registry).
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=False)
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config.client_registry import get_all_client_ids, load_all_clients
from backend.database import audit_db
from backend.database.chromadb_client import ChromaDBClient
from backend.database.neo4j_client import Neo4jClient
from backend.execution.playbook_library import validate_action_id

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Required environment variables — checked at startup
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_ENV_VARS: list[str] = [
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "SERVICENOW_INSTANCE_URL",
    "SERVICENOW_USERNAME",
    "SERVICENOW_PASSWORD",
    "ATLAS_SECRET_KEY",
    "ATLAS_LLM_ENDPOINT",
    "CHROMADB_PATH",
    "ATLAS_AUDIT_DB_PATH",
    "ATLAS_DECISION_DB_PATH",
    "ATLAS_CHECKPOINT_DB_PATH",
]

# Optional — defaults are used if not set. Ollama is the primary LLM path.
_OLLAMA_BASE_URL_DEFAULT = "http://localhost:11434"
_OLLAMA_MODEL_DEFAULT = "qwen3-coder:480b-cloud"


def _validate_env_vars() -> None:
    """Fail immediately with a clear error if any required variable is missing."""
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"ATLAS startup failure: the following required environment variables are not set:\n"
            + "\n".join(f"  - {v}" for v in missing)
            + "\nSet all variables before starting ATLAS."
        )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket connection managers
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    """
    Manages WebSocket connections for a specific channel type.
    Supports per-client isolation and global broadcast.
    """

    def __init__(self) -> None:
        # client_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # Global connections (no client_id filter)
        self._global: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> None:
        await websocket.accept()
        if client_id:
            self._connections.setdefault(client_id, []).append(websocket)
        else:
            self._global.append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str | None = None) -> None:
        if client_id and client_id in self._connections:
            self._connections[client_id] = [
                ws for ws in self._connections[client_id] if ws is not websocket
            ]
        elif websocket in self._global:
            self._global.remove(websocket)

    async def send_to_client(self, client_id: str, message: dict) -> None:
        """Send a message to all connections for a specific client."""
        dead: list[WebSocket] = []
        for ws in self._connections.get(client_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, client_id)

    async def broadcast(self, message: dict) -> None:
        """Send a message to all global connections."""
        dead: list[WebSocket] = []
        for ws in self._global:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# Module-level managers
log_manager = ConnectionManager()
incident_manager = ConnectionManager()
activity_manager = ConnectionManager()

# Active incidents: thread_id → state dict
# Pruned when execution_status reaches a terminal state or after 24 hours.
_active_incidents: dict[str, dict[str, Any]] = {}
_active_incidents_timestamps: dict[str, float] = {}
_ACTIVE_INCIDENT_TTL_SECONDS = 86400  # 24 hours

# Long-lived agent singletons per client — keyed by (client_id, agent_type)
# Agents must survive across events to maintain baseline state and log buffers.
_agent_registry: dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup validation and graceful shutdown."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("atlas.startup.begin")

    _validate_env_vars()
    logger.info("atlas.startup.env_vars_ok")

    # Initialise databases
    audit_db.initialise_db()
    from backend.learning.decision_history import initialise_db as init_decision_db
    init_decision_db()
    from backend.learning.weight_correction import initialise_db as init_weight_db
    init_weight_db()
    logger.info("atlas.startup.databases_initialised")

    # Load client configs
    load_all_clients()
    logger.info("atlas.startup.clients_loaded")

    # Test Neo4j connection
    try:
        neo4j = Neo4jClient()
        await neo4j.health_check()
        logger.info("atlas.startup.neo4j_ok")
    except Exception as exc:
        raise RuntimeError(f"ATLAS startup failure: Neo4j connection failed: {exc}") from exc

    # Test ChromaDB connection
    try:
        chroma = ChromaDBClient()
        if not chroma.health_check():
            raise RuntimeError("ChromaDB health check returned False.")
        logger.info("atlas.startup.chromadb_ok")
    except Exception as exc:
        raise RuntimeError(f"ATLAS startup failure: ChromaDB connection failed: {exc}") from exc

    # Test LLM endpoint (non-fatal — warn only)
    await _test_llm_endpoint()

    # Start background tasks
    client_ids = get_all_client_ids()
    background_tasks: list[asyncio.Task] = []

    # Register activity broadcast callback in pipeline (avoids circular import)
    from backend.orchestrator.pipeline import register_activity_broadcast
    register_activity_broadcast(activity_manager.broadcast)

    # Rebuild accuracy cache from decision history so N6 has real priors on restart
    try:
        from backend.learning.recalibration import force_recalculate_all
        rebuilt = await force_recalculate_all(client_ids)
        logger.info("atlas.startup.accuracy_cache_rebuilt", patterns=rebuilt)
    except Exception as exc:
        logger.warning("atlas.startup.accuracy_cache_rebuild_failed", error=str(exc))

    for cid in client_ids:
        task = asyncio.create_task(_agent_monitoring_loop(cid))
        background_tasks.append(task)
        logger.info("atlas.startup.monitoring_started", client_id=cid)

    # Prune expired active incidents every 5 minutes
    prune_task = asyncio.create_task(_incident_ttl_pruner())
    background_tasks.append(prune_task)

    logger.info("atlas.startup.complete", clients=client_ids)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("atlas.shutdown.begin")
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    from backend.orchestrator.pipeline import close_graph
    await close_graph()
    logger.info("atlas.shutdown.complete")


async def _test_llm_endpoint() -> None:
    """
    Log the configured LLM endpoint. Non-fatal — the endpoint is this server itself,
    so a connectivity test during startup would be a self-ping before the server is
    fully initialised. Connectivity is implicitly verified on the first incident.
    """
    endpoint = os.environ.get("ATLAS_LLM_ENDPOINT", "")
    logger.info(
        "atlas.startup.llm_endpoint_configured",
        endpoint=endpoint,
        note="LLM endpoint is this server — connectivity verified on first incident.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ATLAS AIOps Platform",
    description="Autonomous Telemetry & Log Analysis System",
    version="1.0.0",
    lifespan=lifespan,
)

frontend_origin = os.environ.get("ATLAS_FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class CMDBWebhookPayload(BaseModel):
    """ServiceNow change webhook payload."""
    change_id: str
    client_id: str
    change_description: str
    deployed_by: str
    affected_service: str
    timestamp: str
    risk_rating: str = "LOW"
    cab_approved_by: str = ""


class ApprovalRequest(BaseModel):
    """Human approval submission."""
    thread_id: str
    incident_id: str
    client_id: str
    approver: str
    token: str = Field(default="", description="Cryptographic approval token for PCI-DSS/SOX")


class RejectionRequest(BaseModel):
    """Human rejection with mandatory reason."""
    thread_id: str
    incident_id: str
    client_id: str
    rejector: str
    reason: str = Field(min_length=20, description="Rejection reason — minimum 20 characters")


class ModifyRequest(BaseModel):
    """L2 modification with parameter overrides."""
    thread_id: str
    incident_id: str
    client_id: str
    modifier: str
    modified_parameters: dict[str, Any]


_KNOWN_ATLAS_ROLES: frozenset[str] = frozenset({"L1", "L2", "L3", "SDM", "CLIENT"})
_MUTATION_ALLOWED_ROLES: frozenset[str] = frozenset({"L1", "L2", "L3", "SDM"})
_MODIFY_ALLOWED_ROLES: frozenset[str] = frozenset({"L2", "L3", "SDM"})


_PIPELINE_STAGE_ORDER: list[str] = [
    "ingest",
    "detect",
    "correlate",
    "search",
    "reason",
    "select",
    "route",
    "act",
    "learn",
]

_STAGE_LABELS: dict[str, str] = {
    "ingest": "Ingest",
    "detect": "Detect",
    "correlate": "Correlate",
    "search": "Search",
    "reason": "Reason",
    "select": "Select",
    "route": "Route",
    "act": "Act",
    "learn": "Learn",
}

_AUDIT_STAGE_NODE_MAP: dict[str, str] = {
    "pipeline_entry": "ingest",
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

_AUDIT_IGNORED_KEYS: frozenset[str] = frozenset(
    {
        "timestamp",
        "node",
        "actor",
        "action",
        "incident_id",
        "client_id",
    }
)


def _json_safe(value: Any) -> Any:
    """Return a JSON-safe clone of a value, coercing unsupported objects to strings."""
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return value


def _infer_pipeline_stage_from_state(state: dict[str, Any]) -> str:
    """Infer the current pipeline stage from persisted incident state."""
    execution_status = str(state.get("execution_status") or "").lower()
    resolution = str(state.get("resolution_outcome") or "").lower()

    if resolution == "success":
        return "learn"
    if execution_status in {"executing", "success", "failed", "rollback", "blocked", "error"}:
        return "act"
    if state.get("routing_decision"):
        return "route"
    if state.get("recommended_action_id"):
        return "select"
    if state.get("root_cause"):
        return "reason"
    if state.get("semantic_matches") or state.get("no_historical_precedent"):
        return "search"
    if state.get("blast_radius") or state.get("graph_unavailable"):
        return "correlate"
    if state.get("incident_priority"):
        return "detect"
    return "ingest"


def _stage_reason_ingest(state: dict[str, Any]) -> str:
    evidence_count = len(state.get("evidence_packages") or [])
    return f"Captured {evidence_count} evidence package(s) for incident processing."


def _stage_reason_detect(state: dict[str, Any]) -> str:
    priority = state.get("incident_priority") or "pending"
    summary = str(state.get("situation_summary") or "Detection summary pending.")
    return f"Priority {priority}. {summary}"


def _stage_reason_correlate(state: dict[str, Any]) -> str:
    blast = len(state.get("blast_radius") or [])
    deployments = len(state.get("recent_deployments") or [])
    return f"Graph correlation found {blast} blast-radius service(s) and {deployments} deployment(s)."


def _stage_reason_search(state: dict[str, Any]) -> str:
    if state.get("no_historical_precedent"):
        return "No strong historical precedent found; incident treated as novel."
    matches = len(state.get("semantic_matches") or [])
    return f"Semantic retrieval returned {matches} historical match(es)."


def _stage_reason_reason(state: dict[str, Any]) -> str:
    root_cause = str(state.get("root_cause") or "Root cause reasoning pending.")
    return root_cause[:200]


def _stage_reason_select(state: dict[str, Any]) -> str:
    action_id = state.get("recommended_action_id") or "pending"
    score = state.get("composite_confidence_score")
    if isinstance(score, (int, float)):
        return f"Selected action {action_id} with composite confidence {score:.2f}."
    return f"Selected action {action_id}."


def _stage_reason_route(state: dict[str, Any]) -> str:
    routing = state.get("routing_decision") or "pending"
    human_action = state.get("human_action")
    if human_action:
        return f"Routing {routing}; human decision received: {human_action}."
    return f"Routing decision: {routing}."


def _stage_reason_act(state: dict[str, Any]) -> str:
    execution = state.get("execution_status") or "pending"
    return f"Execution status: {execution}."


def _stage_reason_learn(state: dict[str, Any]) -> str:
    outcome = state.get("resolution_outcome") or "pending"
    mttr_seconds = state.get("mttr_seconds")
    if isinstance(mttr_seconds, int) and mttr_seconds > 0:
        return f"Resolution outcome: {outcome}. MTTR recorded at {mttr_seconds} seconds."
    return f"Resolution outcome: {outcome}."


_STAGE_REASON_BUILDERS: dict[str, Any] = {
    "ingest": _stage_reason_ingest,
    "detect": _stage_reason_detect,
    "correlate": _stage_reason_correlate,
    "search": _stage_reason_search,
    "reason": _stage_reason_reason,
    "select": _stage_reason_select,
    "route": _stage_reason_route,
    "act": _stage_reason_act,
    "learn": _stage_reason_learn,
}


def _build_stage_reason(state: dict[str, Any], stage: str) -> str:
    """Build a concise reason string for each pipeline stage."""
    builder = _STAGE_REASON_BUILDERS.get(stage)
    if not builder:
        return "Stage update recorded."
    return str(builder(state))


def _extract_stage_activity(audit_trail: list[Any]) -> tuple[dict[str, str], dict[str, list[str]]]:
    stage_timestamp: dict[str, str] = {}
    stage_changed_fields: dict[str, list[str]] = {}

    for entry in audit_trail:
        if not isinstance(entry, dict):
            continue
        node_name = str(entry.get("node") or "")
        stage = _AUDIT_STAGE_NODE_MAP.get(node_name)
        if not stage:
            continue

        timestamp = str(entry.get("timestamp") or "")
        if stage not in stage_timestamp and timestamp:
            stage_timestamp[stage] = timestamp

        changed_fields = sorted(str(key) for key in entry.keys() if key not in _AUDIT_IGNORED_KEYS)
        if changed_fields and stage not in stage_changed_fields:
            stage_changed_fields[stage] = changed_fields

    return stage_timestamp, stage_changed_fields


def _stage_status(stage: str, index: int, current_index: int, state: dict[str, Any]) -> str:
    status = "pending"
    if index < current_index:
        status = "completed"
    elif index == current_index:
        status = "active"

    execution_status = str(state.get("execution_status") or "").lower()
    human_action = str(state.get("human_action") or "").lower()
    if stage == "act" and execution_status in {"success", "failed", "rollback", "error"}:
        return "completed"
    if stage == "act" and (execution_status == "blocked" or human_action in {"rejected", "escalated"}):
        return "blocked"
    if stage == "learn" and str(state.get("resolution_outcome") or "").lower() == "success":
        return "completed"
    return status


def _build_stage_timeline(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a normalized nine-stage timeline snapshot from state + audit trail."""
    audit_trail = state.get("audit_trail") if isinstance(state.get("audit_trail"), list) else []
    stage_timestamp, stage_changed_fields = _extract_stage_activity(audit_trail)

    current_stage = _infer_pipeline_stage_from_state(state)
    current_index = _PIPELINE_STAGE_ORDER.index(current_stage)

    timeline = [
        {
            "stage": stage,
            "label": _STAGE_LABELS.get(stage, stage.title()),
            "status": _stage_status(stage, index, current_index, state),
            "timestamp": stage_timestamp.get(stage, ""),
            "reason": _build_stage_reason(state, stage),
            "changed_fields": stage_changed_fields.get(stage, []),
        }
        for index, stage in enumerate(_PIPELINE_STAGE_ORDER)
    ]

    return _json_safe(timeline)


def _serialize_incident_state(thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe, frontend-facing snapshot of one incident state."""
    return {
        "thread_id": thread_id,
        "incident_id": state.get("incident_id"),
        "client_id": state.get("client_id"),
        "priority": state.get("incident_priority"),
        "routing_decision": state.get("routing_decision"),
        "composite_confidence_score": state.get("composite_confidence_score"),
        "execution_status": state.get("execution_status"),
        "servicenow_ticket_id": state.get("servicenow_ticket_id"),
        "sla_breach_time": str(state.get("sla_breach_time", "")),
        "human_action": state.get("human_action"),
        "human_modifier": state.get("human_modifier"),
        "resolution_outcome": state.get("resolution_outcome"),
        "mttr_start_time": state.get("mttr_start_time"),
        "mttr_seconds": state.get("mttr_seconds"),
        "situation_summary": state.get("situation_summary"),
        "root_cause": state.get("root_cause"),
        "explanation_for_engineer": state.get("explanation_for_engineer"),
        "technical_evidence_summary": state.get("technical_evidence_summary"),
        "recommended_action_id": state.get("recommended_action_id"),
        "active_veto_conditions": state.get("active_veto_conditions") or [],
        "blast_radius": state.get("blast_radius") or [],
        "recent_deployments": state.get("recent_deployments") or [],
        "semantic_matches": state.get("semantic_matches") or [],
        "alternative_hypotheses": state.get("alternative_hypotheses") or [],
        "factor_scores": state.get("factor_scores") or {},
        "confidence_factors": state.get("confidence_factors") or {},
        "graph_unavailable": bool(state.get("graph_unavailable", False)),
        "no_historical_precedent": bool(state.get("no_historical_precedent", False)),
        "evidence_packages": state.get("evidence_packages") or [],
        "audit_trail": _json_safe(state.get("audit_trail") or []),
        "stage_timeline": _build_stage_timeline(state),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/webhook/cmdb", status_code=status.HTTP_200_OK)
async def receive_cmdb_webhook(payload: CMDBWebhookPayload) -> dict[str, str]:
    """
    Receive ServiceNow change webhook and update Neo4j knowledge graph.
    Called by ServiceNow when a change record is created or modified.
    """
    if not payload.client_id:
        raise HTTPException(status_code=422, detail="client_id is required.")

    logger.info(
        "webhook.cmdb.received",
        client_id=payload.client_id,
        change_id=payload.change_id,
        service=payload.affected_service,
    )

    # Update Neo4j with the new deployment node
    try:
        neo4j = Neo4jClient()
        cypher = """
        MERGE (d:Deployment {change_id: $change_id, client_id: $client_id})
        SET d.change_description = $change_description,
            d.deployed_by = $deployed_by,
            d.timestamp = datetime($timestamp),
            d.cab_risk_rating = $risk_rating,
            d.cab_approved_by = $cab_approved_by
        WITH d
        MATCH (s:Service {name: $affected_service, client_id: $client_id})
        MERGE (d)-[:MODIFIED_CONFIG_OF]->(s)
        """
        await neo4j.execute_write(
            cypher,
            {
                "change_id": payload.change_id,
                "client_id": payload.client_id,
                "change_description": payload.change_description,
                "deployed_by": payload.deployed_by,
                "timestamp": payload.timestamp,
                "risk_rating": payload.risk_rating,
                "cab_approved_by": payload.cab_approved_by,
                "affected_service": payload.affected_service,
            },
            client_id=payload.client_id,
            caller_module="backend.main",
        )
    except Exception as exc:
        logger.error("webhook.cmdb.neo4j_write_failed", error=str(exc))
        raise HTTPException(status_code=503, detail=f"Graph update failed: {exc}")

    # Broadcast to activity feed
    await activity_manager.broadcast({
        "type": "cmdb_change",
        "client_id": payload.client_id,
        "change_id": payload.change_id,
        "service": payload.affected_service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"status": "accepted", "change_id": payload.change_id}


@app.post("/api/incidents/approve", status_code=status.HTTP_200_OK)
async def approve_incident(request: ApprovalRequest, http_request: Request) -> dict[str, Any]:
    """
    Human approval submission. Resumes the suspended LangGraph pipeline.
    For PCI-DSS/SOX clients, validates the cryptographic approval token.
    """
    role, header_actor = _require_atlas_role(http_request, _MUTATION_ALLOWED_ROLES)
    _enforce_actor_header_match(header_actor, request.approver, "approver")
    _validate_client_id(request.client_id)

    # Validate approval token if provided (PCI-DSS/SOX dual sign-off)
    if request.token:
        from backend.execution.approval_tokens import validate_approval_token
        valid, token_incident_id, _, _reason = validate_approval_token(request.token)
        if not valid:
            raise HTTPException(status_code=403, detail="Approval token is invalid or expired.")
        if token_incident_id != request.incident_id:
            raise HTTPException(status_code=403, detail="Token was issued for a different incident.")

    logger.info(
        "api.approve.received",
        client_id=request.client_id,
        incident_id=request.incident_id,
        approver=request.approver,
        role=role,
        thread_id=request.thread_id,
    )

    from backend.orchestrator.pipeline import resume_after_approval
    try:
        final_state = await resume_after_approval(
            thread_id=request.thread_id,
            human_action="approved",
            modifier=request.approver,
        )
    except Exception as exc:
        logger.error("api.approve.pipeline_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline resume failed: {exc}")

    # Update active incidents and broadcast
    import time as _time
    final_state["thread_id"] = request.thread_id
    _active_incidents[request.thread_id] = final_state
    _active_incidents_timestamps[request.thread_id] = _time.monotonic()
    await incident_manager.send_to_client(request.client_id, {
        "type": "incident_updated",
        "incident": _serialize_incident_state(request.thread_id, final_state),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await activity_manager.broadcast({
        "type": "human_action",
        "action": "approved",
        "incident_id": request.incident_id,
        "client_id": request.client_id,
        "approver": request.approver,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "approved",
        "incident_id": request.incident_id,
        "execution_status": final_state.get("execution_status", ""),
        "resolution_outcome": final_state.get("resolution_outcome", ""),
    }


@app.post("/api/incidents/reject", status_code=status.HTTP_200_OK)
async def reject_incident(request: RejectionRequest, http_request: Request) -> dict[str, Any]:
    """
    Human rejection with mandatory reason. Resumes pipeline with rejection signal.
    """
    role, header_actor = _require_atlas_role(http_request, _MUTATION_ALLOWED_ROLES)
    _enforce_actor_header_match(header_actor, request.rejector, "rejector")
    _validate_client_id(request.client_id)

    logger.info(
        "api.reject.received",
        client_id=request.client_id,
        incident_id=request.incident_id,
        rejector=request.rejector,
        role=role,
    )

    from backend.orchestrator.pipeline import resume_after_approval
    try:
        final_state = await resume_after_approval(
            thread_id=request.thread_id,
            human_action="rejected",
            modifier=request.rejector,
            rejection_reason=request.reason,
        )
    except Exception as exc:
        logger.error("api.reject.pipeline_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline resume failed: {exc}")

    import time as _time
    final_state["thread_id"] = request.thread_id
    _active_incidents[request.thread_id] = final_state
    _active_incidents_timestamps[request.thread_id] = _time.monotonic()
    await incident_manager.send_to_client(request.client_id, {
        "type": "incident_updated",
        "incident": _serialize_incident_state(request.thread_id, final_state),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await activity_manager.broadcast({
        "type": "human_action",
        "action": "rejected",
        "incident_id": request.incident_id,
        "client_id": request.client_id,
        "rejector": request.rejector,
        "reason": request.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "rejected",
        "incident_id": request.incident_id,
        "reason": request.reason,
    }


@app.post("/api/incidents/modify", status_code=status.HTTP_200_OK)
async def modify_incident(request: ModifyRequest, http_request: Request) -> dict[str, Any]:
    """
    L2 modification — approve with parameter overrides. Logs the diff.
    """
    role, header_actor = _require_atlas_role(http_request, _MODIFY_ALLOWED_ROLES)
    _enforce_actor_header_match(header_actor, request.modifier, "modifier")
    _validate_client_id(request.client_id)

    logger.info(
        "api.modify.received",
        client_id=request.client_id,
        incident_id=request.incident_id,
        modifier=request.modifier,
        role=role,
    )

    from backend.orchestrator.pipeline import resume_after_approval
    try:
        final_state = await resume_after_approval(
            thread_id=request.thread_id,
            human_action="modified",
            modifier=request.modifier,
            modified_parameters=request.modified_parameters,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline resume failed: {exc}")

    final_state["thread_id"] = request.thread_id

    # Store modification diff for weight correction learning
    from backend.learning.weight_correction import record_modification_diff
    from backend.execution.playbook_library import get_playbook
    action_id = final_state.get("recommended_action_id", "")
    playbook = get_playbook(action_id) if action_id else None
    playbook_defaults = dict(playbook.parameters) if playbook else {}
    record_modification_diff(
        client_id=request.client_id,
        incident_id=request.incident_id,
        action_id=action_id,
        modification_diff=request.modified_parameters,
        playbook_defaults=playbook_defaults,
    )

    import time as _time
    _active_incidents[request.thread_id] = final_state
    _active_incidents_timestamps[request.thread_id] = _time.monotonic()
    await incident_manager.send_to_client(request.client_id, {
        "type": "incident_updated",
        "incident": _serialize_incident_state(request.thread_id, final_state),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "modified",
        "incident_id": request.incident_id,
        "execution_status": final_state.get("execution_status", ""),
    }


@app.get("/api/incidents/active", status_code=status.HTTP_200_OK)
async def get_active_incidents(client_id: str | None = None) -> dict[str, Any]:
    """
    Return all active incidents. Optionally filtered by client_id.
    """
    if client_id:
        _validate_client_id(client_id)
        incidents = {
            tid: state for tid, state in _active_incidents.items()
            if state.get("client_id") == client_id
        }
    else:
        incidents = dict(_active_incidents)

    return {
        "count": len(incidents),
        "incidents": [
            _serialize_incident_state(tid, state)
            for tid, state in incidents.items()
        ],
    }


@app.get("/api/incidents/details/{thread_id}", status_code=status.HTTP_200_OK)
async def get_incident_details(
    thread_id: str,
    request: Request,
    client_id: str | None = None,
) -> dict[str, Any]:
    """Return a detailed snapshot for one incident thread."""
    _require_atlas_role(request, _KNOWN_ATLAS_ROLES)

    state = _active_incidents.get(thread_id)
    if state is None:
        from backend.orchestrator.pipeline import get_incident_state

        state = await get_incident_state(thread_id)

    if state is None:
        raise HTTPException(status_code=404, detail="Incident thread not found.")

    incident_client_id = str(state.get("client_id") or "")
    if client_id:
        _validate_client_id(client_id)
        if incident_client_id and incident_client_id != client_id:
            raise HTTPException(
                status_code=403,
                detail="client_id does not match the incident thread scope.",
            )

    incident = _serialize_incident_state(thread_id, state)
    audit_trail = incident.get("audit_trail") if isinstance(incident.get("audit_trail"), list) else []
    last_updated = ""
    if audit_trail and isinstance(audit_trail[-1], dict):
        last_updated = str(audit_trail[-1].get("timestamp") or "")

    return {
        "thread_id": thread_id,
        "incident": incident,
        "audit_trail_count": len(audit_trail),
        "last_updated": last_updated,
    }


@app.get("/api/audit", status_code=status.HTTP_200_OK)
async def get_audit_log(
    client_id: str,
    from_time: str | None = None,
    to_time: str | None = None,
) -> dict[str, Any]:
    """
    Query the immutable audit log for a client.
    """
    _validate_client_id(client_id)

    now = datetime.now(timezone.utc)
    date_from = datetime.fromisoformat(from_time) if from_time else now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    date_to = datetime.fromisoformat(to_time) if to_time else now

    records = audit_db.query_audit(client_id, date_from, date_to)
    return {"client_id": client_id, "count": len(records), "records": records}


@app.get("/api/trust/{client_id}", status_code=status.HTTP_200_OK)
async def get_trust_level(client_id: str) -> dict[str, Any]:
    """
    Return trust level, progression metrics, and SLA uptime for a client.
    """
    _validate_client_id(client_id)

    from backend.config.client_registry import get_client
    from backend.learning.trust_progression import get_progression_metrics
    from backend.database.audit_db import get_sla_uptime_percent

    client_config = get_client(client_id)
    metrics = get_progression_metrics(client_id)
    sla_uptime = get_sla_uptime_percent(client_id)

    return {
        "client_id": client_id,
        "trust_level": client_config.get("trust_level", 0),
        "progression_metrics": metrics,
        "sla_uptime_percent": sla_uptime,
    }


@app.post("/api/trust/{client_id}/confirm-upgrade", status_code=status.HTTP_200_OK)
async def confirm_trust_upgrade(client_id: str, http_request: Request) -> dict[str, Any]:
    """
    SDM-only: confirm a pending trust stage upgrade for a client.
    Requires SDM role. Writes an immutable audit record.
    """
    role, header_actor = _require_atlas_role(http_request, frozenset({"SDM"}))
    _validate_client_id(client_id)

    from backend.config.client_registry import get_client
    from backend.learning.trust_progression import confirm_upgrade, get_progression_metrics

    client_config = get_client(client_id)
    current_stage = client_config.get("trust_level", 0)
    new_stage = current_stage + 1

    if new_stage > 4:
        raise HTTPException(status_code=400, detail="Client is already at maximum trust level.")

    try:
        confirm_upgrade(
            client_id=client_id,
            new_stage=new_stage,
            sdm_confirmed_by=header_actor or "SDM",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Trust upgrade failed: {exc}")

    metrics = get_progression_metrics(client_id)

    await activity_manager.broadcast({
        "type": "trust_upgrade",
        "client_id": client_id,
        "new_stage": new_stage,
        "previous_stage": current_stage,
        "confirmed_by": header_actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "client_id": client_id,
        "previous_stage": current_stage,
        "new_stage": new_stage,
        "confirmed_by": header_actor,
        "progression_metrics": metrics,
        "message": f"Trust level upgraded from Stage {current_stage} to Stage {new_stage}.",
    }


@app.get("/api/playbooks", status_code=status.HTTP_200_OK)
async def get_playbook_library() -> dict[str, Any]:
    """
    Return the full playbook library — all registered, versioned playbooks.
    Used by the frontend Playbooks page to display live library data.
    """
    from backend.execution.playbook_library import list_playbooks
    playbooks = list_playbooks()
    return {
        "count": len(playbooks),
        "playbooks": [
            {
                "playbook_id": pb.playbook_id,
                "name": pb.name,
                "description": pb.description,
                "action_class": pb.action_class,
                "auto_execute_eligible": pb.auto_execute_eligible,
                "estimated_resolution_minutes": pb.estimated_resolution_minutes,
                "target_technology": pb.target_technology,
                "anomaly_types_addressed": pb.anomaly_types_addressed,
                "pre_validation_checks": pb.pre_validation_checks,
                "success_metrics": pb.success_metrics,
                "rollback_playbook_id": pb.rollback_playbook_id,
                "parameters": dict(pb.parameters),
                "version": pb.version,
            }
            for pb in playbooks
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/logs/{client_id}")
async def websocket_logs(websocket: WebSocket, client_id: str) -> None:
    """Live log stream for a specific client."""
    try:
        _validate_client_id_ws(client_id)
    except ValueError:
        await websocket.close(code=4403, reason=f"Unknown client_id: '{client_id}'")
        logger.warning("ws.logs.rejected_unknown_client", client_id=client_id)
        return
    await log_manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive — data is pushed by the log generator
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        log_manager.disconnect(websocket, client_id)
        logger.info("ws.logs.disconnected", client_id=client_id)
    except Exception as exc:
        log_manager.disconnect(websocket, client_id)
        logger.warning("ws.logs.error", client_id=client_id, error=str(exc))


@app.websocket("/ws/incidents/{client_id}")
async def websocket_incidents(websocket: WebSocket, client_id: str) -> None:
    """Live incident state updates for a specific client."""
    try:
        _validate_client_id_ws(client_id)
    except ValueError:
        await websocket.close(code=4403, reason=f"Unknown client_id: '{client_id}'")
        logger.warning("ws.incidents.rejected_unknown_client", client_id=client_id)
        return
    await incident_manager.connect(websocket, client_id)

    # Send current active incidents immediately on connect
    current = [
        _serialize_incident_state(tid, state)
        for tid, state in _active_incidents.items()
        if state.get("client_id") == client_id
    ]
    if current:
        await websocket.send_json({"type": "active_incidents", "incidents": current})

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        incident_manager.disconnect(websocket, client_id)
    except Exception as exc:
        incident_manager.disconnect(websocket, client_id)
        logger.warning("ws.incidents.error", client_id=client_id, error=str(exc))


@app.websocket("/ws/activity")
async def websocket_activity(websocket: WebSocket) -> None:
    """Global ATLAS activity feed — all clients, all events."""
    await activity_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        activity_manager.disconnect(websocket)
    except Exception as exc:
        activity_manager.disconnect(websocket)
        logger.warning("ws.activity.error", error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Background tasks
# ─────────────────────────────────────────────────────────────────────────────

async def _agent_monitoring_loop(client_id: str) -> None:
    """
    Background task: continuously monitor agents for a client.
    Reads from the event queue and runs agents. When agents produce
    EvidencePackages, feeds them to the correlation engine.
    """
    from backend.agents.correlation_engine import CorrelationEngine
    from backend.database.neo4j_client import Neo4jClient
    from backend.ingestion.event_queue import get_event_queue

    logger.info("monitoring.started", client_id=client_id)
    neo4j = Neo4jClient()
    correlation_engine = CorrelationEngine(neo4j)
    event_queue = get_event_queue()

    while True:
        try:
            # Drain up to 50 events non-blocking from the client queue
            events: list[dict] = []
            for _ in range(50):
                event = event_queue.dequeue_nowait(client_id)
                if event is None:
                    break
                events.append(event)

            for event in events:
                # Broadcast raw log line to WebSocket log stream subscribers
                await log_manager.send_to_client(client_id, {
                    "type": "log_line",
                    "client_id": client_id,
                    "source": event.get("source_system", "unknown"),
                    "severity": event.get("severity", "INFO"),
                    "line": event.get("raw_payload", event.get("message", "")),
                    "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                })
                # Route event to the appropriate specialist agent
                result = await _route_event_to_agent(event, client_id, correlation_engine)
                if result is not None:
                    # Correlation engine produced an incident package
                    await _handle_incident_package(result, client_id)

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("monitoring.stopped", client_id=client_id)
            break
        except Exception as exc:
            logger.error("monitoring.error", client_id=client_id, error=str(exc))
            await asyncio.sleep(5)


async def _incident_ttl_pruner() -> None:
    """
    Background task: prune expired entries from _active_incidents every 5 minutes.
    Prevents unbounded memory growth during extended demo sessions or repeated runs.
    """
    import time as _time
    while True:
        try:
            await asyncio.sleep(300)  # run every 5 minutes
            now = _time.monotonic()
            expired = [
                tid for tid, ts in _active_incidents_timestamps.items()
                if now - ts > _ACTIVE_INCIDENT_TTL_SECONDS
            ]
            for tid in expired:
                _active_incidents.pop(tid, None)
                _active_incidents_timestamps.pop(tid, None)
            if expired:
                logger.info("incidents.ttl_pruned", count=len(expired))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("incidents.ttl_pruner_error", error=str(exc))


async def _route_event_to_agent(
    event: dict[str, Any],
    client_id: str,
    correlation_engine,
) -> Any:
    """
    Route a normalised event to the appropriate specialist agent based on source_type.
    Agents are long-lived singletons per client — never re-instantiated per event.
    Returns a CorrelatedIncident if the correlation engine fires, otherwise None.
    """
    from backend.agents.java_agent import JavaAgent
    from backend.agents.nodejs_agent import NodejsAgent
    from backend.agents.postgres_agent import PostgresAgent
    from backend.agents.redis_agent import RedisAgent
    from backend.agents.correlation_engine import CorrelatedIncident

    source_type: str = event.get("source_type", "")
    source_system: str = event.get("source_system", "")

    # Select agent type key and class
    if "java" in source_type or "spring" in source_type:
        agent_key = f"{client_id}:java"
        agent_cls = JavaAgent
    elif "node" in source_type or "nodejs" in source_type:
        agent_key = f"{client_id}:nodejs"
        agent_cls = NodejsAgent
    elif "postgres" in source_type or "pg" in source_type:
        agent_key = f"{client_id}:postgres"
        agent_cls = PostgresAgent
    elif "redis" in source_type:
        agent_key = f"{client_id}:redis"
        agent_cls = RedisAgent
    else:
        logger.debug(
            "monitoring.unroutable_event",
            client_id=client_id,
            source_type=source_type,
            source_system=source_system,
        )
        return None

    # Get or create the long-lived agent singleton for this client+type
    if agent_key not in _agent_registry:
        _agent_registry[agent_key] = agent_cls(client_id)
        logger.info("monitoring.agent_created", agent_key=agent_key)

    agent = _agent_registry[agent_key]

    await agent.ingest(event)
    pkg = agent.get_evidence()

    # Report current sigma to the correlation engine for early warning tracking.
    # This keeps the sigma cache fresh for all monitored services, not just those
    # that have fired an EvidencePackage.
    if hasattr(agent, "compute_sigma") and hasattr(agent, "_error_rate_window"):
        error_window = agent._error_rate_window.get(source_system, [])
        if error_window:
            current_error_rate = sum(error_window) / len(error_window)
            sigma = agent.compute_sigma("error_rate", current_error_rate)
            correlation_engine.report_service_sigma(client_id, source_system, sigma)

    if pkg is None:
        return None

    # Broadcast agent detection to activity feed
    await activity_manager.broadcast({
        "type": "agent_detection",
        "id": f"detect-{pkg.evidence_id[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": pkg.agent_id,
        "message": (
            f"{pkg.agent_id}: {pkg.anomaly_type} detected on {pkg.service_name} "
            f"(confidence {pkg.detection_confidence:.0%}, {pkg.severity_classification})"
        ),
        "client_id": client_id,
        "meta": {
            "anomaly_type": pkg.anomaly_type,
            "service_name": pkg.service_name,
            "confidence": pkg.detection_confidence,
        },
    })

    # Feed evidence package to correlation engine
    result: CorrelatedIncident | None = await correlation_engine.ingest_evidence(pkg)
    if result is not None:
        def _pkg_to_dict(p: Any) -> dict:
            d = vars(p) if hasattr(p, "__dict__") else dict(p)
            # Convert datetime fields to ISO strings for msgpack serialization
            for k, v in d.items():
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
            return d

        return {
            "evidence_packages": [_pkg_to_dict(p) for p in result.evidence_packages],
            "correlation_type": result.correlation_type,
            "early_warning_signals": result.early_warning_signals,
        }
    return None


async def _handle_incident_package(package: dict[str, Any], client_id: str) -> None:
    """
    Handle an incident package from the correlation engine.
    Starts the pipeline and tracks the incident.
    Prunes terminal incidents from _active_incidents to prevent unbounded growth.
    """
    import time as _time
    from backend.orchestrator.pipeline import run_incident

    # Prune stale/terminal incidents before adding new ones
    _prune_active_incidents()

    evidence_packages = package.get("evidence_packages", [])
    correlation_type = package.get("correlation_type", "ISOLATED_ANOMALY")
    early_warnings = package.get("early_warning_signals", [])

    try:
        thread_id, state = await run_incident(
            evidence_packages=evidence_packages,
            client_id=client_id,
            correlation_type=correlation_type,
            early_warning_signals=early_warnings,
        )
        # Inject thread_id into state so frontend can use it for approve/reject calls
        state["thread_id"] = thread_id
        _active_incidents[thread_id] = state
        _active_incidents_timestamps[thread_id] = _time.monotonic()

        # Broadcast new incident to WebSocket subscribers
        await incident_manager.send_to_client(client_id, {
            "type": "new_incident",
            **_serialize_incident_state(thread_id, state),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await activity_manager.broadcast({
            "type": "incident_created",
            "client_id": client_id,
            "incident_id": state.get("incident_id"),
            "priority": state.get("incident_priority"),
            "routing": state.get("routing_decision"),
            "confidence": state.get("composite_confidence_score"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        logger.error(
            "main.incident_pipeline_failed",
            client_id=client_id,
            error=str(exc),
        )


def _prune_active_incidents() -> None:
    """
    Remove incidents that have reached a terminal state or exceeded the TTL.
    Terminal states: execution_status in ('success', 'failed', 'error') and
    resolution_outcome is set, or the incident is older than 24 hours.
    """
    import time as _time
    now = _time.monotonic()
    terminal_statuses = frozenset({"success", "failed", "error", "rejected", "escalated"})
    to_remove = []
    for tid, state in _active_incidents.items():
        age = now - _active_incidents_timestamps.get(tid, now)
        exec_status = state.get("execution_status", "")
        resolution = state.get("resolution_outcome", "")
        if age > _ACTIVE_INCIDENT_TTL_SECONDS:
            to_remove.append(tid)
        elif exec_status in terminal_statuses and resolution:
            to_remove.append(tid)
    for tid in to_remove:
        _active_incidents.pop(tid, None)
        _active_incidents_timestamps.pop(tid, None)
    if to_remove:
        logger.info("main.active_incidents_pruned", count=len(to_remove))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Internal LLM endpoint — POST /internal/llm/reason
# ─────────────────────────────────────────────────────────────────────────────

class LLMReasonRequest(BaseModel):
    """Structured reasoning context payload from n5_reasoning.py."""
    incident_context: dict[str, Any]
    evidence_summary: list[dict[str, Any]]
    blast_radius: list[dict[str, Any]] = []
    recent_deployments: list[dict[str, Any]] = []
    historical_graph_matches: list[dict[str, Any]] = []
    semantic_matches: dict[str, Any] = {}
    compliance_profile: dict[str, Any] = {}
    reasoning_instructions: str = ""


_LLM_RESPONSE_SCHEMA = {
    "name": "atlas_reasoning_output",
    "description": "Structured ITIL root cause analysis output",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {"type": "string"},
            "confidence_factors": {"type": "object"},
            "recommended_action_id": {"type": "string"},
            "alternative_hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "hypothesis": {"type": "string"},
                        "evidence_for": {"type": "string"},
                        "evidence_against": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["hypothesis", "evidence_for", "evidence_against", "confidence"],
                },
            },
            "explanation_for_engineer": {"type": "string"},
            "technical_evidence_summary": {"type": "string"},
        },
        "required": [
            "root_cause", "confidence_factors", "recommended_action_id",
            "alternative_hypotheses", "explanation_for_engineer", "technical_evidence_summary",
        ],
    },
}


@app.post("/internal/llm/reason", status_code=status.HTTP_200_OK)
async def internal_llm_reason(request: LLMReasonRequest) -> dict[str, Any]:
    """
    Internal ATLAS LLM reasoning endpoint.
    Called by n5_reasoning.py. Calls Anthropic Claude with tool_use mode.
    Falls back to pre-computed response files if Claude is unavailable.
    """
    import json as _json
    from pathlib import Path

    client_id: str = request.incident_context.get("client_id", "")

    logger.info(
        "llm_endpoint.request_received",
        client_id=client_id,
        incident_id=request.incident_context.get("incident_id", ""),
    )

    # ── Attempt Ollama call (primary — qwen3-coder:480b-cloud) ──────────────────
    ollama_base = os.environ.get("OLLAMA_BASE_URL", _OLLAMA_BASE_URL_DEFAULT)
    ollama_model = os.environ.get("OLLAMA_MODEL", _OLLAMA_MODEL_DEFAULT)
    try:
        result = await _call_ollama(request, ollama_base, ollama_model, client_id)
        if result:
            action_id = result.get("recommended_action_id", "")
            if action_id and not validate_action_id(action_id):
                logger.warning(
                    "llm_endpoint.invalid_action_id_from_ollama",
                    action_id=action_id,
                    client_id=client_id,
                )
                result["recommended_action_id"] = _infer_action_id(request)
            logger.info(
                "llm_endpoint.ollama_success",
                client_id=client_id,
                model=ollama_model,
                action_id=result.get("recommended_action_id"),
            )
            return result
    except Exception as exc:
        logger.warning(
            "llm_endpoint.ollama_failed",
            client_id=client_id,
            model=ollama_model,
            error=str(exc),
        )

    # ── Attempt Claude call (secondary — only if key is set) ─────────────────
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            result = await _call_claude(request, anthropic_key, client_id)
            if result:
                # Validate recommended_action_id before returning
                action_id = result.get("recommended_action_id", "")
                if action_id and not validate_action_id(action_id):
                    logger.warning(
                        "llm_endpoint.invalid_action_id_from_claude",
                        action_id=action_id,
                        client_id=client_id,
                    )
                    result["recommended_action_id"] = _infer_action_id(request)
                logger.info(
                    "llm_endpoint.claude_success",
                    client_id=client_id,
                    action_id=result.get("recommended_action_id"),
                )
                return result
        except Exception as exc:
            logger.warning(
                "llm_endpoint.claude_failed",
                client_id=client_id,
                error=str(exc),
            )

    # ── Fallback to pre-computed response ─────────────────────────────────────
    fallback_dir = Path(__file__).parent.parent / "data" / "fallbacks"
    _FALLBACK_MAP = {
        "FINCORE_UK_001": "financecore_incident_response.json",
        "RETAILMAX_EU_002": "retailmax_incident_response.json",
    }
    filename = _FALLBACK_MAP.get(client_id, f"{client_id.lower()}_incident_response.json")
    fallback_path = fallback_dir / filename

    if fallback_path.exists():
        try:
            with open(fallback_path, encoding="utf-8") as f:
                data = _json.load(f)
            logger.info(
                "llm_endpoint.fallback_loaded",
                client_id=client_id,
                path=str(fallback_path),
            )
            return data
        except Exception as exc:
            logger.error("llm_endpoint.fallback_load_error", error=str(exc))

    raise HTTPException(
        status_code=503,
        detail="LLM unavailable and no fallback found. Incident will be escalated to human review.",
    )


async def _call_ollama(
    request: LLMReasonRequest,
    base_url: str,
    model: str,
    client_id: str,
) -> dict[str, Any] | None:
    """
    Call local Ollama with qwen3-coder:480b-cloud using the /api/chat endpoint.
    Returns structured JSON matching the ATLAS LLM response schema.
    Timeout: 60 seconds (cloud-routed model, latency higher than local).
    """
    import json as _json
    import httpx

    prompt = _build_claude_prompt(request)  # same prompt works for any model

    system_msg = (
        "You are ATLAS, an AIOps reasoning engine. "
        "You MUST respond with ONLY valid JSON matching the exact schema provided. "
        "No markdown, no explanation, no code fences — raw JSON only."
    )

    schema_instruction = (
        "\n\nRespond with ONLY this JSON structure (no other text):\n"
        "{\n"
        '  "root_cause": "string",\n'
        '  "confidence_factors": {},\n'
        '  "recommended_action_id": "connection-pool-recovery-v2 or redis-memory-policy-rollback-v1",\n'
        '  "alternative_hypotheses": [\n'
        '    {"hypothesis": "string", "evidence_for": "string", "evidence_against": "string", "confidence": 0.0}\n'
        "  ],\n"
        '  "explanation_for_engineer": "string (min 50 chars, L2 level)",\n'
        '  "technical_evidence_summary": "string"\n'
        "}"
    )

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt + schema_instruction},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 1024},
            },
        )

    if resp.status_code != 200:
        logger.warning(
            "llm_endpoint.ollama_bad_status",
            status=resp.status_code,
            body=resp.text[:300],
            client_id=client_id,
        )
        return None

    raw_content = resp.json().get("message", {}).get("content", "")
    if not raw_content:
        return None

    # Strip any accidental markdown fences
    raw_content = raw_content.strip()
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()

    try:
        parsed = _json.loads(raw_content)
    except _json.JSONDecodeError as exc:
        logger.warning(
            "llm_endpoint.ollama_invalid_json",
            client_id=client_id,
            error=str(exc),
            raw_preview=raw_content[:200],
        )
        return None

    # Validate required fields are present
    required = {
        "root_cause", "confidence_factors", "recommended_action_id",
        "alternative_hypotheses", "explanation_for_engineer", "technical_evidence_summary",
    }
    missing = required - set(parsed.keys())
    if missing:
        logger.warning(
            "llm_endpoint.ollama_missing_fields",
            client_id=client_id,
            missing=list(missing),
        )
        # Fill missing fields with safe defaults rather than failing
        for field in missing:
            if field == "confidence_factors":
                parsed[field] = {}
            elif field == "alternative_hypotheses":
                parsed[field] = []
            else:
                parsed[field] = ""

    # Validate explanation length
    explanation = parsed.get("explanation_for_engineer", "")
    if len(explanation) < 50:
        parsed["explanation_for_engineer"] = (
            f"{explanation} ATLAS detected an anomaly requiring investigation. "
            "Please review the evidence and recommended action."
        )

    return parsed


async def _call_claude(
    request: LLMReasonRequest,
    api_key: str,
    client_id: str,
) -> dict[str, Any] | None:
    """Call Anthropic Claude with tool_use mode and return structured output."""
    import json as _json
    import httpx

    prompt = _build_claude_prompt(request)

    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 2048,
        "tools": [_LLM_RESPONSE_SCHEMA],
        "tool_choice": {"type": "tool", "name": "atlas_reasoning_output"},
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    if resp.status_code != 200:
        logger.warning(
            "llm_endpoint.anthropic_bad_status",
            status=resp.status_code,
            body=resp.text[:300],
        )
        return None

    data = resp.json()
    # Extract tool_use block
    for block in data.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "atlas_reasoning_output":
            return block.get("input", {})

    return None


def _build_claude_prompt(request: LLMReasonRequest) -> str:
    """Build the ITIL 6-step reasoning prompt for Claude."""
    import json as _json

    evidence_text = _json.dumps(request.evidence_summary, indent=2)
    deployments_text = _json.dumps(request.recent_deployments[:3], indent=2)
    historical_text = _json.dumps(request.historical_graph_matches[:3], indent=2)
    semantic_text = _json.dumps(request.semantic_matches, indent=2)
    blast_text = _json.dumps(request.blast_radius[:5], indent=2)
    compliance = request.compliance_profile

    return f"""You are ATLAS, an AIOps platform performing ITIL-structured root cause analysis.

INCIDENT CONTEXT:
{_json.dumps(request.incident_context, indent=2)}

EVIDENCE FROM SPECIALIST AGENTS:
{evidence_text}

BLAST RADIUS (affected services):
{blast_text}

RECENT DEPLOYMENTS (last 7 days):
{deployments_text}

HISTORICAL GRAPH MATCHES (same service + anomaly type):
{historical_text}

SEMANTIC SIMILARITY MATCHES (ChromaDB vector search):
{semantic_text}

COMPLIANCE PROFILE:
- Frameworks: {compliance.get('compliance_frameworks', [])}
- Max action class: {compliance.get('max_action_class', 1)}
- Trust level: {compliance.get('trust_level', 0)}

INSTRUCTIONS:
{request.reasoning_instructions}

Perform the 6-step ITIL analysis and call the atlas_reasoning_output tool with your structured findings.
The recommended_action_id must be one of: connection-pool-recovery-v2, redis-memory-policy-rollback-v1
The explanation_for_engineer must be at least 50 characters and written at L2 engineer level.
Provide at least 2 alternative_hypotheses with evidence_for and evidence_against."""


def _infer_action_id(request: LLMReasonRequest) -> str:
    """Infer the correct action_id from evidence when Claude returns an invalid one."""
    for pkg in request.evidence_summary:
        anomaly = pkg.get("anomaly_type", "")
        if anomaly in ("CONNECTION_POOL_EXHAUSTED", "DB_DEADLOCK", "DB_PANIC"):
            return "connection-pool-recovery-v2"
        if anomaly in ("REDIS_OOM", "REDIS_COMMAND_REJECTED"):
            return "redis-memory-policy-rollback-v1"
    return "connection-pool-recovery-v2"


# ─────────────────────────────────────────────────────────────────────────────
# Log ingest endpoint — POST /api/logs/ingest
# ─────────────────────────────────────────────────────────────────────────────

class LogIngestPayload(BaseModel):
    """Single log line from fault scripts or log generators."""
    client_id: str
    source: str
    severity: str
    line: str
    timestamp: str = ""


@app.post("/api/logs/ingest", status_code=status.HTTP_200_OK)
async def ingest_log_line(payload: LogIngestPayload) -> dict[str, str]:
    """
    Accept a log line from fault scripts and broadcast it to WebSocket subscribers.
    Also routes the event through the normaliser and into the agent event queue.
    """
    if not payload.client_id:
        raise HTTPException(status_code=422, detail="client_id is required.")

    ts = payload.timestamp or datetime.now(timezone.utc).isoformat()

    # Broadcast to log WebSocket subscribers
    await log_manager.send_to_client(payload.client_id, {
        "type": "log_line",
        "client_id": payload.client_id,
        "source": payload.source,
        "severity": payload.severity,
        "line": payload.line,
        "timestamp": ts,
    })

    # Route into the agent event queue for processing
    try:
        from backend.ingestion.normaliser import normalise
        from backend.ingestion.event_queue import get_event_queue

        source_type = _infer_source_type(payload.source, payload.line)
        raw_event = {
            "client_id": payload.client_id,
            "source_system": payload.source,
            "source_type": source_type,
            "severity": payload.severity,
            "message": payload.line,
            "raw_payload": payload.line,
            "timestamp": ts,
        }
        normalised = normalise(raw_event)
        if normalised:
            eq = get_event_queue()
            await eq.enqueue(normalised, payload.client_id)
    except Exception as exc:
        logger.debug("log_ingest.queue_error", error=str(exc))

    return {"status": "accepted"}


def _infer_source_type(source: str, line: str) -> str:
    """Infer source_type from source name and log line content."""
    s = source.lower()
    l = line.lower()
    if "redis" in s or "cache" in s:
        return "redis"
    if "postgres" in s or "transaction" in s or "pg" in s or "transactiondb" in s:
        return "postgres"
    if "node" in s or "cart" in s or "product" in s or "cartservice" in s or "productapi" in s:
        return "nodejs"
    if "java" in l or "hikari" in l or "spring" in l or "payment" in s or "auth" in s:
        return "java-spring-boot"
    if "kubernetes" in s or "kubernetes" in l or "k8s" in s:
        return "kubernetes"
    return "unknown"


def _validate_client_id(client_id: str) -> None:
    """Raise HTTP 422 if client_id is not registered."""
    from backend.config.client_registry import get_client
    try:
        get_client(client_id)
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown client_id: '{client_id}'. Not registered in ATLAS.",
        )


def _normalize_atlas_role(raw_role: str) -> str:
    """Normalize user role value supplied via request header."""
    return raw_role.strip().upper()


def _require_atlas_role(
    request: Request,
    allowed_roles: frozenset[str],
) -> tuple[str, str]:
    """
    Enforce role headers for mutation/detail APIs without introducing login auth.

    Returns:
        Tuple of (normalized_role, header_actor)
    """
    header_role = _normalize_atlas_role(str(request.headers.get("x-atlas-role") or ""))
    if not header_role:
        raise HTTPException(status_code=403, detail="X-ATLAS-ROLE header is required.")

    if header_role not in _KNOWN_ATLAS_ROLES:
        raise HTTPException(status_code=403, detail="X-ATLAS-ROLE value is not recognized.")

    if header_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{header_role}' is not allowed for this operation.",
        )

    header_actor = str(request.headers.get("x-atlas-user") or "").strip()
    return header_role, header_actor


def _enforce_actor_header_match(header_actor: str, payload_actor: str, actor_field: str) -> None:
    """Reject requests where payload actor is blank or mismatches declared header actor."""
    normalized_payload_actor = str(payload_actor).strip()
    if not normalized_payload_actor:
        raise HTTPException(status_code=422, detail=f"{actor_field} is required.")

    if header_actor and header_actor.casefold() != normalized_payload_actor.casefold():
        raise HTTPException(
            status_code=403,
            detail=f"{actor_field} does not match X-ATLAS-USER header.",
        )


def _validate_client_id_ws(client_id: str) -> None:
    """For WebSocket paths — validate client_id and raise if unknown."""
    from backend.config.client_registry import get_all_client_ids
    if client_id not in get_all_client_ids():
        raise ValueError(f"Unknown client_id for WebSocket: '{client_id}'")
