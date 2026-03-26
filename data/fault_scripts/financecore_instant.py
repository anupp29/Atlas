"""
FinanceCore INSTANT fault simulation - for demos.
Fires critical errors immediately with no buildup.

Usage:
    python data/fault_scripts/financecore_instant.py
    python data/fault_scripts/financecore_instant.py --endpoint http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

CLIENT_ID = "FINCORE_UK_001"
DEFAULT_ENDPOINT = "http://localhost:8000"


def _post_line(endpoint: str, source: str, severity: str, line: str) -> None:
    """POST a single log line to the ATLAS ingest endpoint."""
    payload = json.dumps({
        "client_id": CLIENT_ID,
        "source": source,
        "severity": severity,
        "line": line,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{endpoint}/api/logs/ingest",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except urllib.error.URLError as exc:
        print(f"[WARN] ingest failed: {exc}", file=sys.stderr, flush=True)


def run(endpoint: str = DEFAULT_ENDPOINT) -> None:
    """Emit critical errors immediately."""
    print(f"[financecore_instant] Injecting CRITICAL errors NOW. endpoint={endpoint}", flush=True)
    
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    # FATAL: Connection pool exhausted
    fatal_logs = [
        f"{ts} UTC [1260] FATAL:  remaining connection slots are reserved for non-replication superuser connections",
        f"{ts} UTC [1261] FATAL:  53300: too_many_connections — current count 198/200",
        f"{ts} UTC [1262] ERROR:  HikariPool-1 - Exception during pool initialization. com.zaxxer.hikari.pool.HikariPool$PoolInitializationException: Failed to initialize pool: FATAL: remaining connection slots are reserved",
    ]
    
    for line in fatal_logs:
        print(line, flush=True)
        _post_line(endpoint, "TransactionDB", "ERROR", line)
    
    # ERROR: Java 503 cascade
    java_errors = [
        f"{ts} INFO  [http-nio-8080-exec-3] c.f.payment.PaymentController - POST /api/v2/payments → 503 Service Unavailable",
        f"{ts} ERROR [http-nio-8080-exec-4] c.f.payment.PaymentService - Failed to acquire database connection after 30000ms",
        f"{ts} ERROR [http-nio-8080-exec-5] c.f.payment.PaymentService - com.zaxxer.hikari.pool.HikariPool$PoolTimeoutException: HikariPool-1 - Connection is not available, request timed out after 30000ms.",
        f"{ts} WARN  [http-nio-8080-exec-6] c.f.payment.PaymentController - Circuit breaker OPEN for TransactionDB — downstream unavailable",
    ]
    
    for line in java_errors:
        print(line, flush=True)
        _post_line(endpoint, "PaymentAPI", "ERROR", line)
    
    # ERROR: API Gateway cascade
    gateway_errors = [
        f"{ts} ERROR [gateway] upstream_response_time=30.001 status=503 service=payment-api",
        f"{ts} ERROR [gateway] circuit_breaker_state=OPEN service=payment-api consecutive_failures=5",
        f"{ts} WARN  [gateway] health_check_failed service=payment-api endpoint=/actuator/health",
    ]
    
    for line in gateway_errors:
        print(line, flush=True)
        _post_line(endpoint, "APIGateway", "ERROR", line)
    
    print("[financecore_instant] CRITICAL errors injected. Watch ATLAS detect and respond.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinanceCore instant fault simulation")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="ATLAS backend URL")
    args = parser.parse_args()
    run(endpoint=args.endpoint)
