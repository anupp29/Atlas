"""
Specialist agent for PostgreSQL databases.
Monitors connection count, query latency, lock waits, replication lag.
Critical patterns: FATAL connection slots, deadlock, PANIC (always P1).
Connection thresholds: 70%/85%/95% of max_connections (not standard 2σ/3σ).
Inherits from BaseAgent.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.agents.base_agent import BaseAgent, EvidencePackage
from backend.agents.detection.chronos_detector import ChronosDetector
from backend.agents.detection.conformal import ConformalPredictor
from backend.agents.detection.isolation_forest import IsolationForestDetector

logger = structlog.get_logger(__name__)

# Connection count thresholds (percentage of max_connections)
_CONN_WARNING_PCT = 0.70
_CONN_ALERT_PCT = 0.85
_CONN_CRITICAL_PCT = 0.95

# Default max_connections if not available from CMDB
_DEFAULT_MAX_CONNECTIONS = 100

# Critical PostgreSQL patterns: (regex, anomaly_type, severity, hypothesis)
_CRITICAL_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (
        re.compile(r"PANIC:", re.IGNORECASE),
        "DB_PANIC",
        "P1",
        "PostgreSQL PANIC — database server has encountered a fatal unrecoverable error. "
        "Immediate human escalation required. Database may require restart.",
    ),
    (
        re.compile(
            r"remaining connection slots are reserved|"
            r"too many connections|"
            r"SQLSTATE.*53300|"
            r"connection limit exceeded",
            re.IGNORECASE,
        ),
        "CONNECTION_POOL_EXHAUSTED",
        "P2",
        "Connection pool approaching exhaustion — likely upstream traffic spike, "
        "connection leak, or misconfigured pool size. Check HikariCP maxPoolSize "
        "and active connection count.",
    ),
    (
        re.compile(r"deadlock detected|SQLSTATE.*40P01", re.IGNORECASE),
        "DB_DEADLOCK",
        "P2",
        "Database deadlock detected — likely long-running transaction or missing index. "
        "Check pg_locks and recent query patterns.",
    ),
]

# Connection count extraction from PostgreSQL log lines
_CONN_COUNT_RE = re.compile(r"connections[:\s]+(\d+)", re.IGNORECASE)
_REPLICATION_RE = re.compile(r"replication|replica|standby", re.IGNORECASE)


class PostgresAgent(BaseAgent):
    """
    Specialist agent for PostgreSQL databases.
    Scoped to one client. Monitors all PostgreSQL services for that client.
    """

    def __init__(self, client_id: str) -> None:
        super().__init__(agent_id="postgres-agent", client_id=client_id)
        self._chronos: dict[str, ChronosDetector] = {}
        self._isolation_forest: dict[str, IsolationForestDetector] = {}
        self._conformal: dict[str, ConformalPredictor] = {}
        # Per-service connection count window
        self._conn_count_window: dict[str, list[float]] = {}
        # Per-service max_connections from CMDB enrichment
        self._max_connections: dict[str, int] = {}
        # Per-service replica flag from CMDB
        self._is_replica: dict[str, bool] = {}

    def _ensure_detectors(self, service_name: str) -> None:
        if service_name not in self._chronos:
            self._chronos[service_name] = ChronosDetector(self._client_id, service_name)
            self._isolation_forest[service_name] = IsolationForestDetector(self._client_id, service_name)
            self._conformal[service_name] = ConformalPredictor(self._client_id, service_name)
            self._conn_count_window[service_name] = []
            self._max_connections[service_name] = _DEFAULT_MAX_CONNECTIONS
            self._is_replica[service_name] = False

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    async def ingest(self, event: dict[str, Any]) -> None:
        """
        Process a normalised enriched event from a PostgreSQL service.
        max_connections comes from CMDB-enriched event — never hardcoded.
        """
        if event.get("client_id") != self._client_id:
            logger.error(
                "postgres_agent.client_id_mismatch",
                expected=self._client_id,
                received=event.get("client_id"),
            )
            return

        service_name: str = event.get("source_system", "unknown-postgres")
        self._ensure_detectors(service_name)
        self.record_event_received()

        message: str = event.get("message") or ""
        severity: str = event.get("severity") or "INFO"
        raw_payload: str = event.get("raw_payload") or message

        # Extract max_connections from CMDB enrichment if available
        cmdb_max_conn = event.get("max_connections")
        if cmdb_max_conn and isinstance(cmdb_max_conn, int):
            self._max_connections[service_name] = cmdb_max_conn

        # Detect replica from CMDB
        ci_class = event.get("ci_class") or ""
        if _REPLICATION_RE.search(ci_class):
            self._is_replica[service_name] = True

        self._add_log_sample(service_name, raw_payload)

        # Extract connection count from log line if present
        conn_match = _CONN_COUNT_RE.search(message)
        if conn_match:
            conn_count = float(conn_match.group(1))
            self._conn_count_window[service_name].append(conn_count)
            if len(self._conn_count_window[service_name]) > 60:
                self._conn_count_window[service_name] = self._conn_count_window[service_name][-60:]

        ts = event.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)
        elif not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)

        # Update baselines
        if self._conn_count_window[service_name]:
            current_conn = self._conn_count_window[service_name][-1]
            self.update_baseline("connection_count", current_conn, ts)
            self._chronos[service_name].update_baseline("connection_count", current_conn)
            self._isolation_forest[service_name].add_baseline_observation(
                self._build_observation(service_name)
            )

        # Check critical patterns immediately
        await self._check_critical_patterns(service_name, message, raw_payload, severity)

    async def analyze(self) -> EvidencePackage | None:
        """Run statistical detection across all monitored PostgreSQL services."""
        for service_name in list(self._conn_count_window.keys()):
            pkg = await self._analyze_service(service_name)
            if pkg:
                return pkg
        return None

    def get_evidence(self) -> EvidencePackage | None:
        try:
            return self._output_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    # ------------------------------------------------------------------
    # Internal detection logic
    # ------------------------------------------------------------------

    async def _check_critical_patterns(
        self,
        service_name: str,
        message: str,
        raw_payload: str,
        severity: str,
    ) -> None:
        """
        Check for critical PostgreSQL patterns.
        PANIC always produces P1 regardless of confidence score.
        """
        for pattern, anomaly_type, base_severity, hypothesis in _CRITICAL_PATTERNS:
            if pattern.search(message) or pattern.search(raw_payload):
                # PANIC is always P1 — non-negotiable
                final_severity = "P1" if anomaly_type == "DB_PANIC" else base_severity

                logger.warning(
                    "postgres_agent.critical_pattern_detected",
                    client_id=self._client_id,
                    service=service_name,
                    anomaly_type=anomaly_type,
                    severity=final_severity,
                )

                pkg = self._build_evidence_package(
                    service_name=service_name,
                    anomaly_type=anomaly_type,
                    detection_confidence=0.97 if anomaly_type == "DB_PANIC" else 0.93,
                    shap_feature_values={"error_code_pattern": 100.0},
                    conformal_interval={"lower": 0.0, "upper": 0.97, "confidence_level": 0.97},
                    baseline_mean=self._get_conn_mean(service_name),
                    baseline_stddev=self._get_conn_stddev(service_name),
                    current_value=self._get_current_conn(service_name),
                    deviation_sigma=5.0,
                    preliminary_hypothesis=hypothesis,
                    severity_classification=final_severity,
                    critical_mode=True,
                )
                if pkg:
                    await self._send_evidence(pkg)
                return

    async def _analyze_service(self, service_name: str) -> EvidencePackage | None:
        """
        Statistical detection using connection count thresholds.
        Uses 70%/85%/95% of max_connections — not standard 2σ/3σ.
        """
        window = self._conn_count_window.get(service_name, [])
        if not window:
            return None

        current_conn = window[-1]
        max_conn = self._max_connections[service_name]
        conn_pct = current_conn / max_conn

        # Determine tier based on percentage thresholds
        if conn_pct < _CONN_WARNING_PCT:
            return None

        if conn_pct >= _CONN_CRITICAL_PCT:
            severity = "P1"
            hypothesis = (
                f"Connection count at {conn_pct:.0%} of max_connections ({int(current_conn)}/{max_conn}). "
                "Critical threshold exceeded — immediate action required to prevent total connection exhaustion."
            )
        elif conn_pct >= _CONN_ALERT_PCT:
            severity = "P2"
            hypothesis = (
                f"Connection count at {conn_pct:.0%} of max_connections ({int(current_conn)}/{max_conn}). "
                "Alert threshold exceeded — likely upstream traffic spike or connection leak."
            )
        else:
            # Warning level only — no EvidencePackage
            return None

        # Bootstrap check
        if not self._can_produce_alert():
            logger.info(
                "postgres_agent.bootstrap_suppressed_alert",
                client_id=self._client_id,
                service=service_name,
                conn_pct=round(conn_pct, 3),
            )
            return None

        # Run detection ensemble
        chronos_result = await self._chronos[service_name].score(window)
        chronos_score = chronos_result.get("anomaly_probability", 0.5)

        if_result = self._isolation_forest[service_name].detect(
            self._build_observation(service_name)
        )
        raw_if_score = if_result.get("anomaly_score", 0.0)
        if_normalised = float(min(max(abs(raw_if_score) * 10, 0.0), 1.0))

        conformal_result = self._conformal[service_name].predict(chronos_score, if_normalised)

        mean, stddev = self.get_baseline_stats("connection_count")
        sigma = abs(current_conn - mean) / max(stddev, 1e-6)

        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="CONNECTION_POOL_EXHAUSTED",
            detection_confidence=max(conformal_result.combined_score, conn_pct),
            shap_feature_values=if_result.get("shap_feature_values", {"connection_count": 100.0}),
            conformal_interval={
                "lower": conformal_result.lower_bound,
                "upper": conformal_result.upper_bound,
                "confidence_level": conformal_result.confidence_level,
            },
            baseline_mean=mean,
            baseline_stddev=stddev,
            current_value=current_conn,
            deviation_sigma=sigma,
            preliminary_hypothesis=hypothesis,
            severity_classification=severity,
            critical_mode=conn_pct >= _CONN_CRITICAL_PCT,
        )
        if pkg:
            await self._send_evidence(pkg)
        return pkg

    def _build_observation(self, service_name: str) -> dict[str, float]:
        window = self._conn_count_window.get(service_name, [])
        current_conn = window[-1] if window else 0.0
        max_conn = self._max_connections.get(service_name, _DEFAULT_MAX_CONNECTIONS)
        return {
            "error_rate": current_conn / max_conn,
            "response_time_p95": 0.0,
            "resource_utilisation": current_conn / max_conn,
            "error_code_freq_0": 0.0,
            "error_code_freq_1": 0.0,
            "error_code_freq_2": 0.0,
            "error_code_freq_3": 0.0,
            "error_code_freq_4": 0.0,
        }

    def _get_conn_mean(self, service_name: str) -> float:
        mean, _ = self.get_baseline_stats("connection_count")
        return mean

    def _get_conn_stddev(self, service_name: str) -> float:
        _, stddev = self.get_baseline_stats("connection_count")
        return stddev

    def _get_current_conn(self, service_name: str) -> float:
        window = self._conn_count_window.get(service_name, [])
        return window[-1] if window else 0.0
