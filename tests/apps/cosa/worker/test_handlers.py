from __future__ import annotations

import pytest
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


def _plane():
    return build_cosa_agent_plane(
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
