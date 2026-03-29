"""
Weight correction engine for ATLAS.
Applies weight corrections based on accumulated L2 modification diffs and
L3 rejection signals. Gradually adjusts ATLAS's recommendations toward what
experienced engineers actually prefer.

Three SQLite tables:
  parameter_diffs    — raw diffs from every L2 Modify action
  parameter_defaults — adjusted defaults after 3 same-direction diffs
  hypothesis_weights — per-client adjustments to hypothesis type weights

Adjustment bounds: no parameter default can be moved more than ±50% from
the playbook default through automatic adjustment. Beyond that, a human
review is flagged.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import structlog

from backend.database.audit_db import write_audit_record

logger = structlog.get_logger(__name__)

_DB_PATH_ENV = "ATLAS_DECISION_DB_PATH"
_MAX_ADJUSTMENT_FACTOR = 0.50   # ±50% of playbook default — hard ceiling
_DIFF_THRESHOLD = 3             # diffs in same direction before adjusting default


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
    Create weight correction tables if they do not exist. Idempotent.
    Called once on application startup.
    """
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS parameter_diffs (
                diff_id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                parameter_name TEXT NOT NULL,
                playbook_default REAL NOT NULL,
                engineer_value REAL NOT NULL,
                direction TEXT NOT NULL,
                magnitude REAL NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS parameter_defaults (
                default_id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                parameter_name TEXT NOT NULL,
                adjusted_value REAL NOT NULL,
                playbook_default REAL NOT NULL,
                diff_count INTEGER NOT NULL,
                human_review_flagged INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL,
                UNIQUE(client_id, action_id, parameter_name)
            );

            CREATE TABLE IF NOT EXISTS hypothesis_weights (
                weight_id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                hypothesis_type TEXT NOT NULL,
                weight_adjustment REAL NOT NULL DEFAULT 0.0,
                rejection_count INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL,
                UNIQUE(client_id, hypothesis_type)
            );

            CREATE INDEX IF NOT EXISTS idx_pd_pattern
                ON parameter_diffs(client_id, action_id, parameter_name);
            CREATE INDEX IF NOT EXISTS idx_pd_client
                ON parameter_defaults(client_id, action_id);
        """)
        conn.commit()
    logger.info("weight_correction.initialised", path=_get_db_path())


def record_modification_diff(
    client_id: str,
    incident_id: str,
    action_id: str,
    modification_diff: dict[str, Any],
    playbook_defaults: dict[str, Any],
) -> None:
    """
    Store parameter diffs from an L2 Modify action.
    After accumulating 3 same-direction diffs, compute and store an adjusted default.

    Args:
        client_id:         Client scope — mandatory.
        incident_id:       The incident where the modification occurred.
        action_id:         Playbook ID that was modified.
        modification_diff: Dict of {parameter_name: new_value} from the L2 engineer.
        playbook_defaults: Dict of {parameter_name: default_value} from the playbook library.
    """
    if not client_id:
        raise ValueError("client_id is required for record_modification_diff.")

    now = datetime.now(timezone.utc).isoformat()

    for param_name, new_value in modification_diff.items():
        default_value = playbook_defaults.get(param_name)
        if default_value is None:
            logger.warning(
                "weight_correction.unknown_parameter",
                client_id=client_id,
                action_id=action_id,
                parameter=param_name,
            )
            continue

        try:
            new_val_float = float(new_value)
            default_float = float(default_value)
        except (TypeError, ValueError):
            logger.warning(
                "weight_correction.non_numeric_parameter",
                client_id=client_id,
                action_id=action_id,
                parameter=param_name,
                value=new_value,
            )
            continue

        direction = "up" if new_val_float > default_float else "down"
        magnitude = abs(new_val_float - default_float)

        diff_id = str(uuid.uuid4())
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO parameter_diffs (
                    diff_id, client_id, incident_id, action_id, parameter_name,
                    playbook_default, engineer_value, direction, magnitude, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    diff_id, client_id, incident_id, action_id, param_name,
                    default_float, new_val_float, direction, magnitude, now,
                ),
            )
            conn.commit()

        logger.info(
            "weight_correction.diff_recorded",
            client_id=client_id,
            action_id=action_id,
            parameter=param_name,
            direction=direction,
            magnitude=round(magnitude, 4),
        )

        # Check if we have enough same-direction diffs to adjust the default
        _maybe_update_adjusted_default(
            client_id=client_id,
            action_id=action_id,
            param_name=param_name,
            default_float=default_float,
            incident_id=incident_id,
        )


def record_rejection(
    client_id: str,
    incident_id: str,
    action_id: str,
    rejection_reason: str,
) -> None:
    """
    Parse a rejection reason and update hypothesis weights.
    Best-effort — if the reason cannot be meaningfully parsed, the record
    is stored but no weight adjustment is made.

    Args:
        client_id:        Client scope — mandatory.
        incident_id:      The incident that was rejected.
        action_id:        The playbook that was rejected.
        rejection_reason: Free-text reason from the L2/L3 engineer.
    """
    if not client_id:
        raise ValueError("client_id is required for record_rejection.")

    hypothesis_type = _extract_hypothesis_type(rejection_reason)
    if hypothesis_type is None:
        logger.info(
            "weight_correction.rejection_unparseable",
            client_id=client_id,
            incident_id=incident_id,
            action_id=action_id,
            reason_preview=rejection_reason[:100],
        )
        return

    now = datetime.now(timezone.utc).isoformat()

    with _get_connection() as conn:
        # Upsert hypothesis weight record
        conn.execute(
            """
            INSERT INTO hypothesis_weights (
                weight_id, client_id, hypothesis_type, weight_adjustment,
                rejection_count, last_updated
            ) VALUES (?, ?, ?, -0.05, 1, ?)
            ON CONFLICT(client_id, hypothesis_type) DO UPDATE SET
                weight_adjustment = MAX(weight_adjustment - 0.05, -0.50),
                rejection_count = rejection_count + 1,
                last_updated = excluded.last_updated
            """,
            (str(uuid.uuid4()), client_id, hypothesis_type, now),
        )
        conn.commit()

    logger.info(
        "weight_correction.hypothesis_weight_updated",
        client_id=client_id,
        incident_id=incident_id,
        hypothesis_type=hypothesis_type,
        adjustment=-0.05,
    )

    write_audit_record({
        "client_id": client_id,
        "incident_id": incident_id,
        "action_type": "classification",
        "actor": "ATLAS_AUTO",
        "action_description": (
            f"Hypothesis weight adjusted for type '{hypothesis_type}' on client '{client_id}'. "
            f"Rejection reason: {rejection_reason[:200]}"
        ),
        "confidence_score_at_time": 0.0,
        "outcome": "weight_adjusted",
        "servicenow_ticket_id": "",
        "rollback_available": False,
        "compliance_frameworks_applied": [],
        "reasoning_summary": f"Weight correction triggered by L2/L3 rejection of {action_id}.",
    })


def get_adjusted_default(
    client_id: str,
    action_id: str,
    parameter_name: str,
) -> float | None:
    """
    Return the adjusted default for a parameter, or None if no adjustment exists.
    Called by n5_reasoning.py before assembling the reasoning prompt.

    Args:
        client_id:      Client scope — mandatory.
        action_id:      Playbook ID.
        parameter_name: Parameter to look up.

    Returns:
        Adjusted float value, or None if no adjustment (use playbook default).
    """
    if not client_id:
        raise ValueError("client_id is required for get_adjusted_default.")

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT adjusted_value FROM parameter_defaults
            WHERE client_id = ? AND action_id = ? AND parameter_name = ?
            """,
            (client_id, action_id, parameter_name),
        )
        row = cursor.fetchone()

    if row is None:
        return None
    return float(row["adjusted_value"])


def get_hypothesis_weights(client_id: str) -> dict[str, float]:
    """
    Return all hypothesis weight adjustments for a client.
    Called by n5_reasoning.py to weight hypothesis scoring.

    Args:
        client_id: Client scope — mandatory.

    Returns:
        Dict of {hypothesis_type: weight_adjustment}.
        Empty dict if no adjustments exist.
    """
    if not client_id:
        raise ValueError("client_id is required for get_hypothesis_weights.")

    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT hypothesis_type, weight_adjustment FROM hypothesis_weights WHERE client_id = ?",
            (client_id,),
        )
        return {row["hypothesis_type"]: float(row["weight_adjustment"]) for row in cursor.fetchall()}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_update_adjusted_default(
    client_id: str,
    action_id: str,
    param_name: str,
    default_float: float,
    incident_id: str,
) -> None:
    """
    Check if there are enough same-direction diffs to compute an adjusted default.
    If so, compute the adjusted value (bounded at ±50%) and upsert into parameter_defaults.
    """
    with _get_connection() as conn:
        # Read and write in a single connection so both operations are atomic.
        # A crash between a separate read-conn and write-conn would leave diffs
        # recorded but the default never updated (or vice versa).
        cursor = conn.execute(
            """
            SELECT direction, engineer_value
            FROM parameter_diffs
            WHERE client_id = ? AND action_id = ? AND parameter_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (client_id, action_id, param_name, _DIFF_THRESHOLD),
        )
        recent_diffs = cursor.fetchall()

        if len(recent_diffs) < _DIFF_THRESHOLD:
            return

        # Check if all recent diffs are in the same direction
        directions = [d["direction"] for d in recent_diffs]
        if len(set(directions)) != 1:
            return  # Mixed directions — no adjustment

        direction = directions[0]
        values = [float(d["engineer_value"]) for d in recent_diffs]
        adjusted_value = sum(values) / len(values)  # Mean of engineer-preferred values

        # Enforce ±50% bound from playbook default
        if default_float != 0:
            max_allowed = default_float * (1 + _MAX_ADJUSTMENT_FACTOR)
            min_allowed = default_float * (1 - _MAX_ADJUSTMENT_FACTOR)
        else:
            max_allowed = _MAX_ADJUSTMENT_FACTOR
            min_allowed = -_MAX_ADJUSTMENT_FACTOR

        human_review_flagged = False
        if adjusted_value > max_allowed:
            adjusted_value = max_allowed
            human_review_flagged = True
        elif adjusted_value < min_allowed:
            adjusted_value = min_allowed
            human_review_flagged = True

        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO parameter_defaults (
                default_id, client_id, action_id, parameter_name,
                adjusted_value, playbook_default, diff_count,
                human_review_flagged, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_id, action_id, parameter_name) DO UPDATE SET
                adjusted_value = excluded.adjusted_value,
                diff_count = excluded.diff_count,
                human_review_flagged = excluded.human_review_flagged,
                last_updated = excluded.last_updated
            """,
            (
                str(uuid.uuid4()), client_id, action_id, param_name,
                adjusted_value, default_float, len(recent_diffs),
                int(human_review_flagged), now,
            ),
        )
        conn.commit()

    logger.info(
        "weight_correction.default_adjusted",
        client_id=client_id,
        action_id=action_id,
        parameter=param_name,
        direction=direction,
        adjusted_value=round(adjusted_value, 4),
        playbook_default=default_float,
        human_review_flagged=human_review_flagged,
    )

    if human_review_flagged:
        write_audit_record({
            "client_id": client_id,
            "incident_id": incident_id,
            "action_type": "classification",
            "actor": "ATLAS_AUTO",
            "action_description": (
                f"Parameter '{param_name}' for action '{action_id}' on client '{client_id}' "
                f"has reached the ±50% adjustment ceiling. "
                f"Adjusted value: {adjusted_value:.4f} (playbook default: {default_float:.4f}). "
                "Human review required before further automatic adjustment."
            ),
            "confidence_score_at_time": 0.0,
            "outcome": "human_review_required",
            "servicenow_ticket_id": "",
            "rollback_available": False,
            "compliance_frameworks_applied": [],
            "reasoning_summary": "Weight correction ceiling reached — human review flagged.",
        })


# Keyword mapping for hypothesis type extraction from rejection reasons
_HYPOTHESIS_KEYWORDS: dict[str, list[str]] = {
    "connection_pool_exhaustion": [
        "connection pool", "hikari", "pool size", "max pool", "connection leak",
    ],
    "memory_exhaustion": [
        "memory", "heap", "oom", "out of memory", "maxmemory", "eviction",
    ],
    "deadlock": ["deadlock", "lock contention", "lock wait", "transaction"],
    "downstream_failure": [
        "downstream", "dependency", "econnrefused", "connection refused", "upstream",
    ],
    "deployment_regression": [
        "deployment", "change", "release", "rollback", "regression", "config change",
    ],
    "traffic_spike": ["traffic", "load", "spike", "surge", "throughput", "requests"],
}


def _extract_hypothesis_type(reason: str) -> str | None:
    """
    Best-effort extraction of hypothesis type from a rejection reason string.
    Returns None if no recognisable hypothesis type is found.
    """
    reason_lower = reason.lower()
    for hypothesis_type, keywords in _HYPOTHESIS_KEYWORDS.items():
        if any(kw in reason_lower for kw in keywords):
            return hypothesis_type
    return None
