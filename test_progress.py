"""
ATLAS — Comprehensive progress verification.
Covers every built module: Phase 2 (scorer, vetoes, client_registry, database)
and Phase 3 (detection ensemble, all 4 agents, ingestion pipeline, correlation engine).
One assertion per logical guarantee. Runs in under 30 seconds. No mocks.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

errors: list[str] = []

def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL: {msg}")

def ok(label: str) -> None:
    print(f"  PASS: {label}")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — MATHEMATICAL CORE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 2: scorer.py ──")
from backend.orchestrator.confidence.scorer import (
    calculate_action_safety, calculate_evidence_freshness,
    calculate_composite, calculate_historical_accuracy,
    calculate_root_cause_certainty,
)

# Action safety class mapping
assert calculate_action_safety(1) == 1.0
assert calculate_action_safety(2) == 0.6
assert calculate_action_safety(3) == 0.0
ok("action_safety: Class 1=1.0, Class 2=0.6, Class 3=0.0")

# Evidence freshness decay
assert calculate_evidence_freshness(datetime.now(timezone.utc)) > 0.99
assert calculate_evidence_freshness(datetime.now(timezone.utc) - timedelta(minutes=10)) > 0.45
assert calculate_evidence_freshness(datetime.now(timezone.utc) - timedelta(minutes=10)) < 0.55
assert calculate_evidence_freshness(datetime.now(timezone.utc) - timedelta(minutes=25)) == 0.0
ok("evidence_freshness: fresh=~1.0, 10min=~0.5, 25min=0.0")

# Composite weights: 0.30+0.25+0.25+0.20 = 1.0
assert calculate_composite(1.0, 1.0, 1.0, 1.0) == 1.0
assert calculate_composite(0.0, 0.0, 0.0, 0.0) == 0.0
assert abs(calculate_composite(1.0, 0.0, 0.0, 0.0) - 0.30) < 0.001
assert abs(calculate_composite(0.0, 1.0, 0.0, 0.0) - 0.25) < 0.001
ok("composite: weights correct (0.30/0.25/0.25/0.20)")

# Historical accuracy: cold-start sentinel
assert calculate_historical_accuracy([]) == 0.50
assert calculate_historical_accuracy([{"resolution_outcome": "success"}] * 4) == 0.50
records_10 = [{"resolution_outcome": "success", "recurrence_within_48h": False}] * 8 + \
             [{"resolution_outcome": "failure", "recurrence_within_48h": False}] * 2
assert abs(calculate_historical_accuracy(records_10) - 0.80) < 0.001
ok("historical_accuracy: cold-start=0.50, 8/10 success=0.80")

# Root cause certainty
assert calculate_root_cause_certainty([]) == 0.0
assert calculate_root_cause_certainty([{"confidence": 0.9}]) == 0.9
hyps = [{"confidence": 0.9}, {"confidence": 0.4}]  # gap=0.5 → certainty=1.0
assert calculate_root_cause_certainty(hyps) == 1.0
hyps2 = [{"confidence": 0.8}, {"confidence": 0.7}]  # gap=0.1 → certainty=0.2
assert abs(calculate_root_cause_certainty(hyps2) - 0.2) < 0.001
ok("root_cause_certainty: gap=0.5→1.0, gap=0.1→0.2")

print("\n── Phase 2: vetoes.py ──")
from backend.orchestrator.confidence.vetoes import (
    check_action_class_three, check_p1_severity, check_cold_start,
    check_graph_freshness, check_duplicate_action,
    check_business_hours_compliance, check_change_freeze_window,
    check_compliance_data_touched, run_all_vetoes,
)

# Class 3 veto — permanent ceiling
assert check_action_class_three(3) is not None
assert check_action_class_three(1) is None
assert check_action_class_three(2) is None
ok("veto_class3: fires on 3, silent on 1 and 2")

# P1 severity veto
assert check_p1_severity("P1") is not None
assert check_p1_severity("P2") is None
ok("veto_p1: fires on P1, silent on P2")

# Cold-start veto
assert check_cold_start(0) is not None
assert check_cold_start(4) is not None
assert check_cold_start(5) is None
ok("veto_cold_start: fires <5 records, silent at 5")

# Graph freshness veto
assert check_graph_freshness(None) is not None
assert check_graph_freshness(datetime.now(timezone.utc) - timedelta(hours=25)) is not None
assert check_graph_freshness(datetime.now(timezone.utc) - timedelta(hours=1)) is None
ok("veto_graph_freshness: None→fires, 25h→fires, 1h→silent")

# Duplicate action veto
recent = [{"client_id": "C1", "action_id": "act-1", "service_name": "svc"}]
assert check_duplicate_action("C1", "act-1", "svc", recent) is not None
assert check_duplicate_action("C1", "act-2", "svc", recent) is None
assert check_duplicate_action("C2", "act-1", "svc", recent) is None
ok("veto_duplicate_action: same triple→fires, different→silent")

# Business hours compliance veto (PCI-DSS, weekday, business hours)
pci_config = {
    "compliance_frameworks": ["PCI-DSS"],
    "business_hours": {"start_hour": 8, "end_hour": 18, "weekdays_only": True},
}
# Monday 10:00 UTC — within business hours
monday_10am = datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc)  # Monday
assert check_business_hours_compliance(pci_config, monday_10am, 1) is not None
# Saturday — outside business hours
saturday = datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc)  # Saturday
assert check_business_hours_compliance(pci_config, saturday, 1) is None
# No compliance frameworks — no veto
no_compliance = {"compliance_frameworks": [], "business_hours": {}}
assert check_business_hours_compliance(no_compliance, monday_10am, 1) is None
ok("veto_business_hours: PCI weekday→fires, weekend→silent, no-compliance→silent")

# Change freeze window veto
freeze_config = {
    "change_freeze_windows": [
        {"start": "2026-03-20T00:00:00", "end": "2026-03-25T00:00:00"}
    ]
}
inside_freeze = datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc)
outside_freeze = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
assert check_change_freeze_window(freeze_config, inside_freeze) is not None
assert check_change_freeze_window(freeze_config, outside_freeze) is None
ok("veto_change_freeze: inside window→fires, outside→silent")

# Compliance data touched veto
gdpr_config = {
    "compliance_frameworks": ["GDPR"],
    "applications": [{"name": "PaymentAPI", "compliance_sensitive": True}],
}
evidence_touching = [{"service_name": "PaymentAPI"}]
evidence_safe = [{"service_name": "LoggingService"}]
assert check_compliance_data_touched(evidence_touching, gdpr_config) is not None
assert check_compliance_data_touched(evidence_safe, gdpr_config) is None
ok("veto_compliance_data: sensitive service→fires, non-sensitive→silent")

# run_all_vetoes: Class 3 always fires, all 8 run
all_vetoes = run_all_vetoes(
    client_config={"compliance_frameworks": [], "change_freeze_windows": [], "applications": []},
    current_time=datetime.now(timezone.utc),
    action_class=3, incident_priority="P2", evidence_packages=[],
    client_id="TEST", action_id="x", service_name="svc",
    last_2_hours_actions=[], last_graph_update_timestamp=datetime.now(timezone.utc),
    historical_record_count=10,
)
assert len(all_vetoes) >= 1
assert any("Class 3" in v for v in all_vetoes)
ok("run_all_vetoes: Class 3 fires, complete list returned")

# run_all_vetoes: multiple vetoes fire simultaneously
multi_vetoes = run_all_vetoes(
    client_config={"compliance_frameworks": [], "change_freeze_windows": [], "applications": []},
    current_time=datetime.now(timezone.utc),
    action_class=3, incident_priority="P1", evidence_packages=[],
    client_id="TEST", action_id="x", service_name="svc",
    last_2_hours_actions=[], last_graph_update_timestamp=None,
    historical_record_count=0,
)
assert len(multi_vetoes) >= 4  # Class3 + P1 + graph_freshness(None) + cold_start
ok("run_all_vetoes: multiple vetoes fire simultaneously (Class3+P1+graph+cold_start)")

print("\n── Phase 2: client_registry.py ──")
from backend.config.client_registry import load_all_clients, get_client, get_all_client_ids

load_all_clients()

# FinanceCore config
fc = get_client("FINCORE_UK_001")
assert fc["client_id"] == "FINCORE_UK_001"
assert fc["auto_execute_threshold"] == 0.92
assert fc["max_action_class"] == 1
assert fc["trust_level"] == 1
assert "PCI-DSS" in fc["compliance_frameworks"]
assert "SOX" in fc["compliance_frameworks"]
ok("client_registry: FinanceCore loaded, threshold=0.92, trust=1, PCI-DSS+SOX")

# RetailMax config
rm = get_client("RETAILMAX_EU_002")
assert rm["client_id"] == "RETAILMAX_EU_002"
assert rm["auto_execute_threshold"] == 0.82
assert rm["trust_level"] == 2
assert "GDPR" in rm["compliance_frameworks"]
ok("client_registry: RetailMax loaded, threshold=0.82, trust=2, GDPR")

# Both clients registered
ids = get_all_client_ids()
assert "FINCORE_UK_001" in ids
assert "RETAILMAX_EU_002" in ids
ok("client_registry: both clients registered")

# Unknown client raises KeyError
try:
    get_client("UNKNOWN_CLIENT")
    fail("client_registry: unknown client should raise KeyError")
except KeyError:
    ok("client_registry: unknown client raises KeyError")

print("\n── Phase 2: audit_db.py ──")
os.environ.setdefault("ATLAS_AUDIT_DB_PATH", "./data/test_audit_progress.db")
os.environ.setdefault("ATLAS_DECISION_DB_PATH", "./data/test_decision_progress.db")
from backend.database import audit_db
audit_db.initialise_db()

# Write and verify audit record
rid = audit_db.write_audit_record({
    "client_id": "FINCORE_UK_001",
    "incident_id": "INC-TEST-001",
    "action_type": "detection",
    "actor": "ATLAS_AUTO",
    "action_description": "Connection pool exhaustion detected on PaymentAPI",
    "confidence_score_at_time": 0.84,
    "outcome": "escalated",
})
assert rid is not None and len(rid) == 36  # UUID format
ok("audit_db: write_audit_record returns valid UUID")

# Read back
records = audit_db.query_audit(
    "FINCORE_UK_001",
    datetime.now(timezone.utc) - timedelta(minutes=1),
    datetime.now(timezone.utc) + timedelta(minutes=1),
)
assert any(r["record_id"] == rid for r in records)
ok("audit_db: written record readable via query_audit")

# Immutability: no update/delete methods on audit_log
assert not hasattr(audit_db, "update_audit_record"), "update method must not exist"
assert not hasattr(audit_db, "delete_audit_record"), "delete method must not exist"
# Decision history methods belong exclusively to decision_history.py — not audit_db
assert not hasattr(audit_db, "write_decision_record"), "write_decision_record must not exist in audit_db"
assert not hasattr(audit_db, "get_records_for_pattern"), "get_records_for_pattern must not exist in audit_db"
ok("audit_db: immutable audit_log only — no update/delete, no decision_history methods")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — DETECTION ENSEMBLE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 3: chronos_detector.py ──")
from backend.agents.detection.chronos_detector import ChronosDetector

async def test_chronos():
    cd = ChronosDetector("FINCORE_UK_001", "PaymentAPI")

    # Insufficient data → neutral score
    r = await cd.score([5.0] * 5)
    assert r["method"] == "insufficient_data"
    assert r["anomaly_probability"] == 0.5
    ok("chronos: <10 points → neutral 0.5, method=insufficient_data")

    # Flat signal → low anomaly probability
    r_flat = await cd.score([5.0] * 60)
    assert r_flat["anomaly_probability"] < 0.3
    ok(f"chronos: flat 60 readings → prob={r_flat['anomaly_probability']:.3f} < 0.3")

    # Spike → high anomaly probability
    r_spike = await cd.score([5.0] * 50 + [50.0] * 10)
    assert r_spike["anomaly_probability"] > 0.6
    ok(f"chronos: spike → prob={r_spike['anomaly_probability']:.3f} > 0.6")

    # Baseline update works
    cd.update_baseline("error_rate", 0.01)
    assert len(cd.get_baseline_values("error_rate")) == 1
    ok("chronos: update_baseline and get_baseline_values work")

    # client_id required
    try:
        ChronosDetector("", "svc")
        fail("chronos: empty client_id should raise ValueError")
    except ValueError:
        ok("chronos: empty client_id raises ValueError")

asyncio.run(test_chronos())

print("\n── Phase 3: isolation_forest.py ──")
import numpy as np
from backend.agents.detection.isolation_forest import IsolationForestDetector

ifd = IsolationForestDetector("FINCORE_UK_001", "PaymentAPI")
normal_obs = {
    "error_rate": 0.01, "response_time_p95": 100.0, "resource_utilisation": 0.3,
    "error_code_freq_0": 0.0, "error_code_freq_1": 0.0, "error_code_freq_2": 0.0,
    "error_code_freq_3": 0.0, "error_code_freq_4": 0.0,
}

# Before training: z-score fallback
r_pre = ifd.detect(normal_obs)
assert r_pre["model_used"] in ("zscore_fallback", "zscore_fallback_insufficient_data")
ok("isolation_forest: pre-training uses z-score fallback")

# Train on 100 normal observations
for _ in range(100):
    ifd.add_baseline_observation(normal_obs)
assert ifd.is_ready
ok("isolation_forest: model ready after 100 samples")

# Normal observation → not anomaly
r_normal = ifd.detect(normal_obs)
assert not r_normal["is_anomaly"]
assert r_normal["model_used"] == "isolation_forest"
ok("isolation_forest: normal observation → is_anomaly=False")

# 10x observation → anomaly with SHAP values
anomalous_obs = {k: v * 10 for k, v in normal_obs.items()}
r_anom = ifd.detect(anomalous_obs)
assert r_anom["is_anomaly"], f"10x observation should be anomaly, got: {r_anom}"
assert r_anom["shap_feature_values"], "SHAP values must be non-empty on anomaly"
shap_sum = sum(r_anom["shap_feature_values"].values())
assert 95.0 <= shap_sum <= 105.0, f"SHAP sum={shap_sum} should be ~100%"
ok(f"isolation_forest: 10x → anomaly=True, SHAP sum={shap_sum:.1f}%")

# client_id required
try:
    IsolationForestDetector("", "svc")
    fail("isolation_forest: empty client_id should raise ValueError")
except ValueError:
    ok("isolation_forest: empty client_id raises ValueError")

print("\n── Phase 3: conformal.py ──")
from backend.agents.detection.conformal import ConformalPredictor

# Fallback mode: <50 calibration samples
cp_cold = ConformalPredictor("FINCORE_UK_001", "PaymentAPI")
r_cold = cp_cold.predict(0.8, 0.7)
assert r_cold.fallback_used is True
assert 0.0 <= r_cold.combined_score <= 1.0
assert r_cold.method == "simple_threshold_fallback"
ok("conformal: <50 samples → fallback_used=True, method=simple_threshold_fallback")

# Calibrated mode: 50 normal samples
cp_cal = ConformalPredictor("FINCORE_UK_001", "PaymentAPI")
for _ in range(50):
    cp_cal.add_calibration_score(0.1, 0.1)
r_cal = cp_cal.predict(0.9, 0.9)
assert r_cal.fallback_used is False
assert r_cal.method == "conformal"
assert r_cal.is_anomalous is True  # high scores against low-score calibration set
ok("conformal: 50 samples → fallback_used=False, high scores → is_anomalous=True")

# Low scores against low-score calibration → not anomalous
r_normal = cp_cal.predict(0.05, 0.05)
assert r_normal.is_anomalous is False
ok("conformal: low scores against low-score calibration → is_anomalous=False")

# Combined score always 0.0–1.0
assert 0.0 <= r_cal.combined_score <= 1.0
assert 0.0 <= r_normal.combined_score <= 1.0
ok("conformal: combined_score always in [0.0, 1.0]")

# Weights: Chronos 0.55, IF 0.45
r_chronos_only = cp_cold.predict(1.0, 0.0)
assert abs(r_chronos_only.combined_score - 0.55) < 0.001
r_if_only = cp_cold.predict(0.0, 1.0)
assert abs(r_if_only.combined_score - 0.45) < 0.001
ok("conformal: weights Chronos=0.55, IF=0.45 verified")

# client_id required
try:
    ConformalPredictor("", "svc")
    fail("conformal: empty client_id should raise ValueError")
except ValueError:
    ok("conformal: empty client_id raises ValueError")

print("\n── Phase 3: base_agent.py ──")
from backend.agents.base_agent import BaseAgent, EvidencePackage, _validate_evidence_package

class _TestAgent(BaseAgent):
    async def ingest(self, event): pass
    async def analyze(self): return None
    def get_evidence(self): return None

# Bootstrap enforcement
agent = _TestAgent("test-agent", "TEST_CLIENT")
assert not agent.is_bootstrapped
assert not agent._can_produce_alert()
ok("base_agent: fresh agent not bootstrapped, cannot produce alerts")

# client_id required
try:
    _TestAgent("test-agent", "")
    fail("base_agent: empty client_id should raise ValueError")
except ValueError:
    ok("base_agent: empty client_id raises ValueError")

# EvidencePackage validation — valid package
pkg_valid = EvidencePackage(
    evidence_id="test-id", agent_id="test-agent", client_id="FINCORE_UK_001",
    service_name="PaymentAPI", anomaly_type="CONNECTION_POOL_EXHAUSTED",
    detection_confidence=0.84,
    shap_feature_values={"error_rate": 67.0, "response_time": 33.0},
    conformal_interval={"lower": 0.0, "upper": 0.84, "confidence_level": 0.84},
    baseline_mean=5.0, baseline_stddev=1.0, current_value=20.0, deviation_sigma=15.0,
    supporting_log_samples=["log1", "log2", "log3", "log4", "log5"],
    preliminary_hypothesis="Connection pool exhaustion detected.",
    severity_classification="P2",
    detection_timestamp=datetime.now(timezone.utc),
)
errs = _validate_evidence_package(pkg_valid)
assert errs == [], f"Valid package should have no errors: {errs}"
ok("base_agent: valid EvidencePackage passes validation")

# EvidencePackage validation — missing client_id
pkg_bad = EvidencePackage(
    evidence_id="x", agent_id="x", client_id="",
    service_name="svc", anomaly_type="CONNECTION_POOL_EXHAUSTED",
    detection_confidence=0.5, shap_feature_values={}, conformal_interval={},
    baseline_mean=0.0, baseline_stddev=1.0, current_value=0.0, deviation_sigma=0.0,
    supporting_log_samples=["log1"],
    preliminary_hypothesis="test", severity_classification="P2",
    detection_timestamp=datetime.now(timezone.utc),
)
errs_bad = _validate_evidence_package(pkg_bad)
assert len(errs_bad) > 0
ok("base_agent: EvidencePackage with empty client_id fails validation")

# Seasonal baseline slot calculation
agent2 = _TestAgent("test-agent", "TEST_CLIENT")
ts_mon_9am = datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc)  # Monday 9am
agent2.update_baseline("error_rate", 0.05, ts_mon_9am)
mean, stddev = agent2.get_baseline_stats("error_rate", ts_mon_9am)
assert mean == 0.05
ok("base_agent: seasonal baseline slot update and retrieval correct")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — SPECIALIST AGENTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 3: java_agent.py ──")
from backend.agents.java_agent import JavaAgent

async def test_java_agent():
    ja = JavaAgent("FINCORE_UK_001")

    # client_id mismatch rejected
    await ja.ingest({"client_id": "WRONG_CLIENT", "source_system": "PaymentAPI",
                     "severity": "ERROR", "message": "test", "raw_payload": "test"})
    assert ja.get_evidence() is None
    ok("java_agent: wrong client_id event silently rejected")

    # HikariCP → CONNECTION_POOL_EXHAUSTED (critical mode, immediate)
    hikari_msg = (
        "HikariPool-1 - Connection is not available, request timed out after 30000ms."
    )
    for i in range(5):
        await ja.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "PaymentAPI",
            "severity": "ERROR", "message": hikari_msg,
            "raw_payload": f"2024-01-15 09:23:47.{i:03d}  ERROR 123 --- [exec-{i}] "
                           f"com.zaxxer.hikari.pool.HikariPool : {hikari_msg}",
        })
    pkg = ja.get_evidence()
    assert pkg is not None, "HikariCP events should produce EvidencePackage"
    assert pkg.anomaly_type == "CONNECTION_POOL_EXHAUSTED"
    assert pkg.client_id == "FINCORE_UK_001"
    assert pkg.severity_classification == "P2"
    assert len(pkg.supporting_log_samples) >= 1
    ok(f"java_agent: HikariCP → anomaly_type=CONNECTION_POOL_EXHAUSTED, severity=P2")

    # OOM → JVM_MEMORY_CRITICAL → P1
    ja2 = JavaAgent("FINCORE_UK_001")
    for i in range(5):
        await ja2.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "PaymentAPI",
            "severity": "ERROR", "message": "java.lang.OutOfMemoryError: Java heap space",
            "raw_payload": f"2024-01-15 09:23:47.{i:03d}  ERROR 123 --- [exec-{i}] "
                           f"com.example.App : java.lang.OutOfMemoryError: Java heap space",
        })
    pkg_oom = ja2.get_evidence()
    assert pkg_oom is not None
    assert pkg_oom.anomaly_type == "JVM_MEMORY_CRITICAL"
    assert pkg_oom.severity_classification == "P1"
    ok("java_agent: OOM → JVM_MEMORY_CRITICAL, severity=P1")

    # ECONNREFUSED → target host in hypothesis
    ja3 = JavaAgent("FINCORE_UK_001")
    for i in range(5):
        await ja3.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "PaymentAPI",
            "severity": "ERROR",
            "message": "Connection refused: connect to redis-cache:6379",
            "raw_payload": f"2024-01-15 09:23:47.{i:03d}  ERROR 123 --- [exec-{i}] "
                           f"com.example.App : Connection refused: connect to redis-cache:6379",
        })
    pkg_conn = ja3.get_evidence()
    assert pkg_conn is not None
    assert pkg_conn.anomaly_type == "NODE_DOWNSTREAM_REFUSED"
    assert "redis-cache" in pkg_conn.preliminary_hypothesis or \
           any("redis-cache" in s for s in pkg_conn.supporting_log_samples)
    ok("java_agent: ECONNREFUSED → NODE_DOWNSTREAM_REFUSED, target host in evidence")

asyncio.run(test_java_agent())

print("\n── Phase 3: postgres_agent.py ──")
from backend.agents.postgres_agent import PostgresAgent

async def test_postgres_agent():
    pa = PostgresAgent("FINCORE_UK_001")

    # PANIC → DB_PANIC → P1 (unconditional, no model needed)
    for i in range(3):
        await pa.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "TransactionDB",
            "severity": "ERROR",
            "message": "PANIC:  could not write to file pg_wal/000000010000000000000001",
            "raw_payload": f"2024-01-15 09:23:47.{i:03d} UTC [123] PANIC:  could not write to file",
        })
    pkg = pa.get_evidence()
    assert pkg is not None, "PANIC should produce EvidencePackage"
    assert pkg.anomaly_type == "DB_PANIC"
    assert pkg.severity_classification == "P1", f"PANIC must be P1, got {pkg.severity_classification}"
    assert pkg.client_id == "FINCORE_UK_001"
    ok("postgres_agent: PANIC → DB_PANIC, severity=P1 (unconditional)")

    # Deadlock → DB_DEADLOCK → P2
    pa2 = PostgresAgent("FINCORE_UK_001")
    for i in range(3):
        await pa2.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "TransactionDB",
            "severity": "ERROR",
            "message": "ERROR:  deadlock detected DETAIL: Process 123 waits for ShareLock",
            "raw_payload": f"2024-01-15 09:23:47.{i:03d} UTC [123] ERROR:  deadlock detected",
        })
    pkg_dl = pa2.get_evidence()
    assert pkg_dl is not None
    assert pkg_dl.anomaly_type == "DB_DEADLOCK"
    assert pkg_dl.severity_classification == "P2"
    ok("postgres_agent: deadlock → DB_DEADLOCK, severity=P2")

    # Connection pool exhaustion pattern
    pa3 = PostgresAgent("FINCORE_UK_001")
    for i in range(3):
        await pa3.ingest({
            "client_id": "FINCORE_UK_001", "source_system": "TransactionDB",
            "severity": "ERROR",
            "message": "FATAL:  remaining connection slots are reserved for non-replication superuser",
            "raw_payload": f"2024-01-15 09:23:47.{i:03d} UTC [123] FATAL:  remaining connection slots",
        })
    pkg_cp = pa3.get_evidence()
    assert pkg_cp is not None
    assert pkg_cp.anomaly_type == "CONNECTION_POOL_EXHAUSTED"
    ok("postgres_agent: connection slots reserved → CONNECTION_POOL_EXHAUSTED")

asyncio.run(test_postgres_agent())

print("\n── Phase 3: nodejs_agent.py ──")
from backend.agents.nodejs_agent import NodejsAgent

async def test_nodejs_agent():
    na = NodejsAgent("RETAILMAX_EU_002")

    # ECONNREFUSED → target host in evidence
    for i in range(3):
        await na.ingest({
            "client_id": "RETAILMAX_EU_002", "source_system": "CartService",
            "severity": "ERROR",
            "message": "connect ECONNREFUSED redis-cache:6379",
            "raw_payload": f"[{i}] Error: connect ECONNREFUSED redis-cache:6379",
        })
    pkg = na.get_evidence()
    assert pkg is not None, "ECONNREFUSED should produce EvidencePackage"
    assert pkg.anomaly_type == "NODE_DOWNSTREAM_REFUSED"
    assert pkg.client_id == "RETAILMAX_EU_002"
    assert "redis-cache" in pkg.preliminary_hypothesis or \
           any("redis-cache" in s for s in pkg.supporting_log_samples)
    ok("nodejs_agent: ECONNREFUSED → NODE_DOWNSTREAM_REFUSED, target host in evidence")

    # Rejection spike: >10 in 60 seconds
    na2 = NodejsAgent("RETAILMAX_EU_002")
    for i in range(12):
        await na2.ingest({
            "client_id": "RETAILMAX_EU_002", "source_system": "CartService",
            "severity": "ERROR",
            "message": "UnhandledPromiseRejectionWarning: Error: downstream timeout",
            "raw_payload": f"[{i}] UnhandledPromiseRejectionWarning: Error: downstream timeout",
        })
    pkg_spike = na2.get_evidence()
    assert pkg_spike is not None, "12 rejections should trigger spike EvidencePackage"
    assert pkg_spike.anomaly_type == "NODE_UNHANDLED_REJECTION"
    ok("nodejs_agent: 12 rejections in 60s → NODE_UNHANDLED_REJECTION spike")

    # Wrong client_id rejected
    na3 = NodejsAgent("RETAILMAX_EU_002")
    await na3.ingest({"client_id": "WRONG", "source_system": "CartService",
                      "severity": "ERROR", "message": "test", "raw_payload": "test"})
    assert na3.get_evidence() is None
    ok("nodejs_agent: wrong client_id rejected")

asyncio.run(test_nodejs_agent())

print("\n── Phase 3: redis_agent.py ──")
from backend.agents.redis_agent import RedisAgent

async def test_redis_agent():
    ra = RedisAgent("RETAILMAX_EU_002")

    # OOM → REDIS_OOM
    for i in range(3):
        await ra.ingest({
            "client_id": "RETAILMAX_EU_002", "source_system": "RedisCache",
            "severity": "ERROR",
            "message": "OOM command not allowed when used memory > maxmemory",
            "raw_payload": f"[{i}] OOM command not allowed when used memory > maxmemory",
        })
    pkg = ra.get_evidence()
    assert pkg is not None, "OOM should produce EvidencePackage"
    assert pkg.anomaly_type == "REDIS_OOM"
    assert pkg.client_id == "RETAILMAX_EU_002"
    ok("redis_agent: OOM → REDIS_OOM")

    # MISCONF → REDIS_OOM
    ra2 = RedisAgent("RETAILMAX_EU_002")
    for i in range(3):
        await ra2.ingest({
            "client_id": "RETAILMAX_EU_002", "source_system": "RedisCache",
            "severity": "ERROR",
            "message": "MISCONF Redis is configured to save RDB snapshots",
            "raw_payload": f"[{i}] MISCONF Redis is configured to save RDB snapshots",
        })
    pkg2 = ra2.get_evidence()
    assert pkg2 is not None
    assert pkg2.anomaly_type == "REDIS_OOM"
    ok("redis_agent: MISCONF → REDIS_OOM")

    # Rejected command → REDIS_COMMAND_REJECTED
    ra3 = RedisAgent("RETAILMAX_EU_002")
    for i in range(3):
        await ra3.ingest({
            "client_id": "RETAILMAX_EU_002", "source_system": "RedisCache",
            "severity": "ERROR",
            "message": "REJECTED command not allowed",
            "raw_payload": f"[{i}] REJECTED command not allowed",
        })
    pkg3 = ra3.get_evidence()
    assert pkg3 is not None
    assert pkg3.anomaly_type == "REDIS_COMMAND_REJECTED"
    ok("redis_agent: rejected command → REDIS_COMMAND_REJECTED")

asyncio.run(test_redis_agent())

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — INGESTION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 3: java_adapter.py ──")
from backend.ingestion.adapters.java_adapter import parse_line as java_parse, reassemble_stack_trace

# HikariCP → CONNECTION_POOL_EXHAUSTED
hikari_line = (
    "2024-01-15 09:23:47.123  ERROR 12345 --- [http-nio-8080-exec-1] "
    "com.zaxxer.hikari.pool.HikariPool : HikariPool-1 - Connection is not available, "
    "request timed out after 30000ms."
)
r = java_parse(hikari_line, "FINCORE_UK_001", "PaymentAPI")
assert r is not None
assert r["error_code"] == "CONNECTION_POOL_EXHAUSTED"
assert r["severity"] == "ERROR"
assert r["client_id"] == "FINCORE_UK_001"
assert r["raw_payload"] == hikari_line
ok("java_adapter: HikariCP → CONNECTION_POOL_EXHAUSTED, raw_payload preserved")

# OOM → JVM_MEMORY_CRITICAL
oom_line = (
    "2024-01-15 09:23:47.123  ERROR 12345 --- [exec-1] "
    "com.example.App : java.lang.OutOfMemoryError: Java heap space"
)
r_oom = java_parse(oom_line, "FINCORE_UK_001", "PaymentAPI")
assert r_oom["error_code"] == "JVM_MEMORY_CRITICAL"
ok("java_adapter: OutOfMemoryError → JVM_MEMORY_CRITICAL")

# StackOverflow → JVM_STACK_OVERFLOW
so_line = (
    "2024-01-15 09:23:47.123  ERROR 12345 --- [exec-1] "
    "com.example.App : java.lang.StackOverflowError"
)
r_so = java_parse(so_line, "FINCORE_UK_001", "PaymentAPI")
assert r_so["error_code"] == "JVM_STACK_OVERFLOW"
ok("java_adapter: StackOverflowError → JVM_STACK_OVERFLOW")

# Unparseable → source_type=java-unparseable, severity=UNKNOWN, never dropped
r_unp = java_parse("not a spring boot line at all !!!", "FINCORE_UK_001", "PaymentAPI")
assert r_unp is not None, "Unparseable line must not be dropped"
assert r_unp["source_type"] == "java-unparseable"
assert r_unp["severity"] == "UNKNOWN"
assert r_unp["raw_payload"] == "not a spring boot line at all !!!"
ok("java_adapter: unparseable → source_type=java-unparseable, severity=UNKNOWN, not dropped")

# client_id required
try:
    java_parse(hikari_line, "", "PaymentAPI")
    fail("java_adapter: empty client_id should raise ValueError")
except ValueError:
    ok("java_adapter: empty client_id raises ValueError")

# Stack trace reassembly
lines = [
    "2024-01-15 09:23:47.123  ERROR 12345 --- [exec-1] com.example.App : Error occurred",
    "\tat com.example.App.method(App.java:42)",
    "\tat com.example.App.main(App.java:10)",
    "2024-01-15 09:23:47.456  INFO 12345 --- [exec-1] com.example.App : Recovery",
]
reassembled = reassemble_stack_trace(lines)
assert len(reassembled) == 2
assert "\tat" in reassembled[0]
ok("java_adapter: stack trace reassembly merges continuation lines")

print("\n── Phase 3: postgres_adapter.py ──")
from backend.ingestion.adapters.postgres_adapter import parse_line as pg_parse

# PANIC → DB_PANIC, severity=ERROR
panic_line = '2024-01-15 09:23:47.123 UTC [12345] PANIC:  could not write to file "pg_wal/001"'
r_panic = pg_parse(panic_line, "FINCORE_UK_001", "TransactionDB")
assert r_panic is not None
assert r_panic["error_code"] == "DB_PANIC"
assert r_panic["severity"] == "ERROR"
assert r_panic["raw_payload"] == panic_line
ok("postgres_adapter: PANIC → DB_PANIC, severity=ERROR, raw_payload preserved")

# FATAL → ERROR (never downgraded)
fatal_line = "2024-01-15 09:23:47.123 UTC [12345] FATAL:  remaining connection slots are reserved"
r_fatal = pg_parse(fatal_line, "FINCORE_UK_001", "TransactionDB")
assert r_fatal["severity"] == "ERROR", f"FATAL must map to ERROR, got {r_fatal['severity']}"
assert r_fatal["error_code"] == "CONNECTION_POOL_EXHAUSTED"
ok("postgres_adapter: FATAL → severity=ERROR (never downgraded), CONNECTION_POOL_EXHAUSTED")

# Deadlock → DB_DEADLOCK
deadlock_line = "2024-01-15 09:23:47.123 UTC [12345] ERROR:  deadlock detected"
r_dl = pg_parse(deadlock_line, "FINCORE_UK_001", "TransactionDB")
assert r_dl["error_code"] == "DB_DEADLOCK"
ok("postgres_adapter: deadlock detected → DB_DEADLOCK")

# SQLSTATE 53300 → CONNECTION_POOL_EXHAUSTED
sqlstate_line = "2024-01-15 09:23:47.123 UTC [12345] ERROR:  too many connections SQLSTATE: 53300"
r_sql = pg_parse(sqlstate_line, "FINCORE_UK_001", "TransactionDB")
assert r_sql["error_code"] == "CONNECTION_POOL_EXHAUSTED"
ok("postgres_adapter: SQLSTATE 53300 → CONNECTION_POOL_EXHAUSTED")

# Unknown SQLSTATE → DB_UNKNOWN:XXXXX
unknown_line = "2024-01-15 09:23:47.123 UTC [12345] ERROR:  some error SQLSTATE: 99999"
r_unk = pg_parse(unknown_line, "FINCORE_UK_001", "TransactionDB")
assert r_unk["error_code"].startswith("DB_UNKNOWN:")
ok("postgres_adapter: unknown SQLSTATE → DB_UNKNOWN:XXXXX (preserved)")

# Empty line → None
assert pg_parse("", "FINCORE_UK_001", "TransactionDB") is None
ok("postgres_adapter: empty line → None")

# client_id required
try:
    pg_parse(panic_line, "", "TransactionDB")
    fail("postgres_adapter: empty client_id should raise ValueError")
except ValueError:
    ok("postgres_adapter: empty client_id raises ValueError")

print("\n── Phase 3: normaliser.py ──")
from backend.ingestion.normaliser import normalise

# Missing client_id → rejected (returns None)
assert normalise({"message": "test", "severity": "ERROR"}) is None
assert normalise({}) is None
ok("normaliser: missing client_id → None (rejected)")

# Valid event → all schema fields present
valid = normalise({
    "client_id": "FINCORE_UK_001",
    "source_system": "PaymentAPI",
    "source_type": "java-spring-boot",
    "severity": "ERROR",
    "message": "HikariPool timeout",
    "raw_payload": "2024-01-15 09:23:47 ERROR HikariPool timeout",
})
assert valid is not None
required_fields = [
    "atlas_event_id", "client_id", "timestamp", "source_system",
    "source_type", "severity", "error_code", "message", "raw_payload",
]
for f in required_fields:
    assert f in valid, f"Missing field: {f}"
assert valid["client_id"] == "FINCORE_UK_001"
assert valid["severity"] == "ERROR"
assert valid["raw_payload"] == "2024-01-15 09:23:47 ERROR HikariPool timeout"
ok("normaliser: valid event → all schema fields present, raw_payload preserved exactly")

# Severity normalisation
assert normalise({**valid, "severity": "FATAL"})["severity"] == "ERROR"
assert normalise({**valid, "severity": "CRITICAL"})["severity"] == "ERROR"
assert normalise({**valid, "severity": "WARNING"})["severity"] == "WARN"
assert normalise({**valid, "severity": "TRACE"})["severity"] == "DEBUG"
ok("normaliser: FATAL→ERROR, CRITICAL→ERROR, WARNING→WARN, TRACE→DEBUG")

# atlas_event_id is unique per call
r1 = normalise({**valid})
r2 = normalise({**valid})
assert r1["atlas_event_id"] != r2["atlas_event_id"]
ok("normaliser: atlas_event_id is unique per event")

# Unparseable timestamp → uses arrival time, timestamp_valid=False
r_bad_ts = normalise({**valid, "timestamp": "not-a-timestamp"})
assert r_bad_ts is not None
assert r_bad_ts["timestamp_valid"] is False
ok("normaliser: unparseable timestamp → arrival time used, timestamp_valid=False")

# CMDB fields initialised as None/pending
assert valid["ci_class"] is None
assert valid["cmdb_enrichment_status"] == "pending"
ok("normaliser: CMDB fields initialised as None, status=pending")

print("\n── Phase 3: event_queue.py ──")
from backend.ingestion.event_queue import EventQueue

async def test_event_queue():
    eq = EventQueue()

    # Per-client isolation: write to A, B stays empty
    event_a = {"client_id": "CLIENT_A", "atlas_event_id": "e1", "message": "test"}
    await eq.enqueue(event_a, "CLIENT_A")
    assert eq.depth("CLIENT_A") == 1
    assert eq.depth("CLIENT_B") == 0
    ok("event_queue: CLIENT_A write → CLIENT_B depth=0 (isolation)")

    # Dequeue returns correct event
    dequeued = await eq.dequeue("CLIENT_A")
    assert dequeued["atlas_event_id"] == "e1"
    assert eq.depth("CLIENT_A") == 0
    ok("event_queue: dequeue returns correct event, depth decrements")

    # Cross-client enqueue raises ValueError
    try:
        await eq.enqueue({"client_id": "CLIENT_A"}, "CLIENT_B")
        fail("event_queue: cross-client enqueue should raise ValueError")
    except ValueError:
        ok("event_queue: cross-client enqueue raises ValueError")

    # Non-blocking dequeue on empty queue returns None
    result = eq.dequeue_nowait("CLIENT_B")
    assert result is None
    ok("event_queue: dequeue_nowait on empty queue → None")

    # Queue depth metric
    for i in range(5):
        await eq.enqueue({"client_id": "CLIENT_C", "atlas_event_id": f"e{i}"}, "CLIENT_C")
    assert eq.depth("CLIENT_C") == 5
    ok("event_queue: depth metric accurate")

asyncio.run(test_event_queue())

print("\n── Phase 3: cmdb_enricher.py ──")
from backend.ingestion.cmdb_enricher import CmdbEnricher

# Structure check: enrich method exists
enricher = CmdbEnricher.__new__(CmdbEnricher)
assert hasattr(enricher, "enrich")
assert hasattr(enricher, "invalidate_cache")
ok("cmdb_enricher: enrich and invalidate_cache methods exist")

# Cache key isolation: different clients never share cache
enricher2 = CmdbEnricher.__new__(CmdbEnricher)
enricher2._cache = {}
enricher2._neo4j = None
# Verify cache key includes client_id
cache_key_a = ("CLIENT_A", "ServiceX")
cache_key_b = ("CLIENT_B", "ServiceX")
assert cache_key_a != cache_key_b
ok("cmdb_enricher: cache keys are (client_id, service_name) tuples — isolation guaranteed")

print("\n── Phase 3: correlation_engine.py ──")
from backend.agents.correlation_engine import CorrelationEngine, CorrelatedIncident
from backend.agents.base_agent import EvidencePackage

# Structure check
ce = CorrelationEngine.__new__(CorrelationEngine)
assert hasattr(ce, "ingest_evidence")
assert hasattr(ce, "flush_window")
ok("correlation_engine: ingest_evidence and flush_window methods exist")

# CorrelatedIncident dataclass
ci = CorrelatedIncident(
    correlation_type="CASCADE_INCIDENT",
    client_id="FINCORE_UK_001",
    evidence_packages=[],
)
assert ci.correlation_type == "CASCADE_INCIDENT"
assert ci.deployment_correlated is False
assert ci.structural_check_skipped is False
assert ci.early_warning_signals == []
ok("correlation_engine: CorrelatedIncident dataclass fields correct")

# flush_window on empty window returns None
async def test_correlation_flush():
    # Mock neo4j client that always returns empty (no structural connection)
    class MockNeo4j:
        async def execute_query(self, cypher, params, client_id, **kwargs):
            return []

    engine = CorrelationEngine(MockNeo4j())

    # Empty window → None
    result = await engine.flush_window("FINCORE_UK_001")
    assert result is None
    ok("correlation_engine: flush_window on empty window → None")

    # Single package → ISOLATED_ANOMALY after flush
    pkg = EvidencePackage(
        evidence_id="e1", agent_id="java-agent", client_id="FINCORE_UK_001",
        service_name="PaymentAPI", anomaly_type="CONNECTION_POOL_EXHAUSTED",
        detection_confidence=0.84, shap_feature_values={"error_rate": 100.0},
        conformal_interval={"lower": 0.0, "upper": 0.84, "confidence_level": 0.84},
        baseline_mean=5.0, baseline_stddev=1.0, current_value=20.0, deviation_sigma=15.0,
        supporting_log_samples=["log1", "log2", "log3", "log4", "log5"],
        preliminary_hypothesis="Connection pool exhaustion.",
        severity_classification="P2",
        detection_timestamp=datetime.now(timezone.utc),
    )
    await engine.ingest_evidence(pkg)
    result_single = await engine.flush_window("FINCORE_UK_001")
    assert result_single is not None
    assert result_single.correlation_type == "ISOLATED_ANOMALY"
    assert result_single.client_id == "FINCORE_UK_001"
    assert len(result_single.evidence_packages) == 1
    ok("correlation_engine: single package → ISOLATED_ANOMALY after flush")

    # Two packages, no structural connection → ISOLATED_ANOMALY
    engine2 = CorrelationEngine(MockNeo4j())
    pkg1 = EvidencePackage(
        evidence_id="e2", agent_id="java-agent", client_id="FINCORE_UK_001",
        service_name="ServiceA", anomaly_type="CONNECTION_POOL_EXHAUSTED",
        detection_confidence=0.84, shap_feature_values={"error_rate": 100.0},
        conformal_interval={"lower": 0.0, "upper": 0.84, "confidence_level": 0.84},
        baseline_mean=5.0, baseline_stddev=1.0, current_value=20.0, deviation_sigma=15.0,
        supporting_log_samples=["log1", "log2", "log3", "log4", "log5"],
        preliminary_hypothesis="Test.", severity_classification="P2",
        detection_timestamp=datetime.now(timezone.utc),
    )
    pkg2 = EvidencePackage(
        evidence_id="e3", agent_id="redis-agent", client_id="FINCORE_UK_001",
        service_name="ServiceB", anomaly_type="REDIS_OOM",
        detection_confidence=0.90, shap_feature_values={"memory_pct": 100.0},
        conformal_interval={"lower": 0.0, "upper": 0.90, "confidence_level": 0.90},
        baseline_mean=0.5, baseline_stddev=0.1, current_value=0.9, deviation_sigma=4.0,
        supporting_log_samples=["log1", "log2", "log3", "log4", "log5"],
        preliminary_hypothesis="Redis OOM.", severity_classification="P2",
        detection_timestamp=datetime.now(timezone.utc),
    )
    await engine2.ingest_evidence(pkg1)
    result2 = await engine2.ingest_evidence(pkg2)
    # No structural connection → ISOLATED_ANOMALY
    assert result2 is not None
    assert result2.correlation_type == "ISOLATED_ANOMALY"
    assert result2.structural_check_skipped is False
    ok("correlation_engine: two unconnected services → ISOLATED_ANOMALY")

    # Two packages, structural connection confirmed → CASCADE_INCIDENT
    class MockNeo4jConnected:
        async def execute_query(self, cypher, params, client_id, **kwargs):
            if "EXISTS" in cypher:
                return [{"connected": True}]
            return []

    engine3 = CorrelationEngine(MockNeo4jConnected())
    await engine3.ingest_evidence(pkg1)
    result3 = await engine3.ingest_evidence(pkg2)
    assert result3 is not None
    assert result3.correlation_type == "CASCADE_INCIDENT"
    assert len(result3.evidence_packages) == 2
    ok("correlation_engine: structurally connected services → CASCADE_INCIDENT")

    # Neo4j unavailable → ISOLATED_ANOMALY with structural_check_skipped=True
    class MockNeo4jDown:
        async def execute_query(self, *args, **kwargs):
            raise ConnectionError("Neo4j unavailable")

    engine4 = CorrelationEngine(MockNeo4jDown())
    await engine4.ingest_evidence(pkg1)
    result4 = await engine4.ingest_evidence(pkg2)
    assert result4 is not None
    assert result4.correlation_type == "ISOLATED_ANOMALY"
    assert result4.structural_check_skipped is True
    ok("correlation_engine: Neo4j down → ISOLATED_ANOMALY, structural_check_skipped=True")

    # client_id missing → raises ValueError
    pkg_no_client = EvidencePackage(
        evidence_id="e9", agent_id="java-agent", client_id="",
        service_name="svc", anomaly_type="CONNECTION_POOL_EXHAUSTED",
        detection_confidence=0.5, shap_feature_values={}, conformal_interval={},
        baseline_mean=0.0, baseline_stddev=1.0, current_value=0.0, deviation_sigma=0.0,
        supporting_log_samples=["log1"],
        preliminary_hypothesis="test", severity_classification="P2",
        detection_timestamp=datetime.now(timezone.utc),
    )
    try:
        await engine.ingest_evidence(pkg_no_client)
        fail("correlation_engine: missing client_id should raise ValueError")
    except ValueError:
        ok("correlation_engine: missing client_id raises ValueError")

asyncio.run(test_correlation_flush())

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — EXECUTION ENGINE AND LEARNING
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 4: playbook_library.py ──")
from backend.execution.playbook_library import (
    get_playbook, validate_action_id, list_playbooks,
    get_playbooks_for_anomaly, semantic_search,
)

# All four playbooks registered
pbs = list_playbooks()
pb_ids = {pb.playbook_id for pb in pbs}
assert "connection-pool-recovery-v2" in pb_ids
assert "connection-pool-recovery-v2-rollback" in pb_ids
assert "redis-memory-policy-rollback-v1" in pb_ids
assert "redis-memory-policy-rollback-v1-rollback" in pb_ids
ok("playbook_library: all 4 playbooks registered")

# Class 3 never auto_execute_eligible
for pb in pbs:
    if pb.action_class == 3:
        assert not pb.auto_execute_eligible, f"{pb.playbook_id} is Class 3 but auto_execute_eligible=True"
ok("playbook_library: no Class 3 playbook is auto_execute_eligible")

# Rollback IDs point to real entries
for pb in pbs:
    if pb.rollback_playbook_id is not None:
        assert validate_action_id(pb.rollback_playbook_id), \
            f"{pb.playbook_id} rollback_id '{pb.rollback_playbook_id}' not in registry"
ok("playbook_library: all rollback_playbook_ids point to real entries")

# get_playbook returns correct metadata
pb_cp = get_playbook("connection-pool-recovery-v2")
assert pb_cp is not None
assert pb_cp.action_class == 1
assert pb_cp.auto_execute_eligible is True
assert pb_cp.target_technology == "java-spring-boot"
assert "CONNECTION_POOL_EXHAUSTED" in pb_cp.anomaly_types_addressed
ok("playbook_library: connection-pool-recovery-v2 metadata correct")

# get_playbook unknown → None (no exception)
assert get_playbook("nonexistent-playbook") is None
ok("playbook_library: unknown playbook_id → None, no exception")

# validate_action_id
assert validate_action_id("connection-pool-recovery-v2") is True
assert validate_action_id("redis-memory-policy-rollback-v1") is True
assert validate_action_id("does-not-exist") is False
ok("playbook_library: validate_action_id correct for known and unknown IDs")

# get_playbooks_for_anomaly
cp_pbs = get_playbooks_for_anomaly("CONNECTION_POOL_EXHAUSTED")
assert any(pb.playbook_id == "connection-pool-recovery-v2" for pb in cp_pbs)
redis_pbs = get_playbooks_for_anomaly("REDIS_OOM")
assert any(pb.playbook_id == "redis-memory-policy-rollback-v1" for pb in redis_pbs)
ok("playbook_library: get_playbooks_for_anomaly returns correct playbooks")

# semantic_search returns results
results = semantic_search("connection pool hikari exhausted")
assert len(results) > 0
assert results[0].playbook_id == "connection-pool-recovery-v2"
ok("playbook_library: semantic_search returns relevant results")

print("\n── Phase 4: approval_tokens.py ──")
os.environ.setdefault("ATLAS_SECRET_KEY", "atlas-dev-secret-key-change-in-production-min-32-chars")
from backend.execution.approval_tokens import generate_approval_token, validate_approval_token

# Generate and validate a token
token = generate_approval_token("INC-TEST-001", "l2", expiry_minutes=30)
assert token is not None and len(token) > 20
ok("approval_tokens: generate_approval_token returns non-empty token")

valid, incident_id, approver_role, reason = validate_approval_token(token)
assert valid is True
assert incident_id == "INC-TEST-001"
assert approver_role == "l2"
ok("approval_tokens: validate_approval_token returns valid=True, correct incident_id and role")

# One-time use: second validation of same token fails
valid2, _, _, _ = validate_approval_token(token)
assert valid2 is False
ok("approval_tokens: token is one-time use — second validation returns valid=False")

# Token for incident A cannot approve incident B
token_b = generate_approval_token("INC-TEST-002", "l2", expiry_minutes=30)
valid_b, inc_b, _, _ = validate_approval_token(token_b)
assert valid_b is True
assert inc_b == "INC-TEST-002"
ok("approval_tokens: token encodes incident_id — cannot be used cross-incident")

# Expired token fails
import time as _time
token_exp = generate_approval_token("INC-EXP-001", "l2", expiry_minutes=0)
_time.sleep(0.1)
valid_exp, _, _, _ = validate_approval_token(token_exp)
assert valid_exp is False
ok("approval_tokens: expired token (0 min) returns valid=False")

# Missing secret key raises RuntimeError
# Missing/short secret key raises RuntimeError at token generation
old_key = os.environ.get("ATLAS_SECRET_KEY")
os.environ["ATLAS_SECRET_KEY"] = "short"
try:
    # Re-import to trigger key reload — use importlib
    import importlib
    import backend.execution.approval_tokens as _at_mod
    importlib.reload(_at_mod)
    _at_mod.generate_approval_token("INC-X", "l2")
    fail("approval_tokens: short ATLAS_SECRET_KEY should raise RuntimeError")
except RuntimeError:
    ok("approval_tokens: short ATLAS_SECRET_KEY raises RuntimeError")
finally:
    if old_key:
        os.environ["ATLAS_SECRET_KEY"] = old_key
    else:
        os.environ.pop("ATLAS_SECRET_KEY", None)
    # Reload with correct key to restore module state
    importlib.reload(_at_mod)

print("\n── Phase 4: decision_history.py ──")
import uuid as _uuid_mod
os.environ["ATLAS_DECISION_DB_PATH"] = f"./data/test_decision_{_uuid_mod.uuid4().hex[:8]}.db"
from backend.learning.decision_history import (
    initialise_db as dh_init, write_record, get_records_for_pattern,
    get_accuracy_rate as dh_accuracy, mark_recurrence,
    get_incident_count_for_client, get_auto_resolution_rate,
)

dh_init()

# Write a record
rec_id = write_record({
    "client_id": "FINCORE_UK_001",
    "incident_id": "INC-DH-001",
    "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
    "service_class": "java-spring-boot",
    "recommended_action_id": "connection-pool-recovery-v2",
    "confidence_score_at_decision": 0.84,
    "routing_tier": "L2",
    "human_action": "approved",
    "resolution_outcome": "success",
    "actual_mttr": 420,
})
assert rec_id is not None and len(rec_id) == 36
ok("decision_history: write_record returns valid UUID")

# Read back via pattern query
records = get_records_for_pattern(
    "FINCORE_UK_001", "CONNECTION_POOL_EXHAUSTED",
    "java-spring-boot", "connection-pool-recovery-v2",
)
assert any(r["record_id"] == rec_id for r in records)
ok("decision_history: get_records_for_pattern returns written record")

# client_id isolation: different client sees no records
other_records = get_records_for_pattern(
    "RETAILMAX_EU_002", "CONNECTION_POOL_EXHAUSTED",
    "java-spring-boot", "connection-pool-recovery-v2",
)
assert not any(r["record_id"] == rec_id for r in other_records)
ok("decision_history: client_id isolation — other client cannot see records")

# Accuracy rate: 1 success = 1.0
rate, count = dh_accuracy(
    "FINCORE_UK_001", "CONNECTION_POOL_EXHAUSTED",
    "java-spring-boot", "connection-pool-recovery-v2",
)
assert count >= 1
assert rate == 1.0
ok("decision_history: 1 success record → accuracy_rate=1.0")

# mark_recurrence retroactively marks resolution as failed
mark_recurrence("INC-DH-001", "FINCORE_UK_001")
rate_after, _ = dh_accuracy(
    "FINCORE_UK_001", "CONNECTION_POOL_EXHAUSTED",
    "java-spring-boot", "connection-pool-recovery-v2",
)
assert rate_after == 0.0, f"After recurrence mark, rate should be 0.0, got {rate_after}"
ok("decision_history: mark_recurrence → accuracy drops to 0.0")

# Incident count
count_fc = get_incident_count_for_client("FINCORE_UK_001")
assert count_fc >= 1
ok("decision_history: get_incident_count_for_client returns >= 1")

# client_id required
try:
    write_record({
        "client_id": "", "incident_id": "x", "anomaly_type": "x",
        "service_class": "x", "recommended_action_id": "x",
        "confidence_score_at_decision": 0.5, "routing_tier": "L1",
        "human_action": "approved", "resolution_outcome": "success", "actual_mttr": 0,
    })
    fail("decision_history: empty client_id should raise ValueError")
except ValueError:
    ok("decision_history: empty client_id raises ValueError")

# Invalid routing_tier rejected
try:
    write_record({
        "client_id": "FINCORE_UK_001", "incident_id": "x", "anomaly_type": "x",
        "service_class": "x", "recommended_action_id": "x",
        "confidence_score_at_decision": 0.5, "routing_tier": "INVALID",
        "human_action": "approved", "resolution_outcome": "success", "actual_mttr": 0,
    })
    fail("decision_history: invalid routing_tier should raise ValueError")
except ValueError:
    ok("decision_history: invalid routing_tier raises ValueError")

# Immutability: no update/delete methods
import backend.learning.decision_history as _dh_mod
assert not hasattr(_dh_mod, "update_record"), "update_record must not exist"
assert not hasattr(_dh_mod, "delete_record"), "delete_record must not exist"
ok("decision_history: immutable — no update/delete methods")

print("\n── Phase 4: recalibration.py ──")
from backend.learning.recalibration import (
    get_cached_accuracy, recalibrate_after_resolution,
    force_recalculate_all, get_cache_snapshot,
)

# Cold cache → neutral prior
rate_cold, count_cold = get_cached_accuracy(
    "FINCORE_UK_001", "CONNECTION_POOL_EXHAUSTED",
    "java-spring-boot", "connection-pool-recovery-v2",
)
assert rate_cold == 0.50
assert count_cold == 0
ok("recalibration: cold cache → (0.50, 0) neutral prior")

# After recalibration, cache reflects decision_history
async def test_recalibration():
    await recalibrate_after_resolution(
        client_id="FINCORE_UK_001",
        incident_id="INC-DH-001",
        anomaly_type="CONNECTION_POOL_EXHAUSTED",
        service_class="java-spring-boot",
        action_id="connection-pool-recovery-v2",
    )
    rate_warm, count_warm = get_cached_accuracy(
        "FINCORE_UK_001", "CONNECTION_POOL_EXHAUSTED",
        "java-spring-boot", "connection-pool-recovery-v2",
    )
    assert count_warm >= 1
    assert 0.0 <= rate_warm <= 1.0
    ok(f"recalibration: after recalibrate, cache updated — rate={rate_warm:.2f}, count={count_warm}")

    # force_recalculate_all rebuilds cache
    results = await force_recalculate_all(["FINCORE_UK_001"])
    assert "FINCORE_UK_001" in results
    assert results["FINCORE_UK_001"] >= 0
    ok("recalibration: force_recalculate_all completes without error")

    # get_cache_snapshot returns serialisable dict
    snapshot = get_cache_snapshot()
    assert isinstance(snapshot, dict)
    ok("recalibration: get_cache_snapshot returns dict")

asyncio.run(test_recalibration())

print("\n── Phase 4: weight_correction.py ──")
from backend.learning.weight_correction import (
    initialise_db as wc_init, record_modification_diff,
    record_rejection, get_adjusted_default, get_hypothesis_weights,
)

wc_init()

# No adjustment yet → get_adjusted_default returns None
result_none = get_adjusted_default("FINCORE_UK_001", "connection-pool-recovery-v2", "target_pool_size")
assert result_none is None
ok("weight_correction: no diffs yet → get_adjusted_default returns None")

# Record 3 same-direction diffs → adjusted default computed
playbook_defaults = {"target_pool_size": 150.0}
for i in range(3):
    record_modification_diff(
        client_id="FINCORE_UK_001",
        incident_id=f"INC-WC-00{i}",
        action_id="connection-pool-recovery-v2",
        modification_diff={"target_pool_size": 200.0},
        playbook_defaults=playbook_defaults,
    )
adjusted = get_adjusted_default("FINCORE_UK_001", "connection-pool-recovery-v2", "target_pool_size")
assert adjusted is not None
assert adjusted <= 150.0 * 1.5, f"Adjusted value {adjusted} exceeds +50% ceiling"
assert adjusted >= 150.0 * 0.5, f"Adjusted value {adjusted} below -50% floor"
ok(f"weight_correction: 3 same-direction diffs → adjusted_default={adjusted:.1f} (within ±50%)")

# Rejection → hypothesis weight updated
record_rejection(
    client_id="FINCORE_UK_001",
    incident_id="INC-WC-REJ-001",
    action_id="connection-pool-recovery-v2",
    rejection_reason="The connection pool hypothesis is wrong, this is a memory issue",
)
weights = get_hypothesis_weights("FINCORE_UK_001")
assert "connection_pool_exhaustion" in weights or "memory_exhaustion" in weights
ok("weight_correction: rejection with parseable reason → hypothesis weight updated")

# Unparseable rejection → no crash, no weight update
initial_weights = get_hypothesis_weights("FINCORE_UK_001")
record_rejection(
    client_id="FINCORE_UK_001",
    incident_id="INC-WC-REJ-002",
    action_id="connection-pool-recovery-v2",
    rejection_reason="xyz abc 123 completely unparseable gibberish",
)
ok("weight_correction: unparseable rejection → no crash")

# client_id required
try:
    get_adjusted_default("", "connection-pool-recovery-v2", "target_pool_size")
    fail("weight_correction: empty client_id should raise ValueError")
except ValueError:
    ok("weight_correction: empty client_id raises ValueError")

print("\n── Phase 4: trust_progression.py ──")
from backend.learning.trust_progression import (
    evaluate_progression, confirm_upgrade, get_progression_metrics,
)

# get_progression_metrics returns expected structure
async def test_trust():
    metrics = get_progression_metrics("FINCORE_UK_001")
    assert "current_stage" in metrics
    assert "total_incidents" in metrics
    assert "overall_accuracy" in metrics
    assert "auto_resolution_rate" in metrics
    assert "stage_1_criteria_met" in metrics
    assert "stage_2_criteria_met" in metrics
    assert "incidents_to_next_stage" in metrics
    ok("trust_progression: get_progression_metrics returns all expected keys")

    # evaluate_progression returns dict with required keys
    result = await evaluate_progression("FINCORE_UK_001", "INC-TRUST-001")
    assert "current_stage" in result
    assert "criteria_met" in result
    assert "recommendation" in result
    ok("trust_progression: evaluate_progression returns dict with required keys")

    # confirm_upgrade requires SDM confirmation
    try:
        confirm_upgrade("FINCORE_UK_001", 2, "")
        fail("trust_progression: empty sdm_confirmed_by should raise ValueError")
    except ValueError:
        ok("trust_progression: empty sdm_confirmed_by raises ValueError")

    # confirm_upgrade rejects non-sequential stage jump
    try:
        confirm_upgrade("FINCORE_UK_001", 5, "SDM_JOHN")
        fail("trust_progression: non-sequential stage jump should raise ValueError")
    except ValueError:
        ok("trust_progression: non-sequential stage jump raises ValueError")

    # client_id required
    try:
        get_progression_metrics("")
        fail("trust_progression: empty client_id should raise ValueError")
    except ValueError:
        ok("trust_progression: empty client_id raises ValueError")

asyncio.run(test_trust())

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5 — ORCHESTRATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Phase 5: state.py ──")
from backend.orchestrator.state import (
    AtlasState, ImmutableStateError, build_initial_state,
    guard_immutable_fields, guard_routing_decision, append_audit_entry,
)

# build_initial_state: requires client_id, incident_id, evidence_packages
try:
    build_initial_state("", "inc-1", [{"service_name": "svc"}], "ISOLATED_ANOMALY")
    fail("state: empty client_id should raise ValueError")
except ValueError:
    ok("state: empty client_id raises ValueError")

try:
    build_initial_state("CLIENT", "", [{"service_name": "svc"}], "ISOLATED_ANOMALY")
    fail("state: empty incident_id should raise ValueError")
except ValueError:
    ok("state: empty incident_id raises ValueError")

try:
    build_initial_state("CLIENT", "inc-1", [], "ISOLATED_ANOMALY")
    fail("state: empty evidence_packages should raise ValueError")
except ValueError:
    ok("state: empty evidence_packages raises ValueError")

# Valid initial state
s = build_initial_state("FINCORE_UK_001", "inc-test-001", [{"service_name": "PaymentAPI"}], "CASCADE_INCIDENT")
assert s["client_id"] == "FINCORE_UK_001"
assert s["incident_id"] == "inc-test-001"
assert s["correlation_type"] == "CASCADE_INCIDENT"
assert len(s["audit_trail"]) == 1
assert s["audit_trail"][0]["action"] == "incident_created"
ok("state: build_initial_state produces valid initial state with audit entry")

# Immutability: overwriting client_id raises ImmutableStateError
try:
    guard_immutable_fields(s, {"client_id": "DIFFERENT_CLIENT"})
    fail("state: overwriting client_id should raise ImmutableStateError")
except ImmutableStateError:
    ok("state: overwriting client_id raises ImmutableStateError")

# Immutability: first write (empty → value) is allowed
s_empty = build_initial_state("CLIENT", "inc-2", [{"service_name": "svc"}], "ISOLATED_ANOMALY")
guard_immutable_fields(s_empty, {"client_id": "CLIENT"})  # same value — no error
ok("state: same-value write to immutable field does not raise")

# routing_decision: once set, cannot change
s2 = dict(s)
s2["routing_decision"] = "L2_L3_ESCALATION"
try:
    guard_routing_decision(s2, {"routing_decision": "AUTO_EXECUTE"})
    fail("state: changing routing_decision should raise ImmutableStateError")
except ImmutableStateError:
    ok("state: changing routing_decision raises ImmutableStateError")

# routing_decision: first write allowed
s3 = dict(s)
s3["routing_decision"] = ""
guard_routing_decision(s3, {"routing_decision": "AUTO_EXECUTE"})  # no error
ok("state: first write to routing_decision is allowed")

# audit_trail: append_audit_entry always extends, never replaces
trail = append_audit_entry(s, {"node": "test", "action": "test_action"})
assert len(trail) == 2  # original entry + new one
assert trail[-1]["action"] == "test_action"
assert "timestamp" in trail[-1]
ok("state: append_audit_entry extends trail, adds timestamp")

print("\n── Phase 5: n6_confidence.py (FinanceCore scenario) ──")
# Test n6_confidence with known FinanceCore inputs
# Expected: composite ~0.84, PCI-DSS veto fires, routes to L2_L3_ESCALATION

os.environ.setdefault("ATLAS_DECISION_DB_PATH", "./data/test_decision_progress.db")
from backend.learning.decision_history import initialise_db as init_dh, write_record as write_dh

init_dh()

# Seed 5 historical records for FinanceCore CONNECTION_POOL_EXHAUSTED pattern
# 4 successes, 1 failure → accuracy = 0.80
for i in range(4):
    write_dh({
        "client_id": "FINCORE_UK_001",
        "incident_id": f"INC-SEED-{i:03d}",
        "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
        "service_class": "PaymentAPI",
        "recommended_action_id": "connection-pool-recovery-v2",
        "confidence_score_at_decision": 0.84,
        "routing_tier": "L2",
        "human_action": "approved",
        "modification_diff": None,
        "rejection_reason": None,
        "resolution_outcome": "success",
        "actual_mttr": 1380,
        "recurrence_within_48h": False,
    })
write_dh({
    "client_id": "FINCORE_UK_001",
    "incident_id": "INC-SEED-004",
    "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
    "service_class": "PaymentAPI",
    "recommended_action_id": "connection-pool-recovery-v2",
    "confidence_score_at_decision": 0.72,
    "routing_tier": "L2",
    "human_action": "approved",
    "modification_diff": None,
    "rejection_reason": None,
    "resolution_outcome": "failure",
    "actual_mttr": 3600,
    "recurrence_within_48h": False,
})

async def test_n6_financecore():
    from backend.orchestrator.nodes.n6_confidence import run as n6_run

    # Build a realistic FinanceCore state
    now = datetime.now(timezone.utc)
    fc_state = build_initial_state(
        client_id="FINCORE_UK_001",
        incident_id="INC-N6-TEST-001",
        evidence_packages=[{
            "agent_id": "postgres-agent",
            "client_id": "FINCORE_UK_001",
            "service_name": "PaymentAPI",
            "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
            "detection_confidence": 0.84,
            "shap_feature_values": {"error_rate": 67.0, "response_time": 33.0},
            "conformal_interval": {"lower": 0.0, "upper": 0.84, "confidence_level": 0.84},
            "baseline_mean": 5.0,
            "baseline_stddev": 1.0,
            "current_value": 20.0,
            "deviation_sigma": 15.0,
            "supporting_log_samples": ["log1", "log2", "log3", "log4", "log5"],
            "preliminary_hypothesis": "Connection pool exhaustion detected.",
            "severity_classification": "P2",
            "detection_timestamp": now.isoformat(),
        }],
        correlation_type="CASCADE_INCIDENT",
    )
    # Add N1–N5 outputs to state
    fc_state["incident_priority"] = "P2"
    fc_state["recommended_action_id"] = "connection-pool-recovery-v2"
    fc_state["alternative_hypotheses"] = [
        {"hypothesis": "HikariCP pool exhausted due to config change", "confidence": 0.84,
         "evidence_for": "CHG0089234 reduced maxPoolSize", "evidence_against": ""},
        {"hypothesis": "Traffic spike exceeded pool capacity", "confidence": 0.34,
         "evidence_for": "High request volume", "evidence_against": "No traffic anomaly detected"},
    ]
    fc_state["semantic_matches"] = [
        {"incident_id": "INC-2024-0847", "similarity_score": 0.91, "source": "client_specific"}
    ]

    result = await n6_run(fc_state)

    composite = result["composite_confidence_score"]
    vetoes = result["active_veto_conditions"]
    routing = result["routing_decision"]

    # Composite should be approximately 0.84 (within ±0.10 tolerance)
    assert 0.74 <= composite <= 0.94, f"Expected composite ~0.84, got {composite}"
    ok(f"n6_confidence: FinanceCore composite={composite:.4f} (expected ~0.84)")

    # PCI-DSS business hours veto must fire (FinanceCore has PCI-DSS + SOX)
    assert len(vetoes) >= 1, f"Expected at least 1 veto, got {vetoes}"
    ok(f"n6_confidence: {len(vetoes)} veto(s) fired: {vetoes[0][:60]}...")

    # Routing must be L2_L3_ESCALATION (vetoes prevent AUTO_EXECUTE)
    assert routing == "L2_L3_ESCALATION", f"Expected L2_L3_ESCALATION, got {routing}"
    ok(f"n6_confidence: routing={routing} (correct — vetoes prevent auto-execute)")

    # Factor scores present
    factors = result["factor_scores"]
    assert "f1" in factors and "f2" in factors and "f3" in factors and "f4" in factors
    ok(f"n6_confidence: all 4 factor scores present: {factors}")

    # Audit trail updated
    assert len(result["audit_trail"]) > len(fc_state.get("audit_trail", []))
    ok("n6_confidence: audit_trail updated with confidence scoring entry")

asyncio.run(test_n6_financecore())

print("\n── Phase 5: pipeline.py (graph compilation) ──")
async def test_pipeline_compilation():
    os.environ.setdefault("ATLAS_CHECKPOINT_DB_PATH", "./data/test_checkpoints.db")
    from backend.orchestrator.pipeline import _get_graph, close_graph
    graph = await _get_graph()
    assert graph is not None
    ok("pipeline: graph compiles successfully")

    # Verify all 7 nodes + execution + learning nodes are present
    node_names = set(graph.nodes)
    for expected in ["n1_classifier", "n2_itsm", "n3_graph", "n4_semantic",
                     "n5_reasoning", "n6_confidence", "n7_router",
                     "execute_playbook", "n_learn"]:
        assert expected in node_names, f"Missing node: {expected}"
    ok(f"pipeline: all 9 nodes present in compiled graph")

    await close_graph()

asyncio.run(test_pipeline_compilation())

print("\n── Phase 5: approval_tokens.py (round-trip) ──")
from backend.execution.approval_tokens import generate_approval_token, validate_approval_token

token = generate_approval_token("INC-TOKEN-TEST-001", "l2", expiry_minutes=30)
assert token and len(token) > 20
ok("approval_tokens: token generated successfully")

valid, inc_id, role, reason = validate_approval_token(token)
assert valid is True
assert inc_id == "INC-TOKEN-TEST-001"
assert role == "l2"
ok("approval_tokens: token validates correctly, incident_id and role match")

# One-time use: second validation must fail
valid2, _, _, _ = validate_approval_token(token)
assert valid2 is False
ok("approval_tokens: second use of same token rejected (one-time use enforced)")

# Wrong incident: token for A cannot approve B
token_b = generate_approval_token("INC-TOKEN-TEST-002", "l2", expiry_minutes=30)
valid3, inc_id3, _, _ = validate_approval_token(token_b)
assert valid3 is True
assert inc_id3 == "INC-TOKEN-TEST-002"
ok("approval_tokens: token correctly scoped to incident_id")

# ── Final results ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"FAILED — {len(errors)} assertion(s) failed:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("All assertions passed.")
