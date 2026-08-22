import pytest
from unittest.mock import AsyncMock, MagicMock
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry


@pytest.fixture
def mock_encore_client():
    client = MagicMock(spec=EncoreClient)
    client.post = AsyncMock(return_value={"id": 1, "status": "ok"})
    client.get = AsyncMock(return_value={"items": [{"id": 1}], "status": "ok"})
    return client


@pytest.mark.asyncio
async def test_register_cluster_tools(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    names = registry.names()
    # Operations tools
    assert "task_create" in names
    assert "task_list" in names
    assert "okr_cycle_create" in names
    assert "twelve_wy_plan_create" in names

    # Commercial tools
    assert "lead_create" in names
    assert "opportunity_create" in names
    assert "account_create" in names

    # Finance tools
    assert "transaction_record" in names
    assert "legal_obligation_create" in names

    # Identity tools
    assert "workspace_get" in names
    assert "workforce_member_list" in names


@pytest.mark.asyncio
async def test_invoke_operations_tool(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    result = await registry.invoke("task_create", {"workspaceId": 1, "title": "Test Task"})
    assert result == {"id": 1, "status": "ok"}
    mock_encore_client.post.assert_called_once_with("/operations/tasks", json={"workspaceId": 1, "title": "Test Task"})


@pytest.mark.asyncio
async def test_invoke_commercial_tool(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    result = await registry.invoke("lead_create", {"workspaceId": 1, "name": "Alice Lead"})
    assert result == {"id": 1, "status": "ok"}
    mock_encore_client.post.assert_called_once_with("/commercial/leads", json={"workspaceId": 1, "name": "Alice Lead"})


@pytest.mark.asyncio
async def test_invoke_finance_tool(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    result = await registry.invoke("transaction_record", {"workspaceId": 1, "amount": 1000})
    assert result == {"id": 1, "status": "ok"}
    mock_encore_client.post.assert_called_once_with("/finance-legal/transactions", json={"workspaceId": 1, "amount": 1000})


# These tools previously pointed at URLs that don't exist in `services/` at
# all (e.g. `/operations/okrs/cycles` vs the real `/operations/okr-cycles`) —
# a mocked EncoreClient never catches that, since it returns canned data for
# any path. Pinning the exact real path here (cross-checked against each
# route's `path:` in services/*/*.ts) is a lightweight regression guard
# against the same class of bug recurring silently.
@pytest.mark.asyncio
async def test_okr_cycle_create_calls_the_real_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("okr_cycle_create", {"workspaceId": 1, "name": "Q1-2026"})
    mock_encore_client.post.assert_called_once_with("/operations/okr-cycles", json={"workspaceId": 1, "name": "Q1-2026"})


@pytest.mark.asyncio
async def test_okr_objective_create_calls_the_real_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("okr_objective_create", {"workspaceId": 1, "cycleId": 1, "title": "Grow revenue"})
    mock_encore_client.post.assert_called_once_with(
        "/operations/objectives", json={"workspaceId": 1, "cycleId": 1, "title": "Grow revenue"}
    )


@pytest.mark.asyncio
async def test_okr_key_result_update_progress_calls_the_real_checkin_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("okr_key_result_update_progress", {"id": 7, "currentValue": 42})
    mock_encore_client.post.assert_called_once_with("/operations/key-results/7/checkin", json={"value": 42})


@pytest.mark.asyncio
async def test_twelve_wy_plan_create_calls_the_real_cycles_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("twelve_wy_plan_create", {"workspaceId": 1, "visionStatement": "Ship it"})
    mock_encore_client.post.assert_called_once_with("/operations/cycles", json={"workspaceId": 1, "visionStatement": "Ship it"})


@pytest.mark.asyncio
async def test_accounting_period_create_calls_the_real_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("accounting_period_create", {"workspaceId": 1})
    mock_encore_client.post.assert_called_once_with("/finance-legal/accounting-periods", json={"workspaceId": 1})


@pytest.mark.asyncio
async def test_legal_obligation_create_calls_the_real_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("legal_obligation_create", {"workspaceId": 1, "title": "File annual report"})
    mock_encore_client.post.assert_called_once_with(
        "/finance-legal/obligations", json={"workspaceId": 1, "title": "File annual report"}
    )


@pytest.mark.asyncio
async def test_legal_checklist_create_calls_the_real_route(mock_encore_client):
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)

    await registry.invoke("legal_checklist_create", {"workspaceId": 1, "title": "KYC on file"})
    mock_encore_client.post.assert_called_once_with(
        "/finance-legal/checklist-items", json={"workspaceId": 1, "title": "KYC on file"}
    )


def test_removed_tools_with_no_real_backing_route_are_not_registered(mock_encore_client):
    """`twelve_wy_score_record` and `legal_obligation_list` were removed rather
    than pointed at a wrong path — no route exists in `services/` for either
    (no weekly-plan score endpoint; no list-by-workspace obligations endpoint).
    Asserting their absence keeps a future re-add honest: it must come with a
    real matching route, not just a plausible-looking URL string.
    """
    registry = ToolRegistry()
    registry.register_cluster_tools(encore_client=mock_encore_client)
    names = registry.names()
    assert "twelve_wy_score_record" not in names
    assert "legal_obligation_list" not in names
