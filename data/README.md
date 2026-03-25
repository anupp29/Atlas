# data

Seed data, fault simulation scripts, and pre-computed LLM fallback responses.

---

## Structure

```
data/
  seed/
    financecore_graph.cypher    Neo4j seed for FinanceCore knowledge graph
    retailmax_graph.cypher      Neo4j seed for RetailMax knowledge graph
    historical_incidents.json   Historical incidents for ChromaDB embedding
  fault_scripts/
    financecore_cascade.py      HikariCP connection pool exhaustion cascade
    retailmax_redis_oom.py      Redis OOM from maxmemory-policy change
  fallbacks/                    Pre-computed LLM responses (must be generated before demo)
  mock_services/
    mock_payment_api.py         Lightweight mock of PaymentAPI for local playbook testing
  phase5_verify.py              Phase 5 integration verification — tests state guards, N6, pipeline, tokens, main.py routes, playbook dispatch, and interface contracts
  phase7_verify.py              Phase 7 pre-demo hardening — tests env vars, fallback files, frontend assets, static code wiring, FinanceCore and RetailMax confidence scenarios, playbook library, and all 11 demo numbers
```

---

## seed/

### financecore_graph.cypher

Creates the complete FinanceCore knowledge graph in Neo4j:
- Services: PaymentAPI, TransactionDB, AuthService, NotificationService, APIGateway
- Infrastructure: AWS EKS cluster, AWS RDS instance
- Deployment: CHG0089234 (3 days ago, reduced HikariCP maxPoolSize from 100 to 40, CAB risk LOW)
- Historical incident: INC-2024-0847 (4 months ago, same pattern, resolved by restoring pool to 150)
- SLA nodes, Team nodes, ComplianceRule nodes
- All relationships: DEPENDS_ON, MODIFIED_CONFIG_OF, AFFECTED, COVERED_BY, OWNED_BY, GOVERNED_BY

The deployment correlation query in N3 must return CHG0089234 when queried for PaymentAPI. The historical pattern query must return INC-2024-0847 for CONNECTION_POOL_EXHAUSTED on TransactionDB.

### retailmax_graph.cypher

Creates the RetailMax knowledge graph:
- Services: ProductAPI, CartService, RedisCache, MongoDB, CDN
- Deployment: DEP-20250316-003 (2 days ago, changed Redis maxmemory-policy from allkeys-lru to noeviction)
- No historical incident with REDIS_OOM anomaly type (intentional - demonstrates insufficient precedent routing)

### historical_incidents.json

10 FinanceCore incidents and 6 RetailMax incidents for ChromaDB embedding.

The INC-2024-0847 description is written to semantically match the FinanceCore fault scenario. When the fault script runs and the query text is built from the EvidencePackages, ChromaDB must return INC-2024-0847 with similarity above 0.87.

Run `scripts/validate_similarity.py` to verify this before demo.

---

## fault_scripts/

### financecore_cascade.py

Deterministic fault simulation. Same log lines, same timing, every run.

Timeline:
- T-3min to T+0: normal Java and PostgreSQL logs
- T+0 to T+25min: connection count warnings, increasing frequency
- T+25 to T+35min: HikariCP timeout errors, 1 per 10 seconds
- T+35min: FATAL connection pool exhaustion (PostgreSQL agent fires)
- T+45min: Java HTTP 503 cascade (Java agent fires)
- T+60min: Kubernetes pod restarts
- T+65 to T+75min: continued degradation

```bash
# Real-time (follows actual timing)
python data/fault_scripts/financecore_cascade.py

# Instant output for testing
python data/fault_scripts/financecore_cascade.py --replay

# Point at a different backend
python data/fault_scripts/financecore_cascade.py --endpoint http://localhost:8000
```

### retailmax_redis_oom.py

Redis OOM fault simulation for RetailMax. Produces Redis log lines showing memory pressure and rejected commands.

---

## phase5_verify.py

Integration verification for Phase 5. Run from the `Atlas/` directory.

```bash
python data/phase5_verify.py
```

Checks: state immutability guards, N6 confidence scoring with the FinanceCore scenario, pipeline graph compilation, approval token lifecycle, main.py route registration, playbook dispatch, and interface contracts between modules.

---

## phase7_verify.py

Pre-demo hardening verification. Run from the `Atlas/` directory.

```bash
python data/phase7_verify.py
```

Checks: all required environment variables, fallback JSON files (schema, action IDs, load time under 200ms), frontend fallback video asset, static code wiring for all 5 fallback paths, FinanceCore confidence scenario (composite ~0.84, PCI veto fires, routes to L2), RetailMax confidence scenario (composite ~0.71, cold-start veto fires), playbook library integrity, and all 11 demo numbers from the master spec.

Exit code 0 = all checks passed. Exit code 1 = details printed inline.
