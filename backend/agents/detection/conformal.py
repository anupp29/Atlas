"""
Conformal prediction wrapper combining Chronos-Bolt and Isolation Forest scores.
Produces statistically valid confidence intervals on every combined anomaly score.
Layer C of the two-layer detection ensemble — the calibration layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# Ensemble weights per spec: Chronos-Bolt 0.55, Isolation Forest 0.45
_CHRONOS_WEIGHT = 0.55
_IF_WEIGHT = 0.45

# Minimum calibration samples for conformal prediction to be valid
_MIN_CALIBRATION_SAMPLES = 50

# Default confidence level
_DEFAULT_CONFIDENCE_LEVEL = 0.95


@dataclass
class ConformalResult:
    """Output of the conformal prediction wrapper."""
    combined_score: float          # 0.0–1.0
    is_anomalous: bool
    confidence_level: float        # empirically calibrated, not nominal
    lower_bound: float
    upper_bound: float
    method: str                    # 'conformal' | 'simple_threshold_fallback'
    fallback_used: bool
    chronos_score: float
    isolation_forest_score: float


class ConformalPredictor:
    """
    Combines Chronos-Bolt and Isolation Forest scores using conformal prediction.
    Per-client per-service calibration. Never shared across clients.

    The calibration set is built from baseline observations where the ground truth
    is 'normal'. Nonconformity scores are computed and used to set the threshold
    at the desired confidence level.
    """

    def __init__(self, client_id: str, service_name: str) -> None:
        """
        Args:
            client_id: Mandatory client scope.
            service_name: Service this predictor is calibrated for.
        """
        if not client_id:
            raise ValueError("client_id is required — ConformalPredictor cannot be instantiated without it.")
        self._client_id = client_id
        self._service_name = service_name
        # Calibration set: list of combined scores from known-normal observations
        self._calibration_scores: list[float] = []
        self._threshold: float | None = None
        self._empirical_coverage: float | None = None

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def add_calibration_score(self, chronos_score: float, if_score: float) -> None:
        """
        Add a known-normal observation to the calibration set.
        Call this during the baseline period before the predictor is used for detection.

        Args:
            chronos_score: Anomaly probability from ChronosDetector (0.0–1.0).
            if_score: Anomaly score from IsolationForestDetector, normalised to 0.0–1.0.
        """
        combined = self._combine(chronos_score, if_score)
        self._calibration_scores.append(combined)
        # Invalidate cached threshold when new data arrives
        self._threshold = None
        self._empirical_coverage = None

    def _calibrate(self, confidence_level: float = _DEFAULT_CONFIDENCE_LEVEL) -> tuple[float, float]:
        """
        Compute the conformal threshold and empirical coverage from the calibration set.

        Uses a held-out split: the first 80% of samples build the nonconformity
        distribution; the remaining 20% are used to measure empirical coverage.
        This prevents the data-leakage bug where computing the threshold on the
        same data used to evaluate it always produces near-perfect coverage.

        Returns:
            (threshold, empirical_coverage)
        """
        if len(self._calibration_scores) < _MIN_CALIBRATION_SAMPLES:
            raise ValueError(
                f"Insufficient calibration samples: {len(self._calibration_scores)} "
                f"(minimum {_MIN_CALIBRATION_SAMPLES} required)."
            )

        scores = np.array(self._calibration_scores, dtype=float)

        # 80/20 split — first 80% set the threshold, last 20% measure coverage
        split = max(int(len(scores) * 0.8), 1)
        train_scores = scores[:split]
        test_scores = scores[split:]

        # Conformal threshold: the (1 - alpha) quantile of the training nonconformity scores
        alpha = 1.0 - confidence_level
        threshold = float(np.quantile(train_scores, 1.0 - alpha))

        # Empirical coverage: fraction of held-out points correctly classified as normal
        # (i.e. below the threshold — they ARE normal calibration points)
        if len(test_scores) > 0:
            empirical_coverage = float(np.mean(test_scores <= threshold))
        else:
            # Degenerate case: not enough data for a test split — use training coverage
            empirical_coverage = float(np.mean(train_scores <= threshold))

        return threshold, empirical_coverage

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        chronos_score: float,
        if_score: float,
        confidence_level: float = _DEFAULT_CONFIDENCE_LEVEL,
    ) -> ConformalResult:
        """
        Combine scores and apply conformal prediction to determine anomaly status.

        Args:
            chronos_score: Anomaly probability from ChronosDetector (0.0–1.0).
            if_score: Anomaly score from IsolationForestDetector, normalised to 0.0–1.0.
                      Pass 0.0 if the IF model is not ready.
            confidence_level: Desired confidence level (default 0.95).

        Returns:
            ConformalResult with all fields populated.
        """
        # Clamp inputs
        chronos_score = float(min(max(chronos_score, 0.0), 1.0))
        if_score = float(min(max(if_score, 0.0), 1.0))

        combined = self._combine(chronos_score, if_score)
        combined = float(min(max(combined, 0.0), 1.0))

        # Attempt conformal calibration
        if len(self._calibration_scores) >= _MIN_CALIBRATION_SAMPLES:
            try:
                if self._threshold is None:
                    self._threshold, self._empirical_coverage = self._calibrate(confidence_level)

                threshold = self._threshold
                empirical_coverage = self._empirical_coverage or confidence_level
                is_anomalous = combined > threshold

                # Prediction interval: [0, threshold] is the normal range
                lower_bound = 0.0
                upper_bound = float(threshold)

                logger.debug(
                    "conformal.prediction",
                    client_id=self._client_id,
                    service=self._service_name,
                    combined=round(combined, 4),
                    threshold=round(threshold, 4),
                    is_anomalous=is_anomalous,
                    empirical_coverage=round(empirical_coverage, 4),
                )

                return ConformalResult(
                    combined_score=round(combined, 4),
                    is_anomalous=is_anomalous,
                    confidence_level=round(empirical_coverage, 4),
                    lower_bound=round(lower_bound, 4),
                    upper_bound=round(upper_bound, 4),
                    method="conformal",
                    fallback_used=False,
                    chronos_score=round(chronos_score, 4),
                    isolation_forest_score=round(if_score, 4),
                )

            except Exception as exc:
                logger.warning(
                    "conformal.calibration_failed",
                    client_id=self._client_id,
                    service=self._service_name,
                    error=str(exc),
                )

        # Fallback: simple threshold when calibration set is too small
        return self._simple_threshold_fallback(combined, chronos_score, if_score)

    def _simple_threshold_fallback(
        self,
        combined: float,
        chronos_score: float,
        if_score: float,
    ) -> ConformalResult:
        """
        Simple threshold fallback when calibration set has fewer than 50 samples.
        Uses a fixed threshold of 0.65 as a conservative anomaly boundary.
        """
        _SIMPLE_THRESHOLD = 0.65
        is_anomalous = combined > _SIMPLE_THRESHOLD

        logger.info(
            "conformal.fallback_used",
            client_id=self._client_id,
            service=self._service_name,
            calibration_samples=len(self._calibration_scores),
            combined=round(combined, 4),
        )

        return ConformalResult(
            combined_score=round(combined, 4),
            is_anomalous=is_anomalous,
            confidence_level=0.0,  # No empirical calibration available
            lower_bound=0.0,
            upper_bound=_SIMPLE_THRESHOLD,
            method="simple_threshold_fallback",
            fallback_used=True,
            chronos_score=round(chronos_score, 4),
            isolation_forest_score=round(if_score, 4),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _combine(chronos_score: float, if_score: float) -> float:
        """Weighted ensemble combination."""
        return (_CHRONOS_WEIGHT * chronos_score) + (_IF_WEIGHT * if_score)

    @property
    def calibration_sample_count(self) -> int:
        """Number of calibration samples collected."""
        return len(self._calibration_scores)

    @property
    def is_calibrated(self) -> bool:
        """True when enough calibration samples exist for conformal prediction."""
        return len(self._calibration_scores) >= _MIN_CALIBRATION_SAMPLES
