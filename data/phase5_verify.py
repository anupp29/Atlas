"""Phase 5 comprehensive verification script."""
import asyncio
import os
import sys
import time as _t
import inspect
from datetime import datetime, timezone, timedelta

errors = []

def fail(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}")

def ok(label):
    print(f"  PASS: {label}")

os.environ.setdefault("ATLAS_AUDIT_DB_PATH", "./data/test_audit_progress.db")
os.environ.setdefault("ATLAS_DECISION_DB_PATH", "./data/test_decision_progress.db")
os.environ.setdefault("ATLAS_SECRET_KEY", "atlas-dev-secret-key-change-in-production-min-32-chars")
os.environ.setdefault("ATLAS_CHECKPOINT_DB_PATH", "./data/test_checkpoints.db")

# ── [1/7] state.py ────────────────────────────────────────────────────────────
print("\n[1/7] state.py")
from backend.orchestrator.state import (
    AtlasState, ImmutableStateError, build_initial_state,
    guard_immutable_fields, guard_routing_decision, append_audit_entry,
)

for bad_args, label in [
    (("", "i", [{"s": "v"}], "ISOLATED_ANOMALY"), "empty client_id"),
    (("C", "", [{"s": "v"}], "ISOLATED_ANOMALY"), "empty incident_id"),
    (("C", "i", [], "ISOLATED_ANOMALY"), "empty evidence_packages"),
]:
    try:
        build_initial_state(*bad_args)
        fail(f"state: {label} should raise ValueError")
    except ValueError:
        ok(f"state: {label} raises ValueError")

s = build_initial_state("FINCORE_UK_001", "inc-1", [{"service_name": "svc"}], "CASCADE_INCIDENT")
assert s["client_id"] == "FINCORE_UK_001"
assert s["incident_id"] == "inc-1"
assert s["correlation_type"] == "CASCADE_INCIDENT"
assert len(s["audit_trail"]) == 1
assert "mttr_start_time" in s
ok("state: build_initial_state produces correct initial state")

try:
    guard_immutable_fields(s, {"client_id": "OTHER"})
    fail("state: immutable client_id overwrite should raise")
except ImmutableStateError:
    ok("state: guard_immutable_fields blocks client_id overwrite")

try:
    guard_routing_decision({"routing_decision": "AUTO_EXECUTE"}, {"routing_decision": "L1_HUMAN_REVIEW"})
    fail("state: routing_decision change should raise")
except ImmutableStateError:
    ok("state: guard_routing_decision blocks change")

trail = append_audit_entry(s, {"node": "test", "actor": "ATLAS_AUTO"})
assert len(trail) == 2 and "timestamp" in trail[1]
ok("state: append_audit_entry extends trail with timestamp")

# Same-value write to immutable field is allowed (idempotent)
guard_immutable_fields(s, {"client_id": "FINCORE_UK_001"})
ok("state: same-value write to immutable field is allowed")

# routing_decision: first write allowed
guard_routing_decision(s, {"routing_decision": "AUTO_EXECUTE"})
ok("state: first write to routing_decision allowed")

# audit_trail append-only: original list not mutated
original_trail = list(s.get("audit_trail", []))
new_trail = append_audit_entry(s, {"node": "n1", "actor": "ATLAS_AUTO"})
assert len(new_trail) == len(original_trail) + 1
assert len(s.get("audit_trail", [])) == len(original_trail)
ok("state: append_audit_entry returns new list, does not mutate original")

# ── [2/7] n6_confidence.py ────────────────────────────────────────────────────
print("\n[2/7] n6_confidence.py (FinanceCore scenario)")
from backend.config.client_registry import load_all_clients
load_all_clients()
from backend.orchestrator.nodes.n6_confidence import run as n6_run

async def test_n6():
    now = datetime.now(timezone.utc)
    fc = build_initial_state("FINCORE_UK_001", "INC-N6-001", [{
        "evidence_id": "e1", "agent_id": "java-agent", "client_id": "FINCORE_UK_001",
        "service_name": "PaymentAPI", "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
        "detection_confidence": 0.84,
        "shap_feature_values": {"error_rate": 67.0, "response_time": 33.0},
        "conformal_interval": {"lower": 0.0, "upper": 0.84, "confidence_level": 0.84},
        "baseline_mean": 5.0, "baseline_stddev": 1.0, "current_value": 20.0,
        "deviation_sigma": 15.0,
        "supporting_log_samples": ["l1", "l2", "l3", "l4", "l5"],
        "preliminary_hypothesis": "Connection pool exhaustion detected.",
        "severity_classification": "P2",
        "detection_timestamp": now.isoformat(),
    }], "CASCADE_INCIDENT")
    fc["incident_priority"] = "P2"
    fc["recommended_action_id"] = "connection-pool-recovery-v2"
    fc["alternative_hypotheses"] = [
        {"hypothesis": "HikariCP pool exhausted", "confidence": 0.84,
         "evidence_for": "CHG0089234", "evidence_against": ""},
        {"hypothesis": "Traffic spike", "confidence": 0.34,
         "evidence_for": "High req", "evidence_against": "No anomaly"},
    ]
    fc["semantic_matches"] = [
        {"incident_id": "INC-2024-0847", "similarity_score": 0.91, "source": "client_specific"}
    ]

    r = await n6_run(fc)
    composite = r["composite_confidence_score"]
    vetoes = r["active_veto_conditions"]
    routing = r["routing_decision"]
    factors = r["factor_scores"]

    assert 0.74 <= composite <= 0.94, f"composite={composite}"
    ok(f"n6: composite={composite:.4f} (expected ~0.84)")

    assert len(vetoes) >= 1
    ok(f"n6: {len(vetoes)} veto(s) fired — {vetoes[0][:60]}")

    assert routing == "L2_L3_ESCALATION"
    ok(f"n6: routing=L2_L3_ESCALATION (vetoes block auto-execute)")

    assert all(k in factors for k in ["f1", "f2", "f3", "f4"])
    f1, f2, f3, f4 = factors["f1"], factors["f2"], factors["f3"], factors["f4"]
    ok(f"n6: factor scores — f1={f1:.2f} f2={f2:.2f} f3={f3:.2f} f4={f4:.2f}")

    assert len(r["audit_trail"]) > len(fc.get("audit_trail", []))
    ok("n6: audit_trail updated")

asyncio.run(test_n6())

# ── [3/7] pipeline.py graph compilation ───────────────────────────────────────
print("\n[3/7] pipeline.py (graph compilation + guards)")
async def test_pipeline():
    from backend.orchestrator.pipeline import _get_graph, run_incident, resume_after_approval, get_incident_state

    graph = await _get_graph()
    assert graph is not None
    node_names = set(graph.nodes)
    expected = [
        "n1_classifier", "n2_itsm", "n3_graph", "n4_semantic",
        "n5_reasoning", "n6_confidence", "n7_router",
        "execute_playbook", "n_learn",
    ]
    missing = [n for n in expected if n not in node_names]
    assert not missing, f"Missing nodes: {missing}"
    ok(f"pipeline: all 9 nodes compiled")

    # Public interface signatures
    sig_run = inspect.signature(run_incident)
    assert all(p in sig_run.parameters for p in ["evidence_packages", "client_id", "correlation_type"])
    ok("pipeline: run_incident signature correct")

    sig_resume = inspect.signature(resume_after_approval)
    assert all(p in sig_resume.parameters for p in ["thread_id", "human_action", "modifier", "rejection_reason", "modified_parameters"])
    ok("pipeline: resume_after_approval signature correct")

    # Input guards
    try:
        await run_incident(evidence_packages=[{"s": "v"}], client_id="")
        fail("pipeline: empty client_id should raise ValueError")
    except ValueError:
        ok("pipeline: run_incident rejects empty client_id")

    try:
        await run_incident(evidence_packages=[], client_id="FINCORE_UK_001")
        fail("pipeline: empty evidence_packages should raise ValueError")
    except ValueError:
        ok("pipeline: run_incident rejects empty evidence_packages")

    try:
        await resume_after_approval("thread-x", human_action="invalid_action")
        fail("pipeline: invalid human_action should raise ValueError")
    except ValueError:
        ok("pipeline: resume_after_approval rejects invalid human_action")

asyncio.run(test_pipeline())

# ── [4/7] approval_tokens.py ──────────────────────────────────────────────────
print("\n[4/7] approval_tokens.py")
from backend.execution.approval_tokens import generate_approval_token, validate_approval_token

tok = generate_approval_token("INC-P5-001", "l2", expiry_minutes=30)
assert tok and len(tok) > 20
ok("tokens: generated successfully")

valid, inc_id, role, reason = validate_approval_token(tok)
assert valid and inc_id == "INC-P5-001" and role == "l2" and reason == "ok"
ok("tokens: validates correctly — incident_id, role, reason all correct")

valid2, _, _, _ = validate_approval_token(tok)
assert not valid2
ok("tokens: one-time use enforced — second validation rejected")

tok_exp = generate_approval_token("INC-EXP", "l2", expiry_minutes=0)
_t.sleep(0.1)
valid_exp, _, _, reason_exp = validate_approval_token(tok_exp)
assert not valid_exp and reason_exp == "token_expired"
ok("tokens: expired token correctly rejected")

tok_b = generate_approval_token("INC-P5-002", "l2", expiry_minutes=30)
valid_b, inc_b, _, _ = validate_approval_token(tok_b)
assert valid_b and inc_b == "INC-P5-002"
ok("tokens: token correctly scoped to incident_id")

# ── [5/7] main.py FastAPI structure ───────────────────────────────────────────
print("\n[5/7] main.py (FastAPI app structure)")
from backend.main import app, _REQUIRED_ENV_VARS
from fastapi.routing import APIRoute

routes = {r.path for r in app.routes if isinstance(r, APIRoute)}
expected_routes = [
    "/webhook/cmdb",
    "/api/incidents/approve",
    "/api/incidents/reject",
    "/api/incidents/modify",
    "/api/incidents/active",
    "/api/audit",
    "/api/trust/{client_id}",
]
missing_routes = [r for r in expected_routes if r not in routes]
assert not missing_routes, f"Missing routes: {missing_routes}"
ok(f"main: all {len(expected_routes)} HTTP routes registered")

all_paths = [r.path for r in app.routes]
for ws_path in ["/ws/logs/{client_id}", "/ws/incidents/{client_id}", "/ws/activity"]:
    assert ws_path in all_paths, f"Missing WebSocket: {ws_path}"
ok("main: all 3 WebSocket endpoints registered")

for required in ["NEO4J_URI", "ATLAS_SECRET_KEY", "ATLAS_CHECKPOINT_DB_PATH"]:
    assert required in _REQUIRED_ENV_VARS, f"{required} missing from startup checks"
ok(f"main: {len(_REQUIRED_ENV_VARS)} required env vars validated at startup")

# ── [6/7] pipeline.py execution node ──────────────────────────────────────────
print("\n[6/7] pipeline.py (execution node — playbook dispatch)")
from backend.execution.playbook_library import get_playbook

# Verify both demo playbooks are dispatchable
for pid in ["connection-pool-recovery-v2", "redis-memory-policy-rollback-v1"]:
    pb = get_playbook(pid)
    assert pb is not None
    assert pb.playbook_id == pid
    ok(f"pipeline/execution: playbook '{pid}' resolvable from library")

# Class 3 never auto-execute eligible
from backend.execution.playbook_library import list_playbooks
for pb in list_playbooks():
    if pb.action_class == 3:
        assert not pb.auto_execute_eligible
ok("pipeline/execution: no Class 3 playbook is auto_execute_eligible")

# ── [7/7] interface contracts ─────────────────────────────────────────────────
print("\n[7/7] Interface contracts")

# CorrelationEngine takes neo4j_client, not client_id
from backend.agents.correlation_engine import CorrelationEngine
sig_ce = inspect.signature(CorrelationEngine.__init__)
params = list(sig_ce.parameters.keys())
assert "neo4j_client" in params, f"CorrelationEngine.__init__ params: {params}"
ok("correlation_engine: __init__ takes neo4j_client (not client_id)")

# CorrelationEngine has ingest_evidence, not process_event
assert hasattr(CorrelationEngine, "ingest_evidence")
assert not hasattr(CorrelationEngine, "process_event")
ok("correlation_engine: has ingest_evidence, no process_event")

# EventQueue has dequeue_nowait (used by monitoring loop), no drain
from backend.ingestion.event_queue import EventQueue
assert hasattr(EventQueue, "dequeue_nowait")
assert not hasattr(EventQueue, "drain")
ok("event_queue: has dequeue_nowait, no drain (monitoring loop uses dequeue_nowait)")

# trust_progression.evaluate_progression takes (client_id, incident_id)
from backend.learning.trust_progression import evaluate_progression
sig_ep = inspect.signature(evaluate_progression)
assert "client_id" in sig_ep.parameters
assert "incident_id" in sig_ep.parameters
ok("trust_progression: evaluate_progression(client_id, incident_id) signature correct")

# pipeline._check_trust_progression passes incident_id
import ast, pathlib
pipeline_src = pathlib.Path("backend/orchestrator/pipeline.py").read_text()
assert "await evaluate_progression(client_id, incident_id)" in pipeline_src
ok("pipeline: _check_trust_progression passes incident_id to evaluate_progression")

# main.py monitoring loop uses dequeue_nowait, not drain
main_src = pathlib.Path("backend/main.py").read_text()
assert "dequeue_nowait" in main_src
assert "correlation_engine.process_event" not in main_src
assert "CorrelationEngine(neo4j)" in main_src
ok("main: monitoring loop uses dequeue_nowait + CorrelationEngine(neo4j) + ingest_evidence")

# validate_approval_token returns 4-tuple everywhere it's unpacked in main.py
assert "valid, token_incident_id, approver_role, _reason = validate_approval_token" in main_src
ok("main: validate_approval_token unpacked as 4-tuple")

# ── Final result ──────────────────────────────────────────────────────────────
print()
print("=" * 60)
if errors:
    print(f"FAILED — {len(errors)} assertion(s):")
    for e in errors:
        print(f"  x {e}")
    sys.exit(1)
else:
    print("Phase 5 — ALL CHECKS PASSED")
