# playbooks

Pre-approved, versioned playbook implementations. Each module exports a single `execute()` async function.

---

## Files

| File | Playbook ID | Technology | What it does |
|------|------------|-----------|-------------|
| `connection_pool_recovery_v2.py` | `connection-pool-recovery-v2` | Java Spring Boot | Restores HikariCP maxPoolSize via Spring Boot Actuator |
| `redis_memory_policy_rollback_v1.py` | `redis-memory-policy-rollback-v1` | Redis | Rolls back maxmemory-policy from noeviction to allkeys-lru |

---

## Five mandatory steps

Every playbook executes these five steps in order. No exceptions.

1. Pre-execution validation - confirms target is in expected state. If not, halts and escalates.
2. Action execution - the actual change, parameterised and bounded.
3. Success validation - monitors key metrics for recovery signal within timeout window.
4. Auto-rollback - fires automatically if success validation times out.
5. Immutable audit record - written regardless of outcome (success, failure, or rollback).

---

## connection_pool_recovery_v2.py

Resolves `CONNECTION_POOL_EXHAUSTED` on Java Spring Boot services.

Pre-validation:
- GET `/actuator/health` returns 200 or 503 (service reachable)
- Active connection count above 85% of max_connections
- No ATLAS action on this service in the last 10 minutes
- GET `/actuator` returns 200 (management endpoint accessible)

Action:
- POST `/actuator/env` with `{"name": "spring.datasource.hikari.maximum-pool-size", "value": "150"}`
- POST `/actuator/refresh` to apply the change

Success validation:
- Polls connection count every 30 seconds
- Success: two consecutive readings below 70% of max_connections
- Timeout: 10 minutes

Auto-rollback: restores previous maxPoolSize value, re-escalates to L2/L3.

Default parameters (adjustable by L2 Modify, bounded by weight correction):
```python
target_pool_size = 150
alert_threshold_pct = 0.85
success_threshold_pct = 0.70
success_consecutive_readings = 2
poll_interval_seconds = 30
max_validation_minutes = 10
```

---

## redis_memory_policy_rollback_v1.py

Resolves `REDIS_OOM` and `REDIS_COMMAND_REJECTED` on Redis instances.

Pre-validation:
- PING returns PONG (Redis reachable)
- CONFIG GET maxmemory-policy returns `noeviction` (fault policy is active)
- INFO memory shows used_memory / maxmemory above 85%

Action:
- CONFIG SET maxmemory-policy allkeys-lru
- CONFIG GET to verify change took effect

Success validation:
- Polls memory usage every 30 seconds
- Success: two consecutive readings below 75% of maxmemory
- Timeout: 10 minutes

Auto-rollback: restores `noeviction` to preserve fault state for L2 investigation, re-escalates.

Default parameters:
```python
target_policy = "allkeys-lru"
fault_policy = "noeviction"
alert_threshold_pct = 0.85
success_threshold_pct = 0.75
success_consecutive_readings = 2
poll_interval_seconds = 30
max_validation_minutes = 10
```

---

## Adding a new playbook

1. Create the module in this directory with an `execute()` async function
2. Register it in `playbook_library.py` with a `PlaybookMetadata` entry
3. Add a dispatch case in `pipeline._dispatch_playbook()`
4. Add rollback playbook if applicable
5. Run `_validate_registry_integrity()` (called automatically on import)
