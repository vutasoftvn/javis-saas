"""Pydantic data contracts for COSA Hybrid Platform Sync (Phase 1).

Specifications:
- COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# ENUMS & TAXONOMY
# ============================================================================

class StartupStageEnum(str, Enum):
    """Standardized startup lifecycle stages (Taxonomy)."""
    S0_EXPLORE = "S0_EXPLORE"
    S1_PROBLEM_VALIDATION = "S1_PROBLEM_VALIDATION"
    S2_SOLUTION_VALIDATION = "S2_SOLUTION_VALIDATION"
    S3_BUSINESS_VALIDATION = "S3_BUSINESS_VALIDATION"
    S4_GO_TO_MARKET = "S4_GO_TO_MARKET"
    S5_OPERATE_GROWTH = "S5_OPERATE_GROWTH"
    S6_SCALE_GOVERN = "S6_SCALE_GOVERN"


class ProjectStatusEnum(str, Enum):
    """Project lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DataClassificationEnum(str, Enum):
    """Data classification boundary definitions."""
    PLATFORM_REQUIRED = "PLATFORM_REQUIRED"
    ANALYTICS_REQUIRED = "ANALYTICS_REQUIRED"
    PUBLIC = "PUBLIC"
    COMPANY_PRIVATE = "COMPANY_PRIVATE"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"


class PlatformEventTypeEnum(str, Enum):
    """Idempotent platform lifecycle events."""
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_STAGE_CHANGED = "project.stage_changed"
    PROJECT_ARCHIVED = "project.archived"
    PROJECT_RESTORED = "project.restored"
    PROJECT_DELETED = "project.deleted"
    PROJECT_MILESTONE_REACHED = "project.milestone_reached"
    PROJECT_FIRST_CUSTOMER = "project.first_customer"
    PROJECT_FIRST_REVENUE = "project.first_revenue"
    PROJECT_PAUSED = "project.paused"
    PROJECT_CLOSED = "project.closed"
    FORM_SUBMISSION_RECEIVED = "form.submission_received"


# ============================================================================
# COMMERCIAL & ENTITLEMENTS CONTRACTS
# ============================================================================

class EntitlementLimits(BaseModel):
    max_projects: int = Field(default=1, ge=1)
    max_seats: int = Field(default=2, ge=1)
    max_scheduled_agents: int = Field(default=1, ge=0)


class EntitlementFeatures(BaseModel):
    marketing: bool = True
    crm: bool = True
    finance: bool = False
    custom_domain: bool = False
    priority_sync: bool = False
    private_intake: bool = False


class SignedEntitlementSnapshot(BaseModel):
    """Signed Entitlement Snapshot cached at Local for offline enforcement.

    `signature_alg` distinguishes ED25519 (current, asymmetric — Central
    signs, Local only ever verifies) from HMAC_SHA256 (legacy transition
    path — see G2 P0.1 / G3 §9.1). `key_id` is only meaningful for ED25519
    snapshots and supports key rotation.
    """
    company_id: UUID
    plan: str
    limits: EntitlementLimits
    features: EntitlementFeatures
    issued_at: datetime
    valid_until: datetime
    grace_period_days: int = Field(default=7, ge=0)
    signature: str
    signature_alg: str = Field(default="HMAC_SHA256", description="ED25519 | HMAC_SHA256 (legacy)")
    key_id: Optional[str] = Field(default=None, description="Ed25519 signing key id, for rotation")

    def is_valid(self, at_time: Optional[datetime] = None) -> bool:
        check_time = at_time or datetime.utcnow()
        return check_time <= self.valid_until

    def is_within_grace_period(self, at_time: Optional[datetime] = None) -> bool:
        check_time = at_time or datetime.utcnow()
        from datetime import timedelta
        grace_end = self.valid_until + timedelta(days=self.grace_period_days)
        return self.valid_until < check_time <= grace_end


# ============================================================================
# IDENTITY & MEMBERSHIP CONTRACTS
# ============================================================================

class PlatformUserSync(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None


class CompanySync(BaseModel):
    id: UUID
    slug: str
    name: str
    industry: Optional[str] = None
    country_code: str = "VN"


class MembershipSync(BaseModel):
    company_id: UUID
    user_id: UUID
    platform_role: str = "member"


# ============================================================================
# PROJECT INTELLIGENCE & LIFECYCLE CONTRACTS
# ============================================================================

class ProjectRegistrationPayload(BaseModel):
    platform_project_id: UUID
    company_id: UUID
    local_project_snowflake: int
    name: str
    slug: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    status: ProjectStatusEnum = ProjectStatusEnum.ACTIVE
    current_stage: StartupStageEnum = StartupStageEnum.S0_EXPLORE


class ProjectStageChangePayload(BaseModel):
    platform_project_id: UUID
    company_id: UUID
    from_stage: Optional[StartupStageEnum] = None
    to_stage: StartupStageEnum
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[int] = None
    change_source: str = "local_sync"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectOutcomePayload(BaseModel):
    platform_project_id: UUID
    company_id: UUID
    first_interview_at: Optional[datetime] = None
    first_experiment_at: Optional[datetime] = None
    mvp_launched_at: Optional[datetime] = None
    first_customer_at: Optional[datetime] = None
    first_revenue_at: Optional[datetime] = None
    has_revenue: bool = False
    revenue_band: str = "0"
    team_size_band: str = "1-2"
    outcome_updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectMetricAggregatePayload(BaseModel):
    platform_project_id: UUID
    company_id: UUID
    customer_interview_count: int = 0
    experiment_count: int = 0
    validated_assumption_count: int = 0
    invalidated_assumption_count: int = 0
    lead_count: int = 0
    customer_count: int = 0
    active_campaign_count: int = 0
    mvp_release_count: int = 0


# ============================================================================
# PROGRAM, COHORT & PUBLIC INTAKE CONTRACTS
# ============================================================================

class CohortLinkPayload(BaseModel):
    platform_project_id: UUID
    cohort_id: str
    linked_at: datetime = Field(default_factory=datetime.utcnow)


class FormSubmissionPayload(BaseModel):
    submission_id: UUID
    company_id: UUID
    project_id: Optional[UUID] = None
    form_slug: str
    payload: Dict[str, Any]
    source_domain: Optional[str] = None
    ip_hash: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# STANDARD EVENT ENVELOPE (OUTBOX & INGESTION)
# ============================================================================

class PlatformEventEnvelope(BaseModel):
    """Standard idempotent event envelope for platform sync."""
    event_id: UUID
    company_id: UUID
    project_id: Optional[UUID] = None
    event_type: PlatformEventTypeEnum
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    schema_version: int = 1
    classification: DataClassificationEnum = DataClassificationEnum.PLATFORM_REQUIRED
    payload: Dict[str, Any] = Field(default_factory=dict)
