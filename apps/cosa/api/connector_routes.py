"""Connector proxy routes for COSA Agent Platform."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.cosa.api.schemas import (
    AuthorizeConnectorRequest,
    GrantConnectorRequest,
    InstallConnectorRequest,
    RevokeGrantRequest,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["create_connector_router"]

router = APIRouter(prefix="/agent", tags=["connectors"])


# 12. Connectors Proxy Routes (Task 3)
@router.post("/connectors/install")
async def install_connector(
    request: Request,
    body: InstallConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/install",
            json={
                "workspaceId": identity.workspace_id,
                "connectorKey": body.connector_key,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/authorize")
async def authorize_connector(
    request: Request,
    body: AuthorizeConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/authorize",
            json={
                "installationId": body.installation_id,
                "secretRef": body.secret_ref,
                "grantedScopes": body.granted_scopes,
                "expiresAt": body.expires_at.isoformat(),
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/grant")
async def grant_connector(
    request: Request,
    body: GrantConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/grant",
            json={
                "workspaceId": identity.workspace_id,
                "conversationId": body.conversation_id,
                "authorizationId": body.authorization_id,
                "allowedActions": body.allowed_actions,
                "expiresAt": body.expires_at.isoformat() if body.expires_at else None,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/revoke")
async def revoke_connector(
    request: Request,
    body: RevokeGrantRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/revoke",
            json={
                "workspaceId": identity.workspace_id,
                "conversationId": body.conversation_id,
                "grantId": body.grant_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


def create_connector_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
