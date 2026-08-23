from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from agent_core.capabilities.grants import ConnectorGrant, verify_connector_grant


def test_connector_grant_verification_scenarios():
    """Kiểm thử ConnectorGrant Normalization & Verification (§19 & §43.4)."""
    now = datetime.now(timezone.utc)

    grant = ConnectorGrant(
        grant_id="grant_crm_01",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        connector_id="connector_hubspot",
        allowed_actions=("deal.read", "deal.create", "contact.*"),
        resource_scope=("region:apac", "region:emea"),
        valid_until=now + timedelta(days=7),
    )

    # 1. Hợp lệ
    res_ok = verify_connector_grant(
        grant,
        action="deal.read",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        resource="region:apac",
        current_time=now,
    )
    assert res_ok.is_allowed is True

    # 2. Sai Tenant
    res_tenant_err = verify_connector_grant(
        grant,
        action="deal.read",
        tenant_id="tenant_other",
        principal="agent:sales_specialist",
        current_time=now,
    )
    assert res_tenant_err.is_allowed is False
    assert "Tenant mismatch" in res_tenant_err.reason

    # 3. Action ngoài danh sách
    res_action_err = verify_connector_grant(
        grant,
        action="deal.delete",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        current_time=now,
    )
    assert res_action_err.is_allowed is False
    assert "Action 'deal.delete' is not in allowed actions" in res_action_err.reason

    # 4. Action khớp wildcard prefix
    res_wildcard_ok = verify_connector_grant(
        grant,
        action="contact.create",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        current_time=now,
    )
    assert res_wildcard_ok.is_allowed is True

    # 5. Resource ngoài scope
    res_scope_err = verify_connector_grant(
        grant,
        action="deal.read",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        resource="region:latam",
        current_time=now,
    )
    assert res_scope_err.is_allowed is False
    assert "outside granted scope" in res_scope_err.reason

    # 6. Đã hết hạn
    expired_time = now + timedelta(days=8)
    res_expired = verify_connector_grant(
        grant,
        action="deal.read",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        current_time=expired_time,
    )
    assert res_expired.is_allowed is False
    assert "expired" in res_expired.reason

    # 7. Đã bị thu hồi
    grant.is_revoked = True
    res_revoked = verify_connector_grant(
        grant,
        action="deal.read",
        tenant_id="tenant_acme",
        principal="agent:sales_specialist",
        current_time=now,
    )
    assert res_revoked.is_allowed is False
    assert "has been revoked" in res_revoked.reason
