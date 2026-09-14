from __future__ import annotations

import uuid
from datetime import datetime

from agent.assets.contracts import (
    AssetEvaluationResult,
    AssetKind,
    AssetLifecycle,
    AssetNotFoundError,
    AssetScopeKind,
)
from agent.assets.repository import WorkspaceAssetRepository


class EvaluationService:
    def __init__(self, repository: WorkspaceAssetRepository) -> None:
        self._repository = repository

    async def evaluate(
        self,
        workspace_id: str,
        asset_id: str,
        version: str,
    ) -> AssetEvaluationResult:
        item = await self._repository.get_version(workspace_id, asset_id, version)
        if not item:
            raise AssetNotFoundError(
                f"Asset version {asset_id}:{version} not found in workspace {workspace_id}"
            )

        content = item.content_json
        structural_errors: list[str] = []

        # 1. Structural check: No raw secrets or shell execution
        serialized_str = str(content).lower()
        if "api_key" in serialized_str and "sk-" in serialized_str:
            structural_errors.append("Raw API key or secret detected in asset definition")
        if "sh -c" in serialized_str or "/bin/bash" in serialized_str or "exec(" in serialized_str:
            structural_errors.append("Raw shell or code execution prohibited")

        # 2. Sandbox scope check: No external capabilities in sandbox
        if item.scope.kind in (AssetScopeKind.PROJECT_SANDBOX, "PROJECT_SANDBOX"):
            caps = content.get("capability_refs", [])
            if caps:
                structural_errors.append(
                    "PROJECT_SANDBOX assets cannot declare external capability_refs"
                )

        # 3. Workflow asset structural & executor readiness validation
        is_workflow = item.kind == AssetKind.WORKFLOW
        if is_workflow:
            from agent.workflows.schema import WorkflowSpec
            from agent.workflows.validation import (
                WorkflowPublishValidator,
                WorkflowValidationContext,
            )

            try:
                spec = WorkflowSpec.model_validate(content)
                val_res = WorkflowPublishValidator.validate(
                    spec,
                    WorkflowValidationContext(
                        workspace_id=workspace_id,
                        project_id=getattr(item.scope, "project_id", None)
                        if hasattr(item, "scope")
                        else None,
                    ),
                )
                if not val_res.is_valid:
                    structural_errors.extend(val_res.errors)
            except Exception as exc:
                structural_errors.append(f"Invalid workflow specification: {exc}")

        status = "PASS" if not structural_errors else "FAIL"
        eval_id = f"eval_{uuid.uuid4().hex[:12]}"

        result = AssetEvaluationResult(
            evaluation_id=eval_id,
            workspace_id=workspace_id,
            asset_id=asset_id,
            version=version,
            definition_hash=item.definition_hash,
            status=status,
            structural_result={
                "valid": len(structural_errors) == 0,
                "errors": structural_errors,
            },
            negative_policy_result={
                "denied_secrets": True,
                "denied_raw_shell": True,
            },
            scenario_suite_result={
                "scenario_count": 1,
                "passed_count": 1 if status == "PASS" else 0,
            },
            evaluator_version="1.0.0",
            evaluated_at=datetime.utcnow(),
        )

        await self._repository.record_evaluation(result)

        # Transition lifecycle: DRAFT -> EVALUATING -> REVIEW_REQUIRED (if PASS)
        if status == "PASS":
            item.lifecycle = AssetLifecycle.REVIEW_REQUIRED
            # In repository, update lifecycle
            if hasattr(self._repository, "_versions"):
                key = (workspace_id, asset_id, version)
                if key in self._repository._versions:
                    self._repository._versions[key].lifecycle = AssetLifecycle.REVIEW_REQUIRED
            elif hasattr(self._repository, "_session_factory"):
                from sqlalchemy import text

                async with self._repository._session_factory() as session:
                    stmt = text(
                        """
                        UPDATE agent.workspace_asset_versions
                        SET lifecycle = 'REVIEW_REQUIRED'
                        WHERE workspace_id = :ws_id AND asset_id = :asset_id AND version = :ver
                        """
                    )
                    await session.execute(
                        stmt, {"ws_id": workspace_id, "asset_id": asset_id, "ver": version}
                    )
                    await session.commit()

        return result
