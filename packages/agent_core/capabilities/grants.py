from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["ConnectorGrant", "GrantVerificationResult", "verify_connector_grant"]


class ConnectorGrant(BaseModel):
    """Mô hình cấp quyền Connector chính quy theo Master Guide §19 & §43.4.

    Quy định phạm vi truy cập của Principal/Agent vào external connector.
    """

    grant_id: str
    tenant_id: str
    principal: str
    connector_id: str
    allowed_actions: tuple[str, ...] = Field(
        default_factory=tuple
    )  # vd: ("read", "task.list") hoặc ("*")
    resource_scope: tuple[str, ...] = Field(
        default_factory=tuple
    )  # vd: ("company:1", "dept:finance")
    valid_until: datetime | None = None
    is_revoked: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GrantVerificationResult(BaseModel):
    is_allowed: bool
    reason: str
    grant_id: str | None = None


def verify_connector_grant(
    grant: ConnectorGrant | None,
    *,
    action: str,
    tenant_id: str,
    principal: str,
    resource: str | None = None,
    current_time: datetime | None = None,
) -> GrantVerificationResult:
    """Xác thực tính hợp lệ của ConnectorGrant theo phạm vi và thời hạn."""
    if not grant:
        return GrantVerificationResult(
            is_allowed=False,
            reason="No grant found for connector",
        )

    # 1. Kiểm tra trạng thái thu hồi (revocation)
    if grant.is_revoked:
        return GrantVerificationResult(
            is_allowed=False,
            grant_id=grant.grant_id,
            reason=f"Connector grant '{grant.grant_id}' has been revoked",
        )

    # 2. Kiểm tra Tenant và Principal scope
    if grant.tenant_id not in (tenant_id, "*"):
        return GrantVerificationResult(
            is_allowed=False,
            grant_id=grant.grant_id,
            reason=f"Tenant mismatch: required '{tenant_id}', grant is '{grant.tenant_id}'",
        )

    if grant.principal not in (principal, "*"):
        return GrantVerificationResult(
            is_allowed=False,
            grant_id=grant.grant_id,
            reason=f"Principal mismatch: required '{principal}', grant is '{grant.principal}'",
        )

    # 3. Kiểm tra Expiration
    now = current_time or datetime.now(UTC)
    if grant.valid_until and now > grant.valid_until:
        return GrantVerificationResult(
            is_allowed=False,
            grant_id=grant.grant_id,
            reason=f"Connector grant '{grant.grant_id}' expired at {grant.valid_until.isoformat()}",
        )

    # 4. Kiểm tra Allowed Actions
    if "*" not in grant.allowed_actions and action not in grant.allowed_actions:
        # Check prefix matching (vd: 'task.*')
        matched = False
        for act in grant.allowed_actions:
            if act.endswith("*") and action.startswith(act.rstrip("*")):
                matched = True
                break
        if not matched:
            return GrantVerificationResult(
                is_allowed=False,
                grant_id=grant.grant_id,
                reason=f"Action '{action}' is not in allowed actions: {grant.allowed_actions}",
            )

    # 5. Kiểm tra Resource Scope nếu có
    if (
        resource
        and grant.resource_scope
        and "*" not in grant.resource_scope
        and resource not in grant.resource_scope
    ):
        return GrantVerificationResult(
            is_allowed=False,
            grant_id=grant.grant_id,
            reason=f"Resource '{resource}' is outside granted scope: {grant.resource_scope}",
        )

    return GrantVerificationResult(
        is_allowed=True,
        grant_id=grant.grant_id,
        reason="Grant is active and valid",
    )
