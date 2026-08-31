from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Literal

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from apps.cosa.auth.jwt import (
    InvalidPlatformTokenError,
    mint_company_delegation,
    mint_delegation_token,
    mint_local_delegation_token,
    verify_local_session_token,
    verify_platform_token,
)
from apps.cosa.auth.workspace_client import (
    ResolvedWorkspaceTenantContext,
    WorkspaceTenantContextClient,
    WorkspaceTenantContextError,
)

__all__ = [
    "AuthenticatedIdentity",
    "clear_workspace_resolve_cache",
    "get_authenticated_identity",
    "require_workspace_operator",
    "resolve_identity_workspace",
    "set_workspace_tenant_context_client",
]

logger = logging.getLogger(__name__)


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
    # M1 §1 — token gốc là local session (services/company) hay platform (control-plane).
    # Quyết định delegation token forward xuống services/company phải cùng shape.
    token_kind: Literal["local_session", "platform"] = "platform"

    def mint_delegation(self, *, ttl_seconds: int = 600) -> str:
        """Delegation token ngắn hạn cùng shape với token gốc — để lệnh forward
        xuống services/company verify được (local session ⇒ JWT_SECRET/no-aud;
        platform ⇒ PLATFORM_JWT_SECRET/aud=cosa)."""
        if self.token_kind == "local_session":
            return mint_local_delegation_token(self.platform_user_id, ttl_seconds=ttl_seconds)
        return mint_delegation_token(self.platform_user_id, ttl_seconds=ttl_seconds)

    def mint_company_delegation(
        self, *, run_id: str, capability_ids: list[str], ttl_seconds: int = 600
    ) -> str:
        """Task 3 — delegation CÓ CẤU TRÚC (scoped) để gọi sang
        services/company thay mặt đúng workspace đã cross-check của identity
        này + đúng run_id/capability_ids caller khai báo. Khác hẳn
        mint_delegation() ở trên (chỉ re-sign lại shape token gốc để giảm rủi
        ro lộ bearer token dài hạn trong durable queue) — hàm này không mang
        theo bearer token gốc và bị verify chặt theo scope ở phía Company
        (cosa-delegation.service.ts::verifyCosaDelegation), không phải chỉ
        verify được cùng secret là đủ.

        `workspace_id` LUÔN lấy từ `self.workspace_id` (đã cross-check qua
        `POST /identity/tenant-context/resolve`) — KHÔNG nhận workspace_id
        làm tham số, để không thể mint delegation cho workspace khác với
        workspace caller đã được xác thực.
        """
        return mint_company_delegation(
            sub=self.platform_user_id,
            workspace_id=self.workspace_id,
            run_id=run_id,
            capability_ids=capability_ids,
            ttl_seconds=ttl_seconds,
        )


_WORKSPACE_OPERATOR_ROLES = frozenset({"founder", "co-founder", "admin"})


def resolve_identity_workspace(
    identity: AuthenticatedIdentity, requested_workspace_id: str | None = None
) -> str:
    """Return the authenticated workspace, rejecting a different request scope."""
    if requested_workspace_id is not None and requested_workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return identity.workspace_id


def require_workspace_operator(identity: AuthenticatedIdentity) -> AuthenticatedIdentity:
    """Require a workspace-level operator role for the authenticated identity."""
    if (identity.role_id or "").lower() not in _WORKSPACE_OPERATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="workspace operator role required"
        )
    return identity


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
# Task 6 — cache trên KHÔNG có giới hạn kích thước trước đây: 1 process chạy
# lâu dài phục vụ nhiều principal/workspace/token phân biệt sẽ làm dict này
# phình vô hạn (mỗi entry không tự dọn cho tới khi bị truy cập lại và thấy
# hết TTL). Giới hạn cứng số entry, dọn theo thứ tự: (1) entry đã hết TTL,
# rồi (2) entry cũ nhất — trước khi insert entry mới.
_RESOLVE_CACHE_MAX_ENTRIES = int(
    os.environ.get("COSA_WORKSPACE_RESOLVE_CACHE_MAX_ENTRIES", "10000")
)
_resolve_cache: dict[tuple[str, str, str], tuple[float, ResolvedWorkspaceTenantContext]] = {}


def _token_fingerprint(token: str) -> str:
    """SHA-256 rút gọn — không lưu token thô trong key cache."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def clear_workspace_resolve_cache() -> None:
    """Xoá toàn bộ cache resolve — dùng cho test teardown và (nếu cần) ops
    invalidation thủ công sau khi thu hồi membership hàng loạt."""
    _resolve_cache.clear()


def _prune_resolve_cache_before_insert(now: float) -> None:
    """Dọn cache TRƯỚC khi insert 1 entry mới — không dọn theo lịch nền
    (không có background task nào chạy trong process này để làm việc đó).

    Bước 1: bỏ mọi entry đã hết TTL — dọn rác tự nhiên, không giữ membership
    cũ vô thời hạn chỉ vì entry đó không bị truy cập lại.
    Bước 2: nếu vẫn còn đầy (>= max_entries) sau bước 1, bỏ entry CŨ NHẤT
    (theo `cached_at`) cho tới khi còn chỗ — chặn unbounded growth khi traffic
    có nhiều principal/workspace/token phân biệt trong cùng 1 TTL window.
    """
    expired_keys = [
        key
        for key, (cached_at, _) in _resolve_cache.items()
        if (now - cached_at) >= _RESOLVE_CACHE_TTL_SEC
    ]
    for key in expired_keys:
        _resolve_cache.pop(key, None)

    while len(_resolve_cache) >= _RESOLVE_CACHE_MAX_ENTRIES and _resolve_cache:
        oldest_key = min(_resolve_cache, key=lambda k: _resolve_cache[k][0])
        _resolve_cache.pop(oldest_key, None)


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
        _prune_resolve_cache_before_insert(now)
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

    # M1 §1 — AgentOS là local business runtime ⇒ ưu tiên local session token
    # (services/company). Platform token vẫn chấp nhận cho luồng platform.
    token_kind: Literal["local_session", "platform"]
    try:
        principal_id = verify_local_session_token(token)
        token_kind = "local_session"
    except InvalidPlatformTokenError:
        try:
            principal_id = verify_platform_token(token)
            token_kind = "platform"
        except InvalidPlatformTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or expired session token",
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
        # Final-review Finding 4 — exception thô (có thể mang host/port nội bộ
        # của services/company) KHÔNG được interpolate vào response body
        # client-facing. Log đầy đủ server-side, client chỉ nhận thông báo
        # ổn định.
        logger.exception("workspace scope verification unavailable")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="workspace scope verification unavailable",
        ) from exc

    if resolved.workspace_id != x_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch")

    return AuthenticatedIdentity(
        principal_id=f"user:{principal_id}",
        platform_user_id=principal_id,
        workspace_id=resolved.workspace_id,
        role_id=resolved.membership_role,
        bearer_token=token,
        token_kind=token_kind,
    )
