# backend/app/tests/agents/test_adk_governance_gate_node.py
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from platform_core.auth.models import User, Workspace
from workforce.agents.governance.budget import BudgetCheckResult, MissionBudget
from workforce.agents.governance.stuck_detector import StuckAnalysisResult
from workforce.agents.orchestration.adk.nodes import governance_gate_node as node_module
from workforce.agents.orchestration.adk.nodes.governance_gate_node import (
    build_governance_gate_node,
    governance_gate_fn,
)


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


def _setup_run(db):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"gg-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"GG {workspace_id}"))
    db.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(mission_run)
    db.commit()
    return mission_run


@pytest.mark.asyncio
async def test_governance_gate_fn_continues_when_within_budget(db_session, monkeypatch):
    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)
    mission_run = _setup_run(db_session)
    ctx = SimpleNamespace(
        state={"mission_id": mission_run.id, "mission_budget": MissionBudget().model_dump(), "current_step": 2},
        route=None,
    )
    with patch(
        "workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=False),
    ), patch(
        "workforce.agents.orchestration.adk.nodes.governance_gate_node.StuckDetector.analyze_run",
        return_value=StuckAnalysisResult(is_stuck=False),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": False}
    assert ctx.route == "continue"
    assert "governance_block_reason" not in ctx.state


@pytest.mark.asyncio
async def test_governance_gate_fn_blocks_when_budget_exceeded(db_session, monkeypatch):
    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)
    mission_run = _setup_run(db_session)
    ctx = SimpleNamespace(
        state={"mission_id": mission_run.id, "mission_budget": MissionBudget().model_dump(), "current_step": 20},
        route=None,
    )
    with patch(
        "workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=True, reason_code="STEP_LIMIT_EXCEEDED", message="quá số bước cho phép"),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": True, "reason_code": "STEP_LIMIT_EXCEEDED"}
    assert ctx.route == "blocked"
    assert ctx.state["governance_block_reason"] == "quá số bước cho phép"


def test_build_governance_gate_node_shape():
    node = build_governance_gate_node(name="governance_gate_pre_synthesis")
    assert node.name == "governance_gate_pre_synthesis"
