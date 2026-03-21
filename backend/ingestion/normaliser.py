"""
Normalises raw log events from all three ingestion paths into the unified ATLAS OTel schema.
Every event that enters the system passes through here.
client_id is tagged at creation and is immutable from this point forward.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Severity normalisation map
_SEVERITY_MAP: dict[str, str] = {
    "FATAL": "ERROR",
    "CRITICAL": "ERROR",
    "ERROR": "ERROR",
    "SEVERE": "ERROR",
    "WARN": "WARN",
    "WARNING": "WARN",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
    "TRACE": "DEBUG",
    "FINE": "DEBUG",
    "FINER": "DEBUG",
    "FINEST": "DEBUG",
}

# Maximum event size in bytes before sampling
_MAX_EVENT_SIZE_BYTES = 1_048_576  # 1 MB


def normalise(raw_event: dict[str, Any]) -> dict[str, Any] | None:
    """
    Normalise a raw event from any ingestion path into the unified ATLAS OTel schema.

    Args:
        raw_event: Raw event dict from Path A (OTel), Path B (adapter), or Path C (API pull).
                   Must contain 'client_id'.

    Returns:
        Normalised event dict, or None if the event is rejected (missing client_id).

    Raises:
        Never raises — all errors are logged and handled gracefully.
    """
    # Hard reject: missing client_id
    client_id = raw_event.get("client_id")
    if not client_id:
        logger.error(
            "normaliser.rejected_missing_client_id",
            raw_keys=list(raw_event.keys()),
        )
        return None

    # Generate unique event ID
    atlas_event_id = str(uuid.uuid4())

    # Normalise timestamp
    raw_ts = raw_event.get("timestamp")
    timestamp, ts_valid = _parse_timestamp(raw_ts)

    # Normalise severity
    raw_severity = str(raw_event.get("severity", raw_event.get("level", "INFO"))).upper()
    severity = _SEVERITY_MAP.get(raw_severity, "INFO")

    # Preserve raw payload exactly — never modified
    raw_payload = raw_event.get("raw_payload", raw_event.get("message", ""))
    if not isinstance(raw_payload, str):
        raw_payload = str(raw_payload)

    # Check event size
    event_size = len(raw_payload.encode("utf-8"))
    size_flagged = event_size > _MAX_EVENT_SIZE_BYTES
    if size_flagged:
        logger.warning(
            "normaliser.event_oversized",
            client_id=client_id,
            size_bytes=event_size,
            max_bytes=_MAX_EVENT_SIZE_BYTES,
        )
        # Sample: truncate raw_payload but preserve the flag
        raw_payload = raw_payload[:_MAX_EVENT_SIZE_BYTES] + "...[TRUNCATED]"

    normalised: dict[str, Any] = {
        "atlas_event_id": atlas_event_id,
        "client_id": client_id,                    # immutable from this point
        "timestamp": timestamp.isoformat(),
        "source_system": raw_event.get("source_system", raw_event.get("service_name", "unknown")),
        "source_type": raw_event.get("source_type", "unknown"),
        "severity": severity,
        "error_code": raw_event.get("error_code", ""),
        "message": raw_event.get("message", ""),
        "raw_payload": raw_payload,                # always preserved exactly
        "deployment_id": raw_event.get("deployment_id"),
        # CMDB enrichment fields — populated by cmdb_enricher.py downstream
        "ci_class": None,
        "ci_version": None,
        "business_service_name": None,
        "criticality_tier": None,
        "open_change_records": [],
        "sla_breach_threshold_minutes": None,
        "owner_team": None,
        "cmdb_enrichment_status": "pending",
        "enriched_from_cache": False,
        # Metadata flags
        "timestamp_valid": ts_valid,
        "oversized": size_flagged,
    }

    logger.debug(
        "normaliser.event_normalised",
        atlas_event_id=atlas_event_id,
        client_id=client_id,
        source_type=normalised["source_type"],
        severity=severity,
    )
    return normalised


def _parse_timestamp(raw_ts: Any) -> tuple[datetime, bool]:
    """
    Parse a timestamp from various formats to UTC datetime.
    Returns (parsed_datetime, is_valid).
    Falls back to arrival time with is_valid=False if parsing fails.
    """
    arrival_time = datetime.now(timezone.utc)

    if raw_ts is None:
        return arrival_time, False

    if isinstance(raw_ts, datetime):
        if raw_ts.tzinfo is None:
            raw_ts = raw_ts.replace(tzinfo=timezone.utc)
        return raw_ts, True

    if isinstance(raw_ts, (int, float)):
        # Unix timestamp
        try:
            return datetime.fromtimestamp(raw_ts, tz=timezone.utc), True
        except (OSError, OverflowError, ValueError):
            return arrival_time, False

    if isinstance(raw_ts, str):
        # Try ISO-8601 first
        try:
            dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, True
        except ValueError:
            pass

        # Try common log formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S %z",
            "%b %d %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(raw_ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt, True
            except ValueError:
                continue

    logger.warning(
        "normaliser.timestamp_unparseable",
        raw_ts=str(raw_ts)[:100],
    )
    return arrival_time, False
