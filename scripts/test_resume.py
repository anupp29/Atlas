"""Test resume_after_approval directly."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


async def main():
    # Get active incidents
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        resp = await client.get("/api/incidents/active?client_id=FINCORE_UK_001")
        data = resp.json()
        print(f"Active incidents: {data['count']}")
        if not data["incidents"]:
            print("No active incidents to approve.")
            return

        inc = data["incidents"][0]
        thread_id = inc["thread_id"]
        incident_id = inc["incident_id"]
        print(f"Approving: {incident_id}")
        print(f"Thread: {thread_id}")

        resp = await client.post("/api/incidents/approve", json={
            "thread_id": thread_id,
            "incident_id": incident_id,
            "client_id": "FINCORE_UK_001",
            "approver": "test.engineer",
            "token": "",
        })
        print(f"Approval response: {resp.json()}")

        # Wait for execution
        await asyncio.sleep(20)

        # Check active incidents again
        resp = await client.get("/api/incidents/active?client_id=FINCORE_UK_001")
        data = resp.json()
        for i in data["incidents"]:
            if i["incident_id"] == incident_id:
                print(f"Post-approval status: execution_status={i['execution_status']}")
                break

        # Check audit
        resp = await client.get("/api/audit?client_id=FINCORE_UK_001")
        audit = resp.json()
        print(f"Audit records: {audit['count']}")
        for r in audit["records"][:3]:
            print(f"  {r}")


asyncio.run(main())
