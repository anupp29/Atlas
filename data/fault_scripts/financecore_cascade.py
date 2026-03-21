"""
FinanceCore cascade fault simulation.
Produces realistic Java Spring Boot + PostgreSQL log lines with timing offsets.
T+0 through T+75 minutes. Run this to feed the detection agents during demo.

Usage:
    python data/fault_scripts/financecore_cascade.py
    python data/fault_scripts/financecore_cascade.py --replay  # instant output, no sleep
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta


def _ts(offset_seconds: int = 0) -> str:
    """Return ISO-8601 UTC timestamp with optional offset from now."""
    t = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Log line generators
# ---------------------------------------------------------------------------

def _pg_normal(ts: str) -> list[str]:
    return [
        f"{ts} UTC [1234] LOG:  connection received: host=10.0.1.45 port=52341",
        f"{ts} UTC [1235] LOG:  connection authorized: user=paymentapi database=transactions",
        f"{ts} UTC [1236] LOG:  duration: 12.345 ms  statement: SELECT * FROM transactions WHERE id=$1",
    ]


def _pg_warning(ts: str, pct: int) -> list[str]:
    return [
        f"{ts} UTC [1240] WARNING:  connection count at {pct}% of max_connections (max_connections=200)",
        f"{ts} UTC [1241] LOG:  duration: 145.221 ms  statement: SELECT COUNT(*) FROM pg_stat_activity",
    ]


def _pg_hikari_timeout(ts: str) -> list[str]:
    return [
        f"{ts} UTC [1250] ERROR:  HikariPool-1 - Connection is not available, request timed out after 30000ms",
        f"{ts} UTC [1251] ERROR:  Unable to acquire JDBC Connection; nested exception is com.zaxxer.hikari.pool.HikariPool$PoolTimeoutException",
    ]


def _pg_fatal(ts: str) -> list[str]:
    return [
        f"{ts} UTC [1260] FATAL:  remaining connection slots are reserved for non-replication superuser connections",
        f"{ts} UTC [1261] FATAL:  53300: too_many_connections — current count 198/200",
        f"{ts} UTC [1262] ERROR:  HikariPool-1 - Exception during pool initialization. com.zaxxer.hikari.pool.HikariPool$PoolInitializationException: Failed to initialize pool: FATAL: remaining connection slots are reserved",
    ]


def _java_503(ts: str) -> list[str]:
    return [
        f"{ts} INFO  [http-nio-8080-exec-3] c.f.payment.PaymentController - POST /api/v2/payments → 503 Service Unavailable",
        f"{ts} ERROR [http-nio-8080-exec-4] c.f.payment.PaymentService - Failed to acquire database connection after 30000ms",
        f"{ts} ERROR [http-nio-8080-exec-5] c.f.payment.PaymentService - com.zaxxer.hikari.pool.HikariPool$PoolTimeoutException: HikariPool-1 - Connection is not available, request timed out after 30000ms.",
        f"{ts} WARN  [http-nio-8080-exec-6] c.f.payment.PaymentController - Circuit breaker OPEN for TransactionDB — downstream unavailable",
    ]


def _java_normal(ts: str) -> list[str]:
    return [
        f"{ts} INFO  [http-nio-8080-exec-1] c.f.payment.PaymentController - POST /api/v2/payments → 200 OK (23ms)",
        f"{ts} INFO  [http-nio-8080-exec-2] c.f.payment.PaymentService - Transaction TXN-{int(time.time())} committed successfully",
        f"{ts} DEBUG [http-nio-8080-exec-3] c.f.payment.HikariMetrics - Pool stats: active=12 idle=28 waiting=0 total=40",
    ]


def _k8s_restart(ts: str) -> list[str]:
    return [
        f"{ts} WARN  [kubernetes] pod/payment-api-7d9f8b-xk2p9 — Liveness probe failed: HTTP probe failed with statuscode: 503",
        f"{ts} WARN  [kubernetes] pod/payment-api-7d9f8b-xk2p9 — Back-off restarting failed container payment-api",
        f"{ts} INFO  [kubernetes] pod/payment-api-7d9f8b-xk2p9 — Container payment-api restarted (restart count: 3)",
        f"{ts} INFO  [kubernetes] pod/payment-api-7d9f8b-xk2p9 — Pulling image financecore/payment-api:2.4.1",
    ]


# ---------------------------------------------------------------------------
# Scenario timeline
# ---------------------------------------------------------------------------

SCENARIO: list[tuple[int, list[str]]] = []

# T-3 min to T+0: normal operations (every 30s)
for _offset in range(-180, 0, 30):
    SCENARIO.append((_offset, _java_normal(_ts(_offset))))
    SCENARIO.append((_offset + 5, _pg_normal(_ts(_offset + 5))))

# T+0 to T+25: connection count warnings, increasing frequency
for _offset in range(0, 25 * 60, 30):
    pct = 72 + (_offset // 60) * 2  # climbs from 72% to ~120% (capped at 95 in messages)
    pct = min(pct, 95)
    SCENARIO.append((_offset, _pg_warning(_ts(_offset), pct)))
    SCENARIO.append((_offset + 10, _java_normal(_ts(_offset + 10))))

# T+25 to T+35: HikariCP timeouts, 1 per 10s
for _offset in range(25 * 60, 35 * 60, 10):
    SCENARIO.append((_offset, _pg_hikari_timeout(_ts(_offset))))
    SCENARIO.append((_offset + 5, _pg_warning(_ts(_offset + 5), 92)))

# T+35: FATAL connection pool exhaustion — PostgreSQL agent fires
SCENARIO.append((35 * 60, _pg_fatal(_ts(35 * 60))))

# T+45: Java 503 cascade — Java agent fires
for _offset in range(45 * 60, 60 * 60, 15):
    SCENARIO.append((_offset, _java_503(_ts(_offset))))

# T+60: Kubernetes pod restarts
SCENARIO.append((60 * 60, _k8s_restart(_ts(60 * 60))))
SCENARIO.append((62 * 60, _k8s_restart(_ts(62 * 60))))

# T+65 to T+75: continued degradation
for _offset in range(65 * 60, 75 * 60, 20):
    SCENARIO.append((_offset, _pg_fatal(_ts(_offset))))
    SCENARIO.append((_offset + 10, _java_503(_ts(_offset + 10))))

# Sort by offset
SCENARIO.sort(key=lambda x: x[0])


def run(replay: bool = False) -> None:
    """Emit log lines. In replay mode, no sleep — instant output for testing."""
    print(f"[financecore_cascade] Starting fault simulation. replay={replay}", flush=True)
    base_time = time.monotonic()

    for offset_seconds, lines in SCENARIO:
        if not replay:
            target = base_time + offset_seconds
            now = time.monotonic()
            if target > now:
                time.sleep(target - now)

        for line in lines:
            print(line, flush=True)

    print("[financecore_cascade] Scenario complete.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinanceCore cascade fault simulation")
    parser.add_argument("--replay", action="store_true", help="Instant output, no sleep")
    args = parser.parse_args()
    run(replay=args.replay)
