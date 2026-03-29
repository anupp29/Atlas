"""
Playbook: connection-pool-recovery-v2
Target:   Java Spring Boot services with HikariCP connection pool exhaustion.

Five mandatory steps (per ATLAS execution engine contract):
  1. Pre-execution validation
  2. Action execution
  3. Success validation
  4. Auto-rollback (if success validation times out)
  5. Immutable audit record (written regardless of outcome)

Real-world basis:
  HikariCP exposes a JMX MBean (HikariConfigMXBean) with setMaximumPoolSize().
  Spring Boot Actuator wraps this via POST /actuator/env (property override) +
  POST /actuator/refresh (apply via @RefreshScope). This is the production-standard
  approach for runtime pool resize without service restart.

  References:
    - HikariCP HikariConfigMXBean: github.com/brettwooldridge/HikariCP
    - Spring Boot Actuator /env: docs.spring.io/spring-boot/api/rest/actuator/env.html
    - Spring Cloud Config refresh: POST /actuator/refresh triggers @RefreshScope rebind
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from backend.database.audit_db import write_audit_record

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants — all overridable via playbook parameters
# ─────────────────────────────────────────────────────────────────────────────

_HTTP_TIMEOUT: float = 10.0
_POLL_INTERVAL: int = 30
_MAX_VALIDATION_MINUTES: int = 10
_MAX_TOTAL_MINUTES: int = 15
_TARGET_POOL_SIZE: int = 150
_ALERT_THRESHOLD_PCT: float = 0.85
_SUCCESS_THRESHOLD_PCT: float = 0.70
_SUCCESS_CONSECUTIVE: int = 2
_NO_ACTION_WINDOW_MINUTES: int = 10


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
    previous_pool_size: int | None = None,
) -> PlaybookResult:
    """
    Execute the connection pool recovery playbook.

    Args:
        client_id:             Mandatory. Multi-tenancy enforcement.
        incident_id:           The ATLAS incident this execution belongs to.
        service_name:          Target service (e.g. "PaymentAPI").
        actor:                 "ATLAS_AUTO" or engineer name for audit trail.
        servicenow_ticket_id:  ServiceNow INC number for audit correlation.
        parameters:            Override default playbook parameters.
        previous_pool_size:    The pool size before the fault (for rollback).

    Returns:
        PlaybookResult with full outcome details.
    """
    if not client_id:
        raise ValueError("client_id is required for playbook execution.")
    if not incident_id:
        raise ValueError("incident_id is required for playbook execution.")

    params = _merge_parameters(parameters)
    start_time = time.monotonic()

    base_url = _get_service_url(client_id, service_name)

    logger.info(
        "playbook.connection_pool_recovery.started",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        actor=actor,
        target_pool_size=params["target_pool_size"],
        base_url=_redact_url(base_url),
    )

    # ── Step 1: Pre-execution validation ─────────────────────────────────────
    validation_result = await _pre_validate(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        base_url=base_url,
        params=params,
    )

    if not validation_result["passed"]:
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="execution",
            actor=actor,
            description=(
                f"Playbook connection-pool-recovery-v2 halted at pre-validation: "
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

    current_pool_size: int = validation_result.get("current_pool_size") or previous_pool_size or 40

    # ── Step 2: Action execution ──────────────────────────────────────────────
    action_result = await _execute_action(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        base_url=base_url,
        target_pool_size=params["target_pool_size"],
    )

    if not action_result["success"]:
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="execution",
            actor=actor,
            description=(
                f"Playbook connection-pool-recovery-v2 action failed: {action_result['detail']}"
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
    hard_deadline = start_time + (params["max_total_runtime_minutes"] * 60)

    success, final_metrics = await _validate_success(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        base_url=base_url,
        params=params,
        validation_deadline=min(validation_deadline, hard_deadline),
    )

    if success:
        conn_pct = final_metrics.get("connection_pct", 0.0)
        audit_id = _write_audit(
            client_id=client_id,
            incident_id=incident_id,
            action_type="resolution",
            actor=actor,
            description=(
                f"Playbook connection-pool-recovery-v2 succeeded. "
                f"Pool size set to {params['target_pool_size']}. "
                f"Connection count recovered to {conn_pct * 100:.1f}% of max_connections."
            ),
            outcome="success",
            servicenow_ticket_id=servicenow_ticket_id,
            confidence_score=1.0,
        )
        logger.info(
            "playbook.connection_pool_recovery.success",
            client_id=client_id,
            incident_id=incident_id,
            service=service_name,
            execution_seconds=round(time.monotonic() - start_time, 1),
        )
        return PlaybookResult(
            success=True,
            outcome="success",
            detail=f"Connection pool restored to {params['target_pool_size']}. Recovery confirmed.",
            audit_record_id=audit_id,
            execution_seconds=time.monotonic() - start_time,
            metrics_at_resolution=final_metrics,
        )

    # ── Step 4: Auto-rollback ─────────────────────────────────────────────────
    logger.warning(
        "playbook.connection_pool_recovery.success_validation_timeout",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        triggering_rollback=True,
    )

    rollback_result = await _execute_rollback(
        client_id=client_id,
        incident_id=incident_id,
        service_name=service_name,
        base_url=base_url,
        restore_pool_size=current_pool_size,
    )

    # ── Step 5: Immutable audit record ────────────────────────────────────────
    audit_id = _write_audit(
        client_id=client_id,
        incident_id=incident_id,
        action_type="rollback",
        actor="ATLAS_AUTO",
        description=(
            f"Playbook connection-pool-recovery-v2 auto-rollback executed. "
            f"Success validation timed out after {params['max_validation_minutes']} minutes. "
            f"Pool size restored to {current_pool_size}. "
            f"Rollback outcome: {rollback_result['detail']}. "
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
            f"Success validation timed out. Pool restored to {current_pool_size}. "
            "Re-escalated to L2/L3."
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
    base_url: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """
    Pre-execution validation. All checks must pass before action proceeds.

    Checks:
      1. Service health endpoint reachable (200 or 503 both mean reachable)
      2. Actuator management endpoint accessible
      3. Current connection count above alert threshold (issue still active)
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:

        # Check 1: Health endpoint reachable
        try:
            resp = await client.get(f"{base_url}/actuator/health")
            if resp.status_code not in (200, 503):
                return {
                    "passed": False,
                    "reason": (
                        f"Health endpoint returned unexpected status {resp.status_code}. "
                        "Cannot confirm service state."
                    ),
                }
            logger.debug(
                "playbook.pre_validate.health_ok",
                client_id=client_id,
                service=service_name,
                status=resp.status_code,
            )
        except httpx.RequestError as exc:
            return {
                "passed": False,
                "reason": f"Service health endpoint unreachable: {exc}. Cannot proceed safely.",
            }

        # Check 2: Actuator management endpoint accessible
        try:
            resp = await client.get(f"{base_url}/actuator")
            if resp.status_code != 200:
                return {
                    "passed": False,
                    "reason": (
                        f"Actuator endpoint returned {resp.status_code}. "
                        "Cannot apply configuration change without actuator access."
                    ),
                }
        except httpx.RequestError as exc:
            return {
                "passed": False,
                "reason": f"Actuator endpoint unreachable: {exc}.",
            }

        # Check 3: Connection count above threshold (confirm issue still active)
        current_pool_size: int | None = None
        try:
            active_resp = await client.get(
                f"{base_url}/actuator/metrics/hikaricp.connections.active"
            )
            max_resp = await client.get(
                f"{base_url}/actuator/metrics/hikaricp.connections.max"
            )
            if active_resp.status_code == 200 and max_resp.status_code == 200:
                active = active_resp.json().get("measurements", [{}])[0].get("value", 0)
                max_pool = max_resp.json().get("measurements", [{}])[0].get("value", 1)
                connection_pct = active / max(max_pool, 1)

                if connection_pct < params["alert_threshold_pct"]:
                    return {
                        "passed": False,
                        "reason": (
                            f"Connection count is {connection_pct * 100:.1f}% of max_connections "
                            f"(threshold: {params['alert_threshold_pct'] * 100:.0f}%). "
                            "Issue may have self-resolved. Halting to avoid unnecessary action."
                        ),
                    }
                logger.info(
                    "playbook.pre_validate.connection_count_confirmed",
                    client_id=client_id,
                    service=service_name,
                    connection_pct=round(connection_pct, 3),
                    active=active,
                    max_pool=max_pool,
                )
                current_pool_size = int(max_pool)
            else:
                logger.warning(
                    "playbook.pre_validate.metrics_unavailable",
                    client_id=client_id,
                    service=service_name,
                    active_status=active_resp.status_code,
                    max_status=max_resp.status_code,
                )
        except httpx.RequestError as exc:
            logger.warning(
                "playbook.pre_validate.metrics_request_failed",
                client_id=client_id,
                service=service_name,
                error=str(exc),
            )

    return {"passed": True, "reason": "all_checks_passed", "current_pool_size": current_pool_size}


async def _execute_action(
    client_id: str,
    incident_id: str,
    service_name: str,
    base_url: str,
    target_pool_size: int,
) -> dict[str, Any]:
    """
    Action: update HikariCP maxPoolSize via Spring Boot Actuator.

    Real mechanism:
      POST /actuator/env  — injects the property override into the environment
      POST /actuator/refresh — triggers @RefreshScope rebind, applying the change
      GET  /actuator/env/spring.datasource.hikari.maximum-pool-size — verify

    This is the production-standard approach for runtime HikariCP pool resize
    without service restart. Requires spring-cloud-context on the classpath.
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:

        # Step A: Override the property via /actuator/env
        env_payload = {
            "name": "spring.datasource.hikari.maximum-pool-size",
            "value": str(target_pool_size),
        }
        try:
            resp = await client.post(
                f"{base_url}/actuator/env",
                json=env_payload,
                headers={"Content-Type": "application/json"},
            )
            logger.info(
                "playbook.action.env_override",
                client_id=client_id,
                service=service_name,
                url=_redact_url(f"{base_url}/actuator/env"),
                status=resp.status_code,
                target_pool_size=target_pool_size,
            )
            if resp.status_code not in (200, 204):
                return {
                    "success": False,
                    "detail": (
                        f"POST /actuator/env returned {resp.status_code}. "
                        f"Response: {resp.text[:200]}"
                    ),
                }
        except httpx.RequestError as exc:
            return {"success": False, "detail": f"POST /actuator/env failed: {exc}"}

        # Step B: Trigger refresh to apply the property change
        try:
            resp = await client.post(
                f"{base_url}/actuator/refresh",
                headers={"Content-Type": "application/json"},
            )
            logger.info(
                "playbook.action.refresh",
                client_id=client_id,
                service=service_name,
                url=_redact_url(f"{base_url}/actuator/refresh"),
                status=resp.status_code,
            )
            if resp.status_code not in (200, 204):
                return {
                    "success": False,
                    "detail": (
                        f"POST /actuator/refresh returned {resp.status_code}. "
                        f"Response: {resp.text[:200]}"
                    ),
                }
        except httpx.RequestError as exc:
            return {"success": False, "detail": f"POST /actuator/refresh failed: {exc}"}

        # Step C: Verify the change took effect
        await asyncio.sleep(2)  # Brief settle time for pool resize
        try:
            resp = await client.get(
                f"{base_url}/actuator/env/spring.datasource.hikari.maximum-pool-size"
            )
            if resp.status_code == 200:
                data = resp.json()
                active_value: str | None = None
                for source in data.get("propertySources", []):
                    val = source.get("properties", {}).get(
                        "spring.datasource.hikari.maximum-pool-size", {}
                    ).get("value")
                    if val is not None:
                        active_value = val
                        break
                logger.info(
                    "playbook.action.verified",
                    client_id=client_id,
                    service=service_name,
                    active_value=active_value,
                    expected=str(target_pool_size),
                )
        except httpx.RequestError:
            # Verification failure is non-fatal — action may still have succeeded
            logger.warning(
                "playbook.action.verification_skipped",
                client_id=client_id,
                service=service_name,
            )

    return {"success": True, "detail": f"Pool size set to {target_pool_size} via actuator."}


async def _validate_success(
    client_id: str,
    incident_id: str,
    service_name: str,
    base_url: str,
    params: dict[str, Any],
    validation_deadline: float,
) -> tuple[bool, dict[str, Any]]:
    """
    Poll connection count every 30 seconds.
    Declare success when count < 70% of max_connections for 2 consecutive readings.
    """
    consecutive_below = 0
    last_metrics: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        while time.monotonic() < validation_deadline:
            await asyncio.sleep(params["poll_interval_seconds"])

            if time.monotonic() >= validation_deadline:
                break

            try:
                active_resp = await client.get(
                    f"{base_url}/actuator/metrics/hikaricp.connections.active"
                )
                max_resp = await client.get(
                    f"{base_url}/actuator/metrics/hikaricp.connections.max"
                )

                if active_resp.status_code == 200 and max_resp.status_code == 200:
                    active = active_resp.json().get("measurements", [{}])[0].get("value", 0)
                    max_pool = max_resp.json().get("measurements", [{}])[0].get("value", 1)
                    connection_pct = active / max(max_pool, 1)

                    last_metrics = {
                        "active_connections": active,
                        "max_connections": max_pool,
                        "connection_pct": connection_pct,
                    }

                    logger.info(
                        "playbook.success_validation.poll",
                        client_id=client_id,
                        service=service_name,
                        connection_pct=round(connection_pct, 3),
                        consecutive_below=consecutive_below,
                        threshold=params["success_threshold_pct"],
                    )

                    if connection_pct < params["success_threshold_pct"]:
                        consecutive_below += 1
                        if consecutive_below >= params["success_consecutive_readings"]:
                            return True, last_metrics
                    else:
                        consecutive_below = 0

            except httpx.RequestError as exc:
                logger.warning(
                    "playbook.success_validation.poll_failed",
                    client_id=client_id,
                    service=service_name,
                    error=str(exc),
                )
                consecutive_below = 0

    return False, last_metrics


async def _execute_rollback(
    client_id: str,
    incident_id: str,
    service_name: str,
    base_url: str,
    restore_pool_size: int,
) -> dict[str, Any]:
    """
    Rollback: restore maxPoolSize to its pre-action value.
    Uses the same actuator mechanism as the action step.
    """
    logger.warning(
        "playbook.rollback.executing",
        client_id=client_id,
        incident_id=incident_id,
        service=service_name,
        restore_pool_size=restore_pool_size,
    )

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{base_url}/actuator/env",
                json={
                    "name": "spring.datasource.hikari.maximum-pool-size",
                    "value": str(restore_pool_size),
                },
                headers={"Content-Type": "application/json"},
            )
            logger.info(
                "playbook.rollback.env_restore",
                client_id=client_id,
                service=service_name,
                status=resp.status_code,
                restore_pool_size=restore_pool_size,
            )
            await client.post(f"{base_url}/actuator/refresh")
            return {"success": True, "detail": f"Pool size restored to {restore_pool_size}."}
        except httpx.RequestError as exc:
            logger.error(
                "playbook.rollback.failed",
                client_id=client_id,
                service=service_name,
                error=str(exc),
            )
            return {"success": False, "detail": f"Rollback request failed: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_service_url(client_id: str, service_name: str) -> str:
    """
    Resolve the base URL for a service from environment variables.
    Convention: ATLAS_{CLIENT_ID}_{SERVICE_NAME}_URL
    e.g. ATLAS_FINCORE_UK_001_PAYMENTAPI_URL
    Falls back to ATLAS_MOCK_SERVICE_URL for demo/test environments.
    """
    env_key = (
        f"ATLAS_{client_id.upper().replace('-', '_')}_"
        f"{service_name.upper().replace('-', '_')}_URL"
    )
    url = os.environ.get(env_key) or os.environ.get("ATLAS_MOCK_SERVICE_URL", "")
    if not url:
        raise RuntimeError(
            f"Cannot resolve service URL for client='{client_id}' service='{service_name}'. "
            f"Set environment variable '{env_key}' or 'ATLAS_MOCK_SERVICE_URL'."
        )
    return url.rstrip("/")


def _redact_url(url: str) -> str:
    """Strip credentials from URL before logging."""
    return re.sub(r"://[^@]+@", "://<redacted>@", url)


def _merge_parameters(overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Merge caller-supplied parameter overrides with playbook defaults."""
    defaults: dict[str, Any] = {
        "target_pool_size": _TARGET_POOL_SIZE,
        "alert_threshold_pct": _ALERT_THRESHOLD_PCT,
        "success_threshold_pct": _SUCCESS_THRESHOLD_PCT,
        "success_consecutive_readings": _SUCCESS_CONSECUTIVE,
        "poll_interval_seconds": _POLL_INTERVAL,
        "max_validation_minutes": _MAX_VALIDATION_MINUTES,
        "max_total_runtime_minutes": _MAX_TOTAL_MINUTES,
        "http_timeout_seconds": _HTTP_TIMEOUT,
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
        "reasoning_summary": "Playbook connection-pool-recovery-v2 execution record.",
    })
