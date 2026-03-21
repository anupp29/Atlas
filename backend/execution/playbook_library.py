"""
Playbook library — the registry of every action ATLAS is permitted to take.
This is the absolute boundary of autonomous action. Nothing outside this library
can be executed by the execution engine, ever.

All playbooks are named, versioned, and pre-approved. No ad-hoc commands.
No LLM-generated scripts. The library is read-only at runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class PlaybookMetadata:
    """
    Immutable metadata record for a registered playbook.
    Frozen — no field may be changed after construction.
    """

    playbook_id: str
    name: str
    description: str
    action_class: int                        # 1, 2, or 3
    auto_execute_eligible: bool              # Class 3 is always False — enforced below
    estimated_resolution_minutes: int
    target_technology: str                   # e.g. "java-spring-boot", "redis"
    anomaly_types_addressed: list[str]       # ATLAS taxonomy codes this playbook resolves
    pre_validation_checks: list[str]         # Human-readable list of checks performed
    success_metrics: list[str]               # What ATLAS monitors to confirm resolution
    rollback_playbook_id: str | None         # Must point to a valid playbook or None
    parameters: dict[str, Any]              # Default parameter values
    version: str                             # Semantic version string


# ─────────────────────────────────────────────────────────────────────────────
# MVP Playbook Registry
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, PlaybookMetadata] = {}


def _register(pb: PlaybookMetadata) -> None:
    """Add a playbook to the registry. Called at module load time only."""
    if pb.action_class == 3 and pb.auto_execute_eligible:
        raise ValueError(
            f"Playbook '{pb.playbook_id}' is Class 3 but marked auto_execute_eligible=True. "
            "Class 3 actions never auto-execute. This is a hard constant."
        )
    _REGISTRY[pb.playbook_id] = pb


# ── connection-pool-recovery-v2 ───────────────────────────────────────────────
# Resolves HikariCP connection pool exhaustion on Java Spring Boot services.
# Real-world basis: HikariCP supports runtime pool resize via JMX MBean
# (setMaximumPoolSize) and via Spring Boot Actuator POST /actuator/env +
# POST /actuator/refresh. The mock PaymentAPI exposes a custom management
# endpoint that wraps this pattern.
# Reference: https://github.com/brettwooldridge/HikariCP — HikariConfigMXBean
_register(PlaybookMetadata(
    playbook_id="connection-pool-recovery-v2",
    name="HikariCP Connection Pool Recovery v2",
    description=(
        "Restores HikariCP connection pool to a safe operating size on a Java Spring Boot "
        "service experiencing CONNECTION_POOL_EXHAUSTED. Performs pre-validation to confirm "
        "the issue is still active, patches the pool configuration via the Spring Boot "
        "Actuator management endpoint (POST /actuator/env + POST /actuator/refresh), then "
        "monitors connection count for recovery. Auto-rolls back if recovery is not confirmed "
        "within 10 minutes."
    ),
    action_class=1,
    auto_execute_eligible=True,
    estimated_resolution_minutes=5,
    target_technology="java-spring-boot",
    anomaly_types_addressed=["CONNECTION_POOL_EXHAUSTED"],
    pre_validation_checks=[
        "Target service health endpoint reachable (GET /actuator/health → 200 or 503)",
        "Current active connection count above alert threshold (>85% of max_connections)",
        "No ATLAS action taken on this service in the last 10 minutes",
        "Actuator management endpoint accessible (GET /actuator → 200)",
    ],
    success_metrics=[
        "Active connection count drops below 70% of max_connections",
        "Two consecutive readings below threshold (60-second interval)",
        "HTTP 503 error rate returns to baseline",
    ],
    rollback_playbook_id="connection-pool-recovery-v2-rollback",
    parameters={
        "target_pool_size": 150,             # Restore to this value
        "alert_threshold_pct": 0.85,         # Pre-validation: must be above this
        "success_threshold_pct": 0.70,       # Success: must be below this
        "success_consecutive_readings": 2,
        "poll_interval_seconds": 30,
        "max_validation_minutes": 10,
        "max_total_runtime_minutes": 15,
        "http_timeout_seconds": 10,
    },
    version="2.0.0",
))

# ── connection-pool-recovery-v2-rollback ─────────────────────────────────────
# Rollback: restore previous maxPoolSize value. Triggered automatically if
# success validation times out.
_register(PlaybookMetadata(
    playbook_id="connection-pool-recovery-v2-rollback",
    name="HikariCP Connection Pool Recovery v2 — Rollback",
    description=(
        "Restores HikariCP maxPoolSize to its pre-action value after a failed "
        "connection-pool-recovery-v2 execution. Triggers re-escalation to L2/L3."
    ),
    action_class=1,
    auto_execute_eligible=True,
    estimated_resolution_minutes=2,
    target_technology="java-spring-boot",
    anomaly_types_addressed=["CONNECTION_POOL_EXHAUSTED"],
    pre_validation_checks=[
        "Target service health endpoint reachable",
    ],
    success_metrics=[
        "Pool size restored to previous value (confirmed via GET /actuator/env)",
    ],
    rollback_playbook_id=None,
    parameters={
        "http_timeout_seconds": 10,
    },
    version="2.0.0",
))

# ── redis-memory-policy-rollback-v1 ──────────────────────────────────────────
# Resolves Redis OOM caused by maxmemory-policy=noeviction misconfiguration.
# Real-world basis: Redis CONFIG SET maxmemory-policy is a live runtime command
# that takes effect immediately without restart. Verified via CONFIG GET.
# Reference: https://redis.io/docs/manual/config/ — CONFIG SET command
_register(PlaybookMetadata(
    playbook_id="redis-memory-policy-rollback-v1",
    name="Redis Memory Policy Rollback v1",
    description=(
        "Rolls back Redis maxmemory-policy from noeviction to allkeys-lru on a Redis "
        "instance experiencing REDIS_OOM. Pre-validates that noeviction is the active "
        "policy and memory usage is above threshold. Executes CONFIG SET maxmemory-policy "
        "allkeys-lru and verifies the change took effect. Monitors memory usage for "
        "recovery. Auto-rolls back to noeviction (preserving fault state for L2 "
        "investigation) if recovery is not confirmed within 10 minutes."
    ),
    action_class=1,
    auto_execute_eligible=True,
    estimated_resolution_minutes=5,
    target_technology="redis",
    anomaly_types_addressed=["REDIS_OOM", "REDIS_COMMAND_REJECTED"],
    pre_validation_checks=[
        "Redis instance reachable (PING → PONG)",
        "Current maxmemory-policy is noeviction (CONFIG GET maxmemory-policy)",
        "Memory usage above 85% of maxmemory (INFO memory → used_memory / maxmemory)",
    ],
    success_metrics=[
        "Memory usage drops below 75% of maxmemory",
        "Two consecutive readings below threshold (30-second interval)",
        "OOM command rejections cease (rejected_commands counter stable)",
    ],
    rollback_playbook_id="redis-memory-policy-rollback-v1-rollback",
    parameters={
        "target_policy": "allkeys-lru",      # The correct production policy
        "fault_policy": "noeviction",        # The policy that caused the OOM
        "alert_threshold_pct": 0.85,         # Pre-validation: must be above this
        "success_threshold_pct": 0.75,       # Success: must be below this
        "success_consecutive_readings": 2,
        "poll_interval_seconds": 30,
        "max_validation_minutes": 10,
        "http_timeout_seconds": 10,
    },
    version="1.0.0",
))

# ── redis-memory-policy-rollback-v1-rollback ─────────────────────────────────
# Rollback: restore noeviction to preserve fault state for L2 investigation.
_register(PlaybookMetadata(
    playbook_id="redis-memory-policy-rollback-v1-rollback",
    name="Redis Memory Policy Rollback v1 — Rollback",
    description=(
        "Restores Redis maxmemory-policy to noeviction after a failed "
        "redis-memory-policy-rollback-v1 execution. Preserves the fault state "
        "for L2 investigation. Triggers re-escalation."
    ),
    action_class=1,
    auto_execute_eligible=True,
    estimated_resolution_minutes=1,
    target_technology="redis",
    anomaly_types_addressed=["REDIS_OOM"],
    pre_validation_checks=[
        "Redis instance reachable (PING → PONG)",
    ],
    success_metrics=[
        "maxmemory-policy restored to noeviction (confirmed via CONFIG GET)",
    ],
    rollback_playbook_id=None,
    parameters={
        "http_timeout_seconds": 10,
    },
    version="1.0.0",
))


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_playbook(playbook_id: str) -> PlaybookMetadata | None:
    """
    Return the metadata for a playbook by ID.

    Returns:
        PlaybookMetadata if found, None if not found.
        Never raises — callers must handle None.
    """
    pb = _REGISTRY.get(playbook_id)
    if pb is None:
        logger.warning(
            "playbook_library.not_found",
            playbook_id=playbook_id,
            available=list(_REGISTRY.keys()),
        )
    return pb


def validate_action_id(action_id: str) -> bool:
    """
    Return True if the action_id exists in the library.
    Used by n5_reasoning.py to validate LLM output before accepting it.
    """
    return action_id in _REGISTRY


def list_playbooks() -> list[PlaybookMetadata]:
    """Return all registered playbooks. Read-only view."""
    return list(_REGISTRY.values())


def get_playbooks_for_anomaly(anomaly_type: str) -> list[PlaybookMetadata]:
    """
    Return all playbooks that address a given anomaly type.
    Used for semantic search fallback when LLM returns an unknown action_id.
    """
    return [
        pb for pb in _REGISTRY.values()
        if anomaly_type in pb.anomaly_types_addressed
    ]


def semantic_search(query: str, top_k: int = 3) -> list[PlaybookMetadata]:
    """
    Return the top-k playbooks most relevant to a free-text query.
    Used when an L2 engineer rejects a recommendation — the rejection reason
    text is searched here to find an alternative playbook.

    Implementation: keyword overlap scoring (no external embedding dependency).
    Sufficient for the MVP playbook library size.

    Args:
        query: Free-text query (e.g. rejection reason from L2 engineer).
        top_k: Maximum number of results to return.

    Returns:
        List of PlaybookMetadata sorted by relevance score, highest first.
    """
    query_tokens = set(query.lower().split())
    scored: list[tuple[float, PlaybookMetadata]] = []

    for pb in _REGISTRY.values():
        # Build a searchable text blob from all descriptive fields
        text = " ".join([
            pb.playbook_id,
            pb.name,
            pb.description,
            pb.target_technology,
            " ".join(pb.anomaly_types_addressed),
            " ".join(pb.pre_validation_checks),
        ]).lower()
        text_tokens = set(text.split())
        overlap = len(query_tokens & text_tokens)
        if overlap > 0:
            score = overlap / max(len(query_tokens), 1)
            scored.append((score, pb))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [pb for _, pb in scored[:top_k]]

    logger.debug(
        "playbook_library.semantic_search",
        query_preview=query[:80],
        results=[pb.playbook_id for pb in results],
    )
    return results


def _validate_registry_integrity() -> None:
    """
    Validate the registry on startup:
    - Every rollback_playbook_id must point to a real entry.
    - No Class 3 playbook may be auto_execute_eligible.
    Called once at module load time.
    """
    for pb in _REGISTRY.values():
        if pb.rollback_playbook_id is not None:
            if pb.rollback_playbook_id not in _REGISTRY:
                raise RuntimeError(
                    f"Playbook '{pb.playbook_id}' references rollback playbook "
                    f"'{pb.rollback_playbook_id}' which does not exist in the registry. "
                    "Fix the registry before starting ATLAS."
                )
        if pb.action_class == 3 and pb.auto_execute_eligible:
            raise RuntimeError(
                f"CRITICAL: Playbook '{pb.playbook_id}' is Class 3 and auto_execute_eligible=True. "
                "This must never happen. Fix immediately."
            )

    logger.info(
        "playbook_library.registry_validated",
        playbook_count=len(_REGISTRY),
        playbook_ids=list(_REGISTRY.keys()),
    )


# Validate on import — fail loudly at startup if registry is inconsistent
_validate_registry_integrity()
