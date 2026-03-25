# ingestion

Event ingestion pipeline. Three paths in, one unified schema out. Every event is tagged with `client_id` at creation and enriched with CMDB context before agents see it.

---

## Files

| File | What it does |
|------|-------------|
| `normaliser.py` | Converts raw events from any ingestion path into the unified ATLAS OTel schema. Tags `client_id` at creation. |
| `cmdb_enricher.py` | Attaches CMDB context (criticality, SLA threshold, open change records, owner team) to every normalised event. 60-second TTL cache per service. |
| `event_queue.py` | Per-client async event queue. Strict isolation: no method allows reading across client queues. Simulates Kafka for the MVP. |
| `adapters/java_adapter.py` | Parses native Spring Boot log format. Maps exception class names to ATLAS error taxonomy. Reassembles multi-line stack traces. |
| `adapters/postgres_adapter.py` | Parses native PostgreSQL log format. Maps SQLSTATE codes to ATLAS error taxonomy. FATAL always maps to ERROR. |

---

## Three ingestion paths

**Path A - Modern apps (OTel SDK)**
Applications instrumented with OpenTelemetry send structured JSON directly. No adapter needed.

**Path B - Legacy systems (adapters)**
Purpose-built adapters read native log formats and output to the unified schema. The Java and PostgreSQL adapters are implemented. Each adapter is a standalone module: build once, deploy to every client running that technology.

**Path C - Existing tools (API pull)**
Reads from Splunk, Dynatrace, Datadog, CloudWatch via their APIs. Clients keep existing investments.

All three paths converge into the normaliser, then the CMDB enricher, then the event queue.

---

## normaliser.py

Converts any raw event into the unified schema:

```
atlas_event_id          uuid4, generated here
client_id               mandatory, tagged at creation, immutable
timestamp               ISO-8601 UTC, parsed from multiple formats
source_system           service name
source_type             technology class
severity                ERROR / WARN / INFO / DEBUG (normalised from FATAL, CRITICAL, etc.)
error_code              ATLAS internal taxonomy
message                 normalised description
raw_payload             original log line, always preserved exactly
deployment_id           linked to CMDB change record if available
```

Events without `client_id` are rejected and return `None`. Events with oversized payloads (over 1MB) are truncated with a flag.

---

## cmdb_enricher.py

Attaches CMDB context from Neo4j to every normalised event. Agents never perform their own CMDB lookups.

Fields added:
- `ci_class`, `ci_version`
- `business_service_name`
- `criticality_tier` (P1/P2/P3/P4)
- `open_change_records` (change IDs from last 7 days)
- `sla_breach_threshold_minutes`
- `owner_team`
- `cmdb_enrichment_status` (enriched / cache_hit / not_found)

Cache is per `(client_id, service_name)` with 60-second TTL. If Neo4j is unavailable, serves stale cache if available, otherwise continues with `None` values. Never blocks the pipeline.

---

## event_queue.py

In-memory async queue, one per client. Maximum 10,000 events per client. When full, the oldest event is dropped and logged.

```python
queue = get_event_queue()  # module-level singleton

# Enqueue (raises ValueError if event client_id != queue client_id)
await queue.enqueue(event, client_id="FINCORE_UK_001")

# Dequeue (blocking)
event = await queue.dequeue("FINCORE_UK_001")

# Dequeue (non-blocking, returns None if empty)
event = queue.dequeue_nowait("FINCORE_UK_001")
```

Events older than 5 minutes are flagged as stale but still returned. The monitoring loop in `main.py` drains up to 50 events per iteration.

---

## adapters/

### java_adapter.py

Parses Spring Boot log format:
```
2024-01-15 09:23:47.123  ERROR 12345 --- [thread] logger : message
```

Maps exception class names to ATLAS error taxonomy:
- `HikariPool` / `HikariCP` -> `CONNECTION_POOL_EXHAUSTED`
- `OutOfMemoryError` -> `JVM_MEMORY_CRITICAL`
- `StackOverflowError` -> `JVM_STACK_OVERFLOW`
- `ConnectException` -> `NODE_DOWNSTREAM_REFUSED`

Reassembles multi-line stack traces (up to 50 lines) into single events.

### postgres_adapter.py

Parses PostgreSQL log format:
```
2024-01-15 09:23:47.123 UTC [12345] ERROR:  message
```

Maps SQLSTATE codes to ATLAS error taxonomy:
- `53300` (too_many_connections) -> `CONNECTION_POOL_EXHAUSTED`
- `40P01` (deadlock_detected) -> `DB_DEADLOCK`
- `57P03` (cannot_connect_now) -> `DB_PANIC`

FATAL severity always maps to ERROR. Never downgraded.
