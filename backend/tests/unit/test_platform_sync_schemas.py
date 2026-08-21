"""Unit tests for COSA Hybrid Platform Sync Schemas & Models (Phase 1)."""
from datetime import datetime, timedelta
import pytest

from core.snowflake import generate_snowflake_id

from platform_core.sync.schemas import (
    StartupStageEnum,
    ProjectStatusEnum,
    DataClassificationEnum,
    PlatformEventTypeEnum,
    EntitlementLimits,
    EntitlementFeatures,
    SignedEntitlementSnapshot,
    PlatformUserSync,
    CompanySync,
    ProjectRegistrationPayload,
    ProjectStageChangePayload,
    ProjectOutcomePayload,
    PlatformEventEnvelope,
)
from platform_core.auth.models import User, Workspace
from founder_os.strategy.models import Project


def test_startup_stage_taxonomy_completeness():
    """Verify all 7 stages exist according to COSA Stage Taxonomy."""
    stages = [s.value for s in StartupStageEnum]
    assert "S0_EXPLORE" in stages
    assert "S1_PROBLEM_VALIDATION" in stages
    assert "S2_SOLUTION_VALIDATION" in stages
    assert "S3_BUSINESS_VALIDATION" in stages
    assert "S4_GO_TO_MARKET" in stages
    assert "S5_OPERATE_GROWTH" in stages
    assert "S6_SCALE_GOVERN" in stages
    assert len(stages) == 7


def test_signed_entitlement_snapshot_validity():
    """Verify offline validity and grace period calculation logic."""
    company_id = str(generate_snowflake_id())
    now = datetime.utcnow()

    # 1. Valid snapshot
    valid_snapshot = SignedEntitlementSnapshot(
        company_id=company_id,
        plan="pro",
        limits=EntitlementLimits(max_projects=10, max_seats=5, max_scheduled_agents=3),
        features=EntitlementFeatures(marketing=True, crm=True, finance=True, custom_domain=True),
        issued_at=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        grace_period_days=7,
        signature="mock_ed25519_signature",
    )
    assert valid_snapshot.is_valid(now) is True
    assert valid_snapshot.is_within_grace_period(now) is False

    # 2. In grace period (expired 2 days ago, grace period is 7 days)
    grace_snapshot = SignedEntitlementSnapshot(
        company_id=company_id,
        plan="starter",
        limits=EntitlementLimits(),
        features=EntitlementFeatures(),
        issued_at=now - timedelta(days=35),
        valid_until=now - timedelta(days=2),
        grace_period_days=7,
        signature="mock_signature",
    )
    assert grace_snapshot.is_valid(now) is False
    assert grace_snapshot.is_within_grace_period(now) is True

    # 3. Completely expired (expired 10 days ago, grace period was 7 days)
    expired_snapshot = SignedEntitlementSnapshot(
        company_id=company_id,
        plan="free",
        limits=EntitlementLimits(),
        features=EntitlementFeatures(),
        issued_at=now - timedelta(days=40),
        valid_until=now - timedelta(days=10),
        grace_period_days=7,
        signature="mock_signature",
    )
    assert expired_snapshot.is_valid(now) is False
    assert expired_snapshot.is_within_grace_period(now) is False


def test_project_stage_change_payload():
    """Verify project stage change event payload structure."""
    project_id = str(generate_snowflake_id())
    company_id = str(generate_snowflake_id())

    payload = ProjectStageChangePayload(
        platform_project_id=project_id,
        company_id=company_id,
        from_stage=StartupStageEnum.S1_PROBLEM_VALIDATION,
        to_stage=StartupStageEnum.S2_SOLUTION_VALIDATION,
        duration_seconds=86400 * 14,
        change_source="local_sync",
        metadata={"gate_passed": "GATE_PROBLEM_VALIDATED"},
    )
    assert payload.from_stage == StartupStageEnum.S1_PROBLEM_VALIDATION
    assert payload.to_stage == StartupStageEnum.S2_SOLUTION_VALIDATION
    assert payload.duration_seconds == 86400 * 14
    assert payload.metadata["gate_passed"] == "GATE_PROBLEM_VALIDATED"


def test_platform_event_envelope_serialization():
    """Verify serialization and classification of event envelope."""
    event_id = str(generate_snowflake_id())
    company_id = str(generate_snowflake_id())
    project_id = str(generate_snowflake_id())

    envelope = PlatformEventEnvelope(
        event_id=event_id,
        company_id=company_id,
        project_id=project_id,
        event_type=PlatformEventTypeEnum.PROJECT_STAGE_CHANGED,
        classification=DataClassificationEnum.PLATFORM_REQUIRED,
        payload={
            "from_stage": "S1_PROBLEM_VALIDATION",
            "to_stage": "S2_SOLUTION_VALIDATION",
        },
    )

    data = envelope.model_dump()
    assert data["event_id"] == event_id
    assert data["event_type"] == "project.stage_changed"
    assert data["classification"] == "PLATFORM_REQUIRED"
    assert data["schema_version"] == 1
    assert data["payload"]["to_stage"] == "S2_SOLUTION_VALIDATION"


def test_local_models_platform_fields():
    """Verify that Local SQLAlchemy models have platform UUID fields defined."""
    # User model has platform_user_id
    assert hasattr(User, "platform_user_id")
    # Workspace model has platform_company_id
    assert hasattr(Workspace, "platform_company_id")
    # Project model has platform_project_id, sync_status, last_synced_at
    assert hasattr(Project, "platform_project_id")
    assert hasattr(Project, "sync_status")
    assert hasattr(Project, "last_synced_at")
