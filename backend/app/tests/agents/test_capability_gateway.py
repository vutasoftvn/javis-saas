from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base
from app.modules.iam.models import User, Workspace, WorkspaceMember
from app.agents.capabilities.models import CapabilityGrant
from app.agents.capabilities.registry import (
    RiskLevel,
    get_capability_definition,
    list_capabilities,
)
from app.agents.capabilities.service import CapabilityGateway
from app.agents.governance.models import AgentApproval, AgentToolCall
from app.agents.governance.policy_engine import PermissionLevel, PolicyAction


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        CapabilityGrant.__table__,
        AgentApproval.__table__,
        AgentToolCall.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_workspace(db: Session):
    ws = Workspace(id=generate_snowflake_id(), name="Test Capability Workspace")
    user = User(id=generate_snowflake_id(), email="founder@cosa.ai", display_name="Founder", password_hash="pw")
    db.add_all([ws, user])
    db.commit()
    return ws, user


@pytest.mark.asyncio
async def test_capability_default_deny_on_unregistered(db: Session, test_workspace):
    """INV-01 / INV-03: Default deny for unknown capability without grant."""
    ws, user = test_workspace
    result = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="rogue_agent",
        capability="unregistered.dangerous.action",
    )
    assert result.allowed is False
    assert result.action == PolicyAction.DENY.value
    assert "Default Deny" in result.reason


@pytest.mark.asyncio
async def test_capability_grant_lifecycle_and_check(db: Session, test_workspace):
    """Test granting, evaluating, and revoking capability authorizations."""
    ws, user = test_workspace

    # 1. Unknown capability without grant -> DENY
    res1 = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="custom_agent",
        capability="custom.tool.process",
    )
    assert res1.allowed is False

    # 2. Create Grant
    grant = CapabilityGateway.grant(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="custom_agent",
        capability="custom.tool.process",
        granted_by=user.id,
        notes="Authorized for custom processing",
    )
    assert grant.id is not None

    # 3. Check now succeeds
    res2 = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="custom_agent",
        capability="custom.tool.process",
        permission_profile="l3_execute",
    )
    assert res2.allowed is True
    assert res2.grant_id == str(grant.id)

    # 4. Revoke grant
    CapabilityGateway.revoke(db=db, workspace_id=ws.id, grant_id=grant.id, user_id=user.id)

    # 5. Check after revocation -> DENY
    res3 = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="custom_agent",
        capability="custom.tool.process",
    )
    assert res3.allowed is False


@pytest.mark.asyncio
async def test_capability_grant_expiry(db: Session, test_workspace):
    """Expired grant should not authorize capability execution."""
    ws, user = test_workspace
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)

    CapabilityGateway.grant(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="temp_agent",
        capability="temporary.task.execute",
        expires_at=past_time,
    )

    res = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="temp_agent",
        capability="temporary.task.execute",
    )
    assert res.allowed is False


@pytest.mark.asyncio
async def test_strong_approval_enforcement_on_l5(db: Session, test_workspace):
    """INV-10: Critical L5 capabilities cannot bypass human approval even with L3_EXECUTE."""
    ws, user = test_workspace

    res = await CapabilityGateway.check(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="finance_specialist",
        capability="finance.payment.transfer",
        permission_profile="l3_execute",
        params={"amount": 50000000, "recipient": "Vendor A"},
    )
    assert res.is_strong_approval is True
    assert res.action == PolicyAction.REQUIRE_APPROVAL.value
    assert res.allowed is False
    assert res.simulation is not None


def test_capability_catalog_and_registry():
    """Verify registry taxonomy and lookup helpers."""
    crm_read = get_capability_definition("sales.crm.read")
    assert crm_read is not None
    assert crm_read.risk_level == RiskLevel.L1_INTERNAL_READ
    assert crm_read.requires_approval is False

    sales_caps = list_capabilities(domain="sales")
    assert len(sales_caps) >= 5
