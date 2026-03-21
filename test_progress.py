"""
Incremental progress verification. One assertion per file built.
Must run in under 5 seconds. Not a test suite.
"""

from datetime import datetime, timezone, timedelta

# ── scorer.py ────────────────────────────────────────────────────────────────
from backend.orchestrator.confidence.scorer import (
    calculate_action_safety,
    calculate_evidence_freshness,
    calculate_composite,
)

assert calculate_action_safety(3) == 0.0
assert calculate_action_safety(1) == 1.0
assert calculate_action_safety(2) == 0.6
assert calculate_evidence_freshness(datetime.now(timezone.utc) - timedelta(minutes=25)) == 0.0
assert calculate_composite(1.0, 1.0, 1.0, 1.0) == 1.0

# ── vetoes.py ────────────────────────────────────────────────────────────────
from backend.orchestrator.confidence.vetoes import (
    check_action_class_three,
    run_all_vetoes,
)

assert check_action_class_three(3) is not None
assert check_action_class_three(1) is None
vetoes = run_all_vetoes(
    client_config={"compliance_frameworks": [], "change_freeze_windows": [], "applications": []},
    current_time=datetime.now(timezone.utc),
    action_class=3,
    incident_priority="P2",
    evidence_packages=[],
    client_id="TEST",
    action_id="test-action",
    service_name="TestService",
    last_2_hours_actions=[],
    last_graph_update_timestamp=datetime.now(timezone.utc),
    historical_record_count=10,
)
assert len(vetoes) >= 1  # Class 3 veto must fire

# ── client_registry.py ───────────────────────────────────────────────────────
from backend.config.client_registry import load_all_clients, get_client

load_all_clients()
fc = get_client("FINCORE_UK_001")
assert fc["auto_execute_threshold"] == 0.92
assert fc["trust_level"] == 1

# ── conformal.py ─────────────────────────────────────────────────────────────
from backend.agents.detection.conformal import ConformalPredictor

cp = ConformalPredictor("TEST_CLIENT", "TestService")
# Fallback mode: fewer than 50 calibration samples
result = cp.predict(0.8, 0.7)
assert result.fallback_used is True, "Should use fallback with < 50 calibration samples"
assert 0.0 <= result.combined_score <= 1.0

# Add 50 calibration samples (all normal — low scores)
for _ in range(50):
    cp.add_calibration_score(0.1, 0.1)
result_calibrated = cp.predict(0.9, 0.9)
assert result_calibrated.fallback_used is False, "Should use conformal with >= 50 samples"
assert result_calibrated.is_anomalous is True, "High scores should be anomalous"

# ── base_agent.py ─────────────────────────────────────────────────────────────
from backend.agents.base_agent import BaseAgent, EvidencePackage, _validate_evidence_package
from datetime import datetime, timezone

# Validate that a complete EvidencePackage passes
pkg = EvidencePackage(
    evidence_id="test-id",
    agent_id="test-agent",
    client_id="TEST_CLIENT",
    service_name="TestService",
    anomaly_type="CONNECTION_POOL_EXHAUSTED",
    detection_confidence=0.85,
    shap_feature_values={"error_rate": 100.0},
    conformal_interval={"lower": 0.0, "upper": 0.85, "confidence_level": 0.85},
    baseline_mean=5.0,
    baseline_stddev=1.0,
    current_value=20.0,
    deviation_sigma=15.0,
    supporting_log_samples=["log1", "log2", "log3", "log4", "log5"],
    preliminary_hypothesis="Test hypothesis",
    severity_classification="P2",
    detection_timestamp=datetime.now(timezone.utc),
)
errors = _validate_evidence_package(pkg)
assert errors == [], f"Valid package should have no errors, got: {errors}"

# Validate that a package with missing client_id fails
pkg_bad = EvidencePackage(
    evidence_id="test-id",
    agent_id="test-agent",
    client_id="",  # missing
    service_name="TestService",
    anomaly_type="CONNECTION_POOL_EXHAUSTED",
    detection_confidence=0.85,
    shap_feature_values={},
    conformal_interval={},
    baseline_mean=5.0,
    baseline_stddev=1.0,
    current_value=20.0,
    deviation_sigma=15.0,
    supporting_log_samples=["log1"],
    preliminary_hypothesis="Test",
    severity_classification="P2",
    detection_timestamp=datetime.now(timezone.utc),
)
errors_bad = _validate_evidence_package(pkg_bad)
assert len(errors_bad) > 0, "Package with empty client_id should fail validation"

# ── java_adapter.py ───────────────────────────────────────────────────────────
from backend.ingestion.adapters.java_adapter import parse_line as java_parse

hikari_line = (
    "2024-01-15 09:23:47.123  ERROR 12345 --- [http-nio-8080-exec-1] "
    "com.zaxxer.hikari.pool.HikariPool : HikariPool-1 - Connection is not available, "
    "request timed out after 30000ms."
)
result = java_parse(hikari_line, "FINCORE_UK_001", "PaymentAPI")
assert result is not None
assert result["error_code"] == "CONNECTION_POOL_EXHAUSTED", f"Expected CONNECTION_POOL_EXHAUSTED, got {result['error_code']}"
assert result["severity"] == "ERROR"

# ── postgres_adapter.py ───────────────────────────────────────────────────────
from backend.ingestion.adapters.postgres_adapter import parse_line as pg_parse

panic_line = "2024-01-15 09:23:47.123 UTC [12345] PANIC:  could not write to file \"pg_wal/000000010000000000000001\""
result_pg = pg_parse(panic_line, "FINCORE_UK_001", "TransactionDB")
assert result_pg is not None
assert result_pg["severity"] == "ERROR", "PANIC must map to ERROR severity"
assert result_pg["error_code"] == "DB_PANIC", f"Expected DB_PANIC, got {result_pg['error_code']}"

fatal_line = "2024-01-15 09:23:47.123 UTC [12345] FATAL:  remaining connection slots are reserved for non-replication superuser connections"
result_fatal = pg_parse(fatal_line, "FINCORE_UK_001", "TransactionDB")
assert result_fatal is not None
assert result_fatal["severity"] == "ERROR", "FATAL must map to ERROR — never downgraded"
assert result_fatal["error_code"] == "CONNECTION_POOL_EXHAUSTED"

# ── normaliser.py ─────────────────────────────────────────────────────────────
from backend.ingestion.normaliser import normalise

# Missing client_id must be rejected
rejected = normalise({"message": "test", "severity": "ERROR"})
assert rejected is None, "Event without client_id must be rejected"

# Valid event must produce all schema fields
valid_event = normalise({
    "client_id": "FINCORE_UK_001",
    "source_system": "PaymentAPI",
    "source_type": "java-spring-boot",
    "severity": "ERROR",
    "message": "HikariPool timeout",
    "raw_payload": "2024-01-15 09:23:47 ERROR HikariPool timeout",
})
assert valid_event is not None
assert valid_event["client_id"] == "FINCORE_UK_001"
assert valid_event["atlas_event_id"] is not None
assert valid_event["raw_payload"] == "2024-01-15 09:23:47 ERROR HikariPool timeout"

print("All assertions passed.")
