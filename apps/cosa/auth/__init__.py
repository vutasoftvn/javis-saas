from __future__ import annotations

from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    clear_workspace_resolve_cache,
    get_authenticated_identity,
    require_workspace_operator,
    resolve_identity_workspace,
    set_workspace_tenant_context_client,
)
from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_platform_token
from apps.cosa.auth.workspace_client import (
    ResolvedWorkspaceTenantContext,
    WorkspaceTenantContextClient,
    WorkspaceTenantContextError,
)

__all__ = [
    "AuthenticatedIdentity",
    "InvalidPlatformTokenError",
    "ResolvedWorkspaceTenantContext",
    "WorkspaceTenantContextClient",
    "WorkspaceTenantContextError",
    "clear_workspace_resolve_cache",
    "get_authenticated_identity",
    "require_workspace_operator",
    "resolve_identity_workspace",
    "set_workspace_tenant_context_client",
    "verify_platform_token",
]
