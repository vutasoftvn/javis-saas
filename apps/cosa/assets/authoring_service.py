from __future__ import annotations

from typing import Any

from apps.cosa.assets.evaluation_service import EvaluationService
from packages.agent.assets.contracts import (
    AssetKind,
    AssetNotEvaluatedError,
    AssetNotFoundError,
    AssetScope,
    AssetScopeKind,
    BuiltinAssetReadOnlyError,
    PinnedAssetIdentity,
    WorkspaceAssetDraft,
    WorkspaceAssetVersion,
)
from packages.agent.assets.repository import WorkspaceAssetRepository


class WorkflowPublishDisabledError(Exception):
    """Raised when publishing a workflow is disabled pending registered runtime executors."""


class AuthoringService:
    def __init__(
        self,
        repository: WorkspaceAssetRepository,
        evaluation_service: EvaluationService,
    ) -> None:
        self._repository = repository
        self._evaluation_service = evaluation_service

    async def edit(
        self,
        workspace_id: str,
        identity: PinnedAssetIdentity,
        content: dict[str, Any],
    ) -> WorkspaceAssetVersion:
        if identity.asset_id.startswith("builtin."):
            raise BuiltinAssetReadOnlyError(
                f"Built-in asset {identity.asset_id} is read-only. Founder may only clone."
            )
        return await self._repository.replace_draft_content(
            workspace_id=workspace_id,
            asset_id=identity.asset_id,
            version=identity.version,
            content=content,
        )

    async def clone(
        self,
        workspace_id: str,
        source: PinnedAssetIdentity,
        target_scope: AssetScope,
        created_by: str,
        source_content: dict[str, Any] | None = None,
    ) -> WorkspaceAssetVersion:
        content = source_content or {"instructions": f"Cloned from {source.asset_id}", "model": "gpt-4o"}
        return await self._repository.clone_to_draft(
            workspace_id=workspace_id,
            source=source,
            target_scope=target_scope,
            source_content=content,
            created_by=created_by,
        )

    async def create_agent_draft(
        self,
        workspace_id: str,
        asset_id: str,
        version: str,
        name: str,
        description: str | None,
        content: dict[str, Any],
        scope: AssetScope,
        created_by: str,
    ) -> WorkspaceAssetVersion:
        if scope.kind in (AssetScopeKind.PROJECT_SANDBOX, "PROJECT_SANDBOX"):
            caps = content.get("capability_refs", [])
            if caps:
                raise ValueError("PROJECT_SANDBOX assets cannot declare external capability_refs")

        draft = WorkspaceAssetDraft(
            asset_id=asset_id,
            kind=AssetKind.AGENT,
            version=version,
            name=name,
            description=description,
            content=content,
            scope=scope,
            created_by=created_by,
        )
        return await self._repository.create_draft(workspace_id, draft)

    async def create_workflow_draft(
        self,
        workspace_id: str,
        asset_id: str,
        version: str,
        name: str,
        description: str | None,
        content: dict[str, Any],
        scope: AssetScope,
        created_by: str,
    ) -> WorkspaceAssetVersion:
        draft = WorkspaceAssetDraft(
            asset_id=asset_id,
            kind=AssetKind.WORKFLOW,
            version=version,
            name=name,
            description=description,
            content=content,
            scope=scope,
            created_by=created_by,
        )
        return await self._repository.create_draft(workspace_id, draft)

    async def publish(
        self,
        workspace_id: str,
        asset_id: str,
        expected_hash: str,
        company_command_ref: str | None = None,
    ) -> WorkspaceAssetVersion:
        # Check if asset is a workflow:
        if asset_id.startswith("wf.") or "workflow" in asset_id.lower():
            raise WorkflowPublishDisabledError("WORKFLOW_PUBLISH_DISABLED")

        if not company_command_ref:
            raise ValueError("company_command_ref is required to publish an asset")

        # Load latest candidate/draft version
        item = await self._repository.get_version(workspace_id, asset_id, "0.1.0")
        if not item and hasattr(self._repository, "_versions"):
            matches = [v for (ws, a_id, _), v in self._repository._versions.items() if ws == workspace_id and a_id == asset_id]
            item = matches[0] if matches else None

        if not item:
            raise AssetNotFoundError(f"Asset {asset_id} not found in workspace {workspace_id}")

        # Verify evaluation
        latest_eval = await self._repository.get_latest_evaluation(workspace_id, asset_id, item.version)
        if not latest_eval or latest_eval.status != "PASS":
            raise AssetNotEvaluatedError(
                f"Asset {asset_id} requires a passing evaluation before publish"
            )

        return await self._repository.publish(workspace_id, asset_id, expected_hash)
