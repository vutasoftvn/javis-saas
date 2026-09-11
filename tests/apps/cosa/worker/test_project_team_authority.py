from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.company.project_team_client import (
    ProjectAgentRunAuthority,
    ProjectTeamAuthorityError,
    ProjectTeamClient,
    SpecRef,
)
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


def _plane(mock_team_client: ProjectTeamClient | None = None):
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    if mock_team_client:
        plane.project_team_client = mock_team_client
    return plane


def _payload(agent_profile="finance", **overrides) -> dict:
    base = {
        "run_id": "run_team_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "analyze runway",
        "agent_profile": agent_profile,
        "principal": "user_1",
        "workspace_id": "ws_1",
        "project_id": "proj_1",
        "company_id": "test_company_1",
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_unassigned_profile_denied_before_kernel():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.side_effect = ProjectTeamAuthorityError(
        "Agent not actively assigned", status_code=404
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers._execute_run_task_inner") as mock_inner:
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="finance"))
        assert res.status == "failed"
        assert "authority_denied" in res.error
        mock_inner.assert_not_called()


@pytest.mark.asyncio
async def test_paused_assignment_denied_before_kernel():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.side_effect = ProjectTeamAuthorityError(
        "Agent is paused", status_code=404
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers._execute_run_task_inner") as mock_inner:
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="marketing"))
        assert res.status == "failed"
        assert "authority_denied" in res.error
        mock_inner.assert_not_called()


@pytest.mark.asyncio
async def test_spec_hash_mismatch_denied_before_kernel():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId="proj_1",
        workspaceId="ws_1",
        profileKey="finance",
        assignmentVersion=2,
        agentWorkforceMemberId="wm_123",
        spec=SpecRef(
            id="cosa.agents.finance",
            version="1.1.0",
            hash="forged_or_stale_hash",
        ),
        policySnapshot={},
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers._execute_run_task_inner") as mock_inner:
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="finance"))
        assert res.status == "failed"
        assert res.error == "spec_hash_mismatch"
        mock_inner.assert_not_called()


@pytest.mark.asyncio
async def test_workspace_or_project_mismatch_denied_before_kernel():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId="other_proj",
        workspaceId="ws_1",
        profileKey="finance",
        assignmentVersion=2,
        agentWorkforceMemberId="wm_123",
        spec=SpecRef(
            id="cosa.agents.finance",
            version="1.1.0",
            hash="21bacc10efd681f204e62e827111853a468436fa2413857bdc1b1e7e0c38be96",
        ),
        policySnapshot={},
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers._execute_run_task_inner") as mock_inner:
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="finance"))
        assert res.status == "failed"
        assert res.error == "project_context_mismatch"
        mock_inner.assert_not_called()


@pytest.mark.asyncio
async def test_active_support_without_knowledge_gate_denied_before_kernel():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId="proj_1",
        workspaceId="ws_1",
        profileKey="customer_support",
        assignmentVersion=2,
        agentWorkforceMemberId="wm_cs_123",
        spec=SpecRef(
            id="cosa.agents.customer_support",
            version="1.2.0",
            hash="71fbf6cfccd3299367ad88e68866e53fd488d406c7d74bd0fbaef472731e15aa",
        ),
        policySnapshot={"knowledge_gate_passed": False},
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers.run_customer_support_copilot") as mock_copilot:
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="customer_support"))
        assert res.status == "failed"
        assert res.error == "support_knowledge_gate_required"
        mock_copilot.assert_not_called()


@pytest.mark.asyncio
async def test_active_matching_spec_hash_allows_execution():
    mock_client = AsyncMock(spec=ProjectTeamClient)
    mock_client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId="proj_1",
        workspaceId="ws_1",
        profileKey="finance",
        assignmentVersion=2,
        agentWorkforceMemberId="wm_123",
        spec=SpecRef(
            id="cosa.agents.finance",
            version="1.1.0",
            hash="21bacc10efd681f204e62e827111853a468436fa2413857bdc1b1e7e0c38be96",
        ),
        policySnapshot={},
    )
    plane = _plane(mock_client)
    stream_mgr = CosaEventStreamManager()

    with patch("apps.cosa.worker.handlers._execute_run_task_inner") as mock_inner:
        mock_inner.return_value = None
        res = await execute_run_task(plane, stream_mgr, _payload(agent_profile="finance"))
        assert res.status == "completed"
        mock_inner.assert_called_once()
