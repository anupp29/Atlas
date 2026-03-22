"""
All Neo4j database interactions for ATLAS.
No other module connects to Neo4j directly.
Enforces client_id on every query. Caches results 60 seconds per (query_hash, client_id).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable

logger = structlog.get_logger(__name__)

_CACHE: dict[str, tuple[list[dict], float]] = {}
_CACHE_TTL_SECONDS = 60
_CACHE_LOCK = asyncio.Lock()


def _sanitize_neo4j_record(record: dict) -> dict:
    """
    Recursively convert Neo4j-specific types to JSON/msgpack-safe Python types.
    Neo4j DateTime → ISO-8601 string. Neo4j Date → ISO string. Lists/dicts recurse.
    """
    result: dict = {}
    for k, v in record.items():
        result[k] = _sanitize_value(v)
    return result


def _sanitize_value(v: Any) -> Any:
    """Convert a single Neo4j value to a JSON-safe Python type."""
    # Neo4j temporal types — check by class name to avoid hard import dependency
    type_name = type(v).__name__
    if type_name in ("DateTime", "Date", "Time", "LocalDateTime", "LocalTime"):
        return v.iso_format() if hasattr(v, "iso_format") else str(v)
    if type_name == "Duration":
        return str(v)
    if isinstance(v, dict):
        return {kk: _sanitize_value(vv) for kk, vv in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v

# Modules permitted to execute write transactions
_ALLOWED_WRITERS = frozenset({
    "backend.database.neo4j_client",   # seed operations
    "backend.learning.recalibration",
    "backend.orchestrator.nodes.n2_itsm",
    "backend.orchestrator.nodes.n3_graph",
    "backend.learning.trust_progression",
    "backend.main",                    # CMDB webhook updates
})


class Neo4jClient:
    """
    Async Neo4j client with connection pooling, query caching, and client_id enforcement.
    All queries are read transactions by default.
    Write transactions require explicit caller registration in _ALLOWED_WRITERS.
    """

    def __init__(self) -> None:
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")

        for var, val in (("NEO4J_URI", uri), ("NEO4J_USERNAME", username), ("NEO4J_PASSWORD", password)):
            if not val:
                raise EnvironmentError(f"Required environment variable '{var}' is not set.")

        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_pool_size=50,
            connection_timeout=10,
        )
        logger.info("neo4j_client.initialised", uri=uri)

    async def health_check(self) -> bool:
        """Verify the Neo4j connection is live. Used on startup."""
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                ok = record and record["ok"] == 1
                logger.info("neo4j_client.health_check", status="ok" if ok else "failed")
                return bool(ok)
        except (Neo4jError, ServiceUnavailable) as exc:
            logger.error("neo4j_client.health_check.failed", error=str(exc))
            return False

    async def execute_query(
        self,
        cypher: str,
        params: dict[str, Any],
        client_id: str,
        use_cache: bool = True,
        caller_module: str = "",
    ) -> list[dict] | None:
        """
        Execute a read Cypher query with client_id enforcement and result caching.

        Args:
            cypher: Cypher query string. Must contain $client_id parameter.
            params: Query parameters. Must include 'client_id'.
            client_id: The client this query is scoped to. Validated against params.
            use_cache: Whether to use the 60-second result cache.
            caller_module: __name__ of the calling module (for write permission checks).

        Returns:
            List of result dicts, or None on persistent failure.

        Raises:
            ValueError: If client_id is missing from params or mismatches.
        """
        if "client_id" not in params:
            raise ValueError(
                "client_id is required in query params. "
                "Every Neo4j query must be scoped to a client."
            )
        if params["client_id"] != client_id:
            raise ValueError(
                f"client_id mismatch: params has '{params['client_id']}' "
                f"but client_id argument is '{client_id}'. "
                "This is a critical multi-tenancy violation."
            )

        cache_key = self._cache_key(cypher, params, client_id)
        if use_cache:
            async with _CACHE_LOCK:
                cached = _CACHE.get(cache_key)
            if cached:
                results, ts = cached
                if time.monotonic() - ts < _CACHE_TTL_SECONDS:
                    logger.debug("neo4j_client.cache_hit", client_id=client_id, cache_key=cache_key[:16])
                    return results

        for attempt in range(1, 4):
            try:
                async with self._driver.session() as session:
                    result = await session.run(cypher, params)
                    records = await result.data()
                    rows = [_sanitize_neo4j_record(dict(r)) for r in records]

                if use_cache:
                    async with _CACHE_LOCK:
                        _CACHE[cache_key] = (rows, time.monotonic())

                logger.info(
                    "neo4j_client.query_executed",
                    client_id=client_id,
                    rows_returned=len(rows),
                    attempt=attempt,
                )
                return rows

            except ServiceUnavailable as exc:
                logger.warning(
                    "neo4j_client.service_unavailable",
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < 3:
                    await asyncio.sleep(2 ** attempt)
            except Neo4jError as exc:
                logger.error("neo4j_client.query_error", error=str(exc), cypher=cypher[:80])
                return None

        logger.error("neo4j_client.all_retries_exhausted", client_id=client_id)
        return None

    async def execute_write(
        self,
        cypher: str,
        params: dict[str, Any],
        client_id: str,
        caller_module: str,
    ) -> bool:
        """
        Execute a write Cypher transaction. Restricted to allowed modules.

        Args:
            cypher: Write Cypher query.
            params: Must include 'client_id'.
            client_id: Client scope.
            caller_module: __name__ of calling module. Must be in _ALLOWED_WRITERS.

        Returns:
            True on success, False on failure.

        Raises:
            PermissionError: If caller_module is not in _ALLOWED_WRITERS.
            ValueError: If client_id missing from params.
        """
        if caller_module not in _ALLOWED_WRITERS:
            raise PermissionError(
                f"Module '{caller_module}' is not permitted to execute Neo4j write transactions. "
                f"Allowed writers: {sorted(_ALLOWED_WRITERS)}"
            )
        if "client_id" not in params:
            raise ValueError("client_id is required in write query params.")
        if params["client_id"] != client_id:
            raise ValueError(
                f"client_id mismatch in write transaction: "
                f"params='{params['client_id']}' vs argument='{client_id}'"
            )

        for attempt in range(1, 4):
            try:
                async with self._driver.session() as session:
                    await session.run(cypher, params)
                logger.info(
                    "neo4j_client.write_executed",
                    client_id=client_id,
                    caller=caller_module,
                    attempt=attempt,
                )
                return True
            except ServiceUnavailable as exc:
                logger.warning("neo4j_client.write_unavailable", attempt=attempt, error=str(exc))
                if attempt < 3:
                    await asyncio.sleep(2 ** attempt)
            except Neo4jError as exc:
                logger.error("neo4j_client.write_error", error=str(exc))
                return False

        return False

    async def close(self) -> None:
        """Close the driver connection pool."""
        await self._driver.close()
        logger.info("neo4j_client.closed")

    @staticmethod
    def _cache_key(cypher: str, params: dict, client_id: str) -> str:
        safe_params = _sanitize_neo4j_record(params)
        payload = json.dumps({"cypher": cypher, "params": safe_params, "client_id": client_id}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()
