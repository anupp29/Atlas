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

print("All assertions passed.")
