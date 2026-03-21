"""
SQLite audit database for ATLAS.
Manages the audit_log table only — the compliance and operational audit trail.

Decision history (learning engine memory) is managed exclusively by
backend/learning/decision_history.py in its own database.

All audit records are immutable after writing — no update or delete methods exist.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import structlog

logger = structlog.get_logger(__name__)

_DB_PATH_ENV = "ATLAS_AUDIT_DB_PATH"


def _get_db_path() -> str:
    """
    Resolve the audit database path from environment variables.
    Raises RuntimeError if the variable is not set — no hardcoded defaults.
    """
    path = os.environ.get(_DB_PATH_ENV)
    if not path:
        raise RuntimeError(
            f"Environment variable '{_DB_PATH_ENV}' is not set. "
            "ATLAS cannot start without an audit database path."
        )
    return path


@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Open a WAL-mode SQLite connection with row factory."""
    path = _get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def initialise_db() -> None:
    """
    Create the audit_log table if it does not exist. Idempotent.
    Called once on application startup.
    """
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_log (
                record_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                action_description TEXT NOT NULL,
                confidence_score_at_time REAL,
                reasoning_summary TEXT,
                outcome TEXT,
                servicenow_ticket_id TEXT,
                rollback_available INTEGER DEFAULT 0,
                compliance_frameworks_applied TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_client ON audit_log(client_id);
            CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_log(incident_id);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
        """)
        conn.commit()
    logger.info("audit_db.initialised", path=_get_db_path())


def write_audit_record(record: dict[str, Any]) -> str:
    """
    Insert an immutable audit record into the audit_log table.

    Args:
        record: Dict with audit_log fields. 'client_id', 'incident_id',
                'action_type', 'actor', and 'action_description' are required.

    Returns:
        The generated record_id UUID.

    Raises:
        ValueError: If required fields are missing or client_id is empty.
    """
    required = {"client_id", "incident_id", "action_type", "actor", "action_description"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"audit_record missing required fields: {missing}")

    if not record["client_id"]:
        raise ValueError("client_id cannot be empty — multi-tenancy enforcement.")

    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                record_id, incident_id, client_id, timestamp, action_type, actor,
                action_description, confidence_score_at_time, reasoning_summary,
                outcome, servicenow_ticket_id, rollback_available,
                compliance_frameworks_applied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record["incident_id"],
                record["client_id"],
                record.get("timestamp", now),
                record["action_type"],
                record["actor"],
                record["action_description"],
                record.get("confidence_score_at_time"),
                record.get("reasoning_summary"),
                record.get("outcome"),
                record.get("servicenow_ticket_id"),
                int(record.get("rollback_available", False)),
                json.dumps(record.get("compliance_frameworks_applied", [])),
            ),
        )
        conn.commit()

    logger.info(
        "audit_db.record_written",
        record_id=record_id,
        client_id=record["client_id"],
        action_type=record["action_type"],
    )
    return record_id


def query_audit(
    client_id: str,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """
    Query audit records for a client within a date range.

    Args:
        client_id:  Client scope — mandatory.
        date_from:  Start of date range (inclusive).
        date_to:    End of date range (inclusive).

    Returns:
        List of audit record dicts ordered by timestamp ascending.
    """
    if not client_id:
        raise ValueError("client_id is required for query_audit.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE client_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (client_id, date_from.isoformat(), date_to.isoformat()),
        )
        rows = [dict(r) for r in cursor.fetchall()]

    for row in rows:
        if row.get("compliance_frameworks_applied"):
            try:
                row["compliance_frameworks_applied"] = json.loads(
                    row["compliance_frameworks_applied"]
                )
            except (json.JSONDecodeError, TypeError):
                pass

    return rows


def export_as_csv(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """
    Export audit records as CSV.

    Args:
        client_id:  Client scope — mandatory.
        date_from:  Start of date range.
        date_to:    End of date range.

    Returns:
        File path of the exported CSV.
    """
    records = query_audit(client_id, date_from, date_to)
    path = f"./data/exports/audit_{client_id}_{date_from.date()}_{date_to.date()}.csv"
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if not records:
        logger.info("audit_db.csv_exported_empty", path=path, client_id=client_id)
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    logger.info("audit_db.csv_exported", path=path, records=len(records), client_id=client_id)
    return path


def export_as_json(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """
    Export audit records as JSON.

    Args:
        client_id:  Client scope — mandatory.
        date_from:  Start of date range.
        date_to:    End of date range.

    Returns:
        File path of the exported JSON.
    """
    records = query_audit(client_id, date_from, date_to)
    path = f"./data/exports/audit_{client_id}_{date_from.date()}_{date_to.date()}.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    logger.info("audit_db.json_exported", path=path, records=len(records), client_id=client_id)
    return path


def get_sla_uptime_percent(client_id: str) -> float:
    """
    Calculate SLA uptime percentage for a client from the audit log.
    Uptime = 1 - (breach events / total resolution events).
    Returns 100.0 if no resolution events exist yet (new client).

    Args:
        client_id: Client scope — mandatory.

    Returns:
        Float 0.0–100.0 representing SLA uptime percentage.
    """
    if not client_id:
        raise ValueError("client_id is required for get_sla_uptime_percent.")

    with _get_connection() as conn:
        total_cursor = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM audit_log
            WHERE client_id = ? AND action_type = 'resolution'
            """,
            (client_id,),
        )
        total = total_cursor.fetchone()["cnt"]

        if total == 0:
            return 100.0

        breach_cursor = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM audit_log
            WHERE client_id = ? AND action_type = 'resolution'
            AND outcome LIKE '%sla_breach%'
            """,
            (client_id,),
        )
        breaches = breach_cursor.fetchone()["cnt"]

    uptime = max(0.0, min(100.0, (1.0 - breaches / total) * 100.0))
    logger.info(
        "audit_db.sla_uptime_calculated",
        client_id=client_id,
        total_resolutions=total,
        breaches=breaches,
        uptime_percent=round(uptime, 4),
    )
    return round(uptime, 4)
