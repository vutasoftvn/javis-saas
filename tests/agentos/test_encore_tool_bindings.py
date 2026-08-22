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
