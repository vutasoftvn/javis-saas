"""Helper for generating valid ProjectAgentRunAuthority in test planes."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from apps.cosa.agents.catalog import public_profile_specs
from apps.cosa.company.project_team_client import (
    ProjectAgentRunAuthority,
    ProjectTeamClient,
    SpecRef,
)


def valid_run_authority(
    *,
    workspace_id: str,
    project_id: str,
    profile_key: str = "operations",
    assignment_version: int = 1,
    agent_workforce_member_id: str = "mem_test_agent",
    policy_snapshot: dict[str, Any] | None = None,
) -> ProjectAgentRunAuthority:
    spec = public_profile_specs()[profile_key]
    snapshot = {"knowledge_gate_passed": True}
    if policy_snapshot is not None:
        snapshot.update(policy_snapshot)

    return ProjectAgentRunAuthority(
        projectId=project_id,
        workspaceId=workspace_id,
        profileKey=profile_key,
        assignmentVersion=assignment_version,
        agentWorkforceMemberId=agent_workforce_member_id,
        spec=SpecRef(
            id=spec.id,
            version=spec.version,
            hash=spec.compute_hash(),
        ),
        policySnapshot=snapshot,
    )


def attach_mock_project_team_client(
    plane: Any,
    *,
    default_authority: ProjectAgentRunAuthority | None = None,
) -> AsyncMock:
    mock_team_client = AsyncMock(spec=ProjectTeamClient)

    async def _mock_get_run_authority(*, workspace_id: str, project_id: str, profile_key: str):
        if default_authority is not None:
            return default_authority
        return valid_run_authority(
            workspace_id=workspace_id,
            project_id=project_id,
            profile_key=profile_key,
        )

    mock_team_client.get_run_authority.side_effect = _mock_get_run_authority
    plane.project_team_client = mock_team_client
    return mock_team_client
