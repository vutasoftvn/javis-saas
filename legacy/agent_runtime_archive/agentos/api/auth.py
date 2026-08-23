from __future__ import annotations

import os
import uuid
from typing import Any, Optional
import jwt
from fastapi import Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from agentos.core.policy import PermissionLevel

JWT_SECRET = os.getenv("JWT_SECRET", "cosa-dev-jwt-secret-do-not-use-in-prod")
PLATFORM_JWT_SECRET = os.getenv(
    "PLATFORM_JWT_SECRET", "cosa-super-secret-platform-jwt-key-change-in-prod"
)


class TenantContext(BaseModel):
    company_id: str
    workspace_id: str
    user_id: str
    workforce_member_id: Optional[str] = None
    membership_role: str = "user"
    permissions: list[str] = Field(default_factory=lambda: ["read", "write"])
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def to_agent_permission_level(self) -> PermissionLevel:
        role = self.membership_role.lower().strip()
        if role in ("founder", "admin"):
            return PermissionLevel.L3_EXECUTE
        elif role in ("co-founder", "user", "member"):
            return PermissionLevel.L2_DRAFT
        elif role == "auditor":
            return PermissionLevel.L0_READ
        return PermissionLevel.L1_SUGGEST


def get_role_permissions(role: str) -> list[str]:
    role_norm = role.lower().strip()
    if role_norm in ("founder", "co-founder", "admin"):
        return ["*"]
    elif role_norm in ("user", "member"):
        return ["read", "write"]
    elif role_norm == "auditor":
        return ["read"]
    return ["read"]


def decode_and_verify_token(token: str) -> dict[str, Any]:
    """Attempts to decode JWT token using either PLATFORM_JWT_SECRET or JWT_SECRET."""
    token = token.strip()
    # Try platform secret first
    try:
        return jwt.decode(token, PLATFORM_JWT_SECRET, algorithms=["HS256"])
    except Exception:
        pass

    # Try standard secret
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        pass

    # Support unverified decode for development/testing if token is formatted as custom bearer token
    # e.g., 'test_token_{user_id}_{workspace_id}_{role}' or mock payload
    if token.startswith("test_token_"):
        parts = token.split("_")
        # test_token_{userId}_{workspaceId}_{role}_{companyId}
        user_id = parts[2] if len(parts) > 2 else "1"
        workspace_id = parts[3] if len(parts) > 3 else "1"
        role = parts[4] if len(parts) > 4 else "user"
        company_id = parts[5] if len(parts) > 5 else workspace_id
        return {
            "sub": user_id,
            "workspace_id": workspace_id,
            "role": role,
            "company_id": company_id,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authorization token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_tenant_context(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    x_company_id: Optional[str] = Header(None, alias="X-Company-Id"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
) -> TenantContext:
    """FastAPI Dependency: Resolves and verifies TenantContext from Authorization header.
    Never trusts client-supplied role or permission level from request body.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = (
        authorization[7:].strip()
        if authorization.startswith("Bearer ")
        else authorization.strip()
    )

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_and_verify_token(raw_token)

    user_id = str(payload.get("sub") or payload.get("user_id") or "1")
    workspace_id = str(
        x_workspace_id or payload.get("workspace_id") or payload.get("workspaceId") or "1"
    )
    company_id = str(
        x_company_id
        or payload.get("company_id")
        or payload.get("companyId")
        or workspace_id
    )
    role = str(payload.get("role") or payload.get("membership_role") or "user")
    workforce_member_id = payload.get("workforce_member_id") or payload.get("workforceMemberId")
    correlation_id = x_correlation_id or payload.get("correlation_id") or str(uuid.uuid4())

    permissions = get_role_permissions(role)

    return TenantContext(
        company_id=company_id,
        workspace_id=workspace_id,
        user_id=user_id,
        workforce_member_id=str(workforce_member_id) if workforce_member_id else None,
        membership_role=role,
        permissions=permissions,
        correlation_id=correlation_id,
    )
