from __future__ import annotations

import hashlib
import os
import time

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_platform_token
from apps.cosa.auth.workspace_client import (
    ResolvedWorkspaceTenantContext,
    WorkspaceTenantContextClient,
    WorkspaceTenantContextError,
)

__all__ = [
    "AuthenticatedIdentity",
    "clear_workspace_resolve_cache",
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


_workspace_tenant_context_client: WorkspaceTenantContextClient | None = None


def get_workspace_tenant_context_client() -> WorkspaceTenantContextClient:
    global _workspace_tenant_context_client
    if _workspace_tenant_context_client is None:
        _workspace_tenant_context_client = WorkspaceTenantContextClient()
    return _workspace_tenant_context_client


def set_workspace_tenant_context_client(client: WorkspaceTenantContextClient | None) -> None:
    """Override cho test/composition root."""
    global _workspace_tenant_context_client
    _workspace_tenant_context_client = client


# ---------------------------------------------------------------------------
# Cache lớp phòng thủ chiều sâu cho workspace cross-check (Part 2C.1).
#
# Mỗi request tới `apps/cosa` hiện gọi `POST /identity/tenant-context/resolve`
# (services/company) 1 lần để xác nhận `X-Workspace-Id` thuộc principal. Với
# traffic cao đó là 1 HTTP hop/request thừa. Cache kết quả resolve theo
# `(principal_id, workspace_id, token_fingerprint)` trong TTL ngắn (mặc định
# 60s) — đủ để cắt hop lặp lại nhưng vẫn re-verify thường xuyên nếu membership
# bị thu hồi phía services/company. Token rotate / re-login → fingerprint đổi →
# cache miss tự nhiên, không cần invalidation tường minh.
#
# Cache KHÔNG lưu cho nhánh lỗi (`WorkspaceTenantContextError`) — mất kết nối
# services/company vẫn phải fail-closed từng request (§10.5 freshness).
# ---------------------------------------------------------------------------

_RESOLVE_CACHE_TTL_SEC = float(os.environ.get("COSA_WORKSPACE_RESOLVE_CACHE_TTL_SEC", "60"))
_resolve_cache: dict[tuple[str, str, str], tuple[float, ResolvedWorkspaceTenantContext]] = {}


def _token_fingerprint(token: str) -> str:
    """SHA-256 rút gọn — không lưu token thô trong key cache."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def clear_workspace_resolve_cache() -> None:
    """Xoá toàn bộ cache resolve — dùng cho test teardown và (nếu cần) ops
    invalidation thủ công sau khi thu hồi membership hàng loạt."""
    _resolve_cache.clear()


async def _resolve_workspace_context(
    token: str, principal_id: str, workspace_id: str
) -> ResolvedWorkspaceTenantContext:
    """Resolve workspace context với cache TTL. Cache hit → không gọi HTTP."""
    key = (principal_id, workspace_id, _token_fingerprint(token))
    now = time.monotonic()

    cached = _resolve_cache.get(key)
    if cached is not None:
        cached_at, value = cached
        if (now - cached_at) < _RESOLVE_CACHE_TTL_SEC:
            return value
        _resolve_cache.pop(key, None)

    tenant_client = get_workspace_tenant_context_client()
    resolved = await tenant_client.resolve(token, workspace_id)
    if _RESOLVE_CACHE_TTL_SEC > 0:
        _resolve_cache[key] = (now, resolved)
    return resolved


async def get_authenticated_identity(
    authorization: str | None = Header(None, alias="Authorization"),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-Id"),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="X-Workspace-Id header is required"
        )

    try:
        resolved = await _resolve_workspace_context(token, principal_id, x_workspace_id)
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
