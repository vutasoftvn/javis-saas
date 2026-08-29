from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.mark.asyncio
async def test_agent_plane_marketing_context_read_populated():
    """Verify commercial.marketing_context.read returns populated marketing context."""
    mock_client = AsyncMock(spec=CompanyServiceClient)
    mock_client.get.return_value = {
        "id": "ctx-100",
        "workspaceId": "ws-marketing-1",
        "revision": 2,
        "status": "approved",
        "productMarketing": {
            "category": "B2B AI Platform",
            "positioningStatement": "All-in-one AI platform for B2B founders.",
        },
    }

    plane = build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    reg = plane.capability_registry.get("commercial.marketing_context.read")
    assert reg is not None

    handler = reg.handler
    res = await handler({"workspace_id": "ws-marketing-1"}, {"workspace_id": "ws-marketing-1"})

    assert res["status"] == "approved"
    assert res["workspace_id"] == "ws-marketing-1"
    assert res["context"]["id"] == "ctx-100"
    assert res["missing_evidence"] == []
    mock_client.get.assert_awaited_once_with(
        "/commercial/marketing-context?workspace_id=ws-marketing-1",
        headers={"X-Workspace-Id": "ws-marketing-1"},
    )


@pytest.mark.asyncio
async def test_agent_plane_marketing_context_read_empty_context():
    """Verify commercial.marketing_context.read handles empty context with missing evidence list."""
    mock_client = AsyncMock(spec=CompanyServiceClient)
    mock_client.get.return_value = None

    plane = build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    reg = plane.capability_registry.get("commercial.marketing_context.read")
    assert reg is not None

    handler = reg.handler
    res = await handler({"workspace_id": "ws-empty"}, {"workspace_id": "ws-empty"})

    assert res["status"] == "empty"
    assert res["context"] is None
    assert "icp_segments" in res["missing_evidence"]
    assert "positioning_statement" in res["missing_evidence"]
