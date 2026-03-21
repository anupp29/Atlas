"""
Attaches CMDB context to every normalised event before agents see it.
Agents never perform their own CMDB lookups — all context is pre-attached here.
60-second TTL cache per client. Graceful degradation when Neo4j is unavailable.
"""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from backend.database.neo4j_client import Neo4jClient

logger = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 60

# Cypher query to look up a service's CMDB context
_CMDB_LOOKUP_CYPHER = """
MATCH (s:Service {name: $service_name, client_id: $client_id})
OPTIONAL MATCH (s)-[:COVERED_BY]->(sla:SLA)
OPTIONAL MATCH (s)-[:OWNED_BY]->(team:Team)
OPTIONAL MATCH (d:Deployment {client_id: $client_id})-[:MODIFIED_CONFIG_OF]->(s)
WHERE d.timestamp > datetime() - duration('P7D')
RETURN
    s.tech_type AS ci_class,
    s.version AS ci_version,
    s.criticality AS criticality_tier,
    sla.breach_threshold_minutes AS sla_breach_threshold_minutes,
    team.name AS owner_team,
    collect(d.change_id) AS open_change_records
"""


class CmdbEnricher:
    """
    Enriches normalised events with CMDB context from Neo4j.
    Cache is per client_id — never serves one client's data to another.
    """

    def __init__(self, neo4j_client: "Neo4jClient") -> None:
        self._neo4j = neo4j_client
        # Cache: (client_id, service_name) → (enrichment_dict, timestamp)
        self._cache: dict[tuple[str, str], tuple[dict[str, Any], float]] = {}

    async def enrich(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Attach CMDB context to a normalised event.

        Args:
            event: Normalised event dict. Must have 'client_id' and 'source_system'.

        Returns:
            Event dict with CMDB fields populated.
            If Neo4j is unavailable: returns event with cmdb_enrichment_status='not_found'
            and enriched_from_cache=False (or True if cache hit).
        """
        client_id: str = event.get("client_id", "")
        service_name: str = event.get("source_system", "")

        if not client_id:
            logger.error("cmdb_enricher.missing_client_id", event_id=event.get("atlas_event_id"))
            return {**event, "cmdb_enrichment_status": "error_missing_client_id"}

        # Validate client_id matches event — critical multi-tenancy check
        if event.get("client_id") != client_id:
            logger.error(
                "cmdb_enricher.client_id_mismatch",
                event_client=event.get("client_id"),
                enricher_client=client_id,
            )
            return {**event, "cmdb_enrichment_status": "error_client_id_mismatch"}

        cache_key = (client_id, service_name)
        now = time.monotonic()

        # Check cache first
        cached = self._cache.get(cache_key)
        if cached:
            enrichment, cached_at = cached
            if now - cached_at < _CACHE_TTL_SECONDS:
                logger.debug(
                    "cmdb_enricher.cache_hit",
                    client_id=client_id,
                    service=service_name,
                )
                return {
                    **event,
                    **enrichment,
                    "cmdb_enrichment_status": "cache_hit",
                    "enriched_from_cache": True,
                }

        # Query Neo4j
        try:
            results = await self._neo4j.execute_query(
                cypher=_CMDB_LOOKUP_CYPHER,
                params={"service_name": service_name, "client_id": client_id},
                client_id=client_id,
                use_cache=False,  # We manage our own cache here
            )

            if results:
                row = results[0]
                enrichment = {
                    "ci_class": row.get("ci_class"),
                    "ci_version": row.get("ci_version"),
                    "business_service_name": service_name,
                    "criticality_tier": row.get("criticality_tier"),
                    "open_change_records": row.get("open_change_records", []),
                    "sla_breach_threshold_minutes": row.get("sla_breach_threshold_minutes"),
                    "owner_team": row.get("owner_team"),
                    "cmdb_enrichment_status": "enriched",
                    "enriched_from_cache": False,
                }
                # Store in cache
                self._cache[cache_key] = (enrichment, now)
                logger.info(
                    "cmdb_enricher.enriched",
                    client_id=client_id,
                    service=service_name,
                    criticality=enrichment.get("criticality_tier"),
                )
                return {**event, **enrichment}

            else:
                # Service not found in graph
                enrichment = {
                    "ci_class": None,
                    "ci_version": None,
                    "business_service_name": service_name,
                    "criticality_tier": None,
                    "open_change_records": [],
                    "sla_breach_threshold_minutes": None,
                    "owner_team": None,
                    "cmdb_enrichment_status": "not_found",
                    "enriched_from_cache": False,
                }
                logger.info(
                    "cmdb_enricher.service_not_found",
                    client_id=client_id,
                    service=service_name,
                )
                return {**event, **enrichment}

        except Exception as exc:
            logger.warning(
                "cmdb_enricher.neo4j_unavailable",
                client_id=client_id,
                service=service_name,
                error=str(exc),
            )
            # Serve from cache if available, even if stale
            if cached:
                enrichment, _ = cached
                logger.info(
                    "cmdb_enricher.serving_stale_cache",
                    client_id=client_id,
                    service=service_name,
                )
                return {
                    **event,
                    **enrichment,
                    "cmdb_enrichment_status": "cache_hit",
                    "enriched_from_cache": True,
                }

            # No cache available — continue without enrichment, never block pipeline
            return {
                **event,
                "ci_class": None,
                "ci_version": None,
                "business_service_name": service_name,
                "criticality_tier": None,
                "open_change_records": [],
                "sla_breach_threshold_minutes": None,
                "owner_team": None,
                "cmdb_enrichment_status": "not_found",
                "enriched_from_cache": False,
            }

    def invalidate_cache(self, client_id: str, service_name: str | None = None) -> None:
        """
        Invalidate cache entries for a client (or a specific service).
        Called when a CMDB webhook update arrives.
        """
        if service_name:
            self._cache.pop((client_id, service_name), None)
        else:
            keys_to_remove = [k for k in self._cache if k[0] == client_id]
            for key in keys_to_remove:
                del self._cache[key]
        logger.info(
            "cmdb_enricher.cache_invalidated",
            client_id=client_id,
            service=service_name or "all",
        )
