"""
Java Spring Boot log adapter.
Reads native Spring Boot log format and converts to the unified ATLAS schema.
Path B adapter for Java services.
Handles multi-line stack traces. Maps exception class names to ATLAS error taxonomy.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Spring Boot log format:
# 2024-01-15 09:23:47.123  ERROR 12345 --- [http-nio-8080-exec-1] c.e.PaymentService : Error message
_SPRING_BOOT_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)"
    r"\s+(?P<level>[A-Z]+)"
    r"\s+(?P<pid>\d+)"
    r"\s+---\s+"
    r"\[(?P<thread>[^\]]+)\]"
    r"\s+(?P<logger>\S+)\s*:\s*"
    r"(?P<message>.+)$"
)

# Exception class name to ATLAS error taxonomy
_EXCEPTION_MAP: dict[str, str] = {
    "HikariPool": "CONNECTION_POOL_EXHAUSTED",
    "HikariCP": "CONNECTION_POOL_EXHAUSTED",
    "com.zaxxer.hikari": "CONNECTION_POOL_EXHAUSTED",
    "OutOfMemoryError": "JVM_MEMORY_CRITICAL",
    "java.lang.OutOfMemoryError": "JVM_MEMORY_CRITICAL",
    "StackOverflowError": "JVM_STACK_OVERFLOW",
    "java.lang.StackOverflowError": "JVM_STACK_OVERFLOW",
    "ConnectException": "NODE_DOWNSTREAM_REFUSED",
    "java.net.ConnectException": "NODE_DOWNSTREAM_REFUSED",
    "ECONNREFUSED": "NODE_DOWNSTREAM_REFUSED",
}

# Maximum stack trace lines to reassemble
_MAX_STACK_TRACE_LINES = 50

# Stack trace continuation line pattern
_STACK_TRACE_LINE_RE = re.compile(r"^\s+at\s+|^\s+\.\.\.\s+\d+\s+more|^Caused by:")


def parse_line(
    raw_line: str,
    client_id: str,
    service_name: str,
    source_type: str = "java-spring-boot",
) -> dict[str, Any] | None:
    """
    Parse a single Java Spring Boot log line into a normalised event dict.

    Args:
        raw_line: The raw log line string.
        client_id: Mandatory client scope.
        service_name: The service this log line came from.
        source_type: Source type tag (default: java-spring-boot).

    Returns:
        Normalised event dict ready for cmdb_enricher.py, or None if unparseable.
        Unparseable lines are returned with severity UNKNOWN and source_type java-unparseable.
    """
    if not client_id:
        raise ValueError("client_id is required in java_adapter.parse_line")

    raw_line = raw_line.rstrip("\n\r")
    match = _SPRING_BOOT_RE.match(raw_line)

    if not match:
        # Unparseable — output as-is with UNKNOWN severity, never silently drop
        logger.debug(
            "java_adapter.unparseable_line",
            client_id=client_id,
            service=service_name,
            line_preview=raw_line[:80],
        )
        return {
            "client_id": client_id,
            "source_system": service_name,
            "source_type": "java-unparseable",
            "severity": "UNKNOWN",
            "error_code": "",
            "message": raw_line,
            "raw_payload": raw_line,
            "timestamp": None,
        }

    level = match.group("level").upper()
    message = match.group("message")
    error_code = _map_error_code(message)

    return {
        "client_id": client_id,
        "source_system": service_name,
        "source_type": source_type,
        "severity": level,
        "error_code": error_code,
        "message": message,
        "raw_payload": raw_line,
        "timestamp": match.group("timestamp"),
        "thread_name": match.group("thread"),
        "logger_name": match.group("logger"),
        "pid": match.group("pid"),
    }


def reassemble_stack_trace(lines: list[str]) -> list[str]:
    """
    Reassemble multi-line stack traces into single events.
    Stack trace continuation lines are appended to the preceding log event.

    Args:
        lines: List of raw log lines.

    Returns:
        List of reassembled log entries (each entry may span multiple original lines).
    """
    reassembled: list[str] = []
    current_entry: list[str] = []
    stack_line_count = 0

    for line in lines:
        if _STACK_TRACE_LINE_RE.match(line):
            if current_entry and stack_line_count < _MAX_STACK_TRACE_LINES:
                current_entry.append(line)
                stack_line_count += 1
            # Silently drop stack trace lines beyond the maximum
        else:
            if current_entry:
                reassembled.append("\n".join(current_entry))
            current_entry = [line]
            stack_line_count = 0

    if current_entry:
        reassembled.append("\n".join(current_entry))

    return reassembled


def _map_error_code(message: str) -> str:
    """
    Map exception class names in a log message to ATLAS error taxonomy codes.
    Unknown exception classes get error_code JAVA_UNKNOWN with class name preserved.
    """
    for exception_class, atlas_code in _EXCEPTION_MAP.items():
        if exception_class in message:
            return atlas_code

    # Check for any Java exception pattern
    java_exception_re = re.search(r"([a-z][a-z0-9_]*\.)+[A-Z][A-Za-z0-9_]*Exception", message)
    if java_exception_re:
        return f"JAVA_UNKNOWN:{java_exception_re.group(0)}"

    return ""
