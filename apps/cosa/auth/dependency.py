from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from apps.cosa.auth.workspace_client import WorkspaceTenantContextClient, WorkspaceTenantContextError
from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_platform_token

__all__ = [
    "AuthenticatedIdentity",
    "get_authenticated_identity",
    "set_workspace_tenant_context_client",
]


class AuthenticatedIdentity(BaseModel):
    """Danh tính đã xác thực tại API boundary — workspace-only scope.

    - `principal_id`: lấy từ claim `sub` của JWT đã verify (services/cosa
      `cosa.users.id`), KHÔNG lấy từ client header.
    - `platform_user_id`: raw platform user ID (claim `sub`) trước khi prefix
      với "user:" — dùng để mint delegation token ngắn hạn thay thế bearer
      token dài hạn trong durable queue.
    - `workspace_id`: `X-Workspace-Id` client gửi lên, nhưng chỉ được chấp
      nhận SAU KHI cross-check khớp với workspace thật trả về từ
      `POST /identity/tenant-context/resolve` (services/company) — client header
      chỉ là requested scope, không phải authority.
    """

    principal_id: str
    platform_user_id: str
    workspace_id: str
    role_id: str
    bearer_token: str


_workspace_tenant_context_client: Optional[WorkspaceTenantContextClient] = None


def get_workspace_tenant_context_client() -> WorkspaceTenantContextClient:
    global _workspace_tenant_context_client
    if _workspace_tenant_context_client is None:
        _workspace_tenant_context_client = WorkspaceTenantContextClient()
    return _workspace_tenant_context_client


def set_workspace_tenant_context_client(client: Optional[WorkspaceTenantContextClient]) -> None:
    """Override cho test/composition root."""
    global _workspace_tenant_context_client
    _workspace_tenant_context_client = client


async def get_authenticated_identity(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> AuthenticatedIdentity:
    """FastAPI dependency bắt buộc cho mọi endpoint cần identity thật.

    Flow workspace-only: Authorization → verify tại boundary → principal_id →
    X-Workspace-Id là requested scope → cross-check qua workspace endpoint
    → 403 tenant_scope_mismatch nếu không khớp membership thật.
    X-Company-Id nếu có sẽ bị bỏ qua.
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

    if not x_workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Workspace-Id header is required")

    tenant_client = get_workspace_tenant_context_client()
    try:
        resolved = await tenant_client.resolve(token, x_workspace_id)
    except WorkspaceTenantContextError as exc:
        # Fail closed: không xác nhận được workspace membership KHÔNG được coi là
        # ALLOW (§10.5 freshness invariant) — trả lỗi rõ ràng.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"workspace scope verification unavailable: {exc}",
        ) from exc

    if resolved.workspace_id != x_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch")

    return AuthenticatedIdentity(
        principal_id=f"user:{principal_id}",
        platform_user_id=principal_id,
        workspace_id=resolved.workspace_id,
        role_id=resolved.membership_role,
        bearer_token=token,
    )
