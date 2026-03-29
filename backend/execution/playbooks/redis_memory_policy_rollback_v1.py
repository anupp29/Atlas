"""
Playbook: redis-memory-policy-rollback-v1
Target:   Redis instances experiencing OOM due to maxmemory-policy=noeviction.

Five mandatory steps (per ATLAS execution engine contract):
  1. Pre-execution validation
  2. Action execution
  3. Success validation
  4. Auto-rollback (if success validation times out)
  5. Immutable audit record (written regardless of outcome)

Real-world basis:
  Redis CONFIG SET maxmemory-policy takes effect immediately at runtime without
  restart. The noeviction policy causes OOM errors when memory is full because
  Redis refuses to evict any keys. Switching to allkeys-lru allows Redis to
  evict least-recently-used keys, freeing memory and restoring command acceptance.

  Verification: CONFIG GET maxmemory-policy confirms the change.
  Memory check: INFO memory → used_memory / maxmemory.

  References:
    - Redis CONFIG SET: redis.io/docs/manual/config/
    - Redis memory policies: redis.io/docs/manual/eviction/
    - Redis INFO memory: redis.io/commands/info/

Hard guards (non-negotiable):
  - NEVER execute FLUSHALL or FLUSHDB — not in this playbook at any action class.
  - If policy is already allkeys-lru on entry: halt, report hypothesis wrong.
  - Redis credentials from environment variables only — never hardcoded.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.database.audit_db import write_audit_record

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants — all overridable via playbook parameters
# ─────────────────────────────────────────────────────────────────────────────

_POLL_INTERVAL: int = 30
_MAX_VALIDATION_MINUTES: int = 10
_ALERT_THRESHOLD_PCT: float = 0.85
_SUCCESS_THRESHOLD_PCT: float = 0.75
_SUCCESS_CONSECUTIVE: int = 2
_FAULT_POLICY: str = "noeviction"
_TARGET_POLICY: str = "allkeys-lru"
_REDIS_CONNECT_TIMEOUT: float = 10.0
_REDIS_SOCKET_TIMEOUT: float = 10.0


@dataclass
class PlaybookResult:
    """Outcome of a playbook execution."""

    success: bool
    outcome: str          # "success" | "rollback_executed" | "pre_validation_failed" | "error"
    detail: str
    audit_record_id: str
    execution_seconds: float
    metrics_at_resolution: dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

async def execute(
    client_id: str,
    incident_id: str,
    service_name: str,
    actor: str,
    servicenow_ticket_id: str,
    parameters: dict[str, Any] | None = None,
) -> PlaybookResult:
    """
    Execute the Redis memory policy rollback playbook.

    Args:
        client_id:             Mandatory. Multi-tenancy enforcement.
        incident_id:           The ATLAS incident this execution belongs to.
        service_name:          Target Redis service name (e.g. "RedisCache").
        actor:                 "ATLAS_AUTO" or engineer name for audit trail.
        servicenow_ticket_id:  ServiceNow INC number for audit correlation.
        parameters:            Override default playbook parameters.

    Returns:
        PlaybookResult with full outcome details.
    """
    if not client_id:
        raise ValueError("client_id is required for playbook execution.")
    if not incident_id:
        raise ValueError("incident_id is required for playbook execution.")

    params = _merge_parameters(parameters)
    start_time = time.monotonic()

    redis_host, redis_port, redis_password = _get_redis_config(client_id, service_name)

    logger.info(
        "playbook.redis_policy_rollback.started",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        actor=actor,
        target_policy=params["target_policy"],
        redis_host=redis_host,
        redis_port=redis_port,
    )

    # ── Step 1: Pre-execution validation ─────────────────────────────────────
    validation_result = await _pre_validate(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        params=params,
    )

    if not validation_result["passed"]:
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="execution",
            actor=actor,
            description=(
                f"Playbook redis-memory-policy-rollback-v1 halted at pre-validation: "
                f"{validation_result['reason']}"
            ),
            outcome="pre_validation_failed",
            servicenow_ticket_id=servicenow_ticket_id,
            confidence_score=0.0,
        )
        return PlaybookResult(
            success=False,
            outcome="pre_validation_failed",
            detail=validation_result["reason"],
            audit_record_id=audit_id,
            execution_seconds=time.monotonic() - start_time,
        )

    # ── Step 2: Action execution ──────────────────────────────────────────────
    action_result = await _execute_action(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        target_policy=params["target_policy"],
    )

    if not action_result["success"]:
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="execution",
            actor=actor,
            description=(
                f"Playbook redis-memory-policy-rollback-v1 action failed: "
                f"{action_result['detail']}"
            ),
            outcome="action_failed",
            servicenow_ticket_id=servicenow_ticket_id,
            confidence_score=0.0,
        )
        return PlaybookResult(
            success=False,
            outcome="error",
            detail=action_result["detail"],
            audit_record_id=audit_id,
            execution_seconds=time.monotonic() - start_time,
        )

    # ── Step 3: Success validation ────────────────────────────────────────────
    validation_deadline = start_time + (params["max_validation_minutes"] * 60)

    success, final_metrics = await _validate_success(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        params=params,
        validation_deadline=validation_deadline,
    )

    if success:
        mem_pct = final_metrics.get("memory_pct", 0.0)
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="resolution",
            actor=actor,
            description=(
                f"Playbook redis-memory-policy-rollback-v1 succeeded. "
                f"maxmemory-policy set to {params['target_policy']}. "
                f"Memory usage recovered to {mem_pct * 100:.1f}% of maxmemory."
            ),
            outcome="success",
            servicenow_ticket_id=servicenow_ticket_id,
            confidence_score=1.0,
        )
        logger.info(
            "playbook.redis_policy_rollback.success",
            client_id=client_id,
            incident_id=incident_id,
            service=service_name,
            execution_seconds=round(time.monotonic() - start_time, 1),
        )
        return PlaybookResult(
            success=True,
            outcome="success",
            detail=(
                f"maxmemory-policy set to {params['target_policy']}. "
                "Memory recovery confirmed."
            ),
            audit_record_id=audit_id,
            execution_seconds=time.monotonic() - start_time,
            metrics_at_resolution=final_metrics,
        )

    # ── Step 4: Auto-rollback ─────────────────────────────────────────────────
    # Restore noeviction to preserve fault state for L2 investigation.
    logger.warning(
        "playbook.redis_policy_rollback.success_validation_timeout",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        triggering_rollback=True,
    )

    rollback_result = await _execute_rollback(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        restore_policy=params["fault_policy"],
    )

    # ── Step 5: Immutable audit record ────────────────────────────────────────
    audit_id = _write_audit(
        client_id=client_id,
        incident_id=incident_id,
        action_type="rollback",
        actor="ATLAS_AUTO",
        description=(
            f"Playbook redis-memory-policy-rollback-v1 auto-rollback executed. "
            f"Success validation timed out after {params['max_validation_minutes']} minutes. "
            f"maxmemory-policy restored to {params['fault_policy']} (fault state preserved "
            f"for L2 investigation). Rollback outcome: {rollback_result['detail']}. "
            "Incident re-escalated to L2/L3."
        ),
        outcome="rollback_executed",
        servicenow_ticket_id=servicenow_ticket_id,
        confidence_score=0.0,
    )

    return PlaybookResult(
        success=False,
        outcome="rollback_executed",
        detail=(
            f"Success validation timed out. Policy restored to {params['fault_policy']} "
            "for L2 investigation. Re-escalated to L2/L3."
        ),
        audit_record_id=audit_id,
        execution_seconds=time.monotonic() - start_time,
        metrics_at_resolution=final_metrics,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step implementations
# ─────────────────────────────────────────────────────────────────────────────

async def _pre_validate(
    client_id: str,
    incident_id: str,
    service_name: str,
    redis_host: str,
    redis_port: int,
    redis_password: str | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Pre-execution validation. All checks must pass before action proceeds.

    Checks:
      1. Redis instance reachable (PING → PONG)
      2. Current maxmemory-policy is noeviction (assumed cause must be present)
      3. Memory usage above alert threshold (issue still active)
    """
    import redis.asyncio as aioredis

    try:
        r = aioredis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
            socket_timeout=_REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
        async with r:
            # Check 1: PING
            pong = await r.ping()
            if not pong:
                return {"passed": False, "reason": "Redis PING did not return PONG."}
            logger.debug(
                "playbook.pre_validate.redis_ping_ok",
                client_id=client_id,
                service=service_name,
            )

            # Check 2: Confirm maxmemory-policy is noeviction
            policy_result = await r.config_get("maxmemory-policy")
            current_policy = policy_result.get("maxmemory-policy", "")

            # Hard guard: if already allkeys-lru, the assumed cause is not present
            if current_policy == params["target_policy"]:
                return {
                    "passed": False,
                    "reason": (
                        f"maxmemory-policy is already '{params['target_policy']}'. "
                        "The assumed cause (noeviction misconfiguration) is not present. "
                        "Halting — hypothesis may be incorrect. Escalating for L2 review."
                    ),
                }

            if current_policy != params["fault_policy"]:
                return {
                    "passed": False,
                    "reason": (
                        f"maxmemory-policy is '{current_policy}', expected "
                        f"'{params['fault_policy']}'. Cannot confirm assumed cause. "
                        "Halting for L2 review."
                    ),
                }

            logger.info(
                "playbook.pre_validate.policy_confirmed",
                client_id=client_id,
                service=service_name,
                current_policy=current_policy,
            )

            # Check 3: Memory usage above threshold
            info = await r.info("memory")
            used_memory = int(info.get("used_memory", 0))
            maxmemory = int(info.get("maxmemory", 0))

            if maxmemory == 0:
                # maxmemory=0 means unlimited — OOM from OS perspective, not Redis limit
                logger.warning(
                    "playbook.pre_validate.maxmemory_unlimited",
                    client_id=client_id,
                    service=service_name,
                )
                # Proceed anyway — policy change is still valid
            else:
                memory_pct = used_memory / maxmemory
                if memory_pct < params["alert_threshold_pct"]:
                    return {
                        "passed": False,
                        "reason": (
                            f"Memory usage is {memory_pct * 100:.1f}% of maxmemory "
                            f"(threshold: {params['alert_threshold_pct'] * 100:.0f}%). "
                            "Issue may have self-resolved. Halting to avoid unnecessary action."
                        ),
                    }
                logger.info(
                    "playbook.pre_validate.memory_confirmed",
                    client_id=client_id,
                    service=service_name,
                    memory_pct=round(memory_pct, 3),
                    used_memory=used_memory,
                    maxmemory=maxmemory,
                )

    except Exception as exc:
        # Catch-all for redis connection errors (ConnectionError, AuthenticationError, etc.)
        logger.error(
            "playbook.pre_validate.redis_error",
            client_id=client_id,
            service=service_name,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {
            "passed": False,
            "reason": f"Redis connection failed during pre-validation: {type(exc).__name__}: {exc}",
        }

    return {"passed": True, "reason": "all_checks_passed"}


async def _execute_action(
    client_id: str,
    incident_id: str,
    service_name: str,
    redis_host: str,
    redis_port: int,
    redis_password: str | None,
    target_policy: str,
) -> dict[str, Any]:
    """
    Action: set maxmemory-policy to allkeys-lru via CONFIG SET.

    Real mechanism:
      CONFIG SET maxmemory-policy allkeys-lru — takes effect immediately, no restart.
      CONFIG GET maxmemory-policy — verify the change took effect.

    This is the production-standard approach for runtime Redis policy change.
    allkeys-lru allows Redis to evict least-recently-used keys when memory is full,
    restoring command acceptance and freeing memory.

    HARD GUARD: FLUSHALL and FLUSHDB are never executed. Not in this playbook.
    """
    import redis.asyncio as aioredis

    try:
        r = aioredis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
            socket_timeout=_REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
        async with r:
            # Apply the policy change
            result = await r.config_set("maxmemory-policy", target_policy)
            logger.info(
                "playbook.action.config_set",
                client_id=client_id,
                service=service_name,
                target_policy=target_policy,
                result=result,
            )
            if not result:
                return {
                    "success": False,
                    "detail": f"CONFIG SET maxmemory-policy {target_policy} returned falsy.",
                }

            # Verify the change took effect
            await asyncio.sleep(0.5)
            verify = await r.config_get("maxmemory-policy")
            active_policy = verify.get("maxmemory-policy", "")

            if active_policy != target_policy:
                return {
                    "success": False,
                    "detail": (
                        f"CONFIG SET appeared to succeed but CONFIG GET returned "
                        f"'{active_policy}' instead of '{target_policy}'."
                    ),
                }

            logger.info(
                "playbook.action.verified",
                client_id=client_id,
                service=service_name,
                active_policy=active_policy,
            )

    except Exception as exc:
        logger.error(
            "playbook.action.redis_error",
            client_id=client_id,
            service=service_name,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {
            "success": False,
            "detail": f"Redis action failed: {type(exc).__name__}: {exc}",
        }

    return {"success": True, "detail": f"maxmemory-policy set to {target_policy}."}


async def _validate_success(
    client_id: str,
    incident_id: str,
    service_name: str,
    redis_host: str,
    redis_port: int,
    redis_password: str | None,
    params: dict[str, Any],
    validation_deadline: float,
) -> tuple[bool, dict[str, Any]]:
    """
    Poll memory usage every 30 seconds.
    Declare success when usage < 75% of maxmemory for 2 consecutive readings.
    """
    import redis.asyncio as aioredis

    consecutive_below = 0
    last_metrics: dict[str, Any] = {}

    while time.monotonic() < validation_deadline:
        await asyncio.sleep(params["poll_interval_seconds"])

        if time.monotonic() >= validation_deadline:
            break

        try:
            r = aioredis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
                socket_timeout=_REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            async with r:
                info = await r.info("memory")
                used_memory = int(info.get("used_memory", 0))
                maxmemory = int(info.get("maxmemory", 0))

                if maxmemory == 0:
                    # Unlimited maxmemory — check rejected_commands instead
                    stats = await r.info("stats")
                    rejected = int(stats.get("rejected_connections", 0))
                    last_metrics = {
                        "used_memory": used_memory,
                        "maxmemory": 0,
                        "memory_pct": 0.0,
                        "rejected_connections": rejected,
                    }
                    logger.info(
                        "playbook.success_validation.poll_unlimited_maxmemory",
                        client_id=client_id,
                        service=service_name,
                        rejected_connections=rejected,
                    )
                    # With unlimited maxmemory, declare success after 2 polls with 0 rejections
                    if rejected == 0:
                        consecutive_below += 1
                        if consecutive_below >= params["success_consecutive_readings"]:
                            return True, last_metrics
                    else:
                        consecutive_below = 0
                else:
                    memory_pct = used_memory / maxmemory
                    last_metrics = {
                        "used_memory": used_memory,
                        "maxmemory": maxmemory,
                        "memory_pct": memory_pct,
                    }

                    logger.info(
                        "playbook.success_validation.poll",
                        client_id=client_id,
                        service=service_name,
                        memory_pct=round(memory_pct, 3),
                        consecutive_below=consecutive_below,
                        threshold=params["success_threshold_pct"],
                    )

                    if memory_pct < params["success_threshold_pct"]:
                        consecutive_below += 1
                        if consecutive_below >= params["success_consecutive_readings"]:
                            return True, last_metrics
                    else:
                        consecutive_below = 0

        except Exception as exc:
            logger.warning(
                "playbook.success_validation.poll_failed",
                client_id=client_id,
                service=service_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            consecutive_below = 0

    return False, last_metrics


async def _execute_rollback(
    client_id: str,
    incident_id: str,
    service_name: str,
    redis_host: str,
    redis_port: int,
    redis_password: str | None,
    restore_policy: str,
) -> dict[str, Any]:
    """
    Rollback: restore maxmemory-policy to noeviction.
    Preserves the fault state for L2 investigation.
    Does NOT attempt to fix the underlying memory issue — that requires L2.
    """
    import redis.asyncio as aioredis

    logger.warning(
        "playbook.rollback.executing",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        restore_policy=restore_policy,
    )

    try:
        r = aioredis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
            socket_timeout=_REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
        async with r:
            result = await r.config_set("maxmemory-policy", restore_policy)
            logger.info(
                "playbook.rollback.config_restore",
                client_id=client_id,
                service=service_name,
                restore_policy=restore_policy,
                result=result,
            )
            return {"success": True, "detail": f"maxmemory-policy restored to {restore_policy}."}
    except Exception as exc:
        logger.error(
            "playbook.rollback.failed",
            client_id=client_id,
            service=service_name,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {"success": False, "detail": f"Rollback failed: {type(exc).__name__}: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_redis_config(client_id: str, service_name: str) -> tuple[str, int, str | None]:
    """
    Resolve Redis connection parameters from environment variables.

    Convention:
      ATLAS_{CLIENT_ID}_{SERVICE_NAME}_REDIS_HOST
      ATLAS_{CLIENT_ID}_{SERVICE_NAME}_REDIS_PORT  (default 6379)
      ATLAS_{CLIENT_ID}_{SERVICE_NAME}_REDIS_PASSWORD  (optional)

    Falls back to:
      ATLAS_REDIS_HOST / ATLAS_REDIS_PORT / ATLAS_REDIS_PASSWORD
    """
    prefix = (
        f"ATLAS_{client_id.upper().replace('-', '_')}_"
        f"{service_name.upper().replace('-', '_')}"
    )
    host = (
        os.environ.get(f"{prefix}_REDIS_HOST")
        or os.environ.get("ATLAS_REDIS_HOST", "")
    )
    if not host:
        raise RuntimeError(
            f"Cannot resolve Redis host for client='{client_id}' service='{service_name}'. "
            f"Set '{prefix}_REDIS_HOST' or 'ATLAS_REDIS_HOST'."
        )
    port_str = (
        os.environ.get(f"{prefix}_REDIS_PORT")
        or os.environ.get("ATLAS_REDIS_PORT", "6379")
    )
    try:
        port = int(port_str)
    except ValueError:
        raise RuntimeError(
            f"Invalid Redis port value '{port_str}'. Must be an integer."
        )
    password = (
        os.environ.get(f"{prefix}_REDIS_PASSWORD")
        or os.environ.get("ATLAS_REDIS_PASSWORD")
    )
    return host, port, password


def _merge_parameters(overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Merge caller-supplied parameter overrides with playbook defaults."""
    defaults: dict[str, Any] = {
        "target_policy": _TARGET_POLICY,
        "fault_policy": _FAULT_POLICY,
        "alert_threshold_pct": _ALERT_THRESHOLD_PCT,
        "success_threshold_pct": _SUCCESS_THRESHOLD_PCT,
        "success_consecutive_readings": _SUCCESS_CONSECUTIVE,
        "poll_interval_seconds": _POLL_INTERVAL,
        "max_validation_minutes": _MAX_VALIDATION_MINUTES,
    }
    if overrides:
        defaults.update(overrides)
    return defaults


def _write_audit(
    client_id: str,
    incident_id: str,
    action_type: str,
    actor: str,
    description: str,
    outcome: str,
    servicenow_ticket_id: str,
    confidence_score: float,
) -> str:
    """Write an immutable audit record. Returns the record_id UUID."""
    return write_audit_record({
        "client_id": client_id,
        "incident_id": incident_id,
        "action_type": action_type,
        "actor": actor,
        "action_description": description,
        "confidence_score_at_time": confidence_score,
        "outcome": outcome,
        "servicenow_ticket_id": servicenow_ticket_id,
        "rollback_available": True,
        "compliance_frameworks_applied": [],
        "reasoning_summary": "Playbook redis-memory-policy-rollback-v1 execution record.",
    })
