from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

FOUNDER_ASSET_COMMANDED_EVENT = "founder.asset.commanded.v1"
FOUNDER_ASSET_STATUS_EVENT = "founder.asset.status.v1"

_FORBIDDEN_KEYS = (
    "secret",
    "password",
    "access_token",
    "api_key",
    "raw_prompt",
    "prompt_override",
)


class AssetRefModel(BaseModel):
    asset_id: str = Field(alias="assetId")
    version: str | None = None
    definition_hash: str | None = Field(default=None, alias="definitionHash")

    class Config:
        populate_by_name = True


class FounderAssetCommand(BaseModel):
    command_id: str = Field(alias="commandId")
    workspace_id: str = Field(alias="workspaceId")
    project_id: str | None = Field(default=None, alias="projectId")
    asset_kind: str = Field(alias="assetKind")
    operation: str
    asset_ref: AssetRefModel = Field(alias="assetRef")
    expected_version: int = Field(default=1, alias="expectedVersion")
    idempotency_key: str = Field(alias="idempotencyKey")
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


def validate_founder_asset_command_payload(payload: dict[str, Any]) -> tuple[FounderAssetCommand | None, str | None]:
    if not isinstance(payload, dict):
        return None, "payload must be an object"

    for forbidden in _FORBIDDEN_KEYS:
        if forbidden in payload:
            return None, f"payload contains forbidden key: {forbidden}"

    try:
        cmd = FounderAssetCommand.model_validate(payload)
        return cmd, None
    except Exception as e:
        return None, f"invalid founder asset command: {e}"


async def dispatch_founder_asset_command(deps: Any, env: Any) -> tuple[str, str | None]:
    """Handles founder.asset.commanded.v1 inside router.

    Returns (outcome, reason/scheduled_task_id).
    """
    payload = getattr(env, "payload", {}) or {}
    cmd, err = validate_founder_asset_command_payload(payload)
    if err is not None or cmd is None:
        return "rejected", err or "invalid command payload"

    if cmd.workspace_id != env.workspaceId:
        return "rejected", "workspace mismatch"

    # If deps has explicit founder_asset_handler (used in test mocks or external dispatch):
    handler = getattr(deps, "founder_asset_handler", None)
    if handler is not None:
        if hasattr(handler, "handle_asset_command"):
            await handler.handle_asset_command(payload)
        return "accepted", None

    # Production dispatch via authoring_service / evaluation_service
    authoring_service = getattr(deps, "authoring_service", None)
    evaluation_service = getattr(deps, "evaluation_service", None)
    callback_client = getattr(deps, "status_callback_client", None)

    if authoring_service is not None:
        from packages.agent.assets.contracts import AssetKind, AssetScope, PinnedAssetIdentity

        target_scope = (
            AssetScope.project_sandbox(cmd.project_id)
            if cmd.project_id
            else AssetScope.workspace()
        )
        source_id = PinnedAssetIdentity(
            kind=AssetKind(cmd.asset_kind),
            asset_id=cmd.asset_ref.asset_id,
            version=cmd.asset_ref.version or "1.0.0",
            definition_hash=cmd.asset_ref.definition_hash or "sha256:placeholder",
        )

        status = "SUCCESS"
        out_ref: dict[str, Any] = {
            "assetId": cmd.asset_ref.asset_id,
            "version": cmd.asset_ref.version,
            "definitionHash": cmd.asset_ref.definition_hash,
        }
        eval_summary: dict[str, Any] | None = None
        safe_reason: str | None = None

        try:
            if cmd.operation == "CLONE":
                res = await authoring_service.clone(
                    workspace_id=cmd.workspace_id,
                    source=source_id,
                    target_scope=target_scope,
                    created_by=getattr(getattr(env, "actor", None), "id", "founder"),
                )
                out_ref = {
                    "assetId": res.asset_id,
                    "version": res.version,
                    "definitionHash": res.definition_hash,
                }
            elif cmd.operation == "CREATE":
                if source_id.kind == AssetKind.AGENT:
                    res = await authoring_service.create_agent_draft(
                        workspace_id=cmd.workspace_id,
                        asset_id=cmd.asset_ref.asset_id,
                        version=cmd.asset_ref.version or "0.1.0",
                        name=cmd.metadata.get("name", cmd.asset_ref.asset_id),
                        description=cmd.metadata.get("description"),
                        content=cmd.metadata.get("content", {}),
                        scope=target_scope,
                        created_by=getattr(getattr(env, "actor", None), "id", "founder"),
                    )
                elif source_id.kind == AssetKind.SKILL:
                    res = await authoring_service.create_skill_draft(
                        workspace_id=cmd.workspace_id,
                        asset_id=cmd.asset_ref.asset_id,
                        version=cmd.asset_ref.version or "0.1.0",
                        name=cmd.metadata.get("name", cmd.asset_ref.asset_id),
                        description=cmd.metadata.get("description"),
                        content=cmd.metadata.get("content", {}),
                        scope=target_scope,
                        created_by=getattr(getattr(env, "actor", None), "id", "founder"),
                    )
                elif source_id.kind == AssetKind.WORKFLOW:
                    res = await authoring_service.create_workflow_draft(
                        workspace_id=cmd.workspace_id,
                        asset_id=cmd.asset_ref.asset_id,
                        version=cmd.asset_ref.version or "0.1.0",
                        name=cmd.metadata.get("name", cmd.asset_ref.asset_id),
                        description=cmd.metadata.get("description"),
                        content=cmd.metadata.get("content", {}),
                        scope=target_scope,
                        created_by=getattr(getattr(env, "actor", None), "id", "founder"),
                    )
                else:
                    raise ValueError(f"Unsupported create asset kind: {source_id.kind}")
                out_ref = {
                    "assetId": res.asset_id,
                    "version": res.version,
                    "definitionHash": res.definition_hash,
                }
            elif cmd.operation == "EDIT_DRAFT":
                res = await authoring_service.edit(
                    workspace_id=cmd.workspace_id,
                    identity=source_id,
                    content=cmd.metadata.get("content", {}),
                )
                out_ref = {
                    "assetId": res.asset_id,
                    "version": res.version,
                    "definitionHash": res.definition_hash,
                }
            elif cmd.operation == "EVALUATE":
                if evaluation_service is not None:
                    eval_res = await evaluation_service.evaluate(
                        workspace_id=cmd.workspace_id,
                        asset_id=cmd.asset_ref.asset_id,
                        version=cmd.asset_ref.version or "0.1.0",
                    )
                    status = "SUCCESS" if eval_res.status == "PASS" else "REJECTED"
                    eval_summary = {
                        "status": eval_res.status,
                        "evaluation_id": eval_res.evaluation_id,
                        "structural_result": eval_res.structural_result,
                    }
            elif cmd.operation == "PUBLISH":
                res = await authoring_service.publish(
                    workspace_id=cmd.workspace_id,
                    asset_id=cmd.asset_ref.asset_id,
                    expected_hash=cmd.asset_ref.definition_hash or "",
                    company_command_ref=cmd.command_id,
                )
                out_ref = {
                    "assetId": res.asset_id,
                    "version": res.version,
                    "definitionHash": res.definition_hash,
                }
            else:
                status = "REJECTED"
                safe_reason = f"Unsupported operation: {cmd.operation}"
        except Exception as exc:
            status = "FAILED"
            safe_reason = str(exc)

        # Dispatch status callback to Company
        if callback_client is not None:
            try:
                await callback_client.send_status_callback(
                    command_id=cmd.command_id,
                    workspace_id=cmd.workspace_id,
                    project_id=cmd.project_id,
                    asset_kind=cmd.asset_kind,
                    operation=cmd.operation,
                    status=status,
                    asset_ref=out_ref,
                    evaluation_summary=eval_summary,
                    safe_reason_code=safe_reason,
                )
            except Exception as cb_err:
                logger.error(
                    "Callback delivery failed for command %s: %s",
                    cmd.command_id,
                    cb_err,
                )
                return "failed", f"callback delivery failed: {cb_err}"

    return "accepted", None
