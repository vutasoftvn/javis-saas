from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


def _plane():
    # Task 7 (2026-08-30) — CosaDataModelGate.prepare_initial_input giờ gọi
    # thật self._client.resolve_data_use(...) khi có DataAccessClaim (mock
    # compliance resolver trong build_cosa_agent_plane tự gắn 1 claim mặc
    # định tối thiểu — xem _MockComplianceResolverWithDefaultClaim). Không
    # truyền company_client= ở đây sẽ khiến gate dùng CompanyServiceClient()
    # thật và cố gọi network ra http://localhost:4000 — mock rõ ràng để test
    # này không phụ thuộc 1 server Company thật đang chạy.
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


def _payload(**overrides) -> dict:
    base = {
        "run_id": "run_handler_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": "ws_1",
        "company_id": "test_company_1",
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_execute_run_task_fails_gracefully_when_registry_not_seeded():
    plane = _plane()
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert any(m.status == "failed" for m in messages)


@pytest.mark.asyncio
async def test_execute_run_task_resolves_exact_spec_after_seeding():
    plane = _plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    messages = await plane.conversation_repository.list_messages("conv_1")
    assert not any(m.status == "failed" for m in messages)
    assert any(m.role == "assistant" and m.status == "completed" for m in messages)
