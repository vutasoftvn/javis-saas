from __future__ import annotations

import time

import httpx
import jwt
import pytest
from fastapi import HTTPException

from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient
from apps.cosa.auth.dependency import get_authenticated_identity, set_workspace_tenant_context_client

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def _token(sub="42"):
    return jwt.encode({"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")


def _workspace_client_returning(workspace_id: str) -> WorkspaceTenantContextClient:
    """Mock workspace client returning only workspace-scoped fields."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workspaceId": workspace_id,
                "userId": "99",
                "membershipRole": "founder",
                "permissions": ["*"],
                "correlationId": "corr-1",
            },
        )

    return WorkspaceTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _reset_auth_client():
    yield
    set_workspace_tenant_context_client(None)


@pytest.mark.asyncio
async def test_missing_authorization_header_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=None, x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_authorization_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization="Basic abc", x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwt_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization="Bearer garbage", x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_workspace_header_400():
    """Missing X-Workspace-Id header must return 400."""
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token()}", x_workspace_id=None)
    assert exc.value.status_code == 400
    assert "X-Workspace-Id" in exc.value.detail


@pytest.mark.asyncio
async def test_workspace_not_in_resolved_membership_403_tenant_scope_mismatch():
    """Requested workspace doesn't match server-resolved workspace -> 403."""
    set_workspace_tenant_context_client(_workspace_client_returning("ws_authoritative"))

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(
            authorization=f"Bearer {_token()}", x_workspace_id="ws_different"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "tenant_scope_mismatch"


@pytest.mark.asyncio
async def test_workspace_succeeds_with_correct_identity():
    """Valid bearer token + matching workspace returns AuthenticatedIdentity."""
    set_workspace_tenant_context_client(_workspace_client_returning("ws1"))

    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='99')}", x_workspace_id="ws1"
    )
    assert identity.principal_id == "user:99"
    assert identity.workspace_id == "ws1"
    assert identity.role_id == "founder"
    assert not hasattr(identity, "company_id"), "AuthenticatedIdentity should not have company_id"


@pytest.mark.asyncio
async def test_workspace_verification_unavailable_fails_closed_502():
    """Workspace verification failure must fail closed (502)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    set_workspace_tenant_context_client(
        WorkspaceTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))
    )

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token()}", x_workspace_id="ws1")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_x_company_id_ignored_if_present():
    """X-Company-Id header is ignored in workspace-only mode."""
    set_workspace_tenant_context_client(_workspace_client_returning("ws1"))

    # Even though X-Company-Id is passed, it should be ignored
    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='99')}",
        x_workspace_id="ws1"
    )
    assert identity.workspace_id == "ws1"
    assert identity.principal_id == "user:99"
