from datetime import datetime, timezone
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
from app.agents.capabilities.service import CapabilityGateway
from app.agents.governance.models import AgentApproval, AgentRun, AgentToolCall


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
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def obs_setup(db: Session):
    ws = Workspace(id=generate_snowflake_id(), name="Observation Workspace")
    user = User(id=generate_snowflake_id(), email="user@cosa.ai", display_name="User", password_hash="pw")
    run = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        user_id=user.id,
        agent_key="data_analyst",
        runtime="mock",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add_all([ws, user, run])
    db.commit()
    return ws, user, run


def test_observation_tool_call_recording_with_hash_and_provenance(db: Session, obs_setup):
    """INV-09: Test recording immutable observation record with SHA256 content hash and provenance."""
    ws, user, run = obs_setup

    input_payload = {"query": "SELECT revenue FROM deals", "limit": 100}
    output_payload = {"rows": [{"revenue": 50000000}], "row_count": 1}
    provenance_info = {
        "source": "postgresql://cosa_db/deals",
        "snapshot_id": "snap_99",
        "actor": "data_analyst",
    }

    tool_call = CapabilityGateway.record_observation(
        db=db,
        run_id=run.id,
        agent_key="data_analyst",
        tool_name="sales.crm.read",
        status="success",
        capability="sales.crm.read",
        resource_type="crm_lead",
        resource_id="deals_table",
        input_data=input_payload,
        output_data=output_payload,
        latency_ms=45,
        provenance=provenance_info,
    )

    assert tool_call.id is not None
    assert tool_call.run_id == run.id
    assert tool_call.capability == "sales.crm.read"
    assert tool_call.resource_type == "crm_lead"
    assert tool_call.content_hash is not None
    assert len(tool_call.content_hash) == 64  # Valid SHA-256 hex string
    assert tool_call.provenance_jsonb == provenance_info

    # Query back from DB
    saved = db.query(AgentToolCall).filter(AgentToolCall.id == tool_call.id).first()
    assert saved is not None
    assert saved.tool_name == "sales.crm.read"
    assert saved.status == "success"
