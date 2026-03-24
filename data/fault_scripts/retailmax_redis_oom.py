"""
RetailMax Redis OOM + Node.js cascade fault simulation.
Produces realistic Redis + Node.js log lines with timing offsets.
T+0 through T+60 minutes.

Usage:
    python data/fault_scripts/retailmax_redis_oom.py
    python data/fault_scripts/retailmax_redis_oom.py --replay
    python data/fault_scripts/retailmax_redis_oom.py --replay --endpoint http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone, timedelta

CLIENT_ID = "RETAILMAX_EU_002"
DEFAULT_ENDPOINT = "http://localhost:8000"


def _ts(offset_seconds: int = 0) -> str:
    t = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


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


def _emit(endpoint: str, source: str, severity: str, lines: list[str]) -> None:
    """Print lines to stdout and POST each to the ingest endpoint."""
    for line in lines:
        print(line, flush=True)
        _post_line(endpoint, source, severity, line)


# ---------------------------------------------------------------------------
# Log line generators
# ---------------------------------------------------------------------------

def _redis_normal(ts: str, mem_mb: int) -> list[str]:
    return [
        f"{ts} * {mem_mb}M used_memory_human:{mem_mb}M used_memory_peak_human:{mem_mb + 50}M",
        f"{ts} * connected_clients:42 blocked_clients:0 tracking_clients:0",
        f"{ts} * keyspace_hits:18234 keyspace_misses:1203 evicted_keys:0 expired_keys:12",
    ]


def _redis_memory_warning(ts: str, mem_mb: int, pct: int) -> list[str]:
    return [
        f"{ts} # WARNING: {pct}% of maxmemory reached ({mem_mb}M / 512M). Consider increasing maxmemory.",
        f"{ts} * used_memory:{mem_mb * 1024 * 1024} maxmemory:536870912 mem_fragmentation_ratio:1.23",
    ]


def _redis_oom(ts: str) -> list[str]:
    return [
        f"{ts} # OOM command not allowed when used memory > 'maxmemory'. command=SET key=cart:session:usr_8821 value_size=2048",
        f"{ts} # OOM command not allowed when used memory > 'maxmemory'. command=SETEX key=product:cache:sku_4421 ttl=3600",
        f"{ts} # OOM command not allowed when used memory > 'maxmemory'. command=HSET key=user:preferences:usr_9934",
        f"{ts} # Config maxmemory-policy is 'noeviction'. No keys will be evicted. All write commands will fail.",
    ]


def _redis_rejected(ts: str, count: int) -> list[str]:
    return [
        f"{ts} # ERR OOM: {count} commands rejected in last 10 seconds due to maxmemory policy noeviction",
        f"{ts} * rejected_connections:{count} total_commands_processed:98234",
    ]


def _node_normal(ts: str) -> list[str]:
    return [
        f"{ts} INFO  [CartService] GET /api/cart/usr_8821 → 200 OK (18ms)",
        f"{ts} INFO  [CartService] Redis cache HIT for cart:session:usr_8821",
        f"{ts} INFO  [ProductAPI] GET /api/products/sku_4421 → 200 OK (12ms)",
    ]


def _node_redis_error(ts: str) -> list[str]:
    return [
        f"{ts} ERROR [CartService] Redis write failed: ReplyError: OOM command not allowed when used memory > 'maxmemory'",
        f"{ts} ERROR [CartService] Failed to cache cart session for usr_8821: Redis OOM",
        f"{ts} WARN  [CartService] Falling back to database for cart:session:usr_8821 — Redis unavailable",
        f"{ts} ERROR [ProductAPI] Redis SETEX failed for product:cache:sku_4421: OOM",
    ]


def _node_unhandled_rejection(ts: str) -> list[str]:
    return [
        f"{ts} ERROR [CartService] UnhandledPromiseRejectionWarning: ReplyError: OOM command not allowed when used memory > 'maxmemory'",
        f"{ts} ERROR [CartService] UnhandledPromiseRejectionWarning: Unhandled promise rejection. This error originated either by throwing inside of an async function without a catch block",
        f"{ts} ERROR [ProductAPI] UnhandledPromiseRejectionWarning: ReplyError: OOM command not allowed when used memory > 'maxmemory'",
        f"{ts} WARN  [CartService] DeprecationWarning: Unhandled promise rejections are deprecated. In the future, promise rejections that are not handled will terminate the Node.js process",
    ]


def _node_latency_spike(ts: str) -> list[str]:
    return [
        f"{ts} WARN  [CartService] GET /api/cart/usr_9934 → 200 OK (2341ms) — latency spike detected",
        f"{ts} WARN  [ProductAPI] GET /api/products/sku_8821 → 200 OK (3102ms) — Redis fallback to DB",
        f"{ts} ERROR [CartService] POST /api/cart/usr_8821/checkout → 503 Service Unavailable (Redis write failed)",
    ]


# ---------------------------------------------------------------------------
# Scenario timeline
# ---------------------------------------------------------------------------

SCENARIO: list[tuple[int, str, str, list[str]]] = []

# T-3 min to T+0: normal operations
for _offset in range(-180, 0, 30):
    SCENARIO.append((_offset, "RedisCache", "INFO", _redis_normal(_ts(_offset), 280)))
    SCENARIO.append((_offset + 5, "CartService", "INFO", _node_normal(_ts(_offset + 5))))

# T+0 to T+20: memory climbing
for _offset in range(0, 20 * 60, 60):
    mem = 380 + (_offset // 60) * 7
    pct = int((mem / 512) * 100)
    SCENARIO.append((_offset, "RedisCache", "WARN", _redis_memory_warning(_ts(_offset), mem, pct)))
    SCENARIO.append((_offset + 20, "CartService", "INFO", _node_normal(_ts(_offset + 20))))

# T+20 to T+30: approaching maxmemory
for _offset in range(20 * 60, 30 * 60, 30):
    mem = 490 + (_offset - 20 * 60) // 60
    SCENARIO.append((_offset, "RedisCache", "WARN", _redis_memory_warning(_ts(_offset), mem, 96)))

# T+30: OOM hits — Redis agent fires
SCENARIO.append((30 * 60, "RedisCache", "ERROR", _redis_oom(_ts(30 * 60))))

# T+30 to T+45: OOM rejections + Node.js errors cascade
for _offset in range(30 * 60, 45 * 60, 15):
    SCENARIO.append((_offset, "RedisCache", "ERROR", _redis_rejected(_ts(_offset), 47 + _offset // 60)))
    SCENARIO.append((_offset + 5, "CartService", "ERROR", _node_redis_error(_ts(_offset + 5))))

# T+35: Node.js unhandled rejections spike — Node.js agent fires
for _offset in range(35 * 60, 45 * 60, 10):
    SCENARIO.append((_offset, "CartService", "ERROR", _node_unhandled_rejection(_ts(_offset))))

# T+45 to T+60: latency spikes, continued degradation
for _offset in range(45 * 60, 60 * 60, 20):
    SCENARIO.append((_offset, "CartService", "WARN", _node_latency_spike(_ts(_offset))))
    SCENARIO.append((_offset + 10, "RedisCache", "ERROR", _redis_oom(_ts(_offset + 10))))

SCENARIO.sort(key=lambda x: x[0])


def run(replay: bool = False, endpoint: str = DEFAULT_ENDPOINT) -> None:
    """Emit log lines and POST to ATLAS ingest endpoint."""
    print(f"[retailmax_redis_oom] Starting fault simulation. replay={replay} endpoint={endpoint}", flush=True)
    base_time = time.monotonic()

    for offset_seconds, source, severity, lines in SCENARIO:
        if not replay:
            target = base_time + offset_seconds
            now = time.monotonic()
            if target > now:
                time.sleep(target - now)

        _emit(endpoint, source, severity, lines)

    print("[retailmax_redis_oom] Scenario complete.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailMax Redis OOM fault simulation")
    parser.add_argument("--replay", action="store_true", help="Instant output, no sleep")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="ATLAS backend URL")
    args = parser.parse_args()
    run(replay=args.replay, endpoint=args.endpoint)
