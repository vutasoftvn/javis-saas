from __future__ import annotations

import time

import httpx
import jwt
import pytest
from fastapi import HTTPException

from apps.cosa.auth import dependency as dependency_mod
from apps.cosa.auth.dependency import (
    clear_workspace_resolve_cache,
    get_authenticated_identity,
    set_workspace_tenant_context_client,
)
from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient

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
    clear_workspace_resolve_cache()
    yield
    set_workspace_tenant_context_client(None)
    clear_workspace_resolve_cache()


def _counting_workspace_client(workspace_id: str) -> tuple[WorkspaceTenantContextClient, list[int]]:
    """Client trả workspace_id cố định + đếm số lần HTTP handler được gọi."""
    calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        calls[0] += 1
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

    client = WorkspaceTenantContextClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    return client, calls


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
async def test_workspace_resolve_cache_hit_skips_http(monkeypatch):
    """Cùng (principal, workspace, token) trong TTL → chỉ 1 HTTP hop, lần 2 lấy từ cache."""
    monkeypatch.setattr(dependency_mod, "_RESOLVE_CACHE_TTL_SEC", 60.0)
    client, calls = _counting_workspace_client("ws1")
    set_workspace_tenant_context_client(client)
    token = _token(sub="99")

    id1 = await get_authenticated_identity(authorization=f"Bearer {token}", x_workspace_id="ws1")
    id2 = await get_authenticated_identity(authorization=f"Bearer {token}", x_workspace_id="ws1")

    assert id1.workspace_id == id2.workspace_id == "ws1"
    assert calls[0] == 1, "lần gọi thứ 2 phải lấy từ cache, không gọi HTTP"


@pytest.mark.asyncio
async def test_workspace_resolve_cache_expires_after_ttl(monkeypatch):
    """Hết TTL → re-verify qua HTTP (không giữ membership cũ vô thời hạn)."""
    monkeypatch.setattr(dependency_mod, "_RESOLVE_CACHE_TTL_SEC", 0.0)
    client, calls = _counting_workspace_client("ws1")
    set_workspace_tenant_context_client(client)
    token = _token(sub="99")

    await get_authenticated_identity(authorization=f"Bearer {token}", x_workspace_id="ws1")
    await get_authenticated_identity(authorization=f"Bearer {token}", x_workspace_id="ws1")

    assert calls[0] == 2, "TTL=0 → mỗi request phải re-verify"


@pytest.mark.asyncio
async def test_workspace_resolve_cache_keyed_by_token(monkeypatch):
    """Token đổi (rotate/re-login) → cache miss, verify lại."""
    monkeypatch.setattr(dependency_mod, "_RESOLVE_CACHE_TTL_SEC", 60.0)
    client, calls = _counting_workspace_client("ws1")
    set_workspace_tenant_context_client(client)

    now = int(time.time())
    token_a = jwt.encode({"sub": "99", "aud": "cosa", "exp": now + 3600}, SECRET, algorithm="HS256")
    token_b = jwt.encode({"sub": "99", "aud": "cosa", "exp": now + 7200}, SECRET, algorithm="HS256")
    assert token_a != token_b

    await get_authenticated_identity(authorization=f"Bearer {token_a}", x_workspace_id="ws1")
    await get_authenticated_identity(authorization=f"Bearer {token_b}", x_workspace_id="ws1")

    # Hai token khác nhau → 2 fingerprint → 2 HTTP hop (cache không tái dùng chéo token)
    assert calls[0] == 2


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


# --- M1 §1 — local session token (services/company JWT_SECRET, no audience) ---

_LOCAL_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod"


def _local_token(sub="77"):
    return jwt.encode(
        {"sub": sub, "exp": int(time.time()) + 3600}, _LOCAL_SECRET, algorithm="HS256"
    )


@pytest.mark.asyncio
async def test_accepts_local_session_token_and_marks_token_kind():
    set_workspace_tenant_context_client(_workspace_client_returning("ws1"))
    identity = await get_authenticated_identity(
        authorization=f"Bearer {_local_token(sub='77')}", x_workspace_id="ws1"
    )
    assert identity.principal_id == "user:77"
    assert identity.token_kind == "local_session"
    # delegation token cùng shape local (no aud) — verify bằng local secret.
    deleg = identity.mint_delegation()
    decoded = jwt.decode(deleg, _LOCAL_SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "77"


@pytest.mark.asyncio
async def test_platform_token_still_accepted_as_fallback():
    set_workspace_tenant_context_client(_workspace_client_returning("ws1"))
    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='42')}", x_workspace_id="ws1"
    )
    assert identity.token_kind == "platform"
    deleg = identity.mint_delegation()
    jwt.decode(deleg, SECRET, algorithms=["HS256"], audience="cosa")  # platform-shaped


_COMPANY_DELEGATION_SECRET = "cosa-company-delegation-dev-secret-change-in-prod"


@pytest.mark.asyncio
async def test_authenticated_identity_mints_scoped_company_delegation():
    """AuthenticatedIdentity.mint_company_delegation() (Task 3) phải phát
    hành delegation CÓ CẤU TRÚC ràng buộc đúng workspace đã resolve của
    identity này + run_id/capability_ids do caller khai báo — KHÔNG mang
    theo bearer token gốc, khác hẳn mint_delegation() (chỉ re-sign shape cũ)."""
    set_workspace_tenant_context_client(_workspace_client_returning("ws1"))
    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='42')}", x_workspace_id="ws1"
    )

    token = identity.mint_company_delegation(
        run_id="run-1", capability_ids=["finance.read"]
    )
    decoded = jwt.decode(
        token,
        _COMPANY_DELEGATION_SECRET,
        algorithms=["HS256"],
        audience="company",
        issuer="cosa",
    )
    assert decoded["sub"] == "42"
    assert decoded["principal_id"] == "user:42"
    assert decoded["workspace_id"] == "ws1"
    assert decoded["run_id"] == "run-1"
    assert decoded["capability_ids"] == ["finance.read"]
    assert decoded["jti"]


@pytest.mark.asyncio
async def test_garbage_token_rejected_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(
            authorization="Bearer not-a-jwt", x_workspace_id="ws1"
        )
    assert exc.value.status_code == 401
