"""
PostgreSQL log adapter.
Reads native PostgreSQL log format and converts to the unified ATLAS schema.
Path B adapter for PostgreSQL services.
Maps SQLSTATE codes to ATLAS error taxonomy. FATAL always outputs as ERROR.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# PostgreSQL log format:
# 2024-01-15 09:23:47.123 UTC [12345] ERROR:  message DETAIL: detail CONTEXT: context
# Also handles: FATAL, PANIC, WARNING, LOG, NOTICE, DEBUG
_PG_LOG_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+\w+)"
    r"\s+\[(?P<pid>\d+)\]"
    r"\s+(?P<level>[A-Z]+):\s+"
    r"(?P<message>.+)$"
)

# SQLSTATE code extraction
_SQLSTATE_RE = re.compile(r"SQLSTATE[:\s]+([A-Z0-9]{5})", re.IGNORECASE)

# SQLSTATE to ATLAS error taxonomy
_SQLSTATE_MAP: dict[str, str] = {
    "53300": "CONNECTION_POOL_EXHAUSTED",   # too_many_connections
    "53200": "CONNECTION_POOL_EXHAUSTED",   # out_of_memory
    "40P01": "DB_DEADLOCK",                 # deadlock_detected
    "40001": "DB_DEADLOCK",                 # serialization_failure
    "57P03": "DB_PANIC",                    # cannot_connect_now
    "08006": "CONNECTION_POOL_EXHAUSTED",   # connection_failure
    "08001": "CONNECTION_POOL_EXHAUSTED",   # sqlclient_unable_to_establish_sqlconnection
    "08004": "CONNECTION_POOL_EXHAUSTED",   # sqlserver_rejected_establishment_of_sqlconnection
}

# Message pattern to ATLAS error taxonomy (for cases without SQLSTATE)
_MESSAGE_PATTERN_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"remaining connection slots are reserved|too many connections", re.IGNORECASE), "CONNECTION_POOL_EXHAUSTED"),
    (re.compile(r"deadlock detected", re.IGNORECASE), "DB_DEADLOCK"),
    (re.compile(r"^PANIC:", re.IGNORECASE), "DB_PANIC"),
    (re.compile(r"out of memory", re.IGNORECASE), "CONNECTION_POOL_EXHAUSTED"),
]

# Connection count extraction
_CONN_COUNT_RE = re.compile(r"(\d+)\s+connections?", re.IGNORECASE)

# PostgreSQL severity to ATLAS severity
# FATAL always maps to ERROR — never downgraded
_SEVERITY_MAP: dict[str, str] = {
    "PANIC": "ERROR",
    "FATAL": "ERROR",    # FATAL always outputs as ERROR — never downgraded
    "ERROR": "ERROR",
    "WARNING": "WARN",
    "NOTICE": "INFO",
    "INFO": "INFO",
    "LOG": "INFO",
    "DEBUG": "DEBUG",
    "DEBUG1": "DEBUG",
    "DEBUG2": "DEBUG",
    "DEBUG3": "DEBUG",
    "DEBUG4": "DEBUG",
    "DEBUG5": "DEBUG",
}


def parse_line(
    raw_line: str,
    client_id: str,
    service_name: str,
    source_type: str = "postgresql",
) -> dict[str, Any] | None:
    """
    Parse a single PostgreSQL log line into a normalised event dict.

    Args:
        raw_line: The raw PostgreSQL log line.
        client_id: Mandatory client scope.
        service_name: The PostgreSQL service name.
        source_type: Source type tag (default: postgresql).

    Returns:
        Normalised event dict, or None if the line is empty.
        Unparseable lines are returned with severity INFO and source_type postgresql-unparseable.
        FATAL severity always outputs as ERROR — never downgraded.
    """
    if not client_id:
        raise ValueError("client_id is required in postgres_adapter.parse_line")

    raw_line = raw_line.rstrip("\n\r")
    if not raw_line.strip():
        return None

    match = _PG_LOG_RE.match(raw_line)

    if not match:
        return {
            "client_id": client_id,
            "source_system": service_name,
            "source_type": "postgresql-unparseable",
            "severity": "INFO",
            "error_code": "",
            "message": raw_line,
            "raw_payload": raw_line,
            "timestamp": None,
        }

    pg_level = match.group("level").upper()
    # FATAL always maps to ERROR — never downgraded
    atlas_severity = _SEVERITY_MAP.get(pg_level, "INFO")

    message = match.group("message")
    error_code = _map_error_code(message, pg_level)

    # Extract connection count if present
    conn_match = _CONN_COUNT_RE.search(message)
    conn_count = int(conn_match.group(1)) if conn_match else None

    event: dict[str, Any] = {
        "client_id": client_id,
        "source_system": service_name,
        "source_type": source_type,
        "severity": atlas_severity,
        "error_code": error_code,
        "message": message,
        "raw_payload": raw_line,
        "timestamp": match.group("timestamp"),
        "pid": match.group("pid"),
        "pg_level": pg_level,
    }

    if conn_count is not None:
        event["connection_count"] = conn_count

    return event


def _map_error_code(message: str, pg_level: str) -> str:
    """
    Map PostgreSQL SQLSTATE codes and message patterns to ATLAS error taxonomy.
    Unknown SQLSTATE codes get error_code DB_UNKNOWN with the SQLSTATE preserved.
    PANIC level always returns DB_PANIC.
    """
    # PANIC always maps to DB_PANIC
    if pg_level == "PANIC":
        return "DB_PANIC"

    # Check for SQLSTATE code in message
    sqlstate_match = _SQLSTATE_RE.search(message)
    if sqlstate_match:
        sqlstate = sqlstate_match.group(1)
        if sqlstate in _SQLSTATE_MAP:
            return _SQLSTATE_MAP[sqlstate]
        return f"DB_UNKNOWN:{sqlstate}"

    # Check message patterns
    for pattern, atlas_code in _MESSAGE_PATTERN_MAP:
        if pattern.search(message):
            return atlas_code

    return ""
