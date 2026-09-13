from __future__ import annotations

from typing import Any

from packages.agent.assets.contracts import (
    WorkspaceAssetDraft,
    WorkspaceAssetVersion,
    AssetScope,
    PinnedAssetIdentity,
    AssetConflictError,
    AssetNotFoundError,
    AssetEvaluationResult,
)
from packages.agent.assets.repository import WorkspaceAssetRepository, compute_canonical_hash


class WorkspaceAssetService:
    def __init__(self, repository: WorkspaceAssetRepository) -> None:
        self._repository = repository

    async def create_draft(self, workspace_id: str, draft: WorkspaceAssetDraft) -> WorkspaceAssetVersion:
        return await self._repository.create_draft(workspace_id, draft)

    async def clone_to_draft(
        self,
        workspace_id: str,
        source: PinnedAssetIdentity,
        target_scope: AssetScope,
        source_content: dict[str, Any],
        created_by: str,
    ) -> WorkspaceAssetVersion:
        return await self._repository.clone_to_draft(
            workspace_id=workspace_id,
            source=source,
            target_scope=target_scope,
            source_content=source_content,
            created_by=created_by,
        )

    async def get_version(self, workspace_id: str, asset_id: str, version: str) -> WorkspaceAssetVersion | None:
        return await self._repository.get_version(workspace_id, asset_id, version)

    async def replace_draft_content(
        self, workspace_id: str, asset_id: str, version: str, content: dict[str, Any]
    ) -> WorkspaceAssetVersion:
        return await self._repository.replace_draft_content(workspace_id, asset_id, version, content)

    async def publish(self, workspace_id: str, asset_id: str, expected_hash: str) -> WorkspaceAssetVersion:
        return await self._repository.publish(workspace_id, asset_id, expected_hash)

    async def record_evaluation(self, evaluation: AssetEvaluationResult) -> None:
        await self._repository.record_evaluation(evaluation)

    async def get_latest_evaluation(self, workspace_id: str, asset_id: str, version: str) -> AssetEvaluationResult | None:
        return await self._repository.get_latest_evaluation(workspace_id, asset_id, version)
