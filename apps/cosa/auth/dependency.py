from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from apps.cosa.auth.company_client import CompanyTenantContextClient, CompanyTenantContextError
from apps.cosa.auth.cosa_client import CosaControlPlaneAuthClient, CosaControlPlaneAuthError
from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_platform_token

__all__ = [
    "AuthenticatedIdentity",
    "get_authenticated_identity",
    "get_cosa_auth_client",
    "set_cosa_auth_client",
    "set_company_tenant_context_client",
]


class AuthenticatedIdentity(BaseModel):
    """Danh tính đã xác thực tại API boundary — theo
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §4.2.

    - `principal_id`: lấy từ claim `sub` của JWT đã verify (services/cosa
      `cosa.users.id`), KHÔNG lấy từ client header.
    - `platform_user_id`: raw platform user ID (claim `sub`) trước khi prefix
      với "user:" — dùng để mint delegation token ngắn hạn thay thế bearer
      token dài hạn trong durable queue.
    - `company_id`: `X-Company-Id` client gửi lên, nhưng chỉ được chấp nhận
      SAU KHI cross-check khớp với danh sách membership thật trả về từ
      `GET /platform/auth/me/companies` — client header chỉ là requested
      scope, không phải authority.
    - `workspace_id`: `X-Workspace-Id` client gửi lên, nhưng chỉ được chấp
      nhận SAU KHI cross-check khớp với workspace thật trả về từ
      `POST /identity/tenant-context/resolve` (services/company) — cùng
      nguyên tắc với `company_id`, xem `apps/cosa/auth/company_client.py`.
    """

    principal_id: str
    platform_user_id: str
    company_id: str
    workspace_id: str
    role_id: str
    bearer_token: str


_cosa_auth_client: Optional[CosaControlPlaneAuthClient] = None


def get_cosa_auth_client() -> CosaControlPlaneAuthClient:
    global _cosa_auth_client
    if _cosa_auth_client is None:
        _cosa_auth_client = CosaControlPlaneAuthClient()
    return _cosa_auth_client


def set_cosa_auth_client(client: Optional[CosaControlPlaneAuthClient]) -> None:
    """Override cho test/composition root."""
    global _cosa_auth_client
    _cosa_auth_client = client


_company_tenant_context_client: Optional[CompanyTenantContextClient] = None


def get_company_tenant_context_client() -> CompanyTenantContextClient:
    global _company_tenant_context_client
    if _company_tenant_context_client is None:
        _company_tenant_context_client = CompanyTenantContextClient()
    return _company_tenant_context_client


def set_company_tenant_context_client(client: Optional[CompanyTenantContextClient]) -> None:
    global _company_tenant_context_client
    _company_tenant_context_client = client


async def get_authenticated_identity(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_company_id: Optional[str] = Header(None, alias="X-Company-Id"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> AuthenticatedIdentity:
    """FastAPI dependency bắt buộc cho mọi endpoint cần identity thật.

    Flow đúng theo §4.2: Authorization → verify tại boundary → principal_id →
    X-Company-Id là requested scope → cross-check qua COSA control plane →
    403 tenant_scope_mismatch nếu không khớp membership thật. Không có
    fallback nào trả `company_1`/`ws_1`/`user:default`.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    try:
        principal_id = verify_platform_token(token)
    except InvalidPlatformTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired platform token"
        ) from exc

    if not x_company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Company-Id header is required")
    if not x_workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Workspace-Id header is required")

    client = get_cosa_auth_client()
    try:
        memberships = await client.list_my_companies(token)
    except CosaControlPlaneAuthError as exc:
        # Fail closed: không xác nhận được membership thật KHÔNG được coi là
        # ALLOW (§10.5 freshness invariant) — trả lỗi rõ ràng, không âm thầm
        # cho qua bằng company_id client tự khai.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"tenant scope verification unavailable: {exc}",
        ) from exc

    matched = next((m for m in memberships if m.company_id == x_company_id), None)
    if matched is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch")

    tenant_client = get_company_tenant_context_client()
    try:
        resolved = await tenant_client.resolve(token, x_company_id)
    except CompanyTenantContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"workspace scope verification unavailable: {exc}",
        ) from exc

    if resolved.workspace_id != x_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch")

    return AuthenticatedIdentity(
        principal_id=f"user:{principal_id}",
        platform_user_id=principal_id,
        company_id=x_company_id,
        workspace_id=resolved.workspace_id,
        role_id=matched.role_id,
        bearer_token=token,
    )
