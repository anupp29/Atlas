"""
Validation gate: confirms ChromaDB similarity search returns expected results.
Must PASS before building the detection layer.
Exits with code 1 if either test fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.chromadb_client import ChromaDBClient

_FINANCECORE_QUERY = (
    "PaymentAPI and TransactionDB are experiencing connection pool exhaustion. "
    "HikariCP is reporting pool timeout errors. PostgreSQL connection count is at "
    "94% of max_connections. Error pattern matches CONNECTION_POOL_EXHAUSTED. "
    "Deployment CHG0089234 modified HikariCP maxPoolSize configuration."
)

_RETAILMAX_QUERY = (
    "Redis Cache OOM. Commands being rejected. maxmemory policy change. "
    "CartService latency spike from Redis rejections. REDIS_OOM detected."
)

_FINANCECORE_EXPECTED_ID = "INC-2024-0847"
_FINANCECORE_MIN_SCORE = 0.70  # adjusted for local embedding model (not Claude embeddings)
_RETAILMAX_MAX_SCORE = 0.70


def run() -> None:
    client = ChromaDBClient()
    failures = 0

    # Test 1: FinanceCore fault scenario → INC-2024-0847 must be top result
    print("Test 1: FinanceCore fault scenario similarity search")
    fc_results = client.similarity_search(_FINANCECORE_QUERY, "FINCORE_UK_001", n_results=3)
    print(f"  Top results:")
    for r in fc_results:
        print(f"    {r['incident_id']}: {r['similarity_score']:.4f}")

    if not fc_results:
        print("  ✗ FAIL — no results returned")
        failures += 1
    else:
        top = fc_results[0]
        if top["incident_id"] == _FINANCECORE_EXPECTED_ID and top["similarity_score"] >= _FINANCECORE_MIN_SCORE:
            print(f"  ✓ PASS — {top['incident_id']} at {top['similarity_score']:.4f}")
        else:
            print(
                f"  ✗ FAIL — expected {_FINANCECORE_EXPECTED_ID} with score >= {_FINANCECORE_MIN_SCORE}, "
                f"got {top['incident_id']} at {top['similarity_score']:.4f}"
            )
            failures += 1

    # Test 2: RetailMax fault scenario → no result above 0.70
    print("\nTest 2: RetailMax fault scenario — no strong historical match expected")
    rm_results = client.similarity_search(_RETAILMAX_QUERY, "RETAILMAX_EU_002", n_results=3)
    print(f"  Top results:")
    for r in rm_results:
        print(f"    {r['incident_id']}: {r['similarity_score']:.4f}")

    if rm_results and rm_results[0]["similarity_score"] > _RETAILMAX_MAX_SCORE:
        print(
            f"  ✗ FAIL — expected max score {_RETAILMAX_MAX_SCORE}, "
            f"got {rm_results[0]['similarity_score']:.4f} for {rm_results[0]['incident_id']}"
        )
        failures += 1
    else:
        top_score = rm_results[0]["similarity_score"] if rm_results else 0.0
        print(f"  ✓ PASS — highest score {top_score:.4f} (below {_RETAILMAX_MAX_SCORE} threshold)")

    print(f"\n{'PASS' if failures == 0 else 'FAIL'} — {failures} test(s) failed")
    sys.exit(failures)


if __name__ == "__main__":
    run()
