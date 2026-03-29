from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from backend.orchestrator import pipeline


@dataclass
class _FakeSnapshot:
    values: dict[str, Any]


class _FakeGraph:
    def __init__(self) -> None:
        self.updated_state: dict[str, Any] | None = None

    async def aupdate_state(self, _config: dict[str, Any], update: dict[str, Any]) -> None:
        self.updated_state = update

    async def astream(self, _initial_state: Any, config: dict[str, Any]):
        assert config["configurable"]["thread_id"]
        yield {"execute_playbook": {"execution_status": "success"}}
        yield {"n_learn": {"resolution_outcome": "success", "mttr_seconds": 15}}

    async def aget_state(self, _config: dict[str, Any]) -> _FakeSnapshot:
        return _FakeSnapshot(
            values={
                "client_id": "FINCORE_UK_001",
                "incident_id": "inc-100",
                "execution_status": "success",
                "resolution_outcome": "success",
            }
        )


@pytest.mark.asyncio
async def test_resume_after_approval_broadcasts_node_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_graph = _FakeGraph()

    async def _fake_get_graph() -> _FakeGraph:
        return fake_graph

    node_calls: list[str] = []

    async def _fake_broadcast_node_activity(
        node_name: str,
        updates: dict[str, Any],
        client_id: str,
        incident_id: str,
    ) -> None:
        assert updates
        assert client_id == "FINCORE_UK_001"
        assert incident_id == "inc-100"
        node_calls.append(node_name)

    monkeypatch.setattr(pipeline, "_get_graph", _fake_get_graph)
    monkeypatch.setattr(pipeline, "_broadcast_node_activity", _fake_broadcast_node_activity)

    final_state = await pipeline.resume_after_approval(
        thread_id="FINCORE_UK_001_inc-100",
        human_action="approved",
        modifier="Atlas Manager",
    )

    assert fake_graph.updated_state is not None
    assert fake_graph.updated_state["human_action"] == "approved"
    assert node_calls == ["execute_playbook", "n_learn"]
    assert final_state["execution_status"] == "success"
    assert final_state["resolution_outcome"] == "success"
