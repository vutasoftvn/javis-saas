from __future__ import annotations

import time

import httpx
import jwt
import pytest
from fastapi import HTTPException

from apps.cosa.auth.cosa_client import CosaControlPlaneAuthClient
from apps.cosa.auth.company_client import CompanyTenantContextClient
from apps.cosa.auth.dependency import get_authenticated_identity, set_cosa_auth_client, set_company_tenant_context_client

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def _token(sub="42"):
    return jwt.encode({"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")


def _client_returning(companies: list[dict]) -> CosaControlPlaneAuthClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"companies": companies})

    return CosaControlPlaneAuthClient(base_url="http://test", transport=httpx.MockTransport(handler))


def _workspace_client_returning(workspace_id: str) -> CompanyTenantContextClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "companyId": "c1",
                "workspaceId": workspace_id,
                "userId": "99",
                "membershipRole": "founder",
                "permissions": ["*"],
                "correlationId": "corr-1",
            },
        )

    return CompanyTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _reset_auth_client():
    yield
    set_cosa_auth_client(None)
    set_company_tenant_context_client(None)


@pytest.mark.asyncio
async def test_missing_authorization_header_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=None, x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_authorization_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization="Basic abc", x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwt_401():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization="Bearer garbage", x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_company_header_400():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token()}", x_company_id=None, x_workspace_id="ws1")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_missing_workspace_header_400():
    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token()}", x_company_id="c1", x_workspace_id=None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_company_not_in_membership_list_403_tenant_scope_mismatch():
    """Đây là bài test quan trọng nhất — chứng minh client header KHÔNG được
    tin thẳng: requested company_id không nằm trong danh sách membership thật
    trả về từ COSA control plane -> 403, dù JWT hợp lệ."""
    set_cosa_auth_client(_client_returning([{"company_id": "other_company", "name": "Other", "role_id": "user"}]))

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(
            authorization=f"Bearer {_token()}", x_company_id="company_i_dont_belong_to", x_workspace_id="ws1"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "tenant_scope_mismatch"


@pytest.mark.asyncio
async def test_company_in_membership_list_succeeds():
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))
    set_company_tenant_context_client(_workspace_client_returning("ws1"))

    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws1"
    )
    assert identity.principal_id == "user:99"
    assert identity.company_id == "c1"
    assert identity.workspace_id == "ws1"
    assert identity.role_id == "founder"


@pytest.mark.asyncio
async def test_control_plane_unavailable_fails_closed_502():
    """Không xác nhận được membership KHÔNG được coi là ALLOW ngầm — fail
    closed, không âm thầm chấp nhận company_id client tự khai."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    set_cosa_auth_client(CosaControlPlaneAuthClient(base_url="http://test", transport=httpx.MockTransport(handler)))

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token()}", x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_workspace_id_mismatch_403_tenant_scope_mismatch():
    """Server-resolved workspaceId khác với X-Workspace-Id client gửi lên ->
    403, cùng nguyên tắc với company_id check."""
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))
    set_company_tenant_context_client(_workspace_client_returning("ws_authoritative"))

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(
            authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws_client_claimed"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "tenant_scope_mismatch"


@pytest.mark.asyncio
async def test_workspace_id_match_succeeds_and_uses_server_resolved_value():
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))
    set_company_tenant_context_client(_workspace_client_returning("ws_authoritative"))

    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws_authoritative"
    )
    assert identity.workspace_id == "ws_authoritative"


@pytest.mark.asyncio
async def test_workspace_verification_unavailable_fails_closed_502():
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    set_company_tenant_context_client(
        CompanyTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))
    )

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 502
