from __future__ import annotations

import time

import httpx
import jwt
import pytest
from fastapi import HTTPException

from apps.cosa.auth import dependency, require_workspace_operator, resolve_identity_workspace
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    clear_workspace_resolve_cache,
    get_authenticated_identity,
    set_workspace_tenant_context_client,
)
from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient

_PLATFORM_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def _token(sub: str) -> str:
    return jwt.encode(
        {"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600},
        _PLATFORM_SECRET,
        algorithm="HS256",
    )


def _workspace_client_returning(workspace_id: str) -> WorkspaceTenantContextClient:
    """Mock workspace client trả về workspace_id cố định — không gọi network thật."""

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


def make_identity(*, workspace_id: str = "ws-a", role_id: str = "founder") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        principal_id="user:test",
        platform_user_id="test",
        workspace_id=workspace_id,
        role_id=role_id,
        bearer_token="test-token",
    )


def test_workspace_scope_cannot_be_overridden():
    identity = make_identity(workspace_id="ws-a", role_id="member")
    assert resolve_identity_workspace(identity) == "ws-a"
    with pytest.raises(HTTPException) as error:
        resolve_identity_workspace(identity, "ws-b")
    assert error.value.status_code == 404


def test_workspace_operator_requires_privileged_role():
    with pytest.raises(HTTPException) as error:
        require_workspace_operator(make_identity(role_id="member"))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_workspace_cache_is_bounded(monkeypatch):
    """Cache resolve workspace (Part 2C.1) không được phép phình vô hạn — 1
    process chạy lâu dài tiếp nhiều principal/workspace/token phân biệt phải
    bị giới hạn kích thước (LRU-ish: bỏ expired trước, rồi bỏ entry cũ nhất)
    thay vì rò rỉ bộ nhớ không giới hạn."""
    monkeypatch.setattr(dependency, "_RESOLVE_CACHE_MAX_ENTRIES", 2)
    clear_workspace_resolve_cache()
    try:
        for index, workspace_id in enumerate(("ws-a", "ws-b", "ws-c")):
            set_workspace_tenant_context_client(_workspace_client_returning(workspace_id))
            await get_authenticated_identity(
                authorization=f"Bearer {_token(str(index))}", x_workspace_id=workspace_id
            )

        assert len(dependency._resolve_cache) == 2
    finally:
        set_workspace_tenant_context_client(None)
        clear_workspace_resolve_cache()
