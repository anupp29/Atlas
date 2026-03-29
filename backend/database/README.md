# database

All database clients. No other module connects to any database directly. Every query is scoped to a `client_id`.

---

## Files

| File | What it does |
|------|-------------|
| `neo4j_client.py` | Async Neo4j client. Connection pooling, 60-second query result cache, client_id enforcement on every query, write permission whitelist, 3-retry with exponential backoff. |
| `chromadb_client.py` | ChromaDB client. Collections namespaced per client (`atlas_{client_id}`). Similarity search, cross-client federated search (anonymised), embed-and-store. |
| `audit_db.py` | SQLite audit log. Immutable records. No update or delete methods exist. Exportable as CSV or JSON. Tracks SLA uptime. |

---

## neo4j_client.py

Manages all Neo4j interactions. The knowledge graph stores services, deployments, incidents, SLAs, teams, and compliance rules with their relationships.

Key behaviours:
- Every `execute_query()` call requires `client_id` in both the params dict and as a separate argument. A mismatch raises `ValueError` immediately.
- Results are cached for 60 seconds per `(query_hash, client_id)` pair. The cache is not automatically invalidated on CMDB webhook receipt — the 60-second TTL is the expiry mechanism.
- Write transactions are restricted to a whitelist of allowed modules (`_ALLOWED_WRITERS`). Any other module attempting a write raises `PermissionError`.
- Neo4j temporal types (DateTime, Date, Duration) are automatically converted to ISO-8601 strings before returning results.

```python
# Read query
results = await neo4j.execute_query(cypher, params, client_id="FINCORE_UK_001")

# Write query (only from whitelisted modules)
await neo4j.execute_write(cypher, params, client_id="FINCORE_UK_001", caller_module=__name__)
```

---

## chromadb_client.py

Manages ChromaDB collections. Each client has an isolated collection named `atlas_{client_id}`. Embeddings use a local ONNX sentence-transformer model with no external API calls.

Key behaviours:
- `similarity_search()` only searches the specified client's collection. Never cross-client.
- `cross_client_search()` searches other clients' collections but strips all client-identifying metadata before returning results. Only called when a client has fewer than 5 incidents (cold start).
- Cosine distance from ChromaDB is converted to similarity: `similarity = 1 - distance`, clamped to [0, 1].

```python
# Store an incident
chroma.embed_and_store(incident_record, client_id="FINCORE_UK_001")

# Search
results = chroma.similarity_search(query_text, client_id="FINCORE_UK_001", n_results=3)
# Each result: {incident_id, similarity_score, document, ...metadata}
```

---

## audit_db.py

SQLite audit log in WAL mode. Every action ATLAS takes or a human takes is recorded here. Records are immutable after writing.

Key behaviours:
- `write_audit_record()` requires `client_id`, `incident_id`, `action_type`, `actor`, and `action_description`. Empty `client_id` raises `ValueError`.
- No `update_audit_record()` or `delete_audit_record()` methods exist. This is intentional.
- `query_audit()` is always scoped to a single `client_id`. Cross-client queries are not possible.
- `export_as_csv()` and `export_as_json()` write to `./data/exports/`.
- `get_sla_uptime_percent()` calculates uptime from resolution events in the audit log.

```python
# Write
audit_db.write_audit_record({
    "client_id": "FINCORE_UK_001",
    "incident_id": "INC-001",
    "action_type": "detection",
    "actor": "ATLAS_AUTO",
    "action_description": "HikariCP exhaustion detected",
    ...
})

# Query
records = audit_db.query_audit("FINCORE_UK_001", date_from, date_to)
```

---

## SQLite databases

Three separate SQLite databases, each with its own path from environment variables:

| Database | Env var | Purpose |
|----------|---------|---------|
| Audit log | `ATLAS_AUDIT_DB_PATH` | Compliance audit trail, immutable |
| Decision history | `ATLAS_DECISION_DB_PATH` | Learning engine memory, accuracy rates |
| Checkpoint | `ATLAS_CHECKPOINT_DB_PATH` | LangGraph state persistence across restarts |

All use WAL journal mode for concurrent read performance.
