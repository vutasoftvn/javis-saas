from __future__ import annotations

from typing import Any

from packages.agent.assets.contracts import AssetKind, AssetLifecycle
from packages.agent.assets.repository import WorkspaceAssetRepository


class CompanyDeploymentAuthorityResolver:
    """Resolves live Company deployment authority for governed AGENT steps."""

    def __init__(
        self,
        company_client: Any,
        asset_repository: WorkspaceAssetRepository | None = None,
    ) -> None:
        self._company_client = company_client
        self._asset_repository = asset_repository

    async def resolve_authority(
        self,
        workspace_id: str,
        project_id: str,
        project_agent_deployment_id: str,
    ) -> dict[str, Any]:
        return await self._company_client.get_project_agent_deployment_authority(
            workspace_id,
            project_id,
            project_agent_deployment_id,
        )

    async def resolve_skills(
        self,
        workspace_id: str,
        skill_refs: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve only exact published Skill assets within one Workspace."""
        if self._asset_repository is None:
            raise RuntimeError("Scoped workspace asset repository is required for workflow skill pins")

        resolved: dict[str, Any] = {}
        for skill_id, raw_ref in skill_refs.items():
            if not isinstance(raw_ref, dict):
                raise ValueError(f"Skill pin '{skill_id}' must include version and definition_hash")
            version = raw_ref.get("version")
            definition_hash = raw_ref.get("definition_hash") or raw_ref.get("definitionHash")
            if not isinstance(version, str) or not isinstance(definition_hash, str):
                raise ValueError(f"Skill pin '{skill_id}' must include version and definition_hash")

            skill = await self._asset_repository.get_version(workspace_id, skill_id, version)
            if skill is None:
                raise ValueError(f"Pinned Skill '{skill_id}:{version}' was not found in its workspace")
            if skill.kind != AssetKind.SKILL:
                raise ValueError(f"Pinned asset '{skill_id}:{version}' is not a Skill")
            if skill.lifecycle != AssetLifecycle.PUBLISHED:
                raise ValueError(f"Pinned Skill '{skill_id}:{version}' is not published")
            if skill.definition_hash != definition_hash:
                raise ValueError(f"Pinned Skill '{skill_id}:{version}' does not match its definition hash")
            resolved[skill_id] = skill
        return resolved
