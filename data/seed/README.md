# seed

Seed data for Neo4j and ChromaDB. Run once before starting the application. Use `scripts/seed_neo4j.py` and `scripts/seed_chromadb.py` to execute these files.

---

## Files

| File | What it seeds |
|------|--------------|
| `financecore_graph.cypher` | Complete FinanceCore knowledge graph in Neo4j |
| `retailmax_graph.cypher` | Complete RetailMax knowledge graph in Neo4j |
| `historical_incidents.json` | Historical incidents for ChromaDB embedding |

---

## financecore_graph.cypher

Creates the FinanceCore knowledge graph. The demo scenario depends on specific nodes and relationships existing with exact property values.

Critical nodes:
- `Deployment {change_id: "CHG0089234"}` - 3 days ago, reduced HikariCP maxPoolSize from 100 to 40, CAB risk LOW
- `Incident {incident_id: "INC-2024-0847"}` - 4 months ago, CONNECTION_POOL_EXHAUSTED, resolved by restoring pool to 150

Critical relationships:
- `CHG0089234 -[:MODIFIED_CONFIG_OF]-> PaymentAPI`
- `INC-2024-0847 -[:AFFECTED]-> TransactionDB`
- `PaymentAPI -[:DEPENDS_ON]-> TransactionDB`

The deployment correlation query in N3 must return CHG0089234. The historical pattern query must return INC-2024-0847. Verify with `scripts/seed_neo4j.py` which runs these queries after seeding.

---

## retailmax_graph.cypher

Creates the RetailMax knowledge graph.

Critical node:
- `Deployment {change_id: "DEP-20250316-003"}` - 2 days ago, changed Redis maxmemory-policy from allkeys-lru to noeviction

Intentional absence: no historical Incident node with `anomaly_type: "REDIS_OOM"`. This is deliberate. The RetailMax demo scenario demonstrates the insufficient-precedent routing path (cold-start veto fires, routes to human because there is no strong historical match).

---

## historical_incidents.json

10 FinanceCore incidents and 6 RetailMax incidents.

The INC-2024-0847 description is written to semantically match the FinanceCore fault scenario query text. When the fault script runs and N4 searches ChromaDB, INC-2024-0847 must return with similarity above 0.87.

The RetailMax incidents are written so that no single incident returns above 0.70 similarity for the Redis OOM fault scenario. This is intentional.

Run `scripts/validate_similarity.py` after seeding to verify both thresholds are met.

### Incident record schema

```json
{
  "incident_id": "INC-2024-0847",
  "client_id": "FINCORE_UK_001",
  "service_name": "TransactionDB",
  "anomaly_type": "CONNECTION_POOL_EXHAUSTED",
  "error_codes_observed": ["HikariCP", "CONNECTION_POOL_EXHAUSTED"],
  "root_cause": "HikariCP maxPoolSize reduced from 100 to 40 by deployment CHG0071892",
  "resolution_steps": "Restored maxPoolSize to 150 via Spring Boot Actuator. Restarted connection manager.",
  "mttr_minutes": 23,
  "resolved_by": "l2-engineer@atos.com",
  "playbook_used": "connection-pool-recovery-v2"
}
```
