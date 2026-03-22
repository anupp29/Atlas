"""
Cascade correlation engine.
Sits above all four specialist agents.
90-second window per client. Structural confirmation via Neo4j DEPENDS_ON.
Temporal proximity alone is never sufficient to declare a cascade.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import structlog

from backend.agents.base_agent import EvidencePackage

if TYPE_CHECKING:
    from backend.database.neo4j_client import Neo4jClient

logger = structlog.get_logger(__name__)

# Correlation window: 90 seconds per client
_CORRELATION_WINDOW_SECONDS = 90

# Early warning: services between 1.5σ and 2.5σ
_EARLY_WARNING_LOWER_SIGMA = 1.5
_EARLY_WARNING_UPPER_SIGMA = 2.5

# Neo4j query: check if two services are connected within 3 hops
_STRUCTURAL_CHECK_CYPHER = """
MATCH (a:Service {name: $service_a, client_id: $client_id})
MATCH (b:Service {name: $service_b, client_id: $client_id})
RETURN EXISTS {
    MATCH (a)-[:DEPENDS_ON*1..3]-(b)
} AS connected
"""

# Neo4j query: check for recent change records on affected services
_DEPLOYMENT_CHECK_CYPHER = """
MATCH (d:Deployment {client_id: $client_id})
WHERE d.timestamp > datetime() - duration('P7D')
MATCH (d)-[:MODIFIED_CONFIG_OF|DEPLOYED_TO]->(s:Service)
WHERE s.name IN $affected_services AND s.client_id = $client_id
RETURN d.change_id AS change_id, d.change_description AS description,
       d.deployed_by AS deployed_by, d.timestamp AS timestamp
ORDER BY d.timestamp DESC
LIMIT 5
"""


@dataclass
class CorrelatedIncident:
    """
    Output of the correlation engine.
    Either a CASCADE_INCIDENT (multiple structurally connected agents)
    or an ISOLATED_ANOMALY (single agent or unconnected services).
    """
    correlation_type: str                    # "CASCADE_INCIDENT" | "ISOLATED_ANOMALY"
    client_id: str
    evidence_packages: list[EvidencePackage]
    deployment_correlated: bool = False
    deployment_change_ids: list[str] = field(default_factory=list)
    structural_check_skipped: bool = False   # True when Neo4j was unavailable
    early_warning_signals: list[dict] = field(default_factory=list)
    correlation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CorrelationEngine:
    """
    Correlates EvidencePackages from multiple agents within a 90-second window.
    Structural confirmation via Neo4j DEPENDS_ON is mandatory for CASCADE classification.
    Per-client isolation: a cascade for Client A never picks up signals from Client B.
    """

    def __init__(self, neo4j_client: "Neo4jClient") -> None:
        self._neo4j = neo4j_client
        # Per-client buffer: client_id → list of (EvidencePackage, arrival_time)
        self._window: dict[str, list[tuple[EvidencePackage, float]]] = {}
        self._window_lock: dict[str, asyncio.Lock] = {}
        # Single lock to guard creation of per-client locks (prevents double-init race)
        self._lock_creation_lock = asyncio.Lock()
        # Agent sigma cache: (client_id, service_name) → most recent sigma value
        # Updated by agents via report_service_sigma() so early warning scan has real data
        self._agent_sigma_cache: dict[tuple[str, str], float] = {}

    async def _get_lock(self, client_id: str) -> asyncio.Lock:
        """Return the per-client asyncio.Lock, creating it atomically if needed."""
        if client_id not in self._window_lock:
            async with self._lock_creation_lock:
                # Double-checked: another coroutine may have created it while we waited
                if client_id not in self._window_lock:
                    self._window_lock[client_id] = asyncio.Lock()
        return self._window_lock[client_id]

    async def ingest_evidence(self, pkg: EvidencePackage) -> CorrelatedIncident | None:
        """
        Accept an EvidencePackage from a specialist agent.
        Returns a CorrelatedIncident if the window has been processed, None otherwise.

        The window is processed when:
        - A second package arrives within 90 seconds (potential cascade)
        - 90 seconds have elapsed since the first package (window expires)

        Args:
            pkg: EvidencePackage from any specialist agent.

        Returns:
            CorrelatedIncident or None (if window is still accumulating).
        """
        if not pkg.client_id:
            raise ValueError("EvidencePackage has no client_id — cannot correlate.")

        client_id = pkg.client_id
        async with await self._get_lock(client_id):
            now = time.monotonic()

            if client_id not in self._window:
                self._window[client_id] = []

            # Prune expired entries from the window
            self._window[client_id] = [
                (p, t) for p, t in self._window[client_id]
                if now - t <= _CORRELATION_WINDOW_SECONDS
            ]

            # Add new package
            self._window[client_id].append((pkg, now))

            packages_in_window = [p for p, _ in self._window[client_id]]

            if len(packages_in_window) == 1:
                # First package — start the window, return None
                logger.info(
                    "correlation_engine.window_started",
                    client_id=client_id,
                    service=pkg.service_name,
                    anomaly_type=pkg.anomaly_type,
                )
                return None

            # Multiple packages in window — check for cascade
            return await self._process_window(client_id, packages_in_window)

    def report_service_sigma(self, client_id: str, service_name: str, sigma: float) -> None:
        """
        Called by specialist agents on every metric update to keep the sigma cache fresh.
        The early warning scan uses this to populate real deviation values for adjacent services.

        Args:
            client_id:    Client scope — mandatory.
            service_name: The service whose sigma is being reported.
            sigma:        Current deviation in standard deviations from baseline.
        """
        if not client_id or not service_name:
            return
        self._agent_sigma_cache[(client_id, service_name)] = sigma

    async def flush_window(self, client_id: str) -> CorrelatedIncident | None:
        """
        Force-process the current window for a client.
        Called when the 90-second window expires without a second package arriving.

        Returns:
            CorrelatedIncident with ISOLATED_ANOMALY for each package, or None if empty.
        """
        async with await self._get_lock(client_id):
            if not self._window.get(client_id):
                return None

            packages = [p for p, _ in self._window[client_id]]
            self._window[client_id] = []

            if not packages:
                return None

            if len(packages) == 1:
                return CorrelatedIncident(
                    correlation_type="ISOLATED_ANOMALY",
                    client_id=client_id,
                    evidence_packages=packages,
                )

            return await self._process_window(client_id, packages)

    async def _process_window(
        self,
        client_id: str,
        packages: list[EvidencePackage],
    ) -> CorrelatedIncident:
        """
        Determine if packages represent a CASCADE or multiple ISOLATED anomalies.
        Structural check via Neo4j is mandatory — temporal proximity alone is insufficient.
        """
        if len(packages) == 1:
            return CorrelatedIncident(
                correlation_type="ISOLATED_ANOMALY",
                client_id=client_id,
                evidence_packages=packages,
            )

        # Get unique affected services
        affected_services = list({p.service_name for p in packages})

        # Structural check: are any two affected services connected via DEPENDS_ON?
        structurally_connected, structural_check_skipped = await self._check_structural_connection(
            client_id, affected_services
        )

        if not structurally_connected:
            # Temporal coincidence, not causal — produce separate ISOLATED_ANOMALY packages
            logger.info(
                "correlation_engine.isolated_anomalies",
                client_id=client_id,
                services=affected_services,
                reason="no_structural_connection",
            )
            # Clear the window
            self._window[client_id] = []
            return CorrelatedIncident(
                correlation_type="ISOLATED_ANOMALY",
                client_id=client_id,
                evidence_packages=packages,
                structural_check_skipped=structural_check_skipped,
            )

        # Structurally connected — classify as CASCADE
        logger.info(
            "correlation_engine.cascade_detected",
            client_id=client_id,
            services=affected_services,
            package_count=len(packages),
        )

        # Check for deployment correlation
        deployment_correlated, change_ids = await self._check_deployment_correlation(
            client_id, affected_services
        )

        # Run early warning scan on blast radius (async, does not delay primary incident)
        early_warnings = await self._scan_early_warnings(client_id, affected_services)

        # Clear the window
        self._window[client_id] = []

        return CorrelatedIncident(
            correlation_type="CASCADE_INCIDENT",
            client_id=client_id,
            evidence_packages=packages,
            deployment_correlated=deployment_correlated,
            deployment_change_ids=change_ids,
            structural_check_skipped=structural_check_skipped,
            early_warning_signals=early_warnings,
        )

    async def _check_structural_connection(
        self,
        client_id: str,
        affected_services: list[str],
    ) -> tuple[bool, bool]:
        """
        Check if any two affected services are connected via DEPENDS_ON within 3 hops.

        Returns:
            (is_connected, structural_check_skipped)
        """
        if len(affected_services) < 2:
            return False, False

        try:
            for i, service_a in enumerate(affected_services):
                for service_b in affected_services[i + 1:]:
                    results = await self._neo4j.execute_query(
                        cypher=_STRUCTURAL_CHECK_CYPHER,
                        params={
                            "service_a": service_a,
                            "service_b": service_b,
                            "client_id": client_id,
                        },
                        client_id=client_id,
                    )
                    if results and results[0].get("connected"):
                        logger.info(
                            "correlation_engine.structural_connection_confirmed",
                            client_id=client_id,
                            service_a=service_a,
                            service_b=service_b,
                        )
                        return True, False

            return False, False

        except Exception as exc:
            logger.warning(
                "correlation_engine.structural_check_failed",
                client_id=client_id,
                error=str(exc),
            )
            # Neo4j unavailable — classify as ISOLATED with flag, never block pipeline
            return False, True

    async def _check_deployment_correlation(
        self,
        client_id: str,
        affected_services: list[str],
    ) -> tuple[bool, list[str]]:
        """
        Check if any recent change record touches the affected services.

        Returns:
            (deployment_correlated, list_of_change_ids)
        """
        try:
            results = await self._neo4j.execute_query(
                cypher=_DEPLOYMENT_CHECK_CYPHER,
                params={
                    "client_id": client_id,
                    "affected_services": affected_services,
                },
                client_id=client_id,
            )
            if results:
                change_ids = [r.get("change_id", "") for r in results if r.get("change_id")]
                logger.info(
                    "correlation_engine.deployment_correlated",
                    client_id=client_id,
                    change_ids=change_ids,
                )
                return True, change_ids
            return False, []

        except Exception as exc:
            logger.warning(
                "correlation_engine.deployment_check_failed",
                client_id=client_id,
                error=str(exc),
            )
            return False, []

    async def _scan_early_warnings(
        self,
        client_id: str,
        affected_services: list[str],
    ) -> list[dict]:
        """
        Scan blast-radius-adjacent services for early deviation (1.5σ–2.5σ).
        Runs after CASCADE classification — never delays the primary incident.
        Returns list of EarlyWarning signal dicts.

        sigma values are populated from the agent baseline data held in this
        engine's _agent_sigma_cache, which agents update via report_service_sigma().
        Services with no cached sigma are returned with status 'monitoring' and
        sigma=None — the frontend treats this as "watching, no data yet".
        """
        _BLAST_RADIUS_CYPHER = """
        MATCH (s:Service {client_id: $client_id})
        WHERE s.name IN $affected_services
        MATCH (s)-[:DEPENDS_ON*1..2]-(adjacent:Service {client_id: $client_id})
        WHERE NOT adjacent.name IN $affected_services
        RETURN DISTINCT adjacent.name AS service_name, adjacent.criticality AS criticality
        """
        try:
            results = await self._neo4j.execute_query(
                cypher=_BLAST_RADIUS_CYPHER,
                params={
                    "client_id": client_id,
                    "affected_services": affected_services,
                },
                client_id=client_id,
            )
            if not results:
                return []

            early_warnings = []
            for row in results:
                svc = row.get("service_name")
                # Look up the most recent sigma reported by the agent for this service
                cached_sigma: float | None = self._agent_sigma_cache.get(
                    (client_id, svc)
                )
                # Only flag as early warning if sigma is in the 1.5–2.5 band
                if cached_sigma is not None:
                    if not (_EARLY_WARNING_LOWER_SIGMA <= cached_sigma <= _EARLY_WARNING_UPPER_SIGMA):
                        # Outside the early-warning band — skip
                        continue
                    status = "early_warning"
                else:
                    # No sigma data yet — include as monitoring candidate
                    status = "monitoring"

                early_warnings.append({
                    "service_name": svc,
                    "criticality": row.get("criticality"),
                    "status": status,
                    "sigma": cached_sigma,
                    "client_id": client_id,
                })

            logger.info(
                "correlation_engine.early_warning_scan",
                client_id=client_id,
                adjacent_services=len(results),
                flagged=len([e for e in early_warnings if e["status"] == "early_warning"]),
            )
            return early_warnings

        except Exception as exc:
            logger.warning(
                "correlation_engine.early_warning_scan_failed",
                client_id=client_id,
                error=str(exc),
            )
            return []
