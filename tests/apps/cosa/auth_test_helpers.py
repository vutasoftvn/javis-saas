from __future__ import annotations

from fastapi import FastAPI

from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity

__all__ = ["override_authenticated_identity"]


def override_authenticated_identity(
    app: FastAPI,
    *,
    principal_id: str = "user:test_user",
    company_id: str = "test_company_1",
    workspace_id: str = "test_ws_1",
    role_id: str = "founder",
) -> AuthenticatedIdentity:
    """Override `get_authenticated_identity` (cùng cơ chế FastAPI
    `dependency_overrides` chuẩn) để test HTTP endpoint không cần JWT/COSA
    control plane thật. Trả về identity đã set để test có thể tái sử dụng
    (vd. kiểm tra tenant isolation bằng 1 identity khác)."""
    identity = AuthenticatedIdentity(
        principal_id=principal_id,
        company_id=company_id,
        workspace_id=workspace_id,
        role_id=role_id,
        bearer_token="test-bearer-token",
    )

    async def _fake_identity() -> AuthenticatedIdentity:
        return identity

    app.dependency_overrides[get_authenticated_identity] = _fake_identity
    return identity
