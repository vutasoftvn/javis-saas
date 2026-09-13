from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from apps.cosa.assets.authoring_service import AuthoringService
from apps.cosa.assets.evaluation_service import EvaluationService
from apps.cosa.assets.schemas import AuthoringCommand, AuthoringResponse
from packages.agent.assets.contracts import (
    AssetKind,
    AssetScope,
    PinnedAssetIdentity,
)
from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository
from packages.agent.workflows.repository import InMemoryWorkflowDefinitionRepository

router = APIRouter(prefix="/agent/internal/founder-assets", tags=["founder-assets-internal"])

_DEV_SERVICE_TOKEN = "dev-founder-asset-service-token"

# Shared fallback instances for internal routes
_default_repo = InMemoryWorkspaceAssetRepository()
_default_eval_service = EvaluationService(_default_repo)
_default_authoring_service = AuthoringService(
    _default_repo,
    _default_eval_service,
    workflow_definition_repository=InMemoryWorkflowDefinitionRepository(),
)


def get_authoring_service(request: Request | None = None) -> AuthoringService:
    if request is not None:
        if hasattr(request.app.state, "authoring_service") and request.app.state.authoring_service:
            return request.app.state.authoring_service
        plane = getattr(request.app.state, "plane", None)
        if plane is not None:
            if hasattr(plane, "authoring_service") and plane.authoring_service:
                return plane.authoring_service
            deps = getattr(plane, "event_intake_deps", None)
            if deps is not None and getattr(deps, "authoring_service", None):
                return deps.authoring_service

    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    if env_name in ("production", "staging", "prod"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AuthoringService not configured with persistent PostgreSQL repository in production",
        )
    return _default_authoring_service


def get_evaluation_service(request: Request | None = None) -> EvaluationService:
    if request is not None:
        if hasattr(request.app.state, "evaluation_service") and request.app.state.evaluation_service:
            return request.app.state.evaluation_service
        plane = getattr(request.app.state, "plane", None)
        if plane is not None:
            if hasattr(plane, "evaluation_service") and plane.evaluation_service:
                return plane.evaluation_service
            deps = getattr(plane, "event_intake_deps", None)
            if deps is not None and getattr(deps, "evaluation_service", None):
                return deps.evaluation_service

    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    if env_name in ("production", "staging", "prod"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EvaluationService not configured with persistent PostgreSQL repository in production",
        )
    return _default_eval_service


def _require_service_token(token: str | None) -> None:
    expected = os.environ.get("FOUNDER_ASSET_SERVICE_TOKEN")
    if not expected:
        if os.environ.get("ENVIRONMENT") in ("production", "prod"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FOUNDER_ASSET_SERVICE_TOKEN is not configured",
            )
        expected = _DEV_SERVICE_TOKEN

    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid founder asset service token",
        )


@router.post("/commands", response_model=AuthoringResponse)
async def handle_authoring_command(
    body: AuthoringCommand,
    request: Request,
    x_service_token: str | None = Header(default=None),
) -> AuthoringResponse:
    _require_service_token(x_service_token)

    auth_svc = get_authoring_service(request)
    eval_svc = get_evaluation_service(request)

    if body.operation == "CREATE":
        scope = (
            AssetScope.project_sandbox(body.project_id)
            if body.scope_kind == "PROJECT_SANDBOX" and body.project_id
            else AssetScope.workspace()
        )
        kind = AssetKind(body.asset_kind or "AGENT")
        if kind == AssetKind.AGENT:
            saved = await auth_svc.create_agent_draft(
                workspace_id=body.workspace_id,
                asset_id=body.asset_id or "unnamed-agent",
                version=body.version or "0.1.0",
                name=body.name or "Unnamed Agent",
                description=body.description,
                content=body.content or {},
                scope=scope,
                created_by=body.created_by,
            )
        elif kind == AssetKind.SKILL:
            saved = await auth_svc.create_skill_draft(
                workspace_id=body.workspace_id,
                asset_id=body.asset_id or "unnamed-skill",
                version=body.version or "0.1.0",
                name=body.name or "Unnamed Skill",
                description=body.description,
                content=body.content or {},
                scope=scope,
                created_by=body.created_by,
            )
        elif kind == AssetKind.WORKFLOW:
            saved = await auth_svc.create_workflow_draft(
                workspace_id=body.workspace_id,
                asset_id=body.asset_id or "unnamed-workflow",
                version=body.version or "0.1.0",
                name=body.name or "Unnamed Workflow",
                description=body.description,
                content=body.content or {},
                scope=scope,
                created_by=body.created_by,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported asset kind: {body.asset_kind}")

        return AuthoringResponse(
            asset_id=saved.asset_id,
            version=saved.version,
            definition_hash=saved.definition_hash,
            status="DRAFT",
            lifecycle=saved.lifecycle.value,
        )

    elif body.operation == "CLONE":
        if not body.source_asset_id or not body.source_version or not body.source_definition_hash:
            raise HTTPException(status_code=400, detail="Missing source asset parameters for CLONE")
        source = PinnedAssetIdentity(
            kind=AssetKind(body.asset_kind or "AGENT"),
            asset_id=body.source_asset_id,
            version=body.source_version,
            definition_hash=body.source_definition_hash,
        )
        scope = (
            AssetScope.project_sandbox(body.project_id)
            if body.scope_kind == "PROJECT_SANDBOX" and body.project_id
            else AssetScope.workspace()
        )
        cloned = await auth_svc.clone(
            workspace_id=body.workspace_id,
            source=source,
            target_scope=scope,
            created_by=body.created_by,
        )
        return AuthoringResponse(
            asset_id=cloned.asset_id,
            version=cloned.version,
            definition_hash=cloned.definition_hash,
            status="DRAFT",
            lifecycle=cloned.lifecycle.value,
        )

    elif body.operation == "EVALUATE":
        if not body.asset_id or not body.version:
            raise HTTPException(status_code=400, detail="Missing asset_id or version for EVALUATE")
        eval_result = await eval_svc.evaluate(
            workspace_id=body.workspace_id,
            asset_id=body.asset_id,
            version=body.version,
        )
        return AuthoringResponse(
            asset_id=body.asset_id,
            version=body.version,
            definition_hash=eval_result.definition_hash,
            status=eval_result.status,
            lifecycle="REVIEW_REQUIRED" if eval_result.status == "PASS" else "DRAFT",
            details={"evaluation_id": eval_result.evaluation_id},
        )

    elif body.operation == "PUBLISH":
        if not body.asset_id or not body.expected_hash:
            raise HTTPException(status_code=400, detail="Missing asset_id or expected_hash for PUBLISH")
        if not body.company_command_ref:
            raise HTTPException(
                status_code=400,
                detail="company_command_ref is required for publish to preserve founder authority chain",
            )
        published = await auth_svc.publish(
            workspace_id=body.workspace_id,
            asset_id=body.asset_id,
            expected_hash=body.expected_hash,
            company_command_ref=body.company_command_ref,
            version=body.version,
        )
        return AuthoringResponse(
            asset_id=published.asset_id,
            version=published.version,
            definition_hash=published.definition_hash,
            status="PUBLISHED",
            lifecycle=published.lifecycle.value,
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {body.operation}")


@router.get("/{asset_id}/status", response_model=AuthoringResponse)
async def get_asset_status(
    asset_id: str,
    request: Request,
    workspace_id: str = Query(...),
    version: str = Query("0.1.0"),
    x_service_token: str | None = Header(default=None),
) -> AuthoringResponse:
    _require_service_token(x_service_token)
    auth_svc = get_authoring_service(request)
    item = await auth_svc._repository.get_version(workspace_id, asset_id, version)
    if not item:
        raise HTTPException(status_code=404, detail="Asset version not found")

    return AuthoringResponse(
        asset_id=item.asset_id,
        version=item.version,
        definition_hash=item.definition_hash,
        status=item.lifecycle.value,
        lifecycle=item.lifecycle.value,
    )
