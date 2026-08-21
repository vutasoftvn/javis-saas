from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from workforce.automation.runtime.types import AutomationStartResult
from core.snowflake import generate_snowflake_id
from db.base_class import Base
from platform_core.auth.models import User, Workspace, WorkspaceMember
from workforce.agents.capabilities.connector import N8nResourceConnector, get_connector
from workforce.agents.capabilities.models import CapabilityGrant
from workforce.agents.capabilities.service import CapabilityGateway
from workforce.agents.governance.approval_service import ApprovalService
from workforce.agents.governance.models import AgentApproval, AgentRun, AgentToolCall
from founder_os.strategy.models import CapabilityDefinition as CanonicalCapabilityDefinition


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
        AgentRun.__table__,
        AgentToolCall.__table__,
        CanonicalCapabilityDefinition.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def action_center_setup(db: Session):
    ws = Workspace(id=generate_snowflake_id(), name="Action Center Test Workspace")
    user = User(id=generate_snowflake_id(), email="founder@cosa.ai", display_name="Founder", password_hash="pw")
    db.add_all([ws, user])
    db.commit()
    return ws, user


@pytest.mark.asyncio
async def test_n8n_resource_connector_simulation_and_execution(db: Session, action_center_setup):
    """Test N8nResourceConnector simulate dry-run preview and execution."""
    ws, user = action_center_setup
    connector = N8nResourceConnector()

    params = {"lead_id": "lead_123", "campaign_name": "Q3 Outreach", "channels": ["email"]}

    # 1. Simulate dry-run
    sim = await connector.simulate(
        db=db,
        workspace_id=ws.id,
        capability="automation.n8n.trigger",
        resource_type="workflow",
        resource_id="sales.outbound_campaign",
        params=params,
    )
    assert sim["capability"] == "automation.n8n.trigger"
    assert sim["resource_id"] == "sales.outbound_campaign"
    assert sim["content_hash"] is not None
    assert sim["simulation_status"] == "ready_for_review"
    assert len(sim["estimated_side_effects"]) > 0

    # 2. Mock execute
    mock_start_res = AutomationStartResult(
        execution_id="12345",
        provider_execution_id="n8n_exec_999",
        status="running",
    )
    with patch.object(connector.adapter, "execute", new_callable=AsyncMock, return_value=mock_start_res):
        exec_res = await connector.execute(
            db=db,
            workspace_id=ws.id,
            capability="automation.n8n.trigger",
            resource_type="workflow",
            resource_id="sales.outbound_campaign",
            params=params,
        )
        assert exec_res["status"] == "running"
        assert exec_res["provider_execution_id"] == "n8n_exec_999"


@pytest.mark.asyncio
async def test_action_center_simulate_approval_flow_and_idempotency(db: Session, action_center_setup):
    """INV-05 & INV-06: End-to-end simulate -> propose -> approve -> idempotent execute."""
    ws, user = action_center_setup
    idempotency_key = "idemp_test_action_001"
    params = {"target_email": "prospect@acme.com", "subject": "Intro call"}

    # 1. Attempt execute without prior approval -> Returns awaiting_approval and creates AgentApproval
    first_res = await CapabilityGateway.execute_with_capability(
        db=db,
        workspace_id=ws.id,
        subject_type="agent",
        subject_id="sales_specialist",
        capability="sales.outreach.send",
        resource_type="email",
        resource_id="sales.outreach.send",
        params=params,
        idempotency_key=idempotency_key,
        user_id=user.id,
    )
    assert first_res["status"] == "awaiting_approval"
    approval_id = int(first_res["approval_id"])

    approval = ApprovalService.get_approval(db, ws.id, approval_id)
    assert approval is not None
    assert approval.status == "pending"
    assert approval.capability == "sales.outreach.send"
    assert approval.idempotency_key == idempotency_key
    assert approval.simulation_result_jsonb is not None

    # 2. Human Approves the action
    mock_start_res = AutomationStartResult(
        execution_id="9876",
        provider_execution_id="n8n_exec_outreach_1",
        status="running",
    )
    connector = get_connector("sales") or get_connector("n8n")
    with patch.object(connector.adapter, "execute", new_callable=AsyncMock, return_value=mock_start_res):
        approved_approval = ApprovalService.approve(
            db=db,
            workspace_id=ws.id,
            approval_id=approval_id,
            reviewed_by=user.id,
        )
        assert approved_approval.status == "approved"

        # 3. Post-approval execute
        second_res = await CapabilityGateway.execute_with_capability(
            db=db,
            workspace_id=ws.id,
            subject_type="agent",
            subject_id="sales_specialist",
            capability="sales.outreach.send",
            resource_type="email",
            resource_id="sales.outreach.send",
            params=params,
            idempotency_key=idempotency_key,
            approval_id=approval_id,
            user_id=user.id,
        )
        assert second_res["status"] == "running"

        # 4. INV-06: Second execution with identical idempotency_key -> Returns cached execution result
        third_res = await CapabilityGateway.execute_with_capability(
            db=db,
            workspace_id=ws.id,
            subject_type="agent",
            subject_id="sales_specialist",
            capability="sales.outreach.send",
            resource_type="email",
            resource_id="sales.outreach.send",
            params=params,
            idempotency_key=idempotency_key,
            approval_id=approval_id,
            user_id=user.id,
        )
        assert third_res.get("idempotent_hit") is True
        assert third_res["status"] == "executed"
