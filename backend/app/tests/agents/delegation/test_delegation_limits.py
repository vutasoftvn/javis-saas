import pytest

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.platform.auth.models import User, Workspace


def _identity(db):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"depth-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Depth {workspace_id}"))
    db.flush()
    return user_id, workspace_id


def _run(db, *, user_id, workspace_id, parent_run_id=None):
    run = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
        agent_key="chief_of_staff",
        runtime="mock",
        status="running",
    )
    db.add(run)
    db.flush()
    return run


def test_resolve_run_chain_returns_root_first_and_enforces_max_depth():
    from app.workforce.agents.delegation.limits import (
        DelegationDepthError,
        assert_can_delegate,
        resolve_run_chain,
    )

    db = SessionLocal()
    try:
        user_id, workspace_id = _identity(db)
        root = _run(db, user_id=user_id, workspace_id=workspace_id)
        child = _run(
            db,
            user_id=user_id,
            workspace_id=workspace_id,
            parent_run_id=root.id,
        )

        assert [run.id for run in resolve_run_chain(db, workspace_id, child.id)] == [
            root.id,
            child.id,
        ]
        assert assert_can_delegate(db, workspace_id, root.id) == 1
        with pytest.raises(DelegationDepthError, match="maximum depth"):
            assert_can_delegate(db, workspace_id, child.id)
    finally:
        db.rollback()
        db.close()


def test_depth_fails_closed_on_cross_workspace_parent():
    from app.workforce.agents.delegation.limits import (
        DelegationDepthError,
        resolve_run_chain,
    )

    db = SessionLocal()
    try:
        user_id, workspace_a = _identity(db)
        workspace_b = generate_snowflake_id()
        db.add(Workspace(id=workspace_b, name=f"Depth {workspace_b}"))
        db.flush()
        root = _run(db, user_id=user_id, workspace_id=workspace_a)
        child = _run(
            db,
            user_id=user_id,
            workspace_id=workspace_b,
            parent_run_id=root.id,
        )

        with pytest.raises(DelegationDepthError, match="workspace"):
            resolve_run_chain(db, workspace_b, child.id)
    finally:
        db.rollback()
        db.close()


def test_depth_fails_closed_on_cycle():
    from app.workforce.agents.delegation.limits import (
        DelegationDepthError,
        resolve_run_chain,
    )

    db = SessionLocal()
    try:
        user_id, workspace_id = _identity(db)
        root = _run(db, user_id=user_id, workspace_id=workspace_id)
        child = _run(
            db,
            user_id=user_id,
            workspace_id=workspace_id,
            parent_run_id=root.id,
        )
        root.parent_run_id = child.id
        db.flush()

        with pytest.raises(DelegationDepthError, match="cycle"):
            resolve_run_chain(db, workspace_id, child.id)
    finally:
        db.rollback()
        db.close()
