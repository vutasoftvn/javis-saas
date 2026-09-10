"""Tests for project scoping on agent runs."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


@pytest.fixture
def plane():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    return build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_operations_run_fails_closed_without_project_id(plane):
    stream = CosaEventStreamManager()
    workspace_id = "ws-123"

    result = await execute_run_task(
        plane,
        stream,
        {
            "workspace_id": workspace_id,
            "agent_profile": "operations",
            "project_id": None,
        },
    )
    assert result.status == "failed"
    assert result.error == "project_context_required"
