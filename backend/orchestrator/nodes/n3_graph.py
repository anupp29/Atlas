"""
Node 3 — Graph Intelligence.

Runs three Neo4j Cypher queries in parallel to retrieve blast radius,
deployment correlations, and historical patterns. Stores the graph
traversal path for frontend visualisation.

Inputs:  client_id, evidence_packages (from state)
Outputs: blast_radius, recent_deployments, historical_graph_matches,
         graph_traversal_path, graph_unavailable, audit_trail entry
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.database.neo4j_client import Neo4jClient
from backend.orchestrator.state import AtlasState, append_audit_entry

logger = structlog.get_logger(__name__)

# Module-level client — initialised once, reused across requests
_neo4j: Neo4jClient | None = None
_neo4j_lock = asyncio.Lock()


async def _get_neo4j() -> Neo4jClient:
    """Return the module-level Neo4jClient singleton, creating it atomically if needed."""
    global _neo4j
    if _neo4j is None:
        async with _neo4j_lock:
            if _neo4j is None:
                _neo4j = Neo4jClient()
    return _neo4j


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 3: Run three Cypher queries in parallel.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with graph intelligence results.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    evidence_packages: list[dict] = state["evidence_packages"]

    logger.info(
        "n3_graph.started",
        client_id=client_id,
        incident_id=incident_id,
        evidence_count=len(evidence_packages),
    )

    affected_services = list({p.get("service_name", "") for p in evidence_packages if p.get("service_name")})
    primary_service = affected_services[0] if affected_services else ""
    anomaly_types = list({p.get("anomaly_type", "") for p in evidence_packages if p.get("anomaly_type")})
    primary_anomaly = anomaly_types[0] if anomaly_types else ""

    try:
        blast_radius, deployments, historical = await asyncio.gather(
            _query_blast_radius(client_id, primary_service),
            _query_deployment_correlation(client_id, affected_services),
            _query_historical_pattern(client_id, affected_services, primary_anomaly),
            return_exceptions=True,
        )

        # Handle partial failures gracefully
        if isinstance(blast_radius, Exception):
            logger.warning("n3_graph.blast_radius_failed", error=str(blast_radius))
            blast_radius = []
        if isinstance(deployments, Exception):
            logger.warning("n3_graph.deployments_failed", error=str(deployments))
            deployments = []
        if isinstance(historical, Exception):
            logger.warning("n3_graph.historical_failed", error=str(historical))
            historical = []

        graph_unavailable = False

    except Exception as exc:
        logger.error(
            "n3_graph.neo4j_unavailable",
            client_id=client_id,
            incident_id=incident_id,
            error=str(exc),
        )
        blast_radius, deployments, historical = [], [], []
        graph_unavailable = True

    # Build traversal path for frontend visualisation
    traversal_path = _build_traversal_path(
        primary_service=primary_service,
        blast_radius=blast_radius,
        deployments=deployments,
        historical=historical,
    )

    logger.info(
        "n3_graph.complete",
        client_id=client_id,
        incident_id=incident_id,
        blast_radius_count=len(blast_radius),
        deployments_count=len(deployments),
        historical_count=len(historical),
        graph_unavailable=graph_unavailable,
    )

    return {
        "blast_radius": blast_radius,
        "recent_deployments": deployments,
        "historical_graph_matches": historical,
        "graph_traversal_path": traversal_path,
        "graph_unavailable": graph_unavailable,
        "audit_trail": append_audit_entry(state, {
            "node": "n3_graph",
            "actor": "ATLAS_AUTO",
            "action": "graph_intelligence_complete",
            "blast_radius_services": len(blast_radius),
            "deployments_found": len(deployments),
            "historical_matches": len(historical),
            "graph_unavailable": graph_unavailable,
            "primary_service": primary_service,
        }),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Cypher queries (exact queries from ARCHITECTURE.md)
# ─────────────────────────────────────────────────────────────────────────────

async def _query_blast_radius(client_id: str, service_name: str) -> list[dict]:
    """
    Query 1 — Blast Radius.
    Traverse DEPENDS_ON from affected service up to 3 hops.
    Returns all downstream services with criticality and SLA threshold.
    """
    if not service_name:
        return []

    cypher = """
    MATCH (s:Service {name: $service_name, client_id: $client_id})
    MATCH (s)-[:DEPENDS_ON*1..3]-(connected:Service)
    WHERE connected.client_id = $client_id
    OPTIONAL MATCH (connected)-[:COVERED_BY]->(sla:SLA {client_id: $client_id})
    RETURN DISTINCT
        connected.name AS name,
        connected.criticality AS criticality,
        connected.tech_type AS tech_type,
        sla.breach_threshold_minutes AS breach_threshold_minutes
    ORDER BY connected.criticality
    """
    neo4j = await _get_neo4j()
    results = await neo4j.execute_query(
        cypher,
        {"service_name": service_name, "client_id": client_id},
        client_id=client_id,
    )
    return [dict(r) for r in (results or [])]


async def _query_deployment_correlation(
    client_id: str,
    affected_services: list[str],
) -> list[dict]:
    """
    Query 2 — Deployment Correlation.
    Find CMDB change records from last 7 days touching affected services.
    """
    if not affected_services:
        return []

    cypher = """
    MATCH (d:Deployment {client_id: $client_id})
    WHERE d.timestamp > datetime() - duration('P7D')
    MATCH (d)-[:MODIFIED_CONFIG_OF|DEPLOYED_TO]->(s:Service)
    WHERE s.name IN $affected_services
    AND s.client_id = $client_id
    RETURN
        d.change_id AS change_id,
        d.change_description AS change_description,
        d.deployed_by AS deployed_by,
        d.timestamp AS timestamp,
        d.cab_risk_rating AS cab_risk_rating,
        d.cab_approved_by AS cab_approved_by,
        s.name AS affected_service
    ORDER BY d.timestamp DESC
    """
    neo4j = await _get_neo4j()
    results = await neo4j.execute_query(
        cypher,
        {"affected_services": affected_services, "client_id": client_id},
        client_id=client_id,
    )
    return [dict(r) for r in (results or [])]


async def _query_historical_pattern(
    client_id: str,
    affected_services: list[str],
    anomaly_type: str,
) -> list[dict]:
    """
    Query 3 — Historical Pattern.
    Find past incidents for the same services with the same anomaly type.
    """
    if not affected_services or not anomaly_type:
        return []

    cypher = """
    MATCH (i:Incident {client_id: $client_id})-[:AFFECTED]->(s:Service)
    WHERE s.name IN $affected_services
    AND s.client_id = $client_id
    AND i.anomaly_type = $anomaly_type
    RETURN
        i.incident_id AS incident_id,
        i.title AS title,
        i.root_cause AS root_cause,
        i.resolution AS resolution,
        i.mttr_minutes AS mttr_minutes,
        i.resolved_by AS resolved_by,
        i.playbook_used AS playbook_used,
        i.occurred_at AS occurred_at,
        s.name AS service_name
    ORDER BY i.occurred_at DESC
    LIMIT 5
    """
    neo4j = await _get_neo4j()
    results = await neo4j.execute_query(
        cypher,
        {
            "affected_services": affected_services,
            "anomaly_type": anomaly_type,
            "client_id": client_id,
        },
        client_id=client_id,
    )
    return [dict(r) for r in (results or [])]


def _build_traversal_path(
    primary_service: str,
    blast_radius: list[dict],
    deployments: list[dict],
    historical: list[dict],
) -> list[dict]:
    """
    Build an ordered list of nodes and edges visited during graph traversal.
    Used by the frontend to animate the reasoning path.
    """
    path: list[dict] = []

    if primary_service:
        path.append({"type": "node", "label": primary_service, "node_type": "Service", "role": "affected"})

    for dep in deployments:
        change_id = dep.get("change_id", "")
        if change_id:
            path.append({"type": "node", "label": change_id, "node_type": "Deployment", "role": "deployment"})
            path.append({"type": "edge", "from": change_id, "to": primary_service, "relationship": "MODIFIED_CONFIG_OF"})

    for svc in blast_radius:
        name = svc.get("name", "")
        if name:
            path.append({"type": "node", "label": name, "node_type": "Service", "role": "blast_radius"})
            path.append({"type": "edge", "from": primary_service, "to": name, "relationship": "DEPENDS_ON"})

    for inc in historical:
        inc_id = inc.get("incident_id", "")
        svc_name = inc.get("service_name", primary_service)
        if inc_id:
            path.append({"type": "node", "label": inc_id, "node_type": "Incident", "role": "historical"})
            path.append({"type": "edge", "from": inc_id, "to": svc_name, "relationship": "AFFECTED"})

    return path
