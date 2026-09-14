from __future__ import annotations

import pytest

from apps.cosa.workflows.deployment_authority_resolver import (
    CompanyDeploymentAuthorityResolver,
)
from agent.assets.contracts import AssetKind, AssetScope, WorkspaceAssetDraft
from agent.assets.repository import InMemoryWorkspaceAssetRepository


class RecordingCompanyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def get_project_agent_deployment_authority(
        self, workspace_id: str, project_id: str, deployment_id: str
    ) -> dict:
        self.calls.append((workspace_id, project_id, deployment_id))
        return {
            "workspaceId": workspace_id,
            "projectId": project_id,
            "projectAgentDeploymentId": deployment_id,
            "state": "ACTIVE",
            "agentSpec": {
                "id": "agent.analyst",
                "version": "1.0.0",
                "definitionHash": "sha256:agent",
            },
        }


@pytest.mark.asyncio
async def test_resolver_queries_company_with_the_project_agent_deployment_pin():
    client = RecordingCompanyClient()
    resolver = CompanyDeploymentAuthorityResolver(client)

    authority = await resolver.resolve_authority("ws-1", "proj-1", "deployment-1")

    assert client.calls == [("ws-1", "proj-1", "deployment-1")]
    assert authority["workspaceId"] == "ws-1"
    assert authority["projectId"] == "proj-1"
    assert authority["projectAgentDeploymentId"] == "deployment-1"


@pytest.mark.asyncio
async def test_resolver_loads_only_exact_published_workspace_skill_pins():
    repository = InMemoryWorkspaceAssetRepository()
    draft = await repository.create_draft(
        "ws-1",
        WorkspaceAssetDraft(
            asset_id="skill.sales.summary",
            version="1.0.0",
            name="Sales summary",
            description="Summarizes a sales report",
            kind=AssetKind.SKILL,
            content={"instructions": "Summarize the report."},
            scope=AssetScope.workspace(),
            created_by="founder-1",
        ),
    )
    await repository.publish("ws-1", draft.asset_id, draft.version, draft.definition_hash)
    resolver = CompanyDeploymentAuthorityResolver(RecordingCompanyClient(), asset_repository=repository)

    skills = await resolver.resolve_skills(
        "ws-1",
        {
            draft.asset_id: {
                "version": draft.version,
                "definition_hash": draft.definition_hash,
            }
        },
    )

    assert skills[draft.asset_id].definition_hash == draft.definition_hash
