"""Postgres regression for the supported Strategy -> Tasks -> Chat vertical slice."""

import os
from datetime import datetime

import pytest

from app.db.models import Brain, ChatMessage, ChatSession, Task, User, Workspace, WorkspaceMember
from app.db.session import SessionLocal
from app.modules.strategy.models import StrategyCanvas, StrategyRevision, TwelveWeekCycle, WeeklyPlan


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_core_product_flow_stays_in_one_snowflake_workspace():
    db = SessionLocal()
    try:
        user = User(phone="0999999999", password_hash="test", display_name="Flow")
        workspace = Workspace(name="Flow workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        brain = Brain(workspace_id=workspace.id, name="Flow brain")
        db.add_all([member, brain])
        db.flush()
        canvas = StrategyCanvas(workspace_id=workspace.id, brain_id=brain.id, name="Strategy", created_by=user.id)
        db.add(canvas)
        db.flush()
        revision = StrategyRevision(canvas_id=canvas.id, revision_no=1, created_by=user.id)
        cycle = TwelveWeekCycle(workspace_id=workspace.id, brain_id=brain.id, theme="Execution", start_date=datetime.utcnow())
        db.add_all([revision, cycle])
        db.flush()
        plan = WeeklyPlan(workspace_id=workspace.id, cycle_id=cycle.id, week_no=1, focus="Ship")
        task = Task(workspace_id=workspace.id, title="Ship core flow", assignee_id=user.id)
        session = ChatSession(brain_id=brain.id, title="Core flow")
        db.add_all([plan, task, session])
        db.flush()
        message = ChatMessage(session_id=session.id, role="user", content="Give task context", client_message_id=str(task.id))
        db.add(message)
        db.flush()

        ids = [user.id, workspace.id, brain.id, canvas.id, revision.id, cycle.id, plan.id, task.id, session.id, message.id]
        assert all(isinstance(value, int) and 0 < value < 2**63 for value in ids)
        assert {canvas.workspace_id, cycle.workspace_id, plan.workspace_id, task.workspace_id} == {workspace.id}
        assert session.brain_id == brain.id
        assert message.session_id == session.id
    finally:
        db.rollback()
        db.close()
