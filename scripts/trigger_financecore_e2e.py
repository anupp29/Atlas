"""
End-to-end trigger: feeds FinanceCore fault scenario into ATLAS via /api/logs/ingest.
Runs in replay mode (no sleep) so the full scenario completes quickly.
Prints the incident state after the pipeline suspends for human review.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

BASE_URL = "http://localhost:8000"
CLIENT_ID = "FINCORE_UK_001"


def _infer_source(line: str) -> tuple[str, str]:
    """Return (source, severity) from a log line."""
    l = line.lower()
    if "hikari" in l or "spring" in l or "payment" in l or "http-nio" in l or "kubernetes" in l:
        return "PaymentAPI", "ERROR" if "error" in l or "fatal" in l else "INFO"
    if "utc [" in l or "sqlstate" in l or "pg_stat" in l:
        return "TransactionDB", "ERROR" if "error" in l or "fatal" in l else "INFO"
    return "PaymentAPI", "INFO"


def main() -> None:
    # Import the fault script scenario directly
    from data.fault_scripts.financecore_cascade import SCENARIO

    print(f"[trigger] Sending {len(SCENARIO)} scenario entries to {BASE_URL}", flush=True)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        sent = 0
        for _offset, lines in SCENARIO:
            for line in lines:
                source, severity = _infer_source(line)
                resp = client.post("/api/logs/ingest", json={
                    "client_id": CLIENT_ID,
                    "source": source,
                    "severity": severity,
                    "line": line,
                })
                if resp.status_code != 200:
                    print(f"[trigger] WARN: ingest returned {resp.status_code}: {resp.text[:100]}")
                sent += 1

        print(f"[trigger] Sent {sent} log lines. Waiting 15s for pipeline to process...", flush=True)
        time.sleep(15)

        # Check active incidents
        resp = client.get("/api/incidents/active")
        data = resp.json()
        print(f"\n[trigger] Active incidents: {data['count']}")
        for inc in data["incidents"]:
            print(f"  incident_id={inc['incident_id']}")
            print(f"  routing_decision={inc['routing_decision']}")
            print(f"  confidence={inc['composite_confidence_score']}")
            print(f"  execution_status={inc['execution_status']}")
            print(f"  servicenow_ticket={inc['servicenow_ticket_id']}")
            print()

        # Check audit log
        resp = client.get(f"/api/audit?client_id={CLIENT_ID}")
        audit = resp.json()
        print(f"[trigger] Audit records written: {audit['count']}")


if __name__ == "__main__":
    main()
