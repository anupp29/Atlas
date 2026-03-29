"""
Specialist agent for Redis cache instances.
Monitors memory usage, eviction rate, rejected commands, connected clients.
Critical patterns: OOM, MISCONF, any rejected commands.
Alert threshold: 85% memory (not 3σ — Redis memory is bounded).
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

# Memory alert threshold: 85% (not 3σ — Redis memory is bounded)
_MEMORY_ALERT_PCT = 0.85
_MEMORY_WARNING_PCT = 0.70

# Critical patterns: (regex, anomaly_type, severity, hypothesis)
_CRITICAL_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (
        re.compile(
            r"OOM command not allowed|"
            r"used memory > maxmemory|"
            r"maxmemory.*exceeded|"
            r"ERR.*OOM",
            re.IGNORECASE,
        ),
        "REDIS_OOM",
        "P2",
        "Redis memory exhaustion — maxmemory policy may have changed or memory growth "
        "is exceeding capacity. Check maxmemory-policy configuration and memory usage trend.",
    ),
    (
        re.compile(
            r"MISCONF Redis is configured to save RDB|"
            r"MISCONF.*RDB",
            re.IGNORECASE,
        ),
        "REDIS_OOM",
        "P2",
        "Redis RDB snapshot configuration error — disk may be full or permissions issue. "
        "Check Redis persistence configuration.",
    ),
    (
        re.compile(
            r"REJECTED|"
            r"command not allowed|"
            r"ERR.*LOADING|"
            r"BUSY Redis is busy",
            re.IGNORECASE,
        ),
        "REDIS_COMMAND_REJECTED",
        "P2",
        "Redis commands being rejected — possible memory pressure or server overload. "
        "Check memory usage and connected client count.",
    ),
]

# Memory percentage extraction
_MEMORY_PCT_RE = re.compile(r"memory[_\s]?(?:usage|used)[:\s]+([\d.]+)%", re.IGNORECASE)
_EVICTION_RE = re.compile(r"evict(?:ed|ing)[:\s]+([\d]+)", re.IGNORECASE)


class RedisAgent(BaseAgent):
    """
    Specialist agent for Redis cache instances.
    Scoped to one client. Monitors all Redis services for that client.
    """

    def __init__(self, client_id: str) -> None:
        super().__init__(agent_id="redis-agent", client_id=client_id)
        self._chronos: dict[str, ChronosDetector] = {}
        self._isolation_forest: dict[str, IsolationForestDetector] = {}
        self._conformal: dict[str, ConformalPredictor] = {}
        # Per-service memory percentage window
        self._memory_pct_window: dict[str, list[float]] = {}
        # Per-service eviction rate window
        self._eviction_window: dict[str, list[float]] = {}

    def _ensure_detectors(self, service_name: str) -> None:
        if service_name not in self._chronos:
            self._chronos[service_name] = ChronosDetector(self._client_id, service_name)
            self._isolation_forest[service_name] = IsolationForestDetector(self._client_id, service_name)
            self._conformal[service_name] = ConformalPredictor(self._client_id, service_name)
            self._memory_pct_window[service_name] = []
            self._eviction_window[service_name] = []

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    async def ingest(self, event: dict[str, Any]) -> None:
        """Process a normalised enriched event from a Redis service."""
        if event.get("client_id") != self._client_id:
            logger.error(
                "redis_agent.client_id_mismatch",
                expected=self._client_id,
                received=event.get("client_id"),
            )
            return

        service_name: str = event.get("source_system", "unknown-redis")
        self._ensure_detectors(service_name)
        self.record_event_received()

        message: str = event.get("message") or ""
        raw_payload: str = event.get("raw_payload") or message

        self._add_log_sample(service_name, raw_payload)

        ts = event.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)
        elif not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)

        # Extract memory percentage if present
        mem_match = _MEMORY_PCT_RE.search(message)
        if mem_match:
            mem_pct = float(mem_match.group(1)) / 100.0
            self._memory_pct_window[service_name].append(mem_pct)
            if len(self._memory_pct_window[service_name]) > 60:
                self._memory_pct_window[service_name] = self._memory_pct_window[service_name][-60:]
            self.update_baseline("memory_pct", mem_pct, ts)
            self._chronos[service_name].update_baseline("memory_pct", mem_pct)

        # Extract eviction count if present
        evict_match = _EVICTION_RE.search(message)
        if evict_match:
            eviction_count = float(evict_match.group(1))
            self._eviction_window[service_name].append(eviction_count)
            if len(self._eviction_window[service_name]) > 60:
                self._eviction_window[service_name] = self._eviction_window[service_name][-60:]

        self._isolation_forest[service_name].add_baseline_observation(
            self._build_observation(service_name)
        )

        # Check critical patterns — any rejected command is minimum Warning
        await self._check_critical_patterns(service_name, message, raw_payload)

    async def analyze(self) -> EvidencePackage | None:
        """Run statistical detection across all monitored Redis services."""
        for service_name in list(self._memory_pct_window.keys()):
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
    ) -> None:
        """
        Check for critical Redis patterns.
        Any rejected command triggers at minimum a Warning — zero tolerance.
        """
        for pattern, anomaly_type, severity, hypothesis in _CRITICAL_PATTERNS:
            if pattern.search(message) or pattern.search(raw_payload):
                logger.warning(
                    "redis_agent.critical_pattern_detected",
                    client_id=self._client_id,
                    service=service_name,
                    anomaly_type=anomaly_type,
                )

                current_mem = (
                    self._memory_pct_window[service_name][-1]
                    if self._memory_pct_window[service_name]
                    else 0.0
                )

                pkg = self._build_evidence_package(
                    service_name=service_name,
                    anomaly_type=anomaly_type,
                    detection_confidence=0.93,
                    shap_feature_values={"error_code_pattern": 100.0},
                    conformal_interval={"lower": 0.0, "upper": 0.93, "confidence_level": 0.93},
                    baseline_mean=self._get_mem_mean(service_name),
                    baseline_stddev=self._get_mem_stddev(service_name),
                    current_value=current_mem,
                    deviation_sigma=5.0,
                    preliminary_hypothesis=hypothesis,
                    severity_classification=severity,
                    critical_mode=True,
                )
                if pkg:
                    await self._send_evidence(pkg)
                return

    async def _analyze_service(self, service_name: str) -> EvidencePackage | None:
        """
        Statistical detection using memory percentage threshold.
        Alert at 85% — not 3σ because Redis memory is bounded.
        """
        window = self._memory_pct_window.get(service_name, [])
        if not window:
            return None

        current_mem = window[-1]

        if current_mem < _MEMORY_WARNING_PCT:
            return None

        if current_mem < _MEMORY_ALERT_PCT:
            # Warning level only — no EvidencePackage
            return None

        # Alert level: 85%+ memory
        if not self._can_produce_alert():
            logger.info(
                "redis_agent.bootstrap_suppressed_alert",
                client_id=self._client_id,
                service=service_name,
                memory_pct=round(current_mem, 3),
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

        mean, stddev = self.get_baseline_stats("memory_pct")
        sigma = abs(current_mem - mean) / max(stddev, 1e-6)

        eviction_rate = (
            sum(self._eviction_window[service_name]) / len(self._eviction_window[service_name])
            if self._eviction_window[service_name]
            else 0.0
        )

        hypothesis = (
            f"Redis memory at {current_mem:.0%} of capacity (alert threshold: {_MEMORY_ALERT_PCT:.0%}). "
        )
        if eviction_rate > 0:
            hypothesis += (
                f"Eviction rate: {eviction_rate:.1f}/min — "
                "check if maxmemory-policy is appropriate for workload."
            )
        else:
            hypothesis += "Check maxmemory-policy configuration and memory growth trend."

        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="REDIS_OOM",
            detection_confidence=max(conformal_result.combined_score, current_mem),
            shap_feature_values=if_result.get("shap_feature_values", {"memory_pct": 100.0}),
            conformal_interval={
                "lower": conformal_result.lower_bound,
                "upper": conformal_result.upper_bound,
                "confidence_level": conformal_result.confidence_level,
            },
            baseline_mean=mean,
            baseline_stddev=stddev,
            current_value=current_mem,
            deviation_sigma=sigma,
            preliminary_hypothesis=hypothesis,
            severity_classification="P2",
            critical_mode=False,
        )
        if pkg:
            await self._send_evidence(pkg)
        return pkg

    def _build_observation(self, service_name: str) -> dict[str, float]:
        mem_window = self._memory_pct_window.get(service_name, [])
        evict_window = self._eviction_window.get(service_name, [])
        return {
            "error_rate": mem_window[-1] if mem_window else 0.0,
            "response_time_p95": 0.0,
            "resource_utilisation": mem_window[-1] if mem_window else 0.0,
            "error_code_freq_0": sum(evict_window) / max(len(evict_window), 1),
            "error_code_freq_1": 0.0,
            "error_code_freq_2": 0.0,
            "error_code_freq_3": 0.0,
            "error_code_freq_4": 0.0,
        }

    def _get_mem_mean(self, service_name: str) -> float:
        mean, _ = self.get_baseline_stats("memory_pct")
        return mean

    def _get_mem_stddev(self, service_name: str) -> float:
        _, stddev = self.get_baseline_stats("memory_pct")
        return stddev
