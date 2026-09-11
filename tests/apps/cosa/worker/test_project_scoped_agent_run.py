"""Tests for project scoping on agent runs."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.models import ConversationRecord
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
def conversation_repo():
    return InMemoryConversationRepository()


@pytest.fixture
def run_repo():
    return InMemoryRunRepository()


@pytest.fixture
def plane(conversation_repo, run_repo):
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    return build_cosa_agent_plane(
        company_client=mock_client,
        repository=run_repo,
        conversation_repository=conversation_repo,
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_operations_run_fails_closed_without_project_id(plane, run_repo):
    stream = CosaEventStreamManager()
    workspace_id = "ws-123"
    run_id = "run_missing_project"

    result = await execute_run_task(
        plane,
        stream,
        {
            "run_id": run_id,
            "workspace_id": workspace_id,
            "agent_profile": "operations",
            "project_id": None,
        },
    )
    assert result.status == "failed"
    assert result.error == "project_context_required"

    # Không có run/checkpoint/tool/approval record nào được tạo — fail-closed
    # xảy ra TRƯỚC khi chạm bất kỳ side effect ghi nào.
    assert await run_repo.get_run(run_id) is None


@pytest.mark.asyncio
async def test_operations_run_fails_closed_on_project_id_mismatch(
    plane, conversation_repo, run_repo
):
    """Defense-in-depth: payload đã schedule KHÔNG được tin là nguồn sự thật
    cuối cùng — worker re-check với ConversationRecord ĐÃ LƯU trước khi chạm
    kernel. Payload trôi (project_id khác conversation thật) phải fail-closed,
    không âm thầm chạy nhầm project."""
    stream = CosaEventStreamManager()
    workspace_id = "ws-123"
    conversation_id = "conv_project_mismatch"
    run_id = "run_project_mismatch"

    await conversation_repo.create_conversation(
        ConversationRecord(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            project_id="proj_real",
            scope_state="PROJECT_SCOPED",
            created_by_principal="user:test",
            title="T",
        )
    )

    result = await execute_run_task(
        plane,
        stream,
        {
            "run_id": run_id,
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "agent_profile": "operations",
            "project_id": "proj_stale",
        },
    )
    assert result.status == "failed"
    assert result.error == "project_context_mismatch"

    assert await run_repo.get_run(run_id) is None
