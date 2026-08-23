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
        "strategy.stage_policy.list",
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
    mock_client.get.assert_awaited_with("/operations/projects/proj-1")

    # 2. strategy.next_best_action.get
    res_nba = await tools["strategy.next_best_action.get"].handler({"projectId": "proj-1"})
    assert res_nba["id"] == "proj-1"
    mock_client.get.assert_awaited_with("/operations/strategy/projects/proj-1/next-best-actions")

    # 3. strategy.stage_policy.list
    await tools["strategy.stage_policy.list"].handler({"workspaceId": "ws1", "stageKey": "S2_VALIDATION"})
    mock_client.get.assert_awaited_with(
        "/operations/strategy/stage-policies", params={"workspaceId": "ws1", "stageKey": "S2_VALIDATION"}
    )

    # 4. strategy.gate_evaluation.create — khớp đúng DTO thật (stagePolicyId, không phải currentStage/targetStage)
    res_gate = await tools["strategy.gate_evaluation.create"].handler(
        {"companyId": "c1", "workspaceId": "ws1", "projectId": "proj-1", "stagePolicyId": "policy-1"}
    )
    assert res_gate["success"] is True
    mock_client.post.assert_awaited_with(
        "/operations/strategy/gate-evaluations",
        json={"companyId": "c1", "workspaceId": "ws1", "projectId": "proj-1", "stagePolicyId": "policy-1"},
    )

    # 5. strategy.assumption.create — khớp đúng DTO thật (statement/importance/uncertainty)
    await tools["strategy.assumption.create"].handler(
        {
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "statement": "Agency will pay for automation",
            "importance": 8,
            "uncertainty": 6,
        }
    )
    mock_client.post.assert_awaited_with(
        "/operations/strategy/assumptions",
        json={
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "statement": "Agency will pay for automation",
            "importance": 8,
            "uncertainty": 6,
        },
    )

    # 6. strategy.experiment.create — khớp đúng DTO thật (hypothesis/method/successCriteria)
    await tools["strategy.experiment.create"].handler(
        {
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "assumptionId": "assump-1",
            "hypothesis": "Agency founders will pre-order",
            "method": "landing_page",
            "successCriteria": ">= 5% conversion",
        }
    )
    mock_client.post.assert_awaited_with(
        "/operations/strategy/experiments",
        json={
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "assumptionId": "assump-1",
            "hypothesis": "Agency founders will pre-order",
            "method": "landing_page",
            "successCriteria": ">= 5% conversion",
        },
    )

    # 7. strategy.evidence.create — khớp đúng DTO thật (sourceType/claim, không phải type/summary)
    await tools["strategy.evidence.create"].handler(
        {
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "experimentId": "exp-1",
            "sourceType": "customer_interview",
            "claim": "8/10 founders confirmed urgent need",
        }
    )
    mock_client.post.assert_awaited_with(
        "/operations/strategy/evidence",
        json={
            "companyId": "c1",
            "workspaceId": "ws1",
            "projectId": "proj-1",
            "experimentId": "exp-1",
            "sourceType": "customer_interview",
            "claim": "8/10 founders confirmed urgent need",
        },
    )

    # 8. strategy.decision_record.create — khớp đúng DTO thật (decision, không phải decisionType/title)
    await tools["strategy.decision_record.create"].handler(
        {"companyId": "c1", "workspaceId": "ws1", "projectId": "proj-1", "decision": "pivot", "notes": "CAC too high"}
    )
    mock_client.post.assert_awaited_with(
        "/operations/strategy/decision-records",
        json={"companyId": "c1", "workspaceId": "ws1", "projectId": "proj-1", "decision": "pivot", "notes": "CAC too high"},
    )
