"""
One-time Neo4j seed script. Idempotent — safe to run multiple times.
Executes both Cypher seed files and verifies critical nodes exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

_SEED_DIR = Path(__file__).parent.parent / "data" / "seed"

_VERIFICATION_QUERIES = [
    {
        "name": "FinanceCore CHG0089234 exists",
        "cypher": "MATCH (d:Deployment {change_id: 'CHG0089234', client_id: 'FINCORE_UK_001'}) RETURN d.change_id AS id",
        "expect_field": "id",
        "expect_value": "CHG0089234",
    },
    {
        "name": "CHG0089234 MODIFIED_CONFIG_OF PaymentAPI",
        "cypher": """
            MATCH (d:Deployment {change_id: 'CHG0089234', client_id: 'FINCORE_UK_001'})
            -[:MODIFIED_CONFIG_OF]->(s:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
            RETURN s.name AS name
        """,
        "expect_field": "name",
        "expect_value": "PaymentAPI",
    },
    {
        "name": "INC-2024-0847 exists with correct anomaly_type",
        "cypher": """
            MATCH (i:Incident {incident_id: 'INC-2024-0847', client_id: 'FINCORE_UK_001'})
            RETURN i.anomaly_type AS anomaly_type
        """,
        "expect_field": "anomaly_type",
        "expect_value": "CONNECTION_POOL_EXHAUSTED",
    },
    {
        "name": "Deployment correlation query returns CHG0089234",
        "cypher": """
            MATCH (d:Deployment {client_id: 'FINCORE_UK_001'})
            WHERE d.timestamp > datetime() - duration('P7D')
            MATCH (d)-[:MODIFIED_CONFIG_OF|DEPLOYED_TO]->(s:Service)
            WHERE s.name IN ['PaymentAPI', 'TransactionDB']
            RETURN d.change_id AS change_id
            ORDER BY d.timestamp DESC
        """,
        "expect_field": "change_id",
        "expect_value": "CHG0089234",
    },
    {
        "name": "RetailMax DEP-20250316-003 exists",
        "cypher": "MATCH (d:Deployment {change_id: 'DEP-20250316-003', client_id: 'RETAILMAX_EU_002'}) RETURN d.change_id AS id",
        "expect_field": "id",
        "expect_value": "DEP-20250316-003",
    },
]


def run() -> None:
    uri = os.environ["NEO4J_URI"]
    username = os.environ["NEO4J_USERNAME"]
    password = os.environ["NEO4J_PASSWORD"]

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("Seeding Neo4j...")
    for seed_file in ["financecore_graph.cypher", "retailmax_graph.cypher"]:
        path = _SEED_DIR / seed_file
        raw = path.read_text(encoding="utf-8")

        # Split on semicolons, skip comment-only lines and blank statements
        raw_statements = raw.split(";")
        statements = []
        for s in raw_statements:
            # Strip comment lines and whitespace
            lines = [l for l in s.splitlines() if not l.strip().startswith("//")]
            cleaned = "\n".join(lines).strip()
            if cleaned:
                statements.append(cleaned)

        with driver.session() as session:
            for stmt in statements:
                try:
                    session.run(stmt)
                except Exception as exc:
                    print(f"  Warning: statement failed — {str(exc)[:120]}")
        print(f"  ✓ {seed_file}")

    print("\nVerifying...")
    failures = 0
    for check in _VERIFICATION_QUERIES:
        with driver.session() as session:
            result = session.run(check["cypher"])
            records = result.data()
            passed = any(r.get(check["expect_field"]) == check["expect_value"] for r in records)
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}  {check['name']}")
            if not passed:
                failures += 1
                print(f"         Expected {check['expect_field']}={check['expect_value']!r}, got: {records}")

    driver.close()

    if failures:
        print(f"\n{failures} verification(s) failed. Fix seed data before proceeding.")
        sys.exit(1)
    print("\nAll verifications passed.")


if __name__ == "__main__":
    run()
