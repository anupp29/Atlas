"""
Recalibration engine for ATLAS.
Recalculates Factor 1 (Historical Accuracy Rate) in the confidence engine
after every resolved incident. Ensures the next similar incident is scored
with up-to-date accuracy data.

The in-memory accuracy cache is what n6_confidence.py reads at decision time.
This module owns the cache — it is the only writer.

Recalibration runs asynchronously after resolution — never blocks resolution
confirmation. A read-write lock prevents stale reads during cache updates.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.database.audit_db import write_audit_record
from backend.learning.decision_history import (
    get_accuracy_rate,
    get_all_patterns_for_client,
    get_incident_count_for_client,
)

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# In-memory accuracy cache
# Key: (client_id, anomaly_type, service_class, action_id)
# Value: {"accuracy": float, "record_count": int, "last_updated": datetime}
# ─────────────────────────────────────────────────────────────────────────────

_accuracy_cache: dict[tuple[str, str, str, str], dict[str, Any]] = {}
_cache_lock = asyncio.Lock()

# Minimum records before cold-start veto is lifted
_COLD_START_THRESHOLD = 5


def get_cached_accuracy(
    client_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> tuple[float, int]:
    """
    Read the cached accuracy rate for a pattern triple.
    Called by n6_confidence.py at decision time — must be fast, no I/O.

    Returns:
        Tuple of (accuracy_rate, record_count).
        Returns (0.50, 0) if no cache entry exists — neutral prior.
    """
    key = (client_id, anomaly_type, service_class, action_id)
    entry = _accuracy_cache.get(key)
    if entry is None:
        return 0.50, 0
    return entry["accuracy"], entry["record_count"]


async def recalibrate_after_resolution(
    client_id: str,
    incident_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> None:
    """
    Recalculate and cache the accuracy rate for a pattern triple after resolution.
    Writes a recalibration event to the audit trail.

    This is the primary post-resolution hook. Called by the learning engine
    after every incident resolution. Runs asynchronously — never blocks the
    resolution confirmation path.

    Args:
        client_id:    Client scope — mandatory.
        incident_id:  The resolved incident ID (for audit trail correlation).
        anomaly_type: e.g. 'CONNECTION_POOL_EXHAUSTED'
        service_class: e.g. 'java-spring-boot'
        action_id:    Playbook ID e.g. 'connection-pool-recovery-v2'
    """
    if not client_id:
        raise ValueError("client_id is required for recalibrate_after_resolution.")

    key = (client_id, anomaly_type, service_class, action_id)

    # Read previous value before acquiring write lock
    previous_entry = _accuracy_cache.get(key)
    previous_accuracy = previous_entry["accuracy"] if previous_entry else 0.50
    previous_count = previous_entry["record_count"] if previous_entry else 0

    # Query decision history — I/O outside the lock
    new_accuracy, new_count = get_accuracy_rate(client_id, anomaly_type, service_class, action_id)

    async with _cache_lock:
        _accuracy_cache[key] = {
            "accuracy": new_accuracy,
            "record_count": new_count,
            "last_updated": datetime.now(timezone.utc),
        }

    cold_start_lifted = (
        previous_count < _COLD_START_THRESHOLD
        and new_count >= _COLD_START_THRESHOLD
    )

    logger.info(
        "recalibration.updated",
        client_id=client_id,
        incident_id=incident_id,
        anomaly_type=anomaly_type,
        service_class=service_class,
        action_id=action_id,
        previous_accuracy=round(previous_accuracy, 4),
        new_accuracy=round(new_accuracy, 4),
        record_count=new_count,
        cold_start_lifted=cold_start_lifted,
    )

    # Write recalibration event to audit trail
    description = (
        f"Factor 1 recalibrated for pattern '{anomaly_type}/{service_class}/{action_id}' "
        f"on client '{client_id}': "
        f"{previous_accuracy * 100:.1f}% → {new_accuracy * 100:.1f}% "
        f"based on {new_count} records."
    )
    if cold_start_lifted:
        description += (
            f" Cold-start veto automatically lifted — record count reached "
            f"{_COLD_START_THRESHOLD}."
        )

    write_audit_record({
        "client_id": client_id,
        "incident_id": incident_id,
        "action_type": "classification",
        "actor": "ATLAS_AUTO",
        "action_description": description,
        "confidence_score_at_time": new_accuracy,
        "outcome": "recalibration_complete",
        "servicenow_ticket_id": "",
        "rollback_available": False,
        "compliance_frameworks_applied": [],
        "reasoning_summary": (
            f"Recalibration: {anomaly_type}/{service_class}/{action_id} "
            f"accuracy updated from {previous_accuracy:.4f} to {new_accuracy:.4f}."
        ),
    })


async def force_recalculate_all(client_ids: list[str]) -> dict[str, int]:
    """
    Rebuild the entire accuracy cache from decision history.
    Called on system startup to ensure the cache reflects the full history.

    Args:
        client_ids: List of all registered client IDs to recalculate for.

    Returns:
        Dict mapping client_id → number of patterns recalculated.
    """
    results: dict[str, int] = {}

    for client_id in client_ids:
        if not client_id:
            continue

        patterns = get_all_patterns_for_client(client_id)
        count = 0

        for pattern in patterns:
            anomaly_type = pattern["anomaly_type"]
            service_class = pattern["service_class"]
            action_id = pattern["recommended_action_id"]

            accuracy, record_count = get_accuracy_rate(
                client_id, anomaly_type, service_class, action_id
            )
            key = (client_id, anomaly_type, service_class, action_id)

            async with _cache_lock:
                _accuracy_cache[key] = {
                    "accuracy": accuracy,
                    "record_count": record_count,
                    "last_updated": datetime.now(timezone.utc),
                }
            count += 1

        results[client_id] = count
        logger.info(
            "recalibration.startup_rebuild_complete",
            client_id=client_id,
            patterns_recalculated=count,
        )

    return results


def get_cache_snapshot() -> dict[str, Any]:
    """
    Return a read-only snapshot of the current accuracy cache.
    Used for diagnostics and the frontend trust progress display.

    Returns:
        Dict with cache entries serialised for JSON output.
    """
    snapshot: dict[str, Any] = {}
    for (client_id, anomaly_type, service_class, action_id), entry in _accuracy_cache.items():
        key_str = f"{client_id}|{anomaly_type}|{service_class}|{action_id}"
        snapshot[key_str] = {
            "accuracy": entry["accuracy"],
            "record_count": entry["record_count"],
            "last_updated": entry["last_updated"].isoformat(),
            "cold_start_active": entry["record_count"] < _COLD_START_THRESHOLD,
        }
    return snapshot
