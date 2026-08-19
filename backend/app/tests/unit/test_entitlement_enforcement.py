"""Unit tests for Cryptographic Entitlements, Offline Grace, and Quota Enforcement (Phase 3)."""
from datetime import datetime, timedelta
import uuid
import pytest
from fastapi import HTTPException

from app.platform.sync.entitlement_crypto import EntitlementSigner, EntitlementVerifier
from app.platform.sync.entitlement_manager import EntitlementManager, EntitlementStatusMode
from app.platform.sync.entitlement_guard import check_quota_or_raise
from app.platform.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)


def test_entitlement_signing_and_verification_integrity():
    """Verify that genuine signatures pass and tampered payloads are detected."""
    company_id = uuid.uuid4()
    limits = EntitlementLimits(max_projects=10, max_seats=5, max_scheduled_agents=3)
    features = EntitlementFeatures(marketing=True, crm=True, finance=True, custom_domain=True)

    # 1. Sign snapshot
    snapshot = EntitlementSigner.sign_snapshot(
        company_id=company_id,
        plan="pro",
        limits=limits,
        features=features,
        validity_days=30,
        grace_period_days=7,
    )

    # 2. Verify genuine signature
    assert EntitlementVerifier.verify_signature(snapshot) is True

    # 3. Tamper test: Modifying plan to 'enterprise' without resigning
    tampered_plan = snapshot.model_copy(update={"plan": "enterprise"})
    assert EntitlementVerifier.verify_signature(tampered_plan) is False

    # 4. Tamper test: Altering limits
    tampered_limits = snapshot.model_copy(
        update={"limits": EntitlementLimits(max_projects=999, max_seats=999)}
    )
    assert EntitlementVerifier.verify_signature(tampered_limits) is False

    # 5. Tamper test: Altering company_id
    tampered_company = snapshot.model_copy(update={"company_id": uuid.uuid4()})
    assert EntitlementVerifier.verify_signature(tampered_company) is False


def test_entitlement_manager_caching_and_modes():
    """Verify license lifecycle status modes: ACTIVE -> GRACE_PERIOD -> RESTRICTED."""
    company_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # 1. Default fallback for unlicensed company is Free
    free_snapshot = EntitlementManager.get_snapshot(company_id)
    assert free_snapshot.plan == "free"
    assert free_snapshot.limits.max_projects == 1
    assert free_snapshot.features.custom_domain is False

    # 2. Save active Pro snapshot
    pro_snapshot = EntitlementSigner.sign_snapshot(
        company_id=company_id,
        plan="pro",
        limits=EntitlementLimits(max_projects=20, max_seats=10),
        features=EntitlementFeatures(custom_domain=True, finance=True),
        validity_days=30,
        grace_period_days=7,
        issued_at=now,
    )
    assert EntitlementManager.save_snapshot(pro_snapshot) is True
    assert EntitlementManager.get_status_mode(company_id, at_time=now) == EntitlementStatusMode.ACTIVE
    assert EntitlementManager.is_feature_allowed(company_id, "custom_domain") is True

    # 3. Time travel into Grace Period (Day 33, expired 3 days ago, grace period 7 days)
    grace_time = now + timedelta(days=33)
    assert (
        EntitlementManager.get_status_mode(company_id, at_time=grace_time)
        == EntitlementStatusMode.GRACE_PERIOD
    )
    # Features still accessible in grace period
    assert EntitlementManager.is_feature_allowed(company_id, "custom_domain") is True

    # 4. Time travel past Grace Period into Restricted Mode (Day 40)
    restricted_time = now + timedelta(days=40)
    assert (
        EntitlementManager.get_status_mode(company_id, at_time=restricted_time)
        == EntitlementStatusMode.RESTRICTED
    )


def test_quota_checking_and_enforcement():
    """Verify quota limits and HTTP 402 rejection upon limit breach."""
    company_id = str(uuid.uuid4())
    snapshot = EntitlementSigner.sign_snapshot(
        company_id=company_id,
        plan="starter",
        limits=EntitlementLimits(max_projects=3, max_seats=5, max_scheduled_agents=2),
        features=EntitlementFeatures(marketing=True, crm=True),
    )
    EntitlementManager.save_snapshot(snapshot)

    # Project count: 2 < 3 -> Allowed
    allowed, msg = EntitlementManager.check_quota_allowed(company_id, "max_projects", current_count=2)
    assert allowed is True

    # Project count: 3 >= 3 -> Breached
    allowed, msg = EntitlementManager.check_quota_allowed(company_id, "max_projects", current_count=3)
    assert allowed is False
    assert "Plan limit exceeded" in msg

    # Route guard helper raises HTTP 402
    with pytest.raises(HTTPException) as exc_info:
        check_quota_or_raise(company_id, "max_projects", current_count=3)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "quota_exceeded"
