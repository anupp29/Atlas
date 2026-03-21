"""
SQLite audit database for ATLAS.
Manages audit_log and decision_history tables.
All records are immutable after writing — no update or delete methods exist.
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
_DEFAULT_DB_PATH = "./data/atlas_audit.db"


def _get_db_path() -> str:
    return os.environ.get(_DB_PATH_ENV, _DEFAULT_DB_PATH)


@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
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
    """Create tables if they do not exist. Idempotent."""
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

            CREATE TABLE IF NOT EXISTS decision_history (
                record_id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                service_class TEXT NOT NULL,
                recommended_action_id TEXT NOT NULL,
                confidence_score_at_decision REAL NOT NULL,
                routing_tier TEXT NOT NULL,
                human_action TEXT NOT NULL,
                modification_diff TEXT,
                rejection_reason TEXT,
                resolution_outcome TEXT NOT NULL,
                actual_mttr INTEGER NOT NULL,
                recurrence_within_48h INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_client ON audit_log(client_id);
            CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_log(incident_id);
            CREATE INDEX IF NOT EXISTS idx_decision_pattern ON decision_history(
                client_id, anomaly_type, service_class, recommended_action_id
            );
        """)
        conn.commit()
    logger.info("audit_db.initialised", path=_get_db_path())


def write_audit_record(record: dict[str, Any]) -> str:
    """
    Insert an immutable audit record.

    Args:
        record: Dict with audit_log fields. 'client_id' and 'incident_id' are required.

    Returns:
        The generated record_id.

    Raises:
        ValueError: If required fields are missing.
    """
    required = {"client_id", "incident_id", "action_type", "actor", "action_description"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"audit_record missing required fields: {missing}")

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


def write_decision_record(record: dict[str, Any]) -> str:
    """
    Insert an immutable decision history record.

    Args:
        record: Dict with decision_history fields. All required fields must be present.

    Returns:
        The generated record_id.

    Raises:
        ValueError: If required fields are missing.
    """
    required = {
        "client_id", "incident_id", "anomaly_type", "service_class",
        "recommended_action_id", "confidence_score_at_decision",
        "routing_tier", "human_action", "resolution_outcome", "actual_mttr",
    }
    missing = required - record.keys()
    if missing:
        raise ValueError(f"decision_record missing required fields: {missing}")

    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO decision_history (
                record_id, client_id, incident_id, anomaly_type, service_class,
                recommended_action_id, confidence_score_at_decision, routing_tier,
                human_action, modification_diff, rejection_reason, resolution_outcome,
                actual_mttr, recurrence_within_48h, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record["client_id"],
                record["incident_id"],
                record["anomaly_type"],
                record["service_class"],
                record["recommended_action_id"],
                record["confidence_score_at_decision"],
                record["routing_tier"],
                record["human_action"],
                json.dumps(record.get("modification_diff")) if record.get("modification_diff") else None,
                record.get("rejection_reason"),
                record["resolution_outcome"],
                record["actual_mttr"],
                int(record.get("recurrence_within_48h", False)),
                record.get("timestamp", now),
            ),
        )
        conn.commit()

    logger.info(
        "audit_db.decision_written",
        record_id=record_id,
        client_id=record["client_id"],
        outcome=record["resolution_outcome"],
    )
    return record_id


def get_records_for_pattern(
    client_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> list[dict[str, Any]]:
    """
    Query all decision history records matching a pattern/action/client triple.

    Args:
        client_id: Client scope.
        anomaly_type: e.g. 'CONNECTION_POOL_EXHAUSTED'
        service_class: e.g. 'java-spring-boot'
        action_id: Playbook ID e.g. 'connection-pool-recovery-v2'

    Returns:
        List of record dicts.
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM decision_history
            WHERE client_id = ? AND anomaly_type = ?
              AND service_class = ? AND recommended_action_id = ?
            ORDER BY timestamp DESC
            """,
            (client_id, anomaly_type, service_class, action_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]

    for row in rows:
        if row.get("modification_diff"):
            try:
                row["modification_diff"] = json.loads(row["modification_diff"])
            except (json.JSONDecodeError, TypeError):
                pass

    return rows


def get_accuracy_rate(
    client_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> tuple[float, int]:
    """
    Calculate empirical success rate for a pattern/action/client triple.

    Returns:
        Tuple of (accuracy_rate, record_count).
        Returns (0.50, 0) if no records exist.
    """
    records = get_records_for_pattern(client_id, anomaly_type, service_class, action_id)
    if not records:
        return 0.50, 0

    successes = sum(
        1 for r in records
        if r.get("resolution_outcome") == "success"
        and not r.get("recurrence_within_48h", False)
    )
    return successes / len(records), len(records)


def mark_recurrence(incident_id: str, client_id: str) -> None:
    """
    Mark the original resolution as recurrence_within_48h=True.
    Called 48 hours after resolution if the same pattern reappears.

    Args:
        incident_id: The original incident ID.
        client_id: Client scope for validation.
    """
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE decision_history
            SET recurrence_within_48h = 1
            WHERE incident_id = ? AND client_id = ?
            """,
            (incident_id, client_id),
        )
        conn.commit()
    logger.info("audit_db.recurrence_marked", incident_id=incident_id, client_id=client_id)


def query_audit(
    client_id: str,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Query audit records for a client within a date range."""
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE client_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (client_id, date_from.isoformat(), date_to.isoformat()),
        )
        return [dict(r) for r in cursor.fetchall()]


def export_as_csv(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """Export audit records as CSV. Returns the file path."""
    records = query_audit(client_id, date_from, date_to)
    path = f"./data/exports/audit_{client_id}_{date_from.date()}_{date_to.date()}.csv"
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if not records:
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    logger.info("audit_db.csv_exported", path=path, records=len(records))
    return path


def export_as_json(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """Export audit records as JSON. Returns the file path."""
    records = query_audit(client_id, date_from, date_to)
    path = f"./data/exports/audit_{client_id}_{date_from.date()}_{date_to.date()}.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    logger.info("audit_db.json_exported", path=path, records=len(records))
    return path
