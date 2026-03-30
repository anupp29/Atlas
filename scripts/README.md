# scripts

Setup, validation, and demo utility scripts. All scripts must be run from the `Atlas/` directory.

---

## Files

| File | What it does |
|------|-------------|
| `seed_neo4j.py` | Executes both Cypher seed files and verifies critical nodes exist. Idempotent. Run once before first use. |
| `seed_chromadb.py` | Embeds all historical incidents from `historical_incidents.json` into ChromaDB. Run once before first use. |
| `validate_similarity.py` | Verifies ChromaDB similarity scores meet the required thresholds. Run after seeding and before demo. |
| `trigger_financecore_e2e.py` | End-to-end demo trigger. Feeds the FinanceCore fault scenario into the backend in instant replay mode, then prints the resulting incident state. Use this instead of the fault script when you want to see the full pipeline output quickly. |
| `test_resume.py` | Approves the first active FinanceCore incident via the API. Run after `trigger_financecore_e2e.py` to complete the approval flow and trigger playbook execution. |
| `phase7_demo_check.py` | Pre-demo health check. Verifies all external services, fallback files, and demo data are ready. Run immediately before presenting. Exit code 0 = green light. |
| `check_checkpoints.py` | Inspects the LangGraph SQLite checkpoint database for threads with pending nodes. Use this to debug stuck incidents or verify the graph suspended correctly at the human review node. |
| `test_ollama_qwen3.py` | Verifies Ollama is running and the qwen3-coder model responds correctly. Run this before wiring Ollama into the backend to confirm the model is working. |
| `test_ollama_atlas_integration.py` | Integration test for the full Ollama-to-ATLAS reasoning path. Tests the internal LLM reasoning endpoint with a real incident context payload. |
| `test_resume_direct.py` | Direct pipeline resume test that bypasses the HTTP API. Used for debugging the LangGraph resume path without a running server. |

---

## seed_neo4j.py

Reads `data/seed/financecore_graph.cypher` and `data/seed/retailmax_graph.cypher`, splits on semicolons, and executes each statement against Neo4j.

After seeding, runs 5 verification queries:
1. CHG0089234 exists with correct properties
2. CHG0089234 has MODIFIED_CONFIG_OF relationship to PaymentAPI
3. INC-2024-0847 exists with anomaly_type CONNECTION_POOL_EXHAUSTED
4. Deployment correlation query returns CHG0089234 for PaymentAPI
5. DEP-20250316-003 exists for RetailMax

Exits with code 1 if any verification fails.

```bash
python scripts/seed_neo4j.py
```

Requires `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in environment or `.env`.

---

## seed_chromadb.py

Reads `data/seed/historical_incidents.json` and calls `ChromaDBClient.embed_and_store()` for each incident. Rate-limited to 0.1 seconds between embeddings to avoid overwhelming the local embedding model.

After seeding, prints the document count for each client collection.

```bash
python scripts/seed_chromadb.py
```

Requires `CHROMADB_PATH` in environment or `.env`.

---

## validate_similarity.py

Runs two similarity searches and checks the scores:

1. FinanceCore fault scenario query -> INC-2024-0847 must return with similarity above 0.87
2. RetailMax fault scenario query -> no result should return above 0.70 (intentional absence of strong precedent)

If either test fails, the ChromaDB seed data needs to be revised. The incident descriptions in `historical_incidents.json` must be rewritten until both tests pass.

```bash
python scripts/validate_similarity.py
```

Run this after `seed_chromadb.py` and before the demo. Run it again if you change any incident descriptions.

---

## Order of operations

```bash
# 1. Copy .env.example and fill in your credentials
cp .env.example .env

# 2. Verify Ollama is working (if using Ollama as primary LLM)
python scripts/test_ollama_qwen3.py

# 3. Seed Neo4j
python scripts/seed_neo4j.py

# 4. Seed ChromaDB
python scripts/seed_chromadb.py

# 5. Validate similarity scores
python scripts/validate_similarity.py

# 6. Run the test suite
python test_progress.py

# 7. Start the backend (single-service mode also serves /internal/llm/reason)
uvicorn backend.main:app --port 8000

# 8. Run the demo
python scripts/trigger_financecore_e2e.py

# 9. Approve the incident
python scripts/test_resume.py
```

---

## Before every demo session

```bash
python scripts/phase7_demo_check.py
```

This is the only pre-demo check you need. It covers all external services, fallback files, and demo data in one run.
