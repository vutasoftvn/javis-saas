"""Postgres regression for the /automations/execute approval gate (Governance Realization Plan Step 2).

Requires a real migrated Postgres, same convention as test_vault_graph.py.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.agents.governance.approval_service import ApprovalService
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.models import User, Workspace
from app.db.session import SessionLocal, get_db
from app.main import app
from app.modules.iam.models import WorkspaceMember


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def db_ctx():
    db = SessionLocal()
    # The endpoint under test calls db.commit() itself, so a plain rollback() in teardown
    # cannot undo anything -- clean up explicitly instead (endpoints under test may commit
    # mid-request, same reason test_vault_graph.py's read-only-service assumption doesn't hold
    # here).
    phone = f"090000{generate_snowflake_id() % 10000:04d}"
    try:
        user = User(phone=phone, password_hash="test", display_name="Approval Gate Test")
        workspace = Workspace(name="Approval Gate Workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        db.add(member)
        db.commit()
        db.refresh(workspace)
        db.refresh(member)

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_workspace_member] = lambda: member

        yield db, workspace, member
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_workspace_member, None)
        db.rollback()
        db.execute(text("DELETE FROM automation_runs WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM agent_approvals WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM workspace_members WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM workspaces WHERE id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})
        db.commit()
        db.close()


def test_execute_no_approval_needed_succeeds(db_ctx):
    db, workspace, member = db_ctx
    client = TestClient(app)

    res = client.post(
        "/api/v1/automations/execute",
        json={"automation_key": "system.telegram_notification", "payload": {"text": "hi"}},
    )
    assert res.status_code == 200
    assert res.json()["status"] in ("succeeded", "running")


def test_execute_unknown_automation_key_404(db_ctx):
    client = TestClient(app)
    res = client.post(
        "/api/v1/automations/execute",
        json={"automation_key": "does.not_exist", "payload": {}},
    )
    assert res.status_code == 404


def test_execute_requires_approval_missing_id_403(db_ctx):
    client = TestClient(app)
    res = client.post(
        "/api/v1/automations/execute",
        json={"automation_key": "sales.followup_email", "payload": {"lead_id": 1}},
    )
    assert res.status_code == 403


def test_execute_with_unapproved_approval_403(db_ctx):
    db, workspace, member = db_ctx
    approval = ApprovalService.create_approval(
        db,
        workspace_id=workspace.id,
        agent_key="chief_of_staff",
        action_type="automation_dispatch",
        tool_name="sales.followup_email",
        risk_level="medium",
    )
    client = TestClient(app)
    res = client.post(
        "/api/v1/automations/execute",
        json={
            "automation_key": "sales.followup_email",
            "payload": {"lead_id": 1},
            "approval_id": approval.id,
        },
    )
    assert res.status_code == 403


def test_execute_with_approved_approval_succeeds_then_rejects_reuse(db_ctx):
    db, workspace, member = db_ctx
    approval = ApprovalService.create_approval(
        db,
        workspace_id=workspace.id,
        agent_key="chief_of_staff",
        action_type="automation_dispatch",
        tool_name="sales.followup_email",
        risk_level="medium",
    )
    ApprovalService.approve(db, workspace_id=workspace.id, approval_id=approval.id, reviewed_by=member.user_id)

    client = TestClient(app)
    res1 = client.post(
        "/api/v1/automations/execute",
        json={
            "automation_key": "sales.followup_email",
            "payload": {"lead_id": 1},
            "approval_id": approval.id,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["status"] in ("succeeded", "running")

    # Reusing the same approval_id for a second execute must be rejected.
    res2 = client.post(
        "/api/v1/automations/execute",
        json={
            "automation_key": "sales.followup_email",
            "payload": {"lead_id": 2},
            "approval_id": approval.id,
        },
    )
    assert res2.status_code == 403


def test_execute_with_approval_for_different_automation_key_403(db_ctx):
    db, workspace, member = db_ctx
    approval = ApprovalService.create_approval(
        db,
        workspace_id=workspace.id,
        agent_key="chief_of_staff",
        action_type="automation_dispatch",
        tool_name="marketing.publish_social",  # different automation than the one we try to run
        risk_level="medium",
    )
    ApprovalService.approve(db, workspace_id=workspace.id, approval_id=approval.id, reviewed_by=member.user_id)

    client = TestClient(app)
    res = client.post(
        "/api/v1/automations/execute",
        json={
            "automation_key": "sales.followup_email",
            "payload": {"lead_id": 1},
            "approval_id": approval.id,
        },
    )
    assert res.status_code == 403
