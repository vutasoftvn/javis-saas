# backend/app/tests/agents/test_adk_approval_and_execution_nodes.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from founder_os.outcomes.models import Outcome, OutcomeRun
from platform_core.auth.models import User, Workspace
from workforce.agents.governance.quality_gate import QualityGateResult, QualityGateVerdict
from workforce.agents.orchestration.adk.nodes.approval_gate_node import approval_gate_fn, build_approval_gate_node
from workforce.agents.orchestration.adk.nodes.execution_node import build_execution_node, execution_finalize_fn


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _mission(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"ex-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"EX {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="planning",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()
    return workspace_id, outcome, outcome_run, mission_run


@pytest.mark.asyncio
async def test_approval_gate_fn_derives_priorities_and_creates_approval(db_session, monkeypatch):
    from workforce.agents.orchestration.adk.nodes import approval_gate_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "workspace_id": workspace_id, "mission_id": mission_run.id,
        "specialist_reports": {
            "sales": {"status": "success", "metrics": {"qualified_leads": 3, "total_leads": 10}},
            "finance": {"status": "success", "runway_months": 4},
        },
    })
    result = await approval_gate_fn(ctx)

    assert len(result["action_plan"]) == 2
    assert len(ctx.state["required_approvals"]) == 1  # chỉ action có automation_key mới tạo Approval


@pytest.mark.asyncio
async def test_execution_finalize_fn_marks_completed_when_gate_passes(db_session, monkeypatch):
    from workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "synthesis_status": "completed",
        "quality_gate_results": {"sales": QualityGateResult(verdict=QualityGateVerdict.PASS, domain="sales")},
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "completed"
    outcome = db_session.query(Outcome).filter(Outcome.id == outcome.id).one()
    outcome_run = db_session.query(OutcomeRun).filter(OutcomeRun.id == outcome_run.id).one()
    mission_run = db_session.query(AgentRun).filter(AgentRun.id == mission_run.id).one()
    assert outcome.status == "completed"
    assert outcome_run.status == "succeeded"
    assert mission_run.status == "completed"


@pytest.mark.asyncio
async def test_execution_finalize_fn_downgrades_to_failed_when_gate_fails(db_session, monkeypatch):
    from workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "synthesis_status": "completed",
        "quality_gate_results": {"sales": QualityGateResult(verdict=QualityGateVerdict.FAIL, domain="sales", issues=["no evidence"])},
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "failed"
    outcome = db_session.query(Outcome).filter(Outcome.id == outcome.id).one()
    assert outcome.status == "failed"


@pytest.mark.asyncio
async def test_execution_finalize_fn_handles_governance_block_without_synthesis(db_session, monkeypatch):
    """Đến từ route "blocked" của GovernanceGateNode (Task 13) — synthesis_status/
    quality_gate_results chưa từng được set vì synthesis không chạy."""
    from workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "governance_block_reason": "quá số bước cho phép",
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "failed"
    outcome = db_session.query(Outcome).filter(Outcome.id == outcome.id).one()
    outcome_run = db_session.query(OutcomeRun).filter(OutcomeRun.id == outcome_run.id).one()
    assert outcome.status == "failed"
    assert outcome_run.status == "failed"


def test_build_node_shapes():
    assert build_approval_gate_node().name == "approval_gate_node"
    assert build_execution_node().name == "execution_node"
