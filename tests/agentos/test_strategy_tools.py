# tests/agentos/test_strategy_tools.py
import pytest
from unittest.mock import AsyncMock

from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry
from agentos.tools.clusters.strategy_tools import get_strategy_tools


def test_strategy_tools_registered_in_cluster_tools():
    registry = ToolRegistry()
    registry.register_cluster_tools()

    expected_tools = [
        "strategy.project.get",
        "strategy.gate_evaluation.list",
        "strategy.gate_evaluation.create",
        "strategy.assumption.create",
        "strategy.assumption.list",
        "strategy.experiment.create",
        "strategy.evidence.create",
        "strategy.evidence.list",
        "strategy.decision_record.create",
        "strategy.next_best_action.get",
    ]
    for tool_name in expected_tools:
        spec = registry.get(tool_name)
        assert spec.name == tool_name
        assert spec.risk_level is not None
        assert spec.tool_permission is not None


@pytest.mark.asyncio
async def test_strategy_tools_invocation_with_mock_client():
    mock_client = AsyncMock(spec=EncoreClient)
    mock_client.get.return_value = {"id": "proj-1", "stage": "S1_DISCOVERY"}
    mock_client.post.return_value = {"success": True, "id": "rec-1"}

    tools = {t.name: t for t in get_strategy_tools(mock_client)}

    # 1. strategy.project.get
    res = await tools["strategy.project.get"].handler({"id": "proj-1"})
    assert res["id"] == "proj-1"
    mock_client.get.assert_awaited_with("/operations/strategy/projects/proj-1")

    # 2. strategy.next_best_action.get
    res_nba = await tools["strategy.next_best_action.get"].handler({"projectId": "proj-1"})
    assert res_nba["id"] == "proj-1"
    mock_client.get.assert_awaited_with("/operations/strategy/projects/proj-1/next-best-actions")

    # 3. strategy.gate_evaluation.create
    res_gate = await tools["strategy.gate_evaluation.create"].handler(
        {"projectId": "proj-1", "currentStage": "S1_DISCOVERY", "targetStage": "S2_VALIDATION"}
    )
    assert res_gate["success"] is True
    mock_client.post.assert_awaited_with(
        "/operations/strategy/gate-evaluations",
        json={"projectId": "proj-1", "currentStage": "S1_DISCOVERY", "targetStage": "S2_VALIDATION"},
    )
