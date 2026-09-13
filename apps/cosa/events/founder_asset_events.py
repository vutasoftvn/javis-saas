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
    if err is not None:
        return "rejected", err

    if cmd.workspace_id != env.workspaceId:
        return "rejected", "workspace mismatch"

    # If deps has explicit founder_asset_handler (used in tests or modular dispatch):
    handler = getattr(deps, "founder_asset_handler", None)
    if handler is not None:
        if hasattr(handler, "handle_asset_command"):
            await handler.handle_asset_command(payload)
        return "accepted", None

    # Production dispatch via authoring_service if available
    authoring_service = getattr(deps, "authoring_service", None)
    if authoring_service is not None:
        from packages.agent.assets.contracts import AssetScope, AssetScopeKind, PinnedAssetIdentity

        target_scope = (
            AssetScope(kind=AssetScopeKind.PROJECT_SANDBOX, project_id=cmd.project_id)
            if cmd.project_id
            else AssetScope(kind=AssetScopeKind.WORKSPACE_SHARED)
        )
        source_id = PinnedAssetIdentity(
            asset_id=cmd.asset_ref.asset_id,
            version=cmd.asset_ref.version or "1.0.0",
            definition_hash=cmd.asset_ref.definition_hash or "sha256:placeholder",
        )

        if cmd.operation == "CLONE":
            await authoring_service.clone(
                workspace_id=cmd.workspace_id,
                source=source_id,
                target_scope=target_scope,
                created_by=getattr(getattr(env, "actor", None), "id", "founder"),
            )
        elif cmd.operation == "EDIT_DRAFT":
            await authoring_service.edit(
                workspace_id=cmd.workspace_id,
                identity=source_id,
                content=cmd.metadata.get("content", {}),
            )
        elif cmd.operation == "PUBLISH":
            await authoring_service.publish(
                workspace_id=cmd.workspace_id,
                asset_id=cmd.asset_ref.asset_id,
                expected_hash=cmd.asset_ref.definition_hash or "",
                company_command_ref=cmd.command_id,
            )

    return "accepted", None
