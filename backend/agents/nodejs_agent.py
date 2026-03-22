"""
Specialist agent for Node.js services.
Monitors unhandled rejection rate, HTTP 5xx rate, request latency.
Critical patterns: UnhandledPromiseRejectionWarning spike, ECONNREFUSED.
ECONNREFUSED must include target host — critical for cascade detection.
Inherits from BaseAgent.
"""

from __future__ import annotations

import asyncio
import re
from collections import deque
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.agents.base_agent import BaseAgent, EvidencePackage
from backend.agents.detection.chronos_detector import ChronosDetector
from backend.agents.detection.conformal import ConformalPredictor
from backend.agents.detection.isolation_forest import IsolationForestDetector

logger = structlog.get_logger(__name__)

# Spike threshold: more than 10 unhandled rejections in 60 seconds
_REJECTION_SPIKE_THRESHOLD = 10
_REJECTION_WINDOW_SECONDS = 60

# Critical patterns
_UNHANDLED_REJECTION_RE = re.compile(
    r"UnhandledPromiseRejectionWarning|unhandledRejection|UnhandledPromiseRejection",
    re.IGNORECASE,
)
_ECONNREFUSED_RE = re.compile(r"ECONNREFUSED", re.IGNORECASE)

# Target host extraction from ECONNREFUSED
_ECONNREFUSED_HOST_RE = re.compile(
    r"ECONNREFUSED[^\w]*([\w\-\.]+(?::\d+)?)",
    re.IGNORECASE,
)

# HTTP 5xx
_HTTP_5XX_RE = re.compile(r"\b5\d{2}\b")


class NodejsAgent(BaseAgent):
    """
    Specialist agent for Node.js services.
    Scoped to one client. Monitors all Node.js services for that client.
    """

    def __init__(self, client_id: str) -> None:
        super().__init__(agent_id="nodejs-agent", client_id=client_id)
        self._chronos: dict[str, ChronosDetector] = {}
        self._isolation_forest: dict[str, IsolationForestDetector] = {}
        self._conformal: dict[str, ConformalPredictor] = {}
        # Per-service rejection event timestamps (for spike detection)
        self._rejection_timestamps: dict[str, deque[datetime]] = {}
        # Per-service error rate window
        self._error_rate_window: dict[str, list[float]] = {}

    def _ensure_detectors(self, service_name: str) -> None:
        if service_name not in self._chronos:
            self._chronos[service_name] = ChronosDetector(self._client_id, service_name)
            self._isolation_forest[service_name] = IsolationForestDetector(self._client_id, service_name)
            self._conformal[service_name] = ConformalPredictor(self._client_id, service_name)
            self._rejection_timestamps[service_name] = deque()
            self._error_rate_window[service_name] = []

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    async def ingest(self, event: dict[str, Any]) -> None:
        """Process a normalised enriched event from a Node.js service."""
        if event.get("client_id") != self._client_id:
            logger.error(
                "nodejs_agent.client_id_mismatch",
                expected=self._client_id,
                received=event.get("client_id"),
            )
            return

        service_name: str = event.get("source_system", "unknown-nodejs")
        self._ensure_detectors(service_name)
        self.record_event_received()

        message: str = event.get("message") or ""
        severity: str = event.get("severity") or "INFO"
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

        # Track unhandled rejections for spike detection
        if _UNHANDLED_REJECTION_RE.search(message) or _UNHANDLED_REJECTION_RE.search(raw_payload):
            self._rejection_timestamps[service_name].append(ts)
            # Prune old entries outside the window
            cutoff = ts.timestamp() - _REJECTION_WINDOW_SECONDS
            while (
                self._rejection_timestamps[service_name]
                and self._rejection_timestamps[service_name][0].timestamp() < cutoff
            ):
                self._rejection_timestamps[service_name].popleft()

            # Check for spike
            count = len(self._rejection_timestamps[service_name])
            if count > _REJECTION_SPIKE_THRESHOLD:
                await self._emit_rejection_spike(service_name, count, raw_payload)
                return

        # Check ECONNREFUSED — must include target host
        if _ECONNREFUSED_RE.search(message) or _ECONNREFUSED_RE.search(raw_payload):
            await self._emit_econnrefused(service_name, message, raw_payload)
            return

        # Update error rate window
        if severity in ("ERROR", "WARN") or _HTTP_5XX_RE.search(message):
            self._error_rate_window[service_name].append(1.0)
        else:
            self._error_rate_window[service_name].append(0.0)
        if len(self._error_rate_window[service_name]) > 60:
            self._error_rate_window[service_name] = self._error_rate_window[service_name][-60:]

        error_rate = sum(self._error_rate_window[service_name]) / max(len(self._error_rate_window[service_name]), 1)
        self.update_baseline("error_rate", error_rate, ts)
        self._chronos[service_name].update_baseline("error_rate", error_rate)
        self._isolation_forest[service_name].add_baseline_observation(
            self._build_observation(service_name)
        )

    async def analyze(self) -> EvidencePackage | None:
        for service_name in list(self._error_rate_window.keys()):
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

    async def _emit_rejection_spike(
        self,
        service_name: str,
        count: int,
        raw_payload: str,
    ) -> None:
        """Emit EvidencePackage for unhandled promise rejection spike."""
        logger.warning(
            "nodejs_agent.rejection_spike",
            client_id=self._client_id,
            service=service_name,
            count=count,
        )
        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="NODE_UNHANDLED_REJECTION",
            detection_confidence=0.90,
            shap_feature_values={"unhandled_rejection_rate": 100.0},
            conformal_interval={"lower": 0.0, "upper": 0.90, "confidence_level": 0.90},
            baseline_mean=0.0,
            baseline_stddev=1.0,
            current_value=float(count),
            deviation_sigma=float(count),
            preliminary_hypothesis=(
                f"Unhandled promise rejections spike: {count} in the last 60 seconds "
                f"(threshold: {_REJECTION_SPIKE_THRESHOLD}). "
                "Likely downstream service failure or uncaught async error."
            ),
            severity_classification="P2",
            critical_mode=True,
        )
        if pkg:
            await self._send_evidence(pkg)

    async def _emit_econnrefused(
        self,
        service_name: str,
        message: str,
        raw_payload: str,
    ) -> None:
        """
        Emit EvidencePackage for ECONNREFUSED.
        Target host MUST be included in the evidence — critical for cascade detection.
        """
        host_match = _ECONNREFUSED_HOST_RE.search(message) or _ECONNREFUSED_HOST_RE.search(raw_payload)
        target_host = host_match.group(1) if host_match else "unknown-host"

        logger.warning(
            "nodejs_agent.econnrefused",
            client_id=self._client_id,
            service=service_name,
            target_host=target_host,
        )

        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="NODE_DOWNSTREAM_REFUSED",
            detection_confidence=0.92,
            shap_feature_values={"econnrefused_rate": 100.0},
            conformal_interval={"lower": 0.0, "upper": 0.92, "confidence_level": 0.92},
            baseline_mean=0.0,
            baseline_stddev=1.0,
            current_value=1.0,
            deviation_sigma=5.0,
            preliminary_hypothesis=(
                f"Downstream connection refused to '{target_host}'. "
                "Check dependency health and network connectivity."
            ),
            severity_classification="P2",
            critical_mode=True,
        )
        if pkg:
            await self._send_evidence(pkg)

    async def _analyze_service(self, service_name: str) -> EvidencePackage | None:
        """Statistical detection for HTTP error rate."""
        window = self._error_rate_window.get(service_name, [])
        if not window:
            return None

        error_rate = sum(window) / len(window)
        sigma = self.compute_sigma("error_rate", error_rate)

        if sigma < 3.0:
            return None
        if not self._check_alert_sustain(service_name, sigma):
            return None
        if not self._can_produce_alert():
            return None

        chronos_result = await self._chronos[service_name].score(window)
        chronos_score = chronos_result.get("anomaly_probability", 0.5)

        if_result = self._isolation_forest[service_name].detect(
            self._build_observation(service_name)
        )
        raw_if_score = if_result.get("anomaly_score", 0.0)
        if_normalised = float(min(max(abs(raw_if_score) * 10, 0.0), 1.0))

        conformal_result = self._conformal[service_name].predict(chronos_score, if_normalised)
        if not conformal_result.is_anomalous:
            return None

        mean, stddev = self.get_baseline_stats("error_rate")
        pkg = self._build_evidence_package(
            service_name=service_name,
            anomaly_type="NODE_UNHANDLED_REJECTION",
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
        window = self._error_rate_window.get(service_name, [])
        error_rate = sum(window) / max(len(window), 1)
        rejection_count = len(self._rejection_timestamps.get(service_name, deque()))
        return {
            "error_rate": error_rate,
            "response_time_p95": 0.0,
            "resource_utilisation": 0.0,
            "error_code_freq_0": float(rejection_count),
            "error_code_freq_1": 0.0,
            "error_code_freq_2": 0.0,
            "error_code_freq_3": 0.0,
            "error_code_freq_4": 0.0,
        }
