"""
Pre-demo health check — runs in under 30 seconds.
Run this immediately before walking to the presentation screen.

Checks:
  1. All required env vars are set
  2. Neo4j is reachable and CHG0089234 / INC-2024-0847 exist
  3. ChromaDB data directory is populated
  4. Both fallback JSON files are loadable in under 200ms
  5. Backend server is reachable (if running)
  6. ServiceNow developer instance is reachable
  7. Anthropic API key is valid (lightweight ping)
  8. Frontend public/fallback/ directory exists

Exit code 0 = green light to present.
Exit code 1 = one or more checks failed — do not present until resolved.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
import time as _time

REPO_ROOT = pathlib.Path(__file__).parent.parent

# Ensure repo root is on sys.path so backend imports work
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env from repo root if present
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=False)

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  ✗  {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  ⚠  {msg}")


def ok(label: str) -> None:
    print(f"  ✓  {label}")


def section(title: str) -> None:
    print(f"\n  [{title}]")


# ── 1. Environment variables ──────────────────────────────────────────────────
section("ENV VARS")

CRITICAL_VARS = [
    "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD",
    "ANTHROPIC_API_KEY",
    "SERVICENOW_INSTANCE_URL", "SERVICENOW_USERNAME", "SERVICENOW_PASSWORD",
    "ATLAS_SECRET_KEY", "ATLAS_LLM_ENDPOINT",
]

all_env_ok = True
for var in CRITICAL_VARS:
    if not os.environ.get(var):
        fail(f"{var} not set")
        all_env_ok = False

if all_env_ok:
    ok(f"All {len(CRITICAL_VARS)} critical env vars set")

# ── 2. Fallback files ─────────────────────────────────────────────────────────
section("FALLBACK FILES")

FALLBACK_DIR = REPO_ROOT / "data" / "fallbacks"
for filename, expected_action in [
    ("financecore_incident_response.json", "connection-pool-recovery-v2"),
    ("retailmax_incident_response.json",   "redis-memory-policy-rollback-v1"),
]:
    path = FALLBACK_DIR / filename
    if not path.exists():
        fail(f"{filename} missing — LLM fallback will fail")
        continue

    t0 = _time.perf_counter()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        load_ms = (_time.perf_counter() - t0) * 1000
        action_id = data.get("recommended_action_id", "")
        if action_id != expected_action:
            fail(f"{filename} recommended_action_id='{action_id}' expected '{expected_action}'")
        elif load_ms > 200:
            fail(f"{filename} load time {load_ms:.0f}ms exceeds 200ms SLA")
        else:
            ok(f"{filename} — {load_ms:.0f}ms — action_id='{action_id}'")
    except Exception as exc:
        fail(f"{filename} failed to load: {exc}")

# ── 3. ChromaDB data ──────────────────────────────────────────────────────────
section("CHROMADB")

chroma_sqlite = REPO_ROOT / "data" / "chromadb" / "chroma.sqlite3"
if not chroma_sqlite.exists():
    fail("data/chromadb/chroma.sqlite3 missing — run scripts/seed_chromadb.py")
else:
    size_kb = chroma_sqlite.stat().st_size / 1024
    if size_kb < 10:
        warn(f"chroma.sqlite3 is {size_kb:.1f}KB — may be empty, run seed_chromadb.py")
    else:
        ok(f"chroma.sqlite3 exists ({size_kb:.0f}KB)")

# ── 4. Frontend fallback video ────────────────────────────────────────────────
section("FRONTEND ASSETS")

video_path = REPO_ROOT / "frontend" / "public" / "fallback" / "graph_animation.mp4"
if not video_path.exists():
    warn(
        "graph_animation.mp4 missing — GraphViz will fall back to static SVG. "
        "Record the animation and place it at frontend/public/fallback/graph_animation.mp4"
    )
else:
    size_kb = video_path.stat().st_size / 1024
    ok(f"graph_animation.mp4 exists ({size_kb:.0f}KB)")

# ── 5. Backend server ping ────────────────────────────────────────────────────
section("BACKEND SERVER")

async def ping_backend() -> None:
    """Ping the backend health endpoint."""
    import httpx
    backend_url = os.environ.get("VITE_API_URL", "http://localhost:8000")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{backend_url}/health")
        if resp.status_code == 200:
            ok(f"Backend reachable at {backend_url}")
        else:
            warn(f"Backend returned HTTP {resp.status_code} — start with: uvicorn backend.main:app")
    except Exception:
        warn(f"Backend not reachable at {backend_url} — start with: uvicorn backend.main:app --reload")

asyncio.run(ping_backend())

# ── 6. Neo4j connectivity + demo data ────────────────────────────────────────
section("NEO4J")

async def check_neo4j() -> None:
    """Verify Neo4j is reachable and demo nodes exist."""
    neo4j_uri = os.environ.get("NEO4J_URI", "")
    neo4j_user = os.environ.get("NEO4J_USERNAME", "")
    neo4j_pass = os.environ.get("NEO4J_PASSWORD", "")

    if not all([neo4j_uri, neo4j_user, neo4j_pass]):
        fail("Neo4j credentials incomplete — cannot verify")
        return

    try:
        from neo4j import AsyncGraphDatabase  # type: ignore[import]

        async with AsyncGraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_pass)
        ) as driver:
            async with driver.session() as session:
                # Check CHG0089234 exists
                result = await session.run(
                    "MATCH (d:Deployment {change_id: $cid, client_id: $client}) RETURN d.change_id",
                    cid="CHG0089234",
                    client="FINCORE_UK_001",
                )
                record = await result.single()
                if record:
                    ok("Neo4j: CHG0089234 exists (FinanceCore deployment correlation) ✓")
                else:
                    fail(
                        "Neo4j: CHG0089234 not found — run data/seed/financecore_graph.cypher "
                        "in Neo4j Browser before demo"
                    )

                # Check INC-2024-0847 exists
                result2 = await session.run(
                    "MATCH (i:Incident {incident_id: $iid, client_id: $client}) RETURN i.incident_id",
                    iid="INC-2024-0847",
                    client="FINCORE_UK_001",
                )
                record2 = await result2.single()
                if record2:
                    ok("Neo4j: INC-2024-0847 exists (FinanceCore historical match) ✓")
                else:
                    fail(
                        "Neo4j: INC-2024-0847 not found — run data/seed/financecore_graph.cypher "
                        "in Neo4j Browser before demo"
                    )

                # Check DEP-20250316-003 exists
                result3 = await session.run(
                    "MATCH (d:Deployment {change_id: $cid, client_id: $client}) RETURN d.change_id",
                    cid="DEP-20250316-003",
                    client="RETAILMAX_EU_002",
                )
                record3 = await result3.single()
                if record3:
                    ok("Neo4j: DEP-20250316-003 exists (RetailMax deployment correlation) ✓")
                else:
                    fail(
                        "Neo4j: DEP-20250316-003 not found — run data/seed/retailmax_graph.cypher "
                        "in Neo4j Browser before demo"
                    )

    except ImportError:
        warn("neo4j driver not installed — cannot verify Neo4j connectivity")
    except Exception as exc:
        fail(f"Neo4j connection failed: {exc}")

asyncio.run(check_neo4j())

# ── 7. ServiceNow connectivity ────────────────────────────────────────────────
section("SERVICENOW")

async def check_servicenow() -> None:
    """Verify ServiceNow developer instance is reachable."""
    import httpx
    sn_url = os.environ.get("SERVICENOW_INSTANCE_URL", "")
    sn_user = os.environ.get("SERVICENOW_USERNAME", "")
    sn_pass = os.environ.get("SERVICENOW_PASSWORD", "")

    if not all([sn_url, sn_user, sn_pass]):
        fail("ServiceNow credentials incomplete — cannot verify")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{sn_url}/api/now/table/incident",
                params={"sysparm_limit": "1"},
                auth=(sn_user, sn_pass),
                headers={"Accept": "application/json"},
            )
        if resp.status_code == 200:
            ok(f"ServiceNow reachable at {sn_url} ✓")
        elif resp.status_code == 401:
            fail("ServiceNow: authentication failed — check SERVICENOW_USERNAME/PASSWORD")
        else:
            warn(f"ServiceNow returned HTTP {resp.status_code}")
    except Exception as exc:
        fail(f"ServiceNow not reachable: {exc}")

asyncio.run(check_servicenow())

# ── 8. Anthropic API key ──────────────────────────────────────────────────────
section("ANTHROPIC API")

async def check_anthropic() -> None:
    """Lightweight check that the Anthropic API key is valid."""
    import httpx
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        fail("ANTHROPIC_API_KEY not set")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
        if resp.status_code == 200:
            ok("Anthropic API key valid ✓")
        elif resp.status_code == 401:
            fail("Anthropic API key invalid or expired — LLM calls will fail, fallback will activate")
        else:
            warn(f"Anthropic API returned HTTP {resp.status_code} — verify key is active")
    except Exception as exc:
        warn(f"Anthropic API check failed: {exc} — verify network connectivity")

asyncio.run(check_anthropic())

# ── Final result ──────────────────────────────────────────────────────────────
print(f"\n  {'─' * 50}")

if errors:
    print(f"\n  ✗  NOT READY — {len(errors)} critical issue(s):")
    for e in errors:
        print(f"     • {e}")
    if warnings:
        print(f"\n  ⚠  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"     • {w}")
    print()
    sys.exit(1)
else:
    print(f"\n  ✓  GREEN LIGHT — system ready for demo")
    if warnings:
        print(f"  ⚠  {len(warnings)} non-critical warning(s):")
        for w in warnings:
            print(f"     • {w}")
    print()
