from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend import main as atlas_main


@pytest.fixture(autouse=True)
def _clear_active_incidents() -> None:
    atlas_main._active_incidents.clear()
    atlas_main._active_incidents_timestamps.clear()


@pytest.mark.asyncio
async def test_incident_details_requires_role_header() -> None:
    thread_id = "thread-1"
    atlas_main._active_incidents[thread_id] = {
        "thread_id": thread_id,
        "incident_id": "inc-1",
        "client_id": "FINCORE_UK_001",
        "audit_trail": [],
    }

    async with AsyncClient(
        transport=ASGITransport(app=atlas_main.app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/incidents/details/{thread_id}")

    assert response.status_code == 403
    assert "X-ATLAS-ROLE" in response.text


@pytest.mark.asyncio
async def test_incident_details_rejects_client_scope_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    thread_id = "thread-2"
    atlas_main._active_incidents[thread_id] = {
        "thread_id": thread_id,
        "incident_id": "inc-2",
        "client_id": "FINCORE_UK_001",
        "audit_trail": [],
    }

    monkeypatch.setattr(atlas_main, "_validate_client_id", lambda _client_id: None)

    async with AsyncClient(
        transport=ASGITransport(app=atlas_main.app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/incidents/details/{thread_id}",
            params={"client_id": "RETAILMAX_EU_002"},
            headers={"X-ATLAS-ROLE": "SDM", "X-ATLAS-USER": "Atlas Manager"},
        )

    assert response.status_code == 403
    assert "does not match" in response.text


@pytest.mark.asyncio
async def test_approve_rejects_actor_header_mismatch() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=atlas_main.app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/incidents/approve",
            json={
                "thread_id": "thread-3",
                "incident_id": "inc-3",
                "client_id": "FINCORE_UK_001",
                "approver": "Different User",
                "token": "",
            },
            headers={"X-ATLAS-ROLE": "L2", "X-ATLAS-USER": "Atlas Operator"},
        )

    assert response.status_code == 403
    assert "does not match" in response.text


@pytest.mark.asyncio
async def test_modify_requires_l2_or_higher() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=atlas_main.app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/incidents/modify",
            json={
                "thread_id": "thread-4",
                "incident_id": "inc-4",
                "client_id": "FINCORE_UK_001",
                "modifier": "Atlas L1",
                "modified_parameters": {"max_connections": 10},
            },
            headers={"X-ATLAS-ROLE": "L1", "X-ATLAS-USER": "Atlas L1"},
        )

    assert response.status_code == 403
    assert "not allowed" in response.text
