"""
Decision history database for the ATLAS learning engine.
Stores every human and automated decision made in ATLAS.
This is the memory that makes the confidence engine smarter over time.

Separate from audit_db.py:
  - audit_db.py  = compliance audit log (immutable, regulatory, append-only)
  - decision_history.py = learning memory (pattern matching, accuracy rates, recalibration)

All records are immutable after writing — no update or delete methods exist.
Corrections are made by writing a new record referencing the original.
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

_DB_PATH_ENV = "ATLAS_DECISION_DB_PATH"


def _get_db_path() -> str:
    path = os.environ.get(_DB_PATH_ENV)
    if not path:
        raise RuntimeError(
            f"Environment variable '{_DB_PATH_ENV}' is not set. "
            "ATLAS cannot start without a decision history database path."
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
    Create the decision_history table if it does not exist. Idempotent.
    Called once on application startup.
    """
    with _get_connection() as conn:
        conn.executescript("""
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
                recurrence_within_48h INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_dh_client
                ON decision_history(client_id);
            CREATE INDEX IF NOT EXISTS idx_dh_pattern
                ON decision_history(client_id, anomaly_type, service_class, recommended_action_id);
            CREATE INDEX IF NOT EXISTS idx_dh_incident
                ON decision_history(incident_id);
            CREATE INDEX IF NOT EXISTS idx_dh_timestamp
                ON decision_history(timestamp);
        """)
        conn.commit()
    logger.info("decision_history.initialised", path=_get_db_path())


def write_record(record: dict[str, Any]) -> str:
    """
    Insert an immutable decision history record.

    Required fields: client_id, incident_id, anomaly_type, service_class,
    recommended_action_id, confidence_score_at_decision, routing_tier,
    human_action, resolution_outcome, actual_mttr.

    Args:
        record: Dict matching the DecisionRecord data contract.

    Returns:
        The generated record_id UUID.

    Raises:
        ValueError: If any required field is missing.
    """
    required = {
        "client_id", "incident_id", "anomaly_type", "service_class",
        "recommended_action_id", "confidence_score_at_decision",
        "routing_tier", "human_action", "resolution_outcome", "actual_mttr",
    }
    missing = required - record.keys()
    if missing:
        raise ValueError(f"decision_record missing required fields: {missing}")

    if not record["client_id"]:
        raise ValueError("client_id cannot be empty — multi-tenancy enforcement.")

    _validate_routing_tier(record["routing_tier"])
    _validate_human_action(record["human_action"])
    _validate_resolution_outcome(record["resolution_outcome"])

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
                float(record["confidence_score_at_decision"]),
                record["routing_tier"],
                record["human_action"],
                json.dumps(record["modification_diff"]) if record.get("modification_diff") else None,
                record.get("rejection_reason"),
                record["resolution_outcome"],
                int(record["actual_mttr"]),
                int(record.get("recurrence_within_48h", False)),
                record.get("timestamp", now),
            ),
        )
        conn.commit()

    logger.info(
        "decision_history.record_written",
        record_id=record_id,
        client_id=record["client_id"],
        anomaly_type=record["anomaly_type"],
        outcome=record["resolution_outcome"],
        routing_tier=record["routing_tier"],
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
    Used by recalibration.py and n6_confidence.py for accuracy scoring.

    Args:
        client_id:    Client scope — mandatory, enforced.
        anomaly_type: e.g. 'CONNECTION_POOL_EXHAUSTED'
        service_class: e.g. 'java-spring-boot'
        action_id:    Playbook ID e.g. 'connection-pool-recovery-v2'

    Returns:
        List of record dicts, ordered by timestamp descending (most recent first).
    """
    if not client_id:
        raise ValueError("client_id is required for get_records_for_pattern.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM decision_history
            WHERE client_id = ?
              AND anomaly_type = ?
              AND service_class = ?
              AND recommended_action_id = ?
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
        row["recurrence_within_48h"] = bool(row.get("recurrence_within_48h", 0))

    return rows


def get_accuracy_rate(
    client_id: str,
    anomaly_type: str,
    service_class: str,
    action_id: str,
) -> tuple[float, int]:
    """
    Calculate empirical success rate for a pattern/action/client triple.

    A resolution is counted as successful only if:
      - resolution_outcome == 'success'
      - recurrence_within_48h == False

    Returns:
        Tuple of (accuracy_rate, record_count).
        Returns (0.50, 0) if no records exist — neutral prior, triggers cold-start veto.
    """
    if not client_id:
        raise ValueError("client_id is required for get_accuracy_rate.")

    records = get_records_for_pattern(client_id, anomaly_type, service_class, action_id)
    if not records:
        return 0.50, 0

    # Identify incident_ids that have a recurrence correction record.
    # A correction record's rejection_reason starts with "recurrence_correction_for_record_".
    # The original record for those incidents must NOT count as a success — the fix did not hold.
    recurred_incident_ids: set[str] = {
        r["incident_id"]
        for r in records
        if isinstance(r.get("rejection_reason"), str)
        and r["rejection_reason"].startswith("recurrence_correction_for_record_")
    }

    # Exclude correction records themselves from the count — they are metadata, not decisions.
    decision_records = [
        r for r in records
        if not (
            isinstance(r.get("rejection_reason"), str)
            and r["rejection_reason"].startswith("recurrence_correction_for_record_")
        )
    ]

    if not decision_records:
        return 0.50, 0

    successes = sum(
        1 for r in decision_records
        if r.get("resolution_outcome") == "success"
        and not r.get("recurrence_within_48h", False)
        and r["incident_id"] not in recurred_incident_ids
    )
    rate = successes / len(decision_records)
    logger.debug(
        "decision_history.accuracy_rate_calculated",
        client_id=client_id,
        anomaly_type=anomaly_type,
        service_class=service_class,
        action_id=action_id,
        rate=round(rate, 4),
        record_count=len(decision_records),
        successes=successes,
    )
    return rate, len(decision_records)


def mark_recurrence(incident_id: str, client_id: str) -> None:
    """
    Record that the original resolution recurred within 48 hours.
    Called 48 hours after resolution if the same pattern reappears.

    IMMUTABILITY CONTRACT: The original record is never mutated.
    Instead, a correction record is inserted with human_action='escalated',
    resolution_outcome='failure', and recurrence_within_48h=True.
    This preserves the full audit trail while correctly penalising the
    original resolution in accuracy scoring.

    Args:
        incident_id: The original incident ID.
        client_id:   Client scope for validation — prevents cross-client mutation.
    """
    if not client_id:
        raise ValueError("client_id is required for mark_recurrence.")

    # Fetch the original record to copy its pattern fields
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM decision_history
            WHERE incident_id = ? AND client_id = ?
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (incident_id, client_id),
        )
        original = cursor.fetchone()

    if original is None:
        logger.warning(
            "decision_history.recurrence_original_not_found",
            incident_id=incident_id,
            client_id=client_id,
        )
        return

    original = dict(original)
    correction_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Insert a correction record — original is untouched
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
                correction_id,
                client_id,
                incident_id,
                original["anomaly_type"],
                original["service_class"],
                original["recommended_action_id"],
                original["confidence_score_at_decision"],
                original["routing_tier"],
                "escalated",   # correction action
                None,
                f"recurrence_correction_for_record_{original['record_id']}",
                "failure",     # recurrence = the fix did not hold
                original["actual_mttr"],
                1,             # recurrence_within_48h = True
                now,
            ),
        )
        conn.commit()

    logger.info(
        "decision_history.recurrence_correction_inserted",
        original_incident_id=incident_id,
        correction_record_id=correction_id,
        client_id=client_id,
    )


def get_all_patterns_for_client(client_id: str) -> list[dict[str, Any]]:
    """
    Return all distinct (anomaly_type, service_class, recommended_action_id) triples
    for a client, with their record counts.
    Used by recalibration.py on startup to rebuild the full accuracy cache.

    Args:
        client_id: Client scope — mandatory.

    Returns:
        List of dicts with keys: anomaly_type, service_class, recommended_action_id, count.
    """
    if not client_id:
        raise ValueError("client_id is required for get_all_patterns_for_client.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT anomaly_type, service_class, recommended_action_id, COUNT(*) as count
            FROM decision_history
            WHERE client_id = ?
            GROUP BY anomaly_type, service_class, recommended_action_id
            """,
            (client_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_incident_count_for_client(client_id: str) -> int:
    """
    Return the total number of processed incidents for a client.
    Used by trust_progression.py for stage gate evaluation.
    """
    if not client_id:
        raise ValueError("client_id is required for get_incident_count_for_client.")

    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(DISTINCT incident_id) FROM decision_history WHERE client_id = ?",
            (client_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def get_auto_resolution_rate(client_id: str) -> tuple[float, int]:
    """
    Calculate the auto-resolution success rate for a client.
    Used by trust_progression.py for Stage 2 criteria check.

    Auto-resolution = routing_tier == 'auto' AND resolution_outcome == 'success'
    AND recurrence_within_48h == False.

    Returns:
        Tuple of (rate, total_auto_routed_count).
    """
    if not client_id:
        raise ValueError("client_id is required for get_auto_resolution_rate.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN resolution_outcome = 'success'
                         AND recurrence_within_48h = 0 THEN 1 ELSE 0 END) as successes
            FROM decision_history
            WHERE client_id = ? AND routing_tier = 'auto'
            """,
            (client_id,),
        )
        row = cursor.fetchone()

    total = int(row["total"]) if row else 0
    successes = int(row["successes"] or 0) if row else 0
    rate = successes / total if total > 0 else 0.0
    return rate, total


def export_as_json(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """
    Export decision history records for a client and date range as JSON.
    Used for compliance audit exports.

    Returns:
        Absolute file path of the exported JSON file.
    """
    if not client_id:
        raise ValueError("client_id is required for export_as_json.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM decision_history
            WHERE client_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (client_id, date_from.isoformat(), date_to.isoformat()),
        )
        records = [dict(r) for r in cursor.fetchall()]

    for row in records:
        if row.get("modification_diff"):
            try:
                row["modification_diff"] = json.loads(row["modification_diff"])
            except (json.JSONDecodeError, TypeError):
                pass
        row["recurrence_within_48h"] = bool(row.get("recurrence_within_48h", 0))

    path = f"./data/exports/decisions_{client_id}_{date_from.date()}_{date_to.date()}.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    logger.info("decision_history.json_exported", path=path, records=len(records))
    return path


def export_as_csv(client_id: str, date_from: datetime, date_to: datetime) -> str:
    """
    Export decision history records for a client and date range as CSV.

    Returns:
        Absolute file path of the exported CSV file.
    """
    if not client_id:
        raise ValueError("client_id is required for export_as_csv.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM decision_history
            WHERE client_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (client_id, date_from.isoformat(), date_to.isoformat()),
        )
        records = [dict(r) for r in cursor.fetchall()]

    path = f"./data/exports/decisions_{client_id}_{date_from.date()}_{date_to.date()}.csv"
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if records:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)

    logger.info("decision_history.csv_exported", path=path, records=len(records))
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_ROUTING_TIERS = frozenset({"L1", "L2", "L3", "auto"})
_VALID_HUMAN_ACTIONS = frozenset({"approved", "modified", "rejected", "escalated"})
_VALID_RESOLUTION_OUTCOMES = frozenset({"success", "failure", "partial"})


def _validate_routing_tier(value: str) -> None:
    if value not in _VALID_ROUTING_TIERS:
        raise ValueError(
            f"Invalid routing_tier '{value}'. Must be one of: {_VALID_ROUTING_TIERS}"
        )


def _validate_human_action(value: str) -> None:
    if value not in _VALID_HUMAN_ACTIONS:
        raise ValueError(
            f"Invalid human_action '{value}'. Must be one of: {_VALID_HUMAN_ACTIONS}"
        )


def _validate_resolution_outcome(value: str) -> None:
    if value not in _VALID_RESOLUTION_OUTCOMES:
        raise ValueError(
            f"Invalid resolution_outcome '{value}'. Must be one of: {_VALID_RESOLUTION_OUTCOMES}"
        )
