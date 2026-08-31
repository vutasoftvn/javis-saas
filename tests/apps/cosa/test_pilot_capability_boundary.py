from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.fixture
def agent_plane():
    client = AsyncMock()
    return build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        company_client=client,
        model=FakeSDKModel(),
    )


def test_pilot_capability_registration_boundaries(agent_plane):
    registry = agent_plane.capability_registry
    registered_ids = {spec.id for spec in registry.list_specs()}

    # 1. Registered advisory pilot capabilities
    assert "strategy.pilot.get" in registered_ids
    assert "strategy.pilot.create_draft" in registered_ids

    # 2. Strict non-existence of dangerous autonomous / activation capabilities
    assert "strategy.pilot.activate" not in registered_ids
    assert "strategy.pilot.approve" not in registered_ids
    assert "engineering.deploy" not in registered_ids
    assert "engineering.release.execute" not in registered_ids
    assert "crm.write" not in registered_ids
    assert "strategy.stage.transition" not in registered_ids


@pytest.mark.asyncio
async def test_pilot_create_draft_capability_execution(agent_plane):
    registry = agent_plane.capability_registry
    handler = registry.get_handler("strategy.pilot.create_draft")
    assert handler is not None

    agent_plane.company_client.post.return_value = {
        "id": "704999888",
        "projectId": "100",
        "status": "DRAFT",
    }

    valid_payload = {
        "project_id": "100",
        "design_partner_evidence_refs": ["ev-1"],
        "metric_contract_artifact_ref": "artifact://ws/metrics/v1",
        "instrumentation_artifact_ref": "artifact://ws/inst/v1",
        "onboarding_artifact_ref": "artifact://ws/onb/v1",
        "rollback_artifact_ref": "artifact://ws/rb/v1",
        "release_owner_member_id": "user-1",
    }

    # 1. Execution with workspace context succeeds and returns proposal advisory
    res = await handler(valid_payload, context={"workspace_id": "ws-123"})
    assert res["pilot"]["status"] == "DRAFT"
    assert res["advisory"]["label"] == "proposal"

    # 2. Missing workspace context fails fast
    with pytest.raises(ValueError, match="workspace_id is required"):
        await handler(valid_payload, context=None)

    # 3. Cross-tenant workspace mismatch fails fast
    with pytest.raises(ValueError, match="Cross-tenant workspace_id mismatch"):
        await handler(
            {**valid_payload, "workspace_id": "ws-attacker"},
            context={"workspace_id": "ws-victim"},
        )

