"""
Specialist agent for Java Spring Boot services.
Monitors HTTP error rate, response time P95, JVM heap, thread count.
Critical patterns: HikariCP exhaustion, OOM, StackOverflow.
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

# Detection threshold — must match base_agent._ALERT_SIGMA
_ALERT_SIGMA = 3.0

# ATLAS error taxonomy mappings for Java
_CRITICAL_PATTERNS: dict[str, tuple[str, str, str]] = {
    # pattern_key: (regex, anomaly_type, hypothesis)
    "hikaricp_exhaustion": (
        r"HikariPool.*connection.*not available|HikariPool.*timeout.*pool|"
        r"Unable to acquire JDBC Connection|Connection is not available.*request timed out",
        "CONNECTION_POOL_EXHAUSTED",
        "Connection pool exhaustion — possible connection leak or misconfigured pool size. "
        "Check HikariCP maxPoolSize configuration and active connection count.",
    ),
    "jvm_oom": (
        r"java\.lang\.OutOfMemoryError|OutOfMemoryError",
        "JVM_MEMORY_CRITICAL",
        "JVM heap exhaustion — possible memory leak or undersized heap configuration. "
        "Check heap usage trends and recent deployments that may have increased memory footprint.",
    ),
    "jvm_stack_overflow": (
        r"java\.lang\.StackOverflowError|StackOverflowError",
        "JVM_STACK_OVERFLOW",
        "JVM stack overflow — likely infinite recursion or excessively deep call stack. "
        "Check recent code changes for recursive methods.",
    ),
    "econnrefused": (
        r"Connection refused|ECONNREFUSED|java\.net\.ConnectException.*Connection refused",
        "NODE_DOWNSTREAM_REFUSED",
        "Downstream connection refused — check dependency health and network connectivity.",
    ),
}

# Compiled patterns for performance
_COMPILED_PATTERNS: dict[str, tuple[re.Pattern, str, str]] = {
    key: (re.compile(pattern, re.IGNORECASE), anomaly_type, hypothesis)
    for key, (pattern, anomaly_type, hypothesis) in _CRITICAL_PATTERNS.items()
}

# Target host extraction for ECONNREFUSED
_ECONNREFUSED_HOST_RE = re.compile(
    r"(?:Connection refused|ECONNREFUSED)[^\w]*([\w\-\.]+(?::\d+)?)",
    re.IGNORECASE,
)

# HTTP 5xx detection
_HTTP_5XX_RE = re.compile(r"\b5\d{2}\b")

# Silence threshold
_SILENCE_THRESHOLD_MINUTES = 5


class JavaAgent(BaseAgent):
    """
    Specialist agent for Java Spring Boot services.
    Scoped to one client. Monitors all Java services for that client.
    """

    def __init__(self, client_id: str) -> None:
        super().__init__(agent_id="java-agent", client_id=client_id)
        # Per-service detection components
        self._chronos: dict[str, ChronosDetector] = {}
        self._isolation_forest: dict[str, IsolationForestDetector] = {}
        self._conformal: dict[str, ConformalPredictor] = {}
        # Per-service metric windows
        self._error_rate_window: dict[str, list[float]] = {}
        self._response_time_window: dict[str, list[float]] = {}
        # JVM heap utilisation (0.0–1.0) — populated when jvm_heap_used_pct is present in events
        self._resource_util_window: dict[str, list[float]] = {}
        # Per-service silence tracking
        self._last_event_per_service: dict[str, datetime] = {}

    def _ensure_detectors(self, service_name: str) -> None:
        """Lazily initialise per-service detection components."""
        if service_name not in self._chronos:
            self._chronos[service_name] = ChronosDetector(self._client_id, service_name)
            self._isolation_forest[service_name] = IsolationForestDetector(self._client_id, service_name)
            self._conformal[service_name] = ConformalPredictor(self._client_id, service_name)
            self._error_rate_window[service_name] = []
            self._response_time_window[service_name] = []
            self._resource_util_window[service_name] = []

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    async def ingest(self, event: dict[str, Any]) -> None:
        """
        Process a normalised enriched event from a Java Spring Boot service.

        Args:
            event: NormalisedEvent dict with at minimum: service_name, severity,
                   error_code, message, timestamp, client_id.
        """
        if event.get("client_id") != self._client_id:
            logger.error(
                "java_agent.client_id_mismatch",
                expected=self._client_id,
                received=event.get("client_id"),
            )
            return

        service_name: str = event.get("source_system", "unknown-java-service")
        self._ensure_detectors(service_name)
        self.record_event_received()
        self._last_event_per_service[service_name] = datetime.now(timezone.utc)

        message: str = event.get("message") or ""
        severity: str = event.get("severity") or "INFO"
        raw_payload: str = event.get("raw_payload") or message

        # Add to log buffer
        self._add_log_sample(service_name, raw_payload)

        # Update metric windows
        if severity in ("ERROR", "WARN"):
            self._error_rate_window[service_name].append(1.0)
        else:
            self._error_rate_window[service_name].append(0.0)
        # Keep last 60 readings
        if len(self._error_rate_window[service_name]) > 60:
            self._error_rate_window[service_name] = self._error_rate_window[service_name][-60:]

        # Extract response time from event if present (e.g. from OTel span duration_ms)
        duration_ms = event.get("duration_ms") or event.get("response_time_ms")
        if duration_ms is not None:
            try:
                self._response_time_window[service_name].append(float(duration_ms))
                if len(self._response_time_window[service_name]) > 200:
                    self._response_time_window[service_name] = self._response_time_window[service_name][-200:]
            except (TypeError, ValueError):
                pass

        # Extract JVM heap utilisation if present (from JMX or OTel JVM metrics)
        # Accepts: jvm_heap_used_pct (0.0–1.0), jvm_heap_used_bytes + jvm_heap_max_bytes
        jvm_heap_pct = event.get("jvm_heap_used_pct")
        if jvm_heap_pct is None:
            used = event.get("jvm_heap_used_bytes")
            max_heap = event.get("jvm_heap_max_bytes")
            if used is not None and max_heap and float(max_heap) > 0:
                try:
                    jvm_heap_pct = float(used) / float(max_heap)
                except (TypeError, ValueError):
                    pass
        if jvm_heap_pct is not None:
            try:
                pct = float(jvm_heap_pct)
                pct = min(max(pct, 0.0), 1.0)
                self._resource_util_window[service_name].append(pct)
                if len(self._resource_util_window[service_name]) > 200:
                    self._resource_util_window[service_name] = self._resource_util_window[service_name][-200:]
            except (TypeError, ValueError):
                pass

        # Update seasonal baseline with error rate
        error_rate = sum(self._error_rate_window[service_name]) / max(len(self._error_rate_window[service_name]), 1)
        ts = event.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)
        elif not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)

        self.update_baseline("error_rate", error_rate, ts)

        # Update Chronos baseline
        self._chronos[service_name].update_baseline("error_rate", error_rate)

        # Update Isolation Forest baseline
        observation = self._build_observation(service_name)
        self._isolation_forest[service_name].add_baseline_observation(observation)

        # Check for critical patterns — immediate detection regardless of baseline
        await self._check_critical_patterns(service_name, message, raw_payload, event)

    async def analyze(self) -> EvidencePackage | None:
        """
        Run statistical detection across all monitored services.
        Returns the first anomaly found, or None.
        """
        for service_name in list(self._error_rate_window.keys()):
            pkg = await self._analyze_service(service_name)
            if pkg:
                return pkg
        return None

    def get_evidence(self) -> EvidencePackage | None:
        """Non-blocking poll of the output queue."""
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
        event: dict[str, Any],
    ) -> None:
        """
        Check for critical error patterns that trigger immediate detection
        regardless of statistical baseline or bootstrap state.
        """
        for key, (pattern, anomaly_type, hypothesis) in _COMPILED_PATTERNS.items():
            if pattern.search(message) or pattern.search(raw_payload):
                # For ECONNREFUSED, extract and include target host
                enriched_hypothesis = hypothesis
                if key == "econnrefused":
                    host_match = _ECONNREFUSED_HOST_RE.search(message) or _ECONNREFUSED_HOST_RE.search(raw_payload)
                    if host_match:
                        target_host = host_match.group(1)
                        enriched_hypothesis = (
                            f"Downstream connection refused to '{target_host}' — "
                            "check dependency health and network connectivity."
                        )
                    else:
                        enriched_hypothesis = (
                            "Downstream connection refused (target host not identified in log) — "
                            "check dependency health."
                        )

                logger.warning(
                    "java_agent.critical_pattern_detected",
                    client_id=self._client_id,
                    service=service_name,
                    pattern=key,
                    anomaly_type=anomaly_type,
                )

                # Determine severity: OOM and PANIC are always P1
                severity = "P1" if anomaly_type in ("JVM_MEMORY_CRITICAL", "JVM_STACK_OVERFLOW") else "P2"

                pkg = self._build_evidence_package(
                    service_name=service_name,
                    anomaly_type=anomaly_type,
                    detection_confidence=0.95,  # Critical pattern = high confidence
                    shap_feature_values={"error_code_pattern": 100.0},
                    conformal_interval={"lower": 0.0, "upper": 0.95, "confidence_level": 0.95},
                    baseline_mean=self._get_baseline_mean(service_name),
                    baseline_stddev=self._get_baseline_stddev(service_name),
                    current_value=1.0,
                    deviation_sigma=5.0,  # Critical = well beyond threshold
                    preliminary_hypothesis=enriched_hypothesis,
                    severity_classification=severity,
                    critical_mode=True,
                )
                if pkg:
                    await self._send_evidence(pkg)
                return  # One critical pattern per event is sufficient

    async def _analyze_service(self, service_name: str) -> EvidencePackage | None:
        """Run statistical detection for a single service."""
        if not self._error_rate_window.get(service_name):
            return None

        error_rate = sum(self._error_rate_window[service_name]) / len(self._error_rate_window[service_name])
        sigma = self.compute_sigma("error_rate", error_rate)

        # Warning level: elevated monitoring only, no EvidencePackage
        if sigma < _ALERT_SIGMA:
            return None

        # Alert level: must be sustained for 60 seconds
        if not self._check_alert_sustain(service_name, sigma):
            return None

        # Bootstrap check: only Warnings during bootstrap
        if not self._can_produce_alert():
            logger.info(
                "java_agent.bootstrap_suppressed_alert",
                client_id=self._client_id,
                service=service_name,
                sigma=round(sigma, 2),
            )
            return None

        # Run detection ensemble
        chronos_result = await self._chronos[service_name].score(
            self._error_rate_window[service_name]
        )
        chronos_score = chronos_result.get("anomaly_probability", 0.5)

        if_result = self._isolation_forest[service_name].detect(
            self._build_observation(service_name)
        )
        # Normalise IF score: score_samples returns negative values, more negative = more anomalous
        raw_if_score = if_result.get("anomaly_score", 0.0)
        if_normalised = float(min(max(abs(raw_if_score) * 10, 0.0), 1.0))

        conformal_result = self._conformal[service_name].predict(chronos_score, if_normalised)

        if not conformal_result.is_anomalous:
            return None

        mean, stddev = self.get_baseline_stats("error_rate")
        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="JAVA_UNKNOWN",
            detection_confidence=conformal_result.combined_score,
            shap_feature_values=if_result.get("shap_feature_values", {}),
            conformal_interval={
                "lower": conformal_result.lower_bound,
                "upper": conformal_result.upper_bound,
                "confidence_level": conformal_result.confidence_level,
            },
            baseline_mean=mean,
            baseline_stddev=stddev,
            current_value=error_rate,
            deviation_sigma=sigma,
            preliminary_hypothesis=(
                f"HTTP error rate at {sigma:.1f}σ above baseline — "
                "possible downstream dependency failure or application error spike."
            ),
            severity_classification="P2",
            critical_mode=False,
        )
        if pkg:
            await self._send_evidence(pkg)
        return pkg

    def _build_observation(self, service_name: str) -> dict[str, float]:
        """
        Build the feature observation dict for the Isolation Forest.
        All features are derived from the rolling windows maintained per service.
        resource_utilisation is derived from the error rate window as a proxy
        when JVM heap metrics are not available via JMX. When JVM heap data is
        present in events (field: jvm_heap_used_pct), it is stored in
        _resource_util_window and used directly.
        """
        error_window = self._error_rate_window.get(service_name, [])
        error_rate = sum(error_window) / max(len(error_window), 1)

        response_window = self._response_time_window.get(service_name, [])
        response_p95 = float(sorted(response_window)[int(len(response_window) * 0.95)]) if len(response_window) >= 20 else 0.0

        # resource_utilisation: use JVM heap % if available, else derive from
        # HTTP 5xx rate as a proxy (high error rate correlates with resource pressure).
        resource_util_window = self._resource_util_window.get(service_name, [])
        if resource_util_window:
            resource_utilisation = resource_util_window[-1]
        else:
            # Proxy: sustained error rate above 10% suggests resource pressure
            resource_utilisation = min(1.0, error_rate * 5.0)

        # Error code frequency: count occurrences of each critical pattern in the log buffer
        log_buf = self._log_buffer.get(service_name, [])
        pattern_counts: list[float] = []
        for key, (pattern, _, _) in _COMPILED_PATTERNS.items():
            hits = sum(1 for line in log_buf if pattern.search(line))
            pattern_counts.append(float(hits) / max(len(log_buf), 1))
        # Pad to exactly 5 slots
        while len(pattern_counts) < 5:
            pattern_counts.append(0.0)

        return {
            "error_rate": error_rate,
            "response_time_p95": response_p95,
            "resource_utilisation": resource_utilisation,
            "error_code_freq_0": pattern_counts[0],
            "error_code_freq_1": pattern_counts[1],
            "error_code_freq_2": pattern_counts[2],
            "error_code_freq_3": pattern_counts[3],
            "error_code_freq_4": pattern_counts[4],
        }

    def _get_baseline_mean(self, service_name: str) -> float:
        mean, _ = self.get_baseline_stats("error_rate")
        return mean

    def _get_baseline_stddev(self, service_name: str) -> float:
        _, stddev = self.get_baseline_stats("error_rate")
        return stddev

    def check_silence_all_services(self) -> list[str]:
        """
        Return list of service names that have been silent for more than 5 minutes.
        Callers should emit a Warning to the activity feed for each.
        """
        now = datetime.now(timezone.utc)
        silent = []
        for service_name, last_event in self._last_event_per_service.items():
            elapsed = (now - last_event).total_seconds() / 60
            if elapsed >= _SILENCE_THRESHOLD_MINUTES:
                silent.append(service_name)
        return silent
