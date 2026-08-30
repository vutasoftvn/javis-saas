from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from apps.cosa.capabilities.project_lifecycle import (
    STRATEGY_PROJECT_GET_SPEC,
    STRATEGY_EVIDENCE_LIST_SPEC,
    STRATEGY_EVIDENCE_CREATE_SPEC,
    STRATEGY_GATE_EVALUATION_CREATE_SPEC,
    STRATEGY_NEXT_BEST_ACTION_GET_SPEC,
    create_strategy_project_get_handler,
    create_strategy_evidence_list_handler,
    create_strategy_evidence_create_handler,
    create_strategy_gate_evaluation_create_handler,
    create_strategy_next_best_action_get_handler,
)


@pytest.mark.asyncio
async def test_strategy_project_get_handler():
    client = AsyncMock()
    client.get.return_value = {
        "project": {"id": "100", "title": "Test Proj", "lifecycleStage": "P0_DISCOVERY"}
    }

    handler = create_strategy_project_get_handler(client)

    # Missing workspace_id -> ValueError
    with pytest.raises(ValueError, match="workspace_id is required"):
        await handler({"project_id": "100"}, context=None)

    # Context takes precedence and payload mismatch raises ValueError
    with pytest.raises(ValueError, match="Cross-tenant workspace_id mismatch"):
        await handler({"project_id": "100", "workspace_id": "ws-spoofed"}, context={"workspace_id": "ws-123"})

    res = await handler({"project_id": "100"}, context={"workspace_id": "ws-123"})

    client.get.assert_awaited_once_with(
        "/operations/strategy/stage-context",
        params={"projectId": "100"},
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert res["project"]["project"]["lifecycleStage"] == "P0_DISCOVERY"
    assert res["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_strategy_evidence_list_handler():
    client = AsyncMock()
    client.get.return_value = {"items": [{"id": "ev-1", "claim": "Claim 1"}]}

    handler = create_strategy_evidence_list_handler(client)
    res = await handler(
        {"project_id": "100", "status": "approved"},
        context={"workspace_id": "ws-123"},
    )

    client.get.assert_awaited_once_with(
        "/operations/strategy/evidence",
        params={"projectId": "100", "status": "approved"},
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert len(res["items"]) == 1
    assert res["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_strategy_evidence_create_handler_always_candidate():
    client = AsyncMock()
    client.post.return_value = {
        "id": "ev-2",
        "claim": "Claim 2",
        "status": "candidate",
    }

    handler = create_strategy_evidence_create_handler(client)
    res = await handler(
        {
            "project_id": "100",
            "source_type": "customer_interview",
            "claim": "Founder verified problem statement",
            "workspace_id": "ws-123",
        },
        context=None,
    )

    client.post.assert_awaited_once_with(
        "/operations/strategy/evidence",
        json={
            "projectId": "100",
            "sourceType": "customer_interview",
            "claim": "Founder verified problem statement",
            "status": "candidate",
        },
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert res["evidence"]["status"] == "candidate"
    assert res["advisory"]["label"] == "proposal"


@pytest.mark.asyncio
async def test_strategy_gate_evaluation_create_handler():
    client = AsyncMock()
    client.post.return_value = {
        "id": "gate-1",
        "result": "passed",
        "requirementsMet": True,
    }

    handler = create_strategy_gate_evaluation_create_handler(client)
    res = await handler(
        {
            "project_id": "100",
            "stage_policy_id": "policy-1",
            "workspace_id": "ws-123",
        },
        context=None,
    )

    client.post.assert_awaited_once_with(
        "/operations/strategy/gate-evaluations",
        json={
            "projectId": "100",
            "stagePolicyId": "policy-1",
            "blockingRisks": [],
        },
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert res["evaluation"]["result"] == "passed"
    assert res["advisory"]["label"] == "insight"


@pytest.mark.asyncio
async def test_strategy_next_best_action_get_handler():
    client = AsyncMock()
    client.get.return_value = {"items": [{"id": "nba-1", "recommendation": "Interview users"}]}

    handler = create_strategy_next_best_action_get_handler(client)
    res = await handler(
        {"project_id": "100", "workspace_id": "ws-123"},
        context=None,
    )

    client.get.assert_awaited_once_with(
        "/operations/strategy/projects/100/next-best-actions",
        headers={"X-Workspace-Id": "ws-123"},
    )
    assert len(res["actions"]["items"]) == 1
    assert res["advisory"]["label"] == "insight"
