# adapters

Path B ingestion adapters. Each adapter reads a native log format and outputs to the unified ATLAS OTel schema. Build once, deploy to every client running that technology.

---

## Files

| File | Technology | Log format |
|------|-----------|-----------|
| `java_adapter.py` | Java Spring Boot | Spring Boot log format with timestamp, level, PID, thread, logger, message |
| `postgres_adapter.py` | PostgreSQL | PostgreSQL log format with timestamp, PID, severity, message |

---

## java_adapter.py

Parses Spring Boot log lines:
```
2024-01-15 09:23:47.123  ERROR 12345 --- [http-nio-8080-exec-1] c.e.PaymentService : Error message
```

Key behaviours:
- Unparseable lines are returned with `source_type="java-unparseable"` and `severity="UNKNOWN"`. Never silently dropped.
- `reassemble_stack_trace(lines)` joins multi-line stack traces (up to 50 lines) into single events before parsing.
- Exception class names are mapped to ATLAS error taxonomy. Unknown exceptions get `JAVA_UNKNOWN:{class_name}`.

Error taxonomy mappings:
```
HikariPool / HikariCP / com.zaxxer.hikari  ->  CONNECTION_POOL_EXHAUSTED
OutOfMemoryError                            ->  JVM_MEMORY_CRITICAL
StackOverflowError                          ->  JVM_STACK_OVERFLOW
ConnectException / ECONNREFUSED             ->  NODE_DOWNSTREAM_REFUSED
```

Usage:
```python
event = java_adapter.parse_line(raw_line, client_id="FINCORE_UK_001", service_name="PaymentAPI")
# Returns normalised event dict or None if line is empty
```

---

## postgres_adapter.py

Parses PostgreSQL log lines:
```
2024-01-15 09:23:47.123 UTC [12345] ERROR:  message SQLSTATE: 53300
```

Key behaviours:
- FATAL severity always maps to ERROR. Never downgraded.
- SQLSTATE codes are extracted and mapped to ATLAS error taxonomy.
- PANIC level always returns `DB_PANIC` regardless of message content.
- Unparseable lines are returned with `source_type="postgresql-unparseable"` and `severity="INFO"`.

SQLSTATE mappings:
```
53300 (too_many_connections)  ->  CONNECTION_POOL_EXHAUSTED
40P01 (deadlock_detected)     ->  DB_DEADLOCK
57P03 (cannot_connect_now)    ->  DB_PANIC
08006 (connection_failure)    ->  CONNECTION_POOL_EXHAUSTED
```

Usage:
```python
event = postgres_adapter.parse_line(raw_line, client_id="FINCORE_UK_001", service_name="TransactionDB")
# Returns normalised event dict or None if line is empty
```

---

## Adding a new adapter

Create a new module in this directory. It must export a `parse_line(raw_line, client_id, service_name)` function that returns a normalised event dict or `None`. The dict must include at minimum: `client_id`, `source_system`, `source_type`, `severity`, `message`, `raw_payload`, `timestamp`.

Never silently drop unparseable lines. Return them with a fallback `source_type` and `severity="UNKNOWN"` or `severity="INFO"`.
