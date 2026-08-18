"""Database-backed tenant isolation matrix for the primary product domains.

These cases deliberately use two complete tenant graphs against Postgres.  Unit
tests that only inspect mocked query expressions cannot prove that a foreign
row stays unchanged when a handler takes a write path.
"""

import os

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.db.models import (
    Brain,
    ChatSession,
    FeatureFlag,
    KnowledgeObject,
    OkrCycle,
    RealtimeSession,
    Task,
    User,
    Workspace,
    WorkspaceMember,
)
from app.workforce.chat.router import list_chat_sessions
from app.integrations.realtime.router import RealtimeSessionEndRequest, end_realtime_session
from app.founder_os.strategy.okrs_router import OkrCycleUpdate, update_okr_cycle
from app.founder_os.tasks.router import TaskUpdate, get_task, update_task
from app.platform.vault.knowledge_router import get_knowledge_item


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1",
    reason="requires the isolated Postgres integration database",
)


@pytest.fixture
def tenant_graph():
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        user_a = User(id=generate_snowflake_id(), phone=f"9{generate_snowflake_id()}")
        user_b = User(id=generate_snowflake_id(), phone=f"9{generate_snowflake_id()}")
        workspace_a = Workspace(id=generate_snowflake_id(), name="Isolation A")
        workspace_b = Workspace(id=generate_snowflake_id(), name="Isolation B")
        member_a = WorkspaceMember(id=generate_snowflake_id(), workspace_id=workspace_a.id, user_id=user_a.id, role="admin")
        member_b = WorkspaceMember(id=generate_snowflake_id(), workspace_id=workspace_b.id, user_id=user_b.id, role="admin")
        brain_a = Brain(id=generate_snowflake_id(), workspace_id=workspace_a.id, name="A")
        brain_b = Brain(id=generate_snowflake_id(), workspace_id=workspace_b.id, name="B")
        task_a = Task(id=generate_snowflake_id(), workspace_id=workspace_a.id, title="A private task")
        chat_a = ChatSession(id=generate_snowflake_id(), brain_id=brain_a.id, user_id=user_a.id, title="A private chat")
        realtime_a = RealtimeSession(
            id=generate_snowflake_id(), workspace_id=workspace_a.id, user_id=user_a.id,
            device_type="web", room_name=f"isolation-{generate_snowflake_id()}", status="active",
        )
        knowledge_a = KnowledgeObject(
            id=generate_snowflake_id(), workspace_id=workspace_a.id, brain_id=brain_a.id,
            title="A private knowledge object", generated_by=user_a.id,
        )
        cycle_a = OkrCycle(
            id=generate_snowflake_id(), workspace_id=workspace_a.id, brain_id=brain_a.id, name="A private cycle",
        )
        # The OKR router is explicitly gated; seed only the functional key.
        planning_flag = FeatureFlag(
            id=generate_snowflake_id(), workspace_id=None, key="twelve_week_planning", enabled=True,
        )
        # Flush in FK order. These models deliberately do not declare ORM
        # relationships for every resource, so SQLAlchemy cannot infer it.
        session.add_all([user_a, user_b, workspace_a, workspace_b])
        session.flush()
        session.add_all([member_a, member_b, brain_a, brain_b, planning_flag])
        session.flush()
        session.add_all([task_a, chat_a, realtime_a, knowledge_a, cycle_a])
        session.commit()
        yield {
            "db": session, "member_a": member_a, "member_b": member_b,
            "workspace_a": workspace_a, "workspace_b": workspace_b, "brain_a": brain_a,
            "task_a": task_a, "chat_a": chat_a, "realtime_a": realtime_a,
            "knowledge_a": knowledge_a, "cycle_a": cycle_a,
        }
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_foreign_tenant_matrix_blocks_reads_and_writes_without_side_effects(tenant_graph):
    graph = tenant_graph
    db = graph["db"]
    member_b = graph["member_b"]
    workspace_a = graph["workspace_a"]
    workspace_b = graph["workspace_b"]

    with pytest.raises(HTTPException) as chat_error:
        list_chat_sessions(graph["brain_a"].id, workspace_b.id, member_b, db)
    assert chat_error.value.status_code == 404

    with pytest.raises(HTTPException) as task_read_error:
        get_task(graph["task_a"].id, workspace_b.id, member_b, db)
    assert task_read_error.value.status_code == 404
    with pytest.raises(HTTPException) as task_write_error:
        update_task(graph["task_a"].id, workspace_b.id, TaskUpdate(title="attacker edit"), member_b, db)
    assert task_write_error.value.status_code == 404
    assert db.get(Task, graph["task_a"].id).title == "A private task"

    with pytest.raises(HTTPException) as knowledge_error:
        get_knowledge_item(graph["brain_a"].id, graph["knowledge_a"].id, workspace_b.id, member_b, db)
    assert knowledge_error.value.status_code == 404

    with pytest.raises(HTTPException) as strategy_error:
        update_okr_cycle(graph["cycle_a"].id, workspace_b.id, OkrCycleUpdate(name="attacker edit"), member_b, db)
    assert strategy_error.value.status_code == 404
    assert db.get(OkrCycle, graph["cycle_a"].id).name == "A private cycle"

    # Defense in depth: handlers that mutate a workspace resource must reject a
    # mismatched resolved membership even if called outside FastAPI dependency
    # resolution (e.g. a future internal adapter).
    with pytest.raises(HTTPException) as realtime_error:
        end_realtime_session(
            graph["realtime_a"].id,
            workspace_a.id,
            RealtimeSessionEndRequest(summary="attacker edit"),
            member_b,
            db,
        )
    assert realtime_error.value.status_code == 403
    assert db.get(RealtimeSession, graph["realtime_a"].id).status == "active"
    assert db.get(RealtimeSession, graph["realtime_a"].id).summary is None
