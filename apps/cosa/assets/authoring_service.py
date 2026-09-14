from __future__ import annotations

from typing import Any

from agent.assets.contracts import (
    AssetConflictError,
    AssetKind,
    AssetLifecycle,
    AssetNotEvaluatedError,
    AssetNotFoundError,
    AssetScope,
    AssetScopeKind,
    BuiltinAssetReadOnlyError,
    PinnedAssetIdentity,
    WorkspaceAssetDraft,
    WorkspaceAssetVersion,
)
from agent.assets.repository import WorkspaceAssetRepository
from agent.workflows.repository import WorkflowDefinitionRepository

from apps.cosa.assets.evaluation_service import EvaluationService


class WorkflowPublishDisabledError(Exception):
    """Raised when publishing a workflow is disabled pending registered runtime executors."""


class AuthoringService:
    def __init__(
        self,
        repository: WorkspaceAssetRepository,
        evaluation_service: EvaluationService,
        spec_registry: Any | None = None,
        workflow_definition_repository: WorkflowDefinitionRepository | None = None,
    ) -> None:
        self._repository = repository
        self._evaluation_service = evaluation_service
        self._spec_registry = spec_registry
        self._workflow_definition_repository = workflow_definition_repository

    async def edit(
        self,
        workspace_id: str,
        identity: PinnedAssetIdentity,
        content: dict[str, Any],
    ) -> WorkspaceAssetVersion:
        # Check if asset is builtin (immutable)
        if identity.asset_id.startswith("builtin.") or getattr(identity, "origin", None) == "BUILTIN":
            raise BuiltinAssetReadOnlyError(f"Built-in asset {identity.asset_id} cannot be edited directly")

        # Mutate draft
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
        content = source_content
        if content is None:
            # 1. Try resolving from existing published asset in repository
            existing = await self._repository.get_version(workspace_id, source.asset_id, source.version)
            if existing:
                content = existing.content_json
            # 2. Try resolving from spec_registry if available
            elif self._spec_registry is not None:
                kind_str = source.kind.value.lower() if hasattr(source.kind, "value") else str(source.kind).lower()
                rec = await self._spec_registry.get(kind_str, source.asset_id, source.version)
                if rec:
                    content = (
                        getattr(rec, "spec_data", None)
                        or (rec.get("spec_data") if isinstance(rec, dict) else None)
                        or getattr(rec, "content", None)
                        or {}
                    )

            if not content:
                raise AssetNotFoundError(
                    f"Source asset {source.asset_id}:{source.version} not found for clone"
                )

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
            version=version,
            name=name,
            description=description,
            kind=AssetKind.AGENT,
            content=content,
            scope=scope,
            created_by=created_by,
        )
        return await self._repository.create_draft(workspace_id, draft)

    async def create_skill_draft(
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
            version=version,
            name=name,
            description=description,
            kind=AssetKind.SKILL,
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
            version=version,
            name=name,
            description=description,
            kind=AssetKind.WORKFLOW,
            content=content,
            scope=scope,
            created_by=created_by,
        )
        return await self._repository.create_draft(workspace_id, draft)

    async def evaluate_draft(
        self,
        workspace_id: str,
        asset_id: str,
        version: str,
    ) -> dict[str, Any]:
        item = await self._repository.get_version(workspace_id, asset_id, version)
        if not item:
            raise AssetNotFoundError(f"Asset version {asset_id}:{version} not found")

        eval_result = await self._evaluation_service.evaluate(
            workspace_id=workspace_id,
            asset_id=asset_id,
            version=version,
        )
        return {
            "evaluation_id": eval_result.evaluation_id,
            "status": eval_result.status,
            "definition_hash": eval_result.definition_hash,
        }

    async def publish(
        self,
        workspace_id: str,
        asset_id: str,
        expected_hash: str,
        company_command_ref: str | None = None,
        version: str | None = None,
    ) -> WorkspaceAssetVersion:
        if not company_command_ref:
            raise ValueError("company_command_ref is required to publish an asset")

        # Load candidate/draft version: explicit version or latest version
        if version is not None:
            item = await self._repository.get_version(workspace_id, asset_id, version)
        else:
            item = await self._repository.get_latest_version(workspace_id, asset_id)

        if not item:
            raise AssetNotFoundError(f"Asset {asset_id} not found in workspace {workspace_id}")

        if item.definition_hash != expected_hash:
            raise AssetConflictError(
                f"expected_hash mismatch for asset {asset_id}:{item.version}: "
                f"expected {expected_hash}, found {item.definition_hash}"
            )

        # Check if asset is a workflow:
        is_workflow = item.kind == AssetKind.WORKFLOW

        # Verify evaluation
        latest_eval = await self._repository.get_latest_evaluation(workspace_id, asset_id, item.version)
        if not latest_eval or latest_eval.status != "PASS":
            if is_workflow:
                raise WorkflowPublishDisabledError(
                    f"Workflow {asset_id} version {item.version} requires a passing evaluation before publish"
                )
            raise AssetNotEvaluatedError(
                f"Asset {asset_id} version {item.version} requires a passing evaluation before publish"
            )

        # For workflow assets, validate full DAG structure, executor readiness, and require REVIEW_REQUIRED
        if is_workflow:
            from agent.workflows.schema import WorkflowSpec
            from agent.workflows.validation import (
                WorkflowPublishValidator,
                WorkflowValidationContext,
            )

            if item.lifecycle not in (AssetLifecycle.REVIEW_REQUIRED, "REVIEW_REQUIRED"):
                raise WorkflowPublishDisabledError(
                    f"Workflow {asset_id} version {item.version} must be in REVIEW_REQUIRED state to publish "
                    f"(current: {item.lifecycle})"
                )

            try:
                spec = WorkflowSpec.model_validate(item.content_json)
            except Exception as exc:
                raise WorkflowPublishDisabledError(f"Workflow schema validation failed: {exc}") from exc

            val_res = WorkflowPublishValidator.validate(
                spec,
                WorkflowValidationContext(
                    workspace_id=workspace_id,
                    project_id=getattr(item.scope, "project_id", None) if hasattr(item, "scope") else None,
                ),
            )
            if not val_res.is_valid:
                raise WorkflowPublishDisabledError(
                    f"Workflow publish validation failed: {'; '.join(val_res.errors)}"
                )

            if self._workflow_definition_repository is None:
                raise WorkflowPublishDisabledError(
                    "Workflow publish requires a durable workflow definition repository"
                )

            # Asset version is the canonical identity surfaced to Company.
            # Persist that exact asset hash in the executable definition so a
            # Project binding and a run manifest pin the same immutable body.
            persisted_spec = spec.model_copy(update={"definition_hash": item.definition_hash})
            definition = await self._workflow_definition_repository.save_definition(
                persisted_spec,
                workspace_id=workspace_id,
            )
            if definition.definition_hash != item.definition_hash:
                raise WorkflowPublishDisabledError(
                    "Durable workflow definition hash does not match the asset version hash"
                )

        return await self._repository.publish(
            workspace_id, asset_id, item.version, expected_hash
        )
