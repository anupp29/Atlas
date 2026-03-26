"""Quick ServiceNow connectivity and ticket creation test."""
import urllib.request
import urllib.error
import base64
import json
import os
from pathlib import Path

# Load .env manually
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

url  = os.environ["SERVICENOW_INSTANCE_URL"]
user = os.environ["SERVICENOW_USERNAME"]
pwd  = os.environ["SERVICENOW_PASSWORD"]
creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json", "Accept": "application/json"}

print(f"\n  Instance : {url}")
print(f"  User     : {user}")

# ── 1. Health check ───────────────────────────────────────────────────────────
print("\n[1] Checking instance health...")
req = urllib.request.Request(f"{url}/api/now/table/incident?sysparm_limit=1", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
        print(f"    ✓ Instance alive — {len(data.get('result', []))} record(s) returned")
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    raise SystemExit(1)

# ── 2. Create test incident ───────────────────────────────────────────────────
print("\n[2] Creating test incident ticket...")
payload = json.dumps({
    "short_description": "[ATLAS DEMO] CONNECTION_POOL_EXHAUSTED - PaymentAPI - FINCORE_UK_001",
    "description": (
        "ATLAS automated detection: HikariCP connection pool exhausted on PaymentAPI. "
        "Deployment CHG0089234 reduced maxPoolSize from 100 to 40 three days ago. "
        "Cascade confirmed via Neo4j DEPENDS_ON traversal. "
        "Composite confidence: 0.84. Routing: L2_L3_ESCALATION (PCI-DSS veto)."
    ),
    "urgency": "1",
    "impact": "1",
    "priority": "1",
    "category": "software",
    "subcategory": "application",
    "short_description": "[ATLAS DEMO] CONNECTION_POOL_EXHAUSTED · PaymentAPI · FINCORE_UK_001",
    "caller_id": "admin",
}).encode()

req = urllib.request.Request(
    f"{url}/api/now/table/incident",
    data=payload,
    headers=headers,
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read())["result"]
        number = result["number"]
        sys_id = result["sys_id"]
        ticket_url = f"{url}/nav_to.do?uri=incident.do?sys_id={sys_id}"
        print(f"    ✓ Ticket created : {number}")
        print(f"    ✓ sys_id         : {sys_id}")
        print(f"    ✓ Priority       : {result.get('priority', '?')}")
        print(f"    ✓ State          : {result.get('state', '?')}")
        print(f"\n    OPEN IN BROWSER  : {ticket_url}\n")
except urllib.error.HTTPError as e:
    print(f"    ✗ HTTP {e.code}: {e.read().decode()[:300]}")
    raise SystemExit(1)
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    raise SystemExit(1)

# ── 3. Verify ticket is readable ─────────────────────────────────────────────
print("[3] Verifying ticket is readable...")
req = urllib.request.Request(
    f"{url}/api/now/table/incident/{sys_id}",
    headers=headers,
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())["result"]
        print(f"    ✓ Ticket {result['number']} confirmed in ServiceNow")
        print(f"    ✓ Short description: {result['short_description'][:60]}")
except Exception as e:
    print(f"    ✗ Read-back failed: {e}")

print("\n  ServiceNow is READY for demo.\n")
