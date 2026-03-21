"""
Isolation Forest with SHAP explainability.
Layer B of the two-layer detection ensemble.
Provides point anomaly detection with per-feature contribution percentages.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest

logger = structlog.get_logger(__name__)

_MIN_TRAINING_SAMPLES = 100
_CONTAMINATION = 0.02          # 2% assumed anomaly rate in baseline
_RETRAIN_INTERVAL_SECONDS = 86400  # 24 hours


class IsolationForestDetector:
    """
    Per-client per-service Isolation Forest with SHAP explainability.
    Models are never shared across clients.

    Features: error_rate, response_time_p95, resource_utilisation,
              plus up to 5 top error code frequency features.
    """

    FEATURE_NAMES = [
        "error_rate",
        "response_time_p95",
        "resource_utilisation",
        "error_code_freq_0",
        "error_code_freq_1",
        "error_code_freq_2",
        "error_code_freq_3",
        "error_code_freq_4",
    ]

    def __init__(self, client_id: str, service_name: str) -> None:
        """
        Args:
            client_id: Mandatory client scope.
            service_name: The service this detector monitors.
        """
        if not client_id:
            raise ValueError("client_id is required — IsolationForestDetector cannot be instantiated without it.")
        self.client_id = client_id
        self.service_name = service_name
        self._model: IsolationForest | None = None
        self._explainer: Any = None
        self._baseline_observations: list[list[float]] = []
        self._last_retrain_time: float = 0.0
        self._retrain_lock = threading.Lock()
        self._model_ready = False
        logger.info(
            "isolation_forest.initialised",
            client_id=client_id,
            service_name=service_name,
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def add_baseline_observation(self, observation: dict[str, float]) -> None:
        """
        Add a normal baseline observation for training.

        Args:
            observation: Dict with feature values. Missing features default to 0.0.
        """
        vector = self._dict_to_vector(observation)
        self._baseline_observations.append(vector)

        # Auto-train once we have enough samples
        if (
            len(self._baseline_observations) >= _MIN_TRAINING_SAMPLES
            and not self._model_ready
        ):
            self._train_model()

    def _dict_to_vector(self, observation: dict[str, float]) -> list[float]:
        """Convert observation dict to fixed-length feature vector."""
        return [float(observation.get(name, 0.0)) for name in self.FEATURE_NAMES]

    def _train_model(self) -> None:
        """Train the Isolation Forest on current baseline observations."""
        with self._retrain_lock:
            if len(self._baseline_observations) < _MIN_TRAINING_SAMPLES:
                logger.warning(
                    "isolation_forest.train_skipped",
                    client_id=self.client_id,
                    service_name=self.service_name,
                    reason=f"insufficient samples: {len(self._baseline_observations)}/{_MIN_TRAINING_SAMPLES}",
                )
                return

            try:
                X = np.array(self._baseline_observations, dtype=np.float32)
                model = IsolationForest(
                    contamination=_CONTAMINATION,
                    random_state=42,
                    n_estimators=100,
                )
                model.fit(X)

                try:
                    import shap  # type: ignore[import]
                    explainer = shap.TreeExplainer(model)
                except Exception as exc:
                    logger.warning(
                        "isolation_forest.shap_init_failed",
                        client_id=self.client_id,
                        service_name=self.service_name,
                        error=str(exc),
                    )
                    explainer = None

                self._model = model
                self._explainer = explainer
                self._model_ready = True
                self._last_retrain_time = datetime.now(timezone.utc).timestamp()
                logger.info(
                    "isolation_forest.trained",
                    client_id=self.client_id,
                    service_name=self.service_name,
                    n_samples=len(self._baseline_observations),
                    shap_available=explainer is not None,
                )
            except Exception as exc:
                logger.error(
                    "isolation_forest.train_failed",
                    client_id=self.client_id,
                    service_name=self.service_name,
                    error=str(exc),
                )

    def schedule_retrain(self) -> None:
        """
        Trigger a background retrain if 24 hours have elapsed since last training.
        Runs in a daemon thread — never blocks the detection pipeline.
        """
        import time
        now = time.time()
        if now - self._last_retrain_time < _RETRAIN_INTERVAL_SECONDS:
            return
        thread = threading.Thread(target=self._train_model, daemon=True, name=f"retrain-{self.client_id}-{self.service_name}")
        thread.start()
        logger.info(
            "isolation_forest.retrain_scheduled",
            client_id=self.client_id,
            service_name=self.service_name,
        )

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, observation: dict[str, float]) -> dict[str, Any]:
        """
        Run anomaly detection on a single observation.

        Args:
            observation: Dict with feature values.

        Returns:
            dict with keys:
                is_anomaly (bool)
                anomaly_score (float, more negative = more anomalous)
                shap_feature_values (dict: feature → contribution_percentage, sums to 100)
                shap_calculation_failed (bool)
                model_used (str: 'isolation_forest' or 'zscore_fallback')
                feature_vector (list[float])
        """
        vector = self._dict_to_vector(observation)

        if not self._model_ready:
            return self._zscore_fallback(vector, observation)

        X = np.array([vector], dtype=np.float32)
        raw_score = float(self._model.score_samples(X)[0])
        prediction = int(self._model.predict(X)[0])
        is_anomaly = prediction == -1

        # Z-score override: catch extreme outliers that IF may miss when training
        # data has near-zero variance (e.g. all identical baseline observations).
        zscore_override = False
        zscore_contributions: dict[str, float] = {}
        if not is_anomaly and len(self._baseline_observations) >= 10:
            baseline = np.array(self._baseline_observations, dtype=np.float32)
            means = baseline.mean(axis=0)
            stds = baseline.std(axis=0)
            stds = np.where(stds < 1e-6, 1e-6, stds)
            current = np.array(vector, dtype=np.float32)
            z_scores = np.abs((current - means) / stds)
            if float(z_scores.max()) > 5.0:
                is_anomaly = True
                zscore_override = True
                # Build feature contributions from z-scores (normalised to 100%)
                total_z = float(z_scores.sum())
                if total_z > 0:
                    pcts = (z_scores / total_z * 100.0).tolist()
                    zscore_contributions = {
                        name: round(pct, 2)
                        for name, pct in zip(self.FEATURE_NAMES, pcts)
                    }
                    # Fix floating point drift
                    diff = 100.0 - sum(zscore_contributions.values())
                    if zscore_contributions:
                        first_key = next(iter(zscore_contributions))
                        zscore_contributions[first_key] = round(
                            zscore_contributions[first_key] + diff, 2
                        )

        shap_values: dict[str, float] = {}
        shap_failed = False

        if is_anomaly:
            if zscore_override:
                shap_values = zscore_contributions
                shap_failed = not bool(shap_values)
            else:
                shap_values, shap_failed = self._compute_shap(X)

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(raw_score, 6),
            "shap_feature_values": shap_values,
            "shap_calculation_failed": shap_failed,
            "model_used": "isolation_forest",
            "feature_vector": vector,
        }

    def _compute_shap(self, X: "np.ndarray") -> tuple[dict[str, float], bool]:
        """
        Compute SHAP values for an anomalous observation.
        Returns (shap_dict, failed_flag).
        SHAP values are normalised to sum to 100%.
        """
        if self._explainer is None:
            return {}, True

        try:
            shap_vals = self._explainer.shap_values(X)
            # shap_vals shape: (1, n_features)
            raw = np.abs(shap_vals[0])
            total = raw.sum()
            if total == 0:
                return {}, True

            percentages = (raw / total * 100.0).tolist()
            result = {
                name: round(pct, 2)
                for name, pct in zip(self.FEATURE_NAMES, percentages)
            }
            # Ensure sum is exactly 100 (fix floating point drift)
            diff = 100.0 - sum(result.values())
            if result:
                first_key = next(iter(result))
                result[first_key] = round(result[first_key] + diff, 2)

            return result, False
        except Exception as exc:
            logger.warning(
                "isolation_forest.shap_failed",
                client_id=self.client_id,
                service_name=self.service_name,
                error=str(exc),
            )
            return {}, True

    def _zscore_fallback(
        self,
        vector: list[float],
        observation: dict[str, float],
    ) -> dict[str, Any]:
        """
        Z-score fallback when model is not yet trained.
        Uses per-feature z-scores from the available baseline observations.
        """
        if len(self._baseline_observations) < 10:
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "shap_feature_values": {},
                "shap_calculation_failed": False,
                "model_used": "zscore_fallback_insufficient_data",
                "feature_vector": vector,
            }

        baseline = np.array(self._baseline_observations, dtype=np.float32)
        means = baseline.mean(axis=0)
        stds = baseline.std(axis=0)
        stds = np.where(stds == 0, 1e-6, stds)

        current = np.array(vector, dtype=np.float32)
        z_scores = np.abs((current - means) / stds)
        max_z = float(z_scores.max())
        is_anomaly = max_z > 3.0

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(-max_z / 10.0, 6),  # normalise to IF score range
            "shap_feature_values": {},
            "shap_calculation_failed": False,
            "model_used": "zscore_fallback",
            "feature_vector": vector,
        }

    @property
    def is_ready(self) -> bool:
        """True when the model has been trained and is ready for detection."""
        return self._model_ready

    @property
    def baseline_sample_count(self) -> int:
        """Number of baseline observations collected."""
        return len(self._baseline_observations)
