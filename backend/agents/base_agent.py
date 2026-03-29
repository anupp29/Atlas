"""
Abstract base class for all ATLAS specialist agents.
Defines the contract every agent must satisfy.
Enforces EvidencePackage schema, bootstrap period, seasonal baseline, and client_id isolation.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Bootstrap: agent must have at least 30 minutes of baseline before producing Alerts
_BOOTSTRAP_MINUTES = 30
# Seasonal baseline: 7 days × 24 hours = 168 slots
_SEASONAL_SLOTS = 168
# Exactly 5 log samples required for non-Critical EvidencePackages
_REQUIRED_LOG_SAMPLES = 5
# Rolling log buffer max size per service
_LOG_BUFFER_MAX = 100
# Detection thresholds (sigma)
_WARNING_SIGMA = 2.0
_ALERT_SIGMA = 3.0
# Alert must be sustained for 60 seconds
_ALERT_SUSTAIN_SECONDS = 60


@dataclass
class SeasonalSlot:
    """Rolling mean/stddev for one (hour_of_day, day_of_week) slot."""
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0   # Welford's online variance accumulator

    def update(self, value: float) -> None:
        """Welford's online algorithm for mean and variance."""
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def stddev(self) -> float:
        if self.count < 2:
            return 0.0
        return (self.m2 / (self.count - 1)) ** 0.5

    @property
    def is_established(self) -> bool:
        """True when at least 4 weeks of data exist for this slot (4 readings)."""
        return self.count >= 4


@dataclass
class EvidencePackage:
    """
    Structured output produced by every specialist agent.
    All fields are required. Validated before sending to the correlation engine.
    """
    evidence_id: str
    agent_id: str
    client_id: str
    service_name: str
    anomaly_type: str
    detection_confidence: float          # 0.0–1.0 from conformal prediction
    shap_feature_values: dict[str, float]  # feature → contribution_percentage, sums to 100
    conformal_interval: dict             # {lower: float, upper: float, confidence_level: float}
    baseline_mean: float
    baseline_stddev: float
    current_value: float
    deviation_sigma: float
    supporting_log_samples: list[str]    # exactly 5 lines (or min 1 in Critical mode)
    preliminary_hypothesis: str
    severity_classification: str         # "P1" | "P2" | "P3"
    detection_timestamp: datetime


def _validate_evidence_package(pkg: EvidencePackage) -> list[str]:
    """
    Validate all required fields of an EvidencePackage.
    Returns a list of validation error strings. Empty list = valid.
    """
    errors: list[str] = []

    if not pkg.evidence_id:
        errors.append("evidence_id is required")
    if not pkg.agent_id:
        errors.append("agent_id is required")
    if not pkg.client_id:
        errors.append("client_id is required")
    if not pkg.service_name:
        errors.append("service_name is required")
    if not pkg.anomaly_type:
        errors.append("anomaly_type is required")
    if not (0.0 <= pkg.detection_confidence <= 1.0):
        errors.append(f"detection_confidence must be 0.0–1.0, got {pkg.detection_confidence}")
    if not isinstance(pkg.shap_feature_values, dict):
        errors.append("shap_feature_values must be a dict")
    if not isinstance(pkg.conformal_interval, dict):
        errors.append("conformal_interval must be a dict")
    if pkg.severity_classification not in ("P1", "P2", "P3"):
        errors.append(f"severity_classification must be P1/P2/P3, got {pkg.severity_classification}")
    if not pkg.preliminary_hypothesis:
        errors.append("preliminary_hypothesis is required")
    if not pkg.supporting_log_samples:
        errors.append("supporting_log_samples must not be empty")
    if not isinstance(pkg.detection_timestamp, datetime):
        errors.append("detection_timestamp must be a datetime")

    return errors


class BaseAgent(ABC):
    """
    Abstract base class for all ATLAS specialist agents.
    Subclasses implement ingest(), analyze(), and get_evidence().
    All shared logic (baseline, bootstrap, validation, output) lives here.
    """

    def __init__(self, agent_id: str, client_id: str) -> None:
        """
        Args:
            agent_id: Unique identifier for this agent type (e.g. 'java-agent').
            client_id: The client this agent instance is scoped to. Mandatory.
        """
        if not client_id:
            raise ValueError(f"client_id is required — {self.__class__.__name__} cannot be instantiated without it.")
        if not agent_id:
            raise ValueError("agent_id is required.")

        self._agent_id = agent_id
        self._client_id = client_id

        # Seasonal baseline: metric_name → slot_index (0–167) → SeasonalSlot
        # slot_index = day_of_week * 24 + hour_of_day
        self._seasonal_baseline: dict[str, list[SeasonalSlot]] = defaultdict(
            lambda: [SeasonalSlot() for _ in range(_SEASONAL_SLOTS)]
        )

        # Bootstrap tracking: when did this agent first receive data?
        self._first_data_time: datetime | None = None
        self._is_bootstrapped: bool = False

        # Rolling log sample buffer per service
        self._log_buffer: dict[str, list[str]] = defaultdict(list)
        self._log_buffer_max = _LOG_BUFFER_MAX

        # Alert sustain tracking: service → (first_alert_time, sigma)
        self._alert_sustain: dict[str, tuple[datetime, float]] = {}

        # Health status
        self._last_event_time: datetime | None = None
        self._is_active: bool = False

        # Output queue: completed EvidencePackages waiting to be sent
        self._output_queue: asyncio.Queue[EvidencePackage] = asyncio.Queue()

        logger.info(
            "base_agent.initialised",
            agent_id=agent_id,
            client_id=client_id,
        )

    # ------------------------------------------------------------------
    # Abstract interface — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def ingest(self, event: dict[str, Any]) -> None:
        """
        Process a single normalised enriched event.
        Update internal state, log buffers, and metric windows.
        """
        ...

    @abstractmethod
    async def analyze(self) -> EvidencePackage | None:
        """
        Run detection on current state.
        Returns an EvidencePackage if an anomaly is detected, None otherwise.
        """
        ...

    @abstractmethod
    def get_evidence(self) -> EvidencePackage | None:
        """
        Return the most recent completed EvidencePackage, or None.
        Non-blocking. Used by the correlation engine to poll for output.
        """
        ...

    # ------------------------------------------------------------------
    # Seasonal baseline management
    # ------------------------------------------------------------------

    def _slot_index(self, ts: datetime) -> int:
        """Convert a timestamp to a seasonal slot index (0–167)."""
        return ts.weekday() * 24 + ts.hour

    def update_baseline(self, metric_name: str, value: float, ts: datetime | None = None) -> None:
        """
        Add a normal reading to the seasonal baseline for a metric.

        Args:
            metric_name: The metric being tracked.
            value: The observed value.
            ts: Timestamp of the observation. Defaults to now.
        """
        if ts is None:
            ts = datetime.now(timezone.utc)
        slot = self._slot_index(ts)
        self._seasonal_baseline[metric_name][slot].update(value)

        # Track bootstrap state
        if self._first_data_time is None:
            self._first_data_time = ts
        elapsed = (ts - self._first_data_time).total_seconds() / 60
        if not self._is_bootstrapped and elapsed >= _BOOTSTRAP_MINUTES:
            self._is_bootstrapped = True
            logger.info(
                "base_agent.bootstrap_complete",
                agent_id=self._agent_id,
                client_id=self._client_id,
                elapsed_minutes=round(elapsed, 1),
            )

    def get_baseline_stats(self, metric_name: str, ts: datetime | None = None) -> tuple[float, float]:
        """
        Return (mean, stddev) for the current seasonal slot.

        Returns:
            (mean, stddev). Returns (0.0, 1.0) if slot has no data.
        """
        if ts is None:
            ts = datetime.now(timezone.utc)
        slot = self._slot_index(ts)
        s = self._seasonal_baseline[metric_name][slot]
        if s.count == 0:
            return 0.0, 1.0
        return s.mean, max(s.stddev, 1e-6)

    def compute_sigma(self, metric_name: str, current_value: float, ts: datetime | None = None) -> float:
        """
        Compute how many standard deviations the current value is from the seasonal baseline.
        """
        mean, stddev = self.get_baseline_stats(metric_name, ts)
        return abs(current_value - mean) / stddev

    # ------------------------------------------------------------------
    # Detection tier logic
    # ------------------------------------------------------------------

    def _check_alert_sustain(self, service_name: str, sigma: float) -> bool:
        """
        Returns True if the service has been at Alert level (≥3σ) for 60+ seconds.
        Resets the sustain timer if sigma drops below Alert threshold.
        """
        now = datetime.now(timezone.utc)
        if sigma >= _ALERT_SIGMA:
            if service_name not in self._alert_sustain:
                self._alert_sustain[service_name] = (now, sigma)
                return False
            first_time, _ = self._alert_sustain[service_name]
            elapsed = (now - first_time).total_seconds()
            return elapsed >= _ALERT_SUSTAIN_SECONDS
        else:
            # Reset sustain timer
            self._alert_sustain.pop(service_name, None)
            return False

    def _can_produce_alert(self) -> bool:
        """
        Returns True if the agent has completed the bootstrap period.
        During bootstrap, only Warnings are permitted.
        """
        return self._is_bootstrapped

    # ------------------------------------------------------------------
    # Log buffer management
    # ------------------------------------------------------------------

    def _add_log_sample(self, service_name: str, log_line: str) -> None:
        """Add a log line to the rolling buffer for a service."""
        buf = self._log_buffer[service_name]
        buf.append(log_line)
        if len(buf) > self._log_buffer_max:
            self._log_buffer[service_name] = buf[-self._log_buffer_max:]

    def _get_log_samples(self, service_name: str, count: int = _REQUIRED_LOG_SAMPLES) -> list[str]:
        """Return the most recent log samples for a service."""
        buf = self._log_buffer[service_name]
        return buf[-count:] if len(buf) >= count else list(buf)

    def _has_enough_log_samples(self, service_name: str) -> bool:
        """True when at least 5 log samples are available."""
        return len(self._log_buffer[service_name]) >= _REQUIRED_LOG_SAMPLES

    # ------------------------------------------------------------------
    # EvidencePackage construction and validation
    # ------------------------------------------------------------------

    def _build_evidence_package(
        self,
        service_name: str,
        anomaly_type: str,
        detection_confidence: float,
        shap_feature_values: dict[str, float],
        conformal_interval: dict,
        baseline_mean: float,
        baseline_stddev: float,
        current_value: float,
        deviation_sigma: float,
        preliminary_hypothesis: str,
        severity_classification: str,
        critical_mode: bool = False,
    ) -> EvidencePackage | None:
        """
        Construct and validate an EvidencePackage.
        Returns None if validation fails (logs the errors).

        Args:
            critical_mode: If True, send with however many log samples are available (min 1).
                           If False, hold until exactly 5 samples are available.
        """
        log_samples = self._get_log_samples(service_name)

        if not critical_mode and len(log_samples) < _REQUIRED_LOG_SAMPLES:
            logger.info(
                "base_agent.holding_package",
                agent_id=self._agent_id,
                client_id=self._client_id,
                service=service_name,
                reason=f"only {len(log_samples)}/{_REQUIRED_LOG_SAMPLES} log samples available",
            )
            return None

        if critical_mode and not log_samples:
            logger.warning(
                "base_agent.no_log_samples_critical",
                agent_id=self._agent_id,
                client_id=self._client_id,
                service=service_name,
            )
            return None

        pkg = EvidencePackage(
            evidence_id=str(uuid.uuid4()),
            agent_id=self._agent_id,
            client_id=self._client_id,
            service_name=service_name,
            anomaly_type=anomaly_type,
            detection_confidence=round(float(min(max(detection_confidence, 0.0), 1.0)), 4),
            shap_feature_values=shap_feature_values,
            conformal_interval=conformal_interval,
            baseline_mean=round(float(baseline_mean), 4),
            baseline_stddev=round(float(baseline_stddev), 4),
            current_value=round(float(current_value), 4),
            deviation_sigma=round(float(deviation_sigma), 4),
            supporting_log_samples=log_samples[-_REQUIRED_LOG_SAMPLES:] if not critical_mode else (log_samples[-_REQUIRED_LOG_SAMPLES:] if len(log_samples) >= _REQUIRED_LOG_SAMPLES else log_samples),
            preliminary_hypothesis=preliminary_hypothesis,
            severity_classification=severity_classification,
            detection_timestamp=datetime.now(timezone.utc),
        )

        errors = _validate_evidence_package(pkg)
        if errors:
            logger.error(
                "base_agent.evidence_package_invalid",
                agent_id=self._agent_id,
                client_id=self._client_id,
                service=service_name,
                errors=errors,
            )
            return None

        logger.info(
            "base_agent.evidence_package_built",
            agent_id=self._agent_id,
            client_id=self._client_id,
            service=service_name,
            anomaly_type=anomaly_type,
            severity=severity_classification,
            confidence=pkg.detection_confidence,
        )
        return pkg

    async def _send_evidence(self, pkg: EvidencePackage) -> None:
        """
        Validate client_id and enqueue the EvidencePackage for the correlation engine.
        Hard error if client_id is missing or mismatched.
        """
        if not pkg.client_id:
            raise ValueError(
                f"EvidencePackage from agent '{self._agent_id}' has no client_id. "
                "This is a critical multi-tenancy violation."
            )
        if pkg.client_id != self._client_id:
            raise ValueError(
                f"EvidencePackage client_id '{pkg.client_id}' does not match "
                f"agent client_id '{self._client_id}'. Multi-tenancy violation."
            )
        await self._output_queue.put(pkg)
        logger.info(
            "base_agent.evidence_sent",
            agent_id=self._agent_id,
            client_id=self._client_id,
            evidence_id=pkg.evidence_id,
        )

    # ------------------------------------------------------------------
    # Health status
    # ------------------------------------------------------------------

    def record_event_received(self) -> None:
        """Call on every ingested event to track agent liveness."""
        self._last_event_time = datetime.now(timezone.utc)
        self._is_active = True

    def check_service_silence(self, service_name: str, silence_threshold_minutes: int = 5) -> bool:
        """
        Returns True if no events have been received for more than the threshold.
        Callers should emit a Warning to the activity feed when this returns True.
        """
        if self._last_event_time is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._last_event_time).total_seconds() / 60
        return elapsed >= silence_threshold_minutes

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def is_bootstrapped(self) -> bool:
        return self._is_bootstrapped

    @property
    def output_queue(self) -> asyncio.Queue[EvidencePackage]:
        """The queue the correlation engine reads from."""
        return self._output_queue
