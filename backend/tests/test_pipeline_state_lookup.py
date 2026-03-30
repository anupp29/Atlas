from __future__ import annotations

import asyncio

import pytest

from backend.orchestrator import pipeline


class _FakeSnapshot:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values


class _FakeGraph:
    def __init__(self, snapshot: _FakeSnapshot) -> None:
        self._snapshot = snapshot

    async def aget_state(self, _config: dict[str, object]) -> _FakeSnapshot:
        await asyncio.sleep(0)
        return self._snapshot


@pytest.mark.asyncio
async def test_get_incident_state_returns_none_for_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_graph() -> _FakeGraph:
        await asyncio.sleep(0)
        return _FakeGraph(_FakeSnapshot({}))

    monkeypatch.setattr(pipeline, "_get_graph", _fake_get_graph)

    state = await pipeline.get_incident_state("missing-thread")

    assert state is None


@pytest.mark.asyncio
async def test_get_incident_state_returns_none_without_identity_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_graph() -> _FakeGraph:
        await asyncio.sleep(0)
        return _FakeGraph(_FakeSnapshot({"routing_decision": "AUTO_EXECUTE"}))

    monkeypatch.setattr(pipeline, "_get_graph", _fake_get_graph)

    state = await pipeline.get_incident_state("missing-thread")

    assert state is None


@pytest.mark.asyncio
async def test_get_incident_state_returns_values_for_real_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {
        "incident_id": "inc-123",
        "client_id": "FINCORE_UK_001",
        "routing_decision": "L2_L3_ESCALATION",
    }

    async def _fake_get_graph() -> _FakeGraph:
        await asyncio.sleep(0)
        return _FakeGraph(_FakeSnapshot(expected))

    monkeypatch.setattr(pipeline, "_get_graph", _fake_get_graph)

    state = await pipeline.get_incident_state("thread-123")

    assert state == expected
