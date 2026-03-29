# detection

Two-layer detection ensemble plus conformal prediction calibration. Used by all four specialist agents.

---

## Files

| File | Layer | What it does |
|------|-------|-------------|
| `chronos_detector.py` | A | Chronos-Bolt time-series foundation model. Detects gradual degradation and temporal pattern violations. |
| `isolation_forest.py` | B | Isolation Forest with SHAP explainability. Detects sudden point anomalies. |
| `conformal.py` | C | Combines Layer A and B scores into a statistically calibrated confidence interval. |

---

## chronos_detector.py

Wraps the `amazon/chronos-bolt-tiny` model from HuggingFace. Pretrained on 100 billion real-world time-series data points. Zero client-specific training required.

Key behaviours:
- Model loads once at process start, shared across all detector instances
- Inference timeout: 500ms. If exceeded, returns the last cached score with `timed_out=True`
- Falls back to z-score if model fails to load or inference errors
- Per-client per-service baseline stored in `_baseline` dict for z-score fallback

```python
detector = ChronosDetector(client_id="FINCORE_UK_001", service_name="PaymentAPI")
result = await detector.score(values=[...])  # list of float, min 10 points
# result: {anomaly_probability, lower_bound, upper_bound, method, timed_out}
```

The z-score fallback uses the stored baseline (known-normal data) rather than the input window itself, to avoid inflating std when the window contains anomalous values.

---

## isolation_forest.py

Isolation Forest trained on baseline observations. SHAP TreeExplainer produces per-feature contribution percentages that sum to exactly 100.

Feature vector (8 features):
```
error_rate
response_time_p95
resource_utilisation
error_code_freq_0  through  error_code_freq_4
```

Key behaviours:
- Requires 100 baseline observations before training. Falls back to z-score until then.
- Retrains every 24 hours in a background daemon thread. Never blocks detection.
- Z-score override: if any feature exceeds 5 sigma, marks as anomaly even if IF says normal. Catches extreme outliers when baseline variance is near-zero.
- SHAP values are normalised to sum to 100%. Floating point drift is corrected.

```python
detector = IsolationForestDetector(client_id="FINCORE_UK_001", service_name="PaymentAPI")
detector.add_baseline_observation({"error_rate": 0.01, "response_time_p95": 45.0, ...})
result = detector.detect({"error_rate": 0.85, "response_time_p95": 2400.0, ...})
# result: {is_anomaly, anomaly_score, shap_feature_values, model_used, feature_vector}
```

---

## conformal.py

Combines Chronos-Bolt (55% weight) and Isolation Forest (45% weight) scores using conformal prediction.

Calibration: built from known-normal observations during the baseline period. Uses an 80/20 train/test split to measure empirical coverage without data leakage. Requires 50 calibration samples.

Falls back to a fixed 0.65 threshold when fewer than 50 samples exist. Fallback is flagged with `fallback_used=True` and `confidence_level=0.0`.

```python
predictor = ConformalPredictor(client_id="FINCORE_UK_001", service_name="PaymentAPI")
predictor.add_calibration_score(chronos_score=0.1, if_score=0.05)  # during baseline
result = predictor.predict(chronos_score=0.87, if_score=0.92)
# result: ConformalResult(combined_score, is_anomalous, confidence_level, lower_bound, upper_bound, ...)
```

The `confidence_level` in the result is empirically calibrated from the held-out test split, not the nominal 0.95 target. This is what makes the confidence claim statistically valid rather than just claimed.
