# fault_scripts

Deterministic fault simulators. Same log lines, same timing, every run. Used to trigger the detection agents during demo and testing.

---

## Files

| File | Client | Fault scenario |
|------|--------|---------------|
| `financecore_cascade.py` | FinanceCore | HikariCP connection pool exhaustion cascade (PostgreSQL + Java agents) |
| `retailmax_redis_oom.py` | RetailMax | Redis OOM from maxmemory-policy change (Redis agent) |

---

## financecore_cascade.py

Simulates the FinanceCore HikariCP cascade. Posts log lines to `http://localhost:8000/api/logs/ingest`.

Timeline:
- T-3min to T+0: normal Java and PostgreSQL logs
- T+0 to T+25min: PostgreSQL connection count warnings, increasing from 72% to 95%
- T+25 to T+35min: HikariCP timeout errors every 10 seconds
- T+35min: FATAL connection pool exhaustion - PostgreSQL agent fires
- T+45min: Java HTTP 503 errors - Java agent fires, cascade correlation confirms
- T+60min: Kubernetes pod restarts
- T+65 to T+75min: continued degradation

```bash
# Real-time (follows actual timing offsets)
python data/fault_scripts/financecore_cascade.py

# Instant output for testing (no sleep)
python data/fault_scripts/financecore_cascade.py --replay

# Point at a different backend
python data/fault_scripts/financecore_cascade.py --endpoint http://localhost:8000
```

---

## retailmax_redis_oom.py

Simulates the RetailMax Redis OOM scenario. Posts Redis log lines showing memory pressure and rejected commands.

```bash
python data/fault_scripts/retailmax_redis_oom.py
python data/fault_scripts/retailmax_redis_oom.py --replay
```

---

## What happens after injection

1. Log lines arrive at `/api/logs/ingest`
2. Normaliser converts to unified schema
3. CMDB enricher attaches service context
4. Event queue routes to the appropriate specialist agent
5. Agent detects anomaly, builds EvidencePackage
6. Correlation engine classifies CASCADE_INCIDENT
7. Pipeline starts: N1 through N7
8. Incident appears on dashboard, briefing card populates
9. Human approves via dashboard or API

The entire flow from fault injection to briefing card ready takes under 90 seconds.
