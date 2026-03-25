# execution

Playbook library and cryptographic approval tokens. The absolute boundary of what ATLAS is permitted to do autonomously.

---

## Files

| File | What it does |
|------|-------------|
| `playbook_library.py` | Registry of all pre-approved playbooks. Read-only at runtime. Provides lookup, validation, and semantic search. |
| `approval_tokens.py` | HMAC-SHA256 one-time approval tokens for PCI-DSS and SOX dual sign-off. |
| `playbooks/connection_pool_recovery_v2.py` | Restores HikariCP connection pool size via Spring Boot Actuator. |
| `playbooks/redis_memory_policy_rollback_v1.py` | Rolls back Redis maxmemory-policy from noeviction to allkeys-lru. |

---

## playbook_library.py

Every action ATLAS can take is registered here. No ad-hoc commands. No LLM-generated scripts. If a playbook ID is not in this registry, it cannot be executed.

### Registered playbooks

| ID | Technology | Action class | Auto-execute |
|----|-----------|-------------|-------------|
| `connection-pool-recovery-v2` | Java Spring Boot | 1 | Yes |
| `connection-pool-recovery-v2-rollback` | Java Spring Boot | 1 | Yes |
| `redis-memory-policy-rollback-v1` | Redis | 1 | Yes |
| `redis-memory-policy-rollback-v1-rollback` | Redis | 1 | Yes |

### Action classes

| Class | Examples | Auto-execute eligible |
|-------|---------|----------------------|
| 1 | Service restart, cache clear, config parameter tuning | Yes, if threshold and vetoes pass |
| 2 | Redeployment, infrastructure scaling | No, always human |
| 3 | Database operations, network changes, production data | Never, permanent ceiling |

Class 3 playbooks cannot be registered with `auto_execute_eligible=True`. The registry validates this on import and raises `RuntimeError` if violated.

### Key functions

```python
get_playbook("connection-pool-recovery-v2")   # returns PlaybookMetadata or None
validate_action_id("connection-pool-recovery-v2")  # returns bool, used by N5
list_playbooks()                               # all registered playbooks
get_playbooks_for_anomaly("REDIS_OOM")         # playbooks that address this anomaly type
semantic_search("connection leak pool size")   # keyword overlap search, used on L2 rejection
```

### Each playbook has five mandatory components

1. Pre-execution validation - confirms target is in expected state before acting
2. Action execution - parameterised, bounded, specific
3. Success validation - monitors key metrics for recovery signal
4. Auto-rollback - fires automatically if success validation times out
5. Immutable audit record - written regardless of outcome

---

## approval_tokens.py

Cryptographic one-time tokens for dual sign-off on PCI-DSS and SOX clients.

Uses HMAC-SHA256 with the `ATLAS_SECRET_KEY` environment variable. The key must be at least 32 bytes. Missing or short key raises `RuntimeError` at import time.

Nonces are persisted to SQLite so replay attacks are blocked across server restarts.

### Token lifecycle

```python
# Generate (primary approver clicks Approve on dashboard)
token = generate_approval_token(incident_id, "secondary", expiry_minutes=30)
# Token is sent to secondary approver via Slack

# Validate (secondary approver clicks the link)
valid, incident_id, role, reason = validate_approval_token(token)
# valid=False if: wrong signature, expired, or already used
```

### Validation checks (in order)

1. Token format valid (two parts separated by `.`)
2. HMAC signature correct (constant-time comparison)
3. Token not expired
4. Nonce not previously used (checked against SQLite, survives restarts)

After successful validation, the nonce is marked used immediately. The same token cannot be validated twice.

---

## playbooks/

Each playbook module exports a single `execute()` async function. The pipeline calls it by dispatching on `action_id`.

### connection_pool_recovery_v2.py

Restores HikariCP `maxPoolSize` on a Java Spring Boot service via Spring Boot Actuator:
1. GET `/actuator/health` - confirms service is reachable
2. Checks active connection count is above alert threshold (85%)
3. POST `/actuator/env` with new pool size
4. POST `/actuator/refresh` to apply
5. Polls connection count every 30 seconds for up to 10 minutes
6. Auto-rollback if count does not drop below 70% within timeout

### redis_memory_policy_rollback_v1.py

Rolls back Redis `maxmemory-policy` from `noeviction` to `allkeys-lru`:
1. PING - confirms Redis is reachable
2. CONFIG GET `maxmemory-policy` - confirms fault policy is active
3. Checks memory usage is above 85%
4. CONFIG SET `maxmemory-policy allkeys-lru`
5. CONFIG GET to verify change took effect
6. Polls memory usage every 30 seconds for up to 10 minutes
7. Auto-rollback to `noeviction` if memory does not drop below 75% within timeout
