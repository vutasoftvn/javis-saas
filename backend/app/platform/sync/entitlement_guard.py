"""FastAPI Route Guards and Entitlement Dependencies (Phase 3).

Enforces plan limits and feature availability on API routes.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 3, 4, 5)

G2 P0.4 / G3 §9.4: `require_feature` used to derive `company_id` straight from
the `X-Company-ID` header with zero JWT auth and a hardcoded fallback UUID —
any caller could claim to be any company. Confirmed unwired from any live
route (dead-but-dangerous), fixed rather than deleted since feature gating is
a real, still-needed capability. `company_id` is now always derived from a
verified `WorkspaceContext` (JWT + `WorkspaceMember` check), never a raw
header. `get_current_company_id` (the standalone header-trusting helper) is
removed outright — its job is now `WorkspaceContext.company_id`.
"""
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.workspace_context import WorkspaceContext, get_workspace_context
from app.platform.sync.entitlement_manager import EntitlementManager


def require_feature(feature_name: str) -> Callable:
    """Dependency that gates API endpoints behind plan feature flags."""
    def dependency(ctx: WorkspaceContext = Depends(get_workspace_context)) -> WorkspaceContext:
        company_id = ctx.company_id or str(ctx.workspace_id)
        allowed = EntitlementManager.is_feature_allowed(company_id, feature_name)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_entitled",
                    "feature": feature_name,
                    "message": f"Feature '{feature_name}' is not available in your current plan. Please upgrade.",
                },
            )
        return ctx
    return dependency


def check_quota_or_raise(company_id: str, quota_name: str, current_count: int) -> None:
    """Helper to check quota and raise HTTP 402 if exceeded."""
    allowed, message = EntitlementManager.check_quota_allowed(company_id, quota_name, current_count)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exceeded",
                "quota": quota_name,
                "current_count": current_count,
                "message": message,
            },
        )
