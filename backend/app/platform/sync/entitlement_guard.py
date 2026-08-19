"""FastAPI Route Guards and Entitlement Dependencies (Phase 3).

Enforces plan limits and feature availability on API routes.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 3, 4, 5)
"""
from typing import Callable, Optional
from fastapi import Header, HTTPException, status

from app.platform.sync.entitlement_manager import EntitlementManager, EntitlementStatusMode


def get_current_company_id(
    x_company_id: Optional[str] = Header(None, alias="X-Company-ID"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
) -> str:
    """Extracts company_id from request headers with fallback to default test company."""
    return x_company_id or x_workspace_id or "00000000-0000-0000-0000-000000000001"


def require_feature(feature_name: str) -> Callable:
    """Dependency that gates API endpoints behind plan feature flags."""
    def dependency(company_id: str = Header(None, alias="X-Company-ID")):
        resolved_company_id = company_id or "00000000-0000-0000-0000-000000000001"
        allowed = EntitlementManager.is_feature_allowed(resolved_company_id, feature_name)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_entitled",
                    "feature": feature_name,
                    "message": f"Feature '{feature_name}' is not available in your current plan. Please upgrade.",
                },
            )
        return True
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
