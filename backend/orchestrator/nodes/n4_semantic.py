"""
Node 4 — Semantic Retrieval.

Runs ChromaDB vector similarity search to find historically similar incidents.
Cross-references with N3 graph results for double-confirmation.
Falls back to cross-client federated search on cold start (<5 incidents).

Inputs:  client_id, evidence_packages, historical_graph_matches (from state)
Outputs: semantic_matches, no_historical_precedent, audit_trail entry
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from backend.database.chromadb_client import ChromaDBClient
from backend.orchestrator.state import AtlasState, append_audit_entry

logger = structlog.get_logger(__name__)

_MIN_SIMILARITY_THRESHOLD: float = 0.50
_COLD_START_THRESHOLD: int = 5

# Module-level client — initialised once
_chroma: ChromaDBClient | None = None
_chroma_lock = asyncio.Lock()


async def _get_chroma() -> ChromaDBClient:
    """Return the module-level ChromaDBClient singleton, creating it atomically if needed."""
    global _chroma
    if _chroma is None:
        async with _chroma_lock:
            if _chroma is None:
                _chroma = ChromaDBClient()
    return _chroma


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 4: Run ChromaDB similarity search.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with semantic search results.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]
    evidence_packages: list[dict] = state["evidence_packages"]
    graph_matches: list[dict] = state.get("historical_graph_matches", [])

    logger.info(
        "n4_semantic.started",
        client_id=client_id,
        incident_id=incident_id,
    )

    # Build search query from current incident context
    query_text = _build_query_text(evidence_packages)

    try:
        chroma = await _get_chroma()

        # Check collection size for cold-start detection
        collection = chroma.get_or_create_collection(client_id)
        collection_size = collection.count()

        # Primary search: client-specific collection
        raw_results = chroma.similarity_search(
            query_text=query_text,
            client_id=client_id,
            n_results=3,
        )

        # Filter to results above minimum threshold
        results = [r for r in raw_results if r.get("similarity_score", 0.0) >= _MIN_SIMILARITY_THRESHOLD]

        # Cold-start: supplement with cross-client federated search
        if collection_size < _COLD_START_THRESHOLD:
            logger.info(
                "n4_semantic.cold_start_detected",
                client_id=client_id,
                collection_size=collection_size,
            )
            tech_stack = _extract_tech_stack(evidence_packages)
            cross_results = chroma.cross_client_search(
                query_text=query_text,
                tech_stack=tech_stack,
                exclude_client_id=client_id,
                n_results=3,
            )
            cross_filtered = [r for r in cross_results if r.get("similarity_score", 0.0) >= _MIN_SIMILARITY_THRESHOLD]
            results = results + cross_filtered

        # Cross-reference with N3 graph results for double-confirmation
        graph_incident_ids = {m.get("incident_id", "") for m in graph_matches}
        for result in results:
            inc_id = result.get("incident_id", "")
            if inc_id and inc_id in graph_incident_ids:
                result["double_confirmed"] = True
                result["context_weight"] = "maximum"
                logger.info(
                    "n4_semantic.double_confirmed",
                    incident_id=inc_id,
                    client_id=client_id,
                )
            else:
                result.setdefault("double_confirmed", False)
                result.setdefault("context_weight", "standard")

        no_precedent = len(results) == 0

        logger.info(
            "n4_semantic.complete",
            client_id=client_id,
            incident_id=incident_id,
            results=len(results),
            no_precedent=no_precedent,
            top_score=results[0]["similarity_score"] if results else 0.0,
        )

    except Exception as exc:
        logger.error(
            "n4_semantic.chromadb_error",
            client_id=client_id,
            incident_id=incident_id,
            error=str(exc),
        )
        results = []
        no_precedent = True

    return {
        "semantic_matches": results,
        "no_historical_precedent": no_precedent,
        "audit_trail": append_audit_entry(state, {
            "node": "n4_semantic",
            "actor": "ATLAS_AUTO",
            "action": "semantic_search_complete",
            "results_count": len(results),
            "no_historical_precedent": no_precedent,
            "top_similarity": results[0]["similarity_score"] if results else 0.0,
            "double_confirmed_count": sum(1 for r in results if r.get("double_confirmed")),
        }),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_query_text(evidence_packages: list[dict]) -> str:
    """
    Construct the ChromaDB search query from current incident evidence.
    Combines service names, anomaly types, error codes, and hypotheses.
    """
    parts: list[str] = []

    for pkg in evidence_packages:
        service = pkg.get("service_name", "")
        anomaly = pkg.get("anomaly_type", "")
        hypothesis = pkg.get("preliminary_hypothesis", "")
        log_samples = pkg.get("supporting_log_samples", [])

        if service:
            parts.append(service)
        if anomaly:
            parts.append(anomaly)
        if hypothesis:
            parts.append(hypothesis)
        # Include first log sample for keyword richness
        if log_samples:
            parts.append(log_samples[0])

    return " ".join(p for p in parts if p).strip() or "unknown anomaly"


def _extract_tech_stack(evidence_packages: list[dict]) -> list[str]:
    """
    Extract technology types from evidence packages for cross-client search scoping.
    Maps anomaly types to technology classes.
    """
    _ANOMALY_TO_TECH: dict[str, str] = {
        "CONNECTION_POOL_EXHAUSTED": "java-spring-boot",
        "DB_DEADLOCK":               "postgresql",
        "DB_PANIC":                  "postgresql",
        "JVM_MEMORY_CRITICAL":       "java-spring-boot",
        "JVM_STACK_OVERFLOW":        "java-spring-boot",
        "REDIS_OOM":                 "redis",
        "REDIS_COMMAND_REJECTED":    "redis",
        "NODE_UNHANDLED_REJECTION":  "nodejs",
        "NODE_DOWNSTREAM_REFUSED":   "nodejs",
    }

    tech_stack: list[str] = []
    for pkg in evidence_packages:
        anomaly = pkg.get("anomaly_type", "")
        tech = _ANOMALY_TO_TECH.get(anomaly)
        if tech and tech not in tech_stack:
            tech_stack.append(tech)

    return tech_stack
