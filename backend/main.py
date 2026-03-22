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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
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
async def approve_incident(request: ApprovalRequest) -> dict[str, Any]:
    """
    Human approval submission. Resumes the suspended LangGraph pipeline.
    For PCI-DSS/SOX clients, validates the cryptographic approval token.
    """
    _validate_client_id(request.client_id)

    # Validate approval token if provided (PCI-DSS/SOX dual sign-off)
    if request.token:
        from backend.execution.approval_tokens import validate_approval_token
        valid, token_incident_id, approver_role, _reason = validate_approval_token(request.token)
        if not valid:
            raise HTTPException(status_code=403, detail="Approval token is invalid or expired.")
        if token_incident_id != request.incident_id:
            raise HTTPException(status_code=403, detail="Token was issued for a different incident.")

    logger.info(
        "api.approve.received",
        client_id=request.client_id,
        incident_id=request.incident_id,
        approver=request.approver,
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
    final_state["thread_id"] = request.thread_id
    _active_incidents[request.thread_id] = final_state
    await incident_manager.send_to_client(request.client_id, {
        "type": "incident_approved",
        "incident_id": request.incident_id,
        "thread_id": request.thread_id,
        "execution_status": final_state.get("execution_status", ""),
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
async def reject_incident(request: RejectionRequest) -> dict[str, Any]:
    """
    Human rejection with mandatory reason. Resumes pipeline with rejection signal.
    """
    _validate_client_id(request.client_id)

    logger.info(
        "api.reject.received",
        client_id=request.client_id,
        incident_id=request.incident_id,
        rejector=request.rejector,
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

    final_state["thread_id"] = request.thread_id
    _active_incidents[request.thread_id] = final_state
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
async def modify_incident(request: ModifyRequest) -> dict[str, Any]:
    """
    L2 modification — approve with parameter overrides. Logs the diff.
    """
    _validate_client_id(request.client_id)

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
            {
                "thread_id": tid,
                "incident_id": state.get("incident_id"),
                "client_id": state.get("client_id"),
                "priority": state.get("incident_priority"),
                "routing_decision": state.get("routing_decision"),
                "composite_confidence_score": state.get("composite_confidence_score"),
                "execution_status": state.get("execution_status"),
                "servicenow_ticket_id": state.get("servicenow_ticket_id"),
                "sla_breach_time": str(state.get("sla_breach_time", "")),
            }
            for tid, state in incidents.items()
        ],
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
        state for state in _active_incidents.values()
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
            "thread_id": thread_id,
            "incident_id": state.get("incident_id"),
            "priority": state.get("incident_priority"),
            "routing_decision": state.get("routing_decision"),
            "composite_confidence_score": state.get("composite_confidence_score"),
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
    if "redis" in s:
        return "redis"
    if "postgres" in s or "transaction" in s or "pg" in s:
        return "postgres"
    if "node" in s or "cart" in s or "product" in s:
        return "nodejs"
    if "java" in l or "hikari" in l or "spring" in l or "payment" in s or "auth" in s:
        return "java-spring-boot"
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


def _validate_client_id_ws(client_id: str) -> None:
    """For WebSocket paths — validate client_id and raise if unknown."""
    from backend.config.client_registry import get_all_client_ids
    if client_id not in get_all_client_ids():
        raise ValueError(f"Unknown client_id for WebSocket: '{client_id}'")
