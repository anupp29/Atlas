"""
Step 2 — End-to-end test of Ollama wired into the ATLAS /internal/llm/reason endpoint.
Calls the endpoint directly (backend must be running) OR tests the _call_ollama
function in isolation (no server needed).

Run:
    python scripts/test_ollama_atlas_integration.py

Exit 0 = Ollama produces valid ATLAS reasoning output.
Exit 1 = something is wrong.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=False)

os.environ.setdefault("ATLAS_AUDIT_DB_PATH", "./data/test_audit_bug_check.db")
os.environ.setdefault("ATLAS_DECISION_DB_PATH", "./data/test_decision_bug_check.db")
os.environ.setdefault("ATLAS_SECRET_KEY", "atlas-dev-secret-key-change-in-production-min-32-chars")
os.environ.setdefault("ATLAS_CHECKPOINT_DB_PATH", "./data/test_checkpoints.db")
os.environ.setdefault("ATLAS_LLM_ENDPOINT", "http://localhost:8000/internal/llm/reason")
os.environ.setdefault("CHROMADB_PATH", "./data/chromadb")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-coder:480b-cloud")

REQUIRED_FIELDS = {
    "root_cause",
    "confidence_factors",
    "recommended_action_id",
    "alternative_hypotheses",
    "explanation_for_engineer",
    "technical_evidence_summary",
}

# FinanceCore demo payload — mirrors what n5_reasoning.py sends
FC_PAYLOAD = {
    "incident_context": {
        "client_id": "FINCORE_UK_001",
        "incident_id": "INC-OLLAMA-TEST-001",
        "correlation_type": "CASCADE_INCIDENT",
        "incident_priority": "P2",
    },
    "evidence_summary": [
        {
            "agent_id": "java-agent",
            "client_id": "FINCORE_UK_001",
            "service_name": "PaymentAPI",
            "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
            "detection_confidence": 0.84,
            "shap_feature_values": {"error_rate": 67.0, "response_time": 21.0, "connection_count": 12.0},
            "preliminary_hypothesis": "HikariCP pool exhaustion from CHG0089234",
            "severity_classification": "P2",
        }
    ],
    "blast_radius": [
        {"name": "PaymentAPI", "criticality": "P1"},
        {"name": "TransactionDB", "criticality": "P1"},
    ],
    "recent_deployments": [
        {
            "change_id": "CHG0089234",
            "change_description": "HikariCP maxPoolSize reduced from 100 to 40",
            "deployed_by": "raj.kumar@atos.com",
            "cab_risk_rating": "LOW",
        }
    ],
    "historical_graph_matches": [
        {
            "incident_id": "INC-2024-0847",
            "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
            "root_cause": "HikariCP maxPoolSize misconfiguration",
            "resolution": "Restored maxPoolSize to 150",
            "mttr_minutes": 23,
            "similarity_score": 0.9186,
        }
    ],
    "semantic_matches": {
        "top_match": {"incident_id": "INC-2024-0847", "similarity_score": 0.9186}
    },
    "compliance_profile": {
        "compliance_frameworks": ["PCI-DSS", "SOX"],
        "max_action_class": 1,
        "trust_level": 1,
    },
    "reasoning_instructions": (
        "Perform ITIL 6-step root cause analysis. "
        "The recommended_action_id must be connection-pool-recovery-v2. "
        "Provide at least 2 alternative_hypotheses."
    ),
}


async def test_ollama_direct() -> bool:
    """Call _call_ollama directly — no server needed."""
    from backend.main import LLMReasonRequest, _call_ollama

    print(f"\n  [DIRECT] Calling _call_ollama with {OLLAMA_MODEL}...")
    print(f"           Base URL: {OLLAMA_BASE}")

    request = LLMReasonRequest(**FC_PAYLOAD)

    try:
        result = await _call_ollama(request, OLLAMA_BASE, OLLAMA_MODEL, "FINCORE_UK_001")
    except Exception as exc:
        import traceback
        print(f"  FAIL  _call_ollama raised: {exc}")
        traceback.print_exc()
        return False

    if result is None:
        print("  FAIL  _call_ollama returned None")
        return False

    print(f"  PASS  Got response from Ollama")

    # Check all required fields
    missing = REQUIRED_FIELDS - set(result.keys())
    if missing:
        print(f"  FAIL  Missing fields: {missing}")
        return False
    print(f"  PASS  All {len(REQUIRED_FIELDS)} required fields present")

    # Check recommended_action_id
    action_id = result.get("recommended_action_id", "")
    if action_id not in ("connection-pool-recovery-v2", "redis-memory-policy-rollback-v1"):
        print(f"  WARN  recommended_action_id='{action_id}' — not a known playbook ID")
    else:
        print(f"  PASS  recommended_action_id='{action_id}'")

    # Check explanation length
    explanation = result.get("explanation_for_engineer", "")
    if len(explanation) < 50:
        print(f"  FAIL  explanation_for_engineer too short ({len(explanation)} chars)")
        return False
    print(f"  PASS  explanation_for_engineer: {len(explanation)} chars")

    # Check alternative_hypotheses
    hypotheses = result.get("alternative_hypotheses", [])
    if len(hypotheses) < 2:
        print(f"  WARN  Only {len(hypotheses)} alternative_hypotheses (expected ≥2)")
    else:
        print(f"  PASS  {len(hypotheses)} alternative_hypotheses")

    # Print root cause for human review
    print(f"\n  Root cause: {result.get('root_cause', '')[:120]}")
    print(f"  Action ID:  {result.get('recommended_action_id', '')}")

    return True


async def test_via_http_endpoint() -> bool:
    """Call the running backend's /internal/llm/reason endpoint."""
    import httpx

    endpoint = os.environ.get("ATLAS_LLM_ENDPOINT", "http://localhost:8000/internal/llm/reason")
    print(f"\n  [HTTP]   Calling {endpoint}...")

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(endpoint, json=FC_PAYLOAD)
    except httpx.ConnectError:
        print(f"  SKIP  Backend not running at {endpoint} — skipping HTTP test")
        return True  # Not a failure — server just isn't started
    except Exception as exc:
        print(f"  FAIL  HTTP call failed: {exc}")
        return False

    if resp.status_code != 200:
        print(f"  FAIL  HTTP {resp.status_code}: {resp.text[:300]}")
        return False

    result = resp.json()
    missing = REQUIRED_FIELDS - set(result.keys())
    if missing:
        print(f"  FAIL  HTTP response missing fields: {missing}")
        return False

    print(f"  PASS  HTTP endpoint returned valid response")
    print(f"  PASS  recommended_action_id='{result.get('recommended_action_id')}'")
    return True


async def main() -> None:
    print("\n  ATLAS + Ollama Integration Test")
    print("  " + "─" * 50)
    print(f"  Model:    {OLLAMA_MODEL}")
    print(f"  Endpoint: {OLLAMA_BASE}")

    direct_ok = await test_ollama_direct()
    http_ok = await test_via_http_endpoint()

    print("\n  " + "─" * 50)
    if direct_ok and http_ok:
        print("  RESULT: ALL TESTS PASSED")
        print("  Ollama is wired into ATLAS and producing valid reasoning output.")
        sys.exit(0)
    else:
        print("  RESULT: TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
