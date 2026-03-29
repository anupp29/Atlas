# agents

Specialist detection agents. One agent type per technology domain. Each agent is a long-lived singleton per client, running continuously in the background monitoring loop.

The platform is designed to support any number of agent types across any technology stack. Current agents cover Java, PostgreSQL, Node.js, and Redis. New agents extend `base_agent.py` and plug in without changes to the core platform — the architecture scales to any service type, language runtime, or infrastructure component.

---

## Files

| File | What it does |
|------|-------------|
| `base_agent.py` | Abstract base class. Defines the contract all agents must satisfy. Implements seasonal baseline, bootstrap period, log buffer, EvidencePackage construction and validation, and client_id enforcement. |
| `java_agent.py` | Monitors Java Spring Boot services. Detects HikariCP exhaustion, JVM OOM, StackOverflow, and HTTP 5xx spikes. |
| `postgres_agent.py` | Monitors PostgreSQL. Detects connection pool exhaustion, deadlocks, and FATAL errors via SQLSTATE codes. |
| `nodejs_agent.py` | Monitors Node.js services. Detects unhandled rejection spikes and downstream connection refusals. |
| `redis_agent.py` | Monitors Redis. Detects OOM, rejected commands, and memory threshold breaches. Alert threshold is 85% memory, not 3 sigma, because Redis memory is bounded. |
| `correlation_engine.py` | Sits above all active agents. 90-second window per client. Classifies incidents as CASCADE or ISOLATED using Neo4j structural confirmation. Runs early warning scan on blast-radius services. |

---

## detection/

| File | What it does |
|------|-------------|
| `chronos_detector.py` | Chronos-Bolt time-series foundation model wrapper. Layer A of the detection ensemble. Loads the model once, runs inference per service. Falls back to z-score if model is unavailable or inference times out (500ms). |
| `isolation_forest.py` | Isolation Forest with SHAP explainability. Layer B. Detects point anomalies. SHAP TreeExplainer produces per-feature contribution percentages that sum to 100. Retrains every 24 hours in a background thread. |
| `conformal.py` | Conformal prediction wrapper. Layer C. Combines Chronos-Bolt (55% weight) and Isolation Forest (45% weight) scores into a statistically calibrated confidence interval. Falls back to a fixed 0.65 threshold when fewer than 50 calibration samples exist. |

---

## Detection flow

```
Event arrives
    -> ingest() updates log buffer, metric windows, seasonal baseline
    -> Critical pattern check (immediate, no baseline required)
    -> analyze() runs detection ensemble:
        Chronos-Bolt score
        Isolation Forest score + SHAP values
        Conformal prediction combines both
    -> EvidencePackage built and validated
    -> Sent to correlation engine output queue
```

---

## EvidencePackage

Every agent produces this dataclass when an anomaly is detected. All fields are required. The package is validated before it leaves the agent.

```python
@dataclass
class EvidencePackage:
    evidence_id: str              # uuid4
    agent_id: str                 # e.g. "java-agent"
    client_id: str                # mandatory, enforced on every send
    service_name: str             # e.g. "PaymentAPI"
    anomaly_type: str             # e.g. "CONNECTION_POOL_EXHAUSTED"
    detection_confidence: float   # 0.0-1.0 from conformal prediction
    shap_feature_values: dict[str, float]  # feature -> contribution_pct, sums to 100
    conformal_interval: dict      # {lower: float, upper: float, confidence_level: float}
    baseline_mean: float          # seasonal baseline mean for this time slot
    baseline_stddev: float        # seasonal baseline stddev
    current_value: float          # observed metric value
    deviation_sigma: float        # standard deviations from baseline
    supporting_log_samples: list[str]  # 5 real log lines (1 minimum in critical mode)
    preliminary_hypothesis: str   # plain-English domain-specific explanation
    severity_classification: str  # "P1" | "P2" | "P3"
    detection_timestamp: datetime # UTC
```

---

## Cascade correlation

The correlation engine holds a 90-second window per client. When two or more EvidencePackages arrive within the window, it checks Neo4j to confirm the affected services are structurally connected via DEPENDS_ON. Temporal proximity alone is never sufficient to declare a cascade.

If structurally connected: `CASCADE_INCIDENT`
If not connected: two separate `ISOLATED_ANOMALY` packages

After cascade classification, it checks for recent CMDB change records on the affected services and scans blast-radius-adjacent services for early deviation (1.5 to 2.5 sigma).

---

## Multi-tenancy

Every agent instance is scoped to one `client_id`. The `client_id` is validated on every `ingest()` call and on every `EvidencePackage` before it leaves the agent. A mismatch raises a hard error, not a warning.
