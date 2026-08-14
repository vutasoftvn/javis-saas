"""End-to-end regression for the Governance Realization Plan (Step 5).

Real Postgres, no mocked DB: Chief of Staff produces a real AgentApproval from real Sales
data -> approve it -> POST /automations/execute consumes it for real. If this passes, the
governance chain described in docs/architecture/COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md
actually works end-to-end, not just in isolated unit tests with mocked pieces.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.agents.governance.approval_service import ApprovalService
from app.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator
from app.agents.runtime.adapters.mock import MockRuntime
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.models import User, Workspace
from app.db.session import SessionLocal, get_db
from app.main import app
from app.modules.iam.models import WorkspaceMember
from app.modules.sales.models import SalesLead


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def db_ctx():
    db = SessionLocal()
    phone = f"090001{generate_snowflake_id() % 10000:04d}"
    try:
        user = User(phone=phone, password_hash="test", display_name="Governance E2E")
        workspace = Workspace(name="Governance E2E Workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        db.add(member)

        # Real qualified lead so ChiefOfStaffOrchestrator's data-driven action_plan actually
        # proposes a sales.followup_email action (see chief_of_staff._derive_priorities_and_actions).
        lead = SalesLead(
            workspace_id=workspace.id,
            name="Enterprise Deal E2E",
            company="E2E Corp",
            stage="QUALIFIED",
            qualification_status="QUALIFIED",
            source="website",
        )
        db.add(lead)
        db.commit()
        db.refresh(workspace)
        db.refresh(member)

        yield db, workspace, user, member
    finally:
        db.rollback()
        db.execute(text("DELETE FROM agent_events WHERE run_id IN (SELECT id FROM agent_runs WHERE workspace_id = :ws)"), {"ws": workspace.id})
        db.execute(text("DELETE FROM automation_runs WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM agent_approvals WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM agent_runs WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM sales_leads WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM workspace_members WHERE workspace_id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM workspaces WHERE id = :ws"), {"ws": workspace.id})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_chief_of_staff_to_automation_execute_full_chain(db_ctx):
    db, workspace, user, member = db_ctx

    # 1. Chief of Staff runs for real against Postgres and proposes a real, approval-gated action.
    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=workspace.id,
        user_id=user.id,
        goal="Doanh số tuần này thế nào, có cần follow-up gấp không?",
        runtime=MockRuntime(),
    )
    assert len(result.required_approvals) == 1
    approval = result.required_approvals[0]
    assert approval["tool_name"] == "sales.followup_email"
    assert approval["status"] == "pending"
    approval_id = int(approval["approval_id"])

    # 2. agent_runs/agent_events must be real, queryable rows - not only SSE events.
    run_row = db.execute(text("SELECT status FROM agent_runs WHERE id = :id"), {"id": int(result.mission_id)}).fetchone()
    assert run_row is not None
    event_count = db.execute(
        text("SELECT COUNT(*) FROM agent_events WHERE run_id = :id"), {"id": int(result.mission_id)}
    ).scalar()
    assert event_count >= 5  # mission_started, 2x delegated, 2x completed, synthesis*, mission_completed

    # 3. Approval is still pending -> executing the automation now must be rejected.
    client = TestClient(app)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    try:
        res_before_approval = client.post(
            "/api/v1/automations/execute",
            json={
                "automation_key": "sales.followup_email",
                "payload": {"note": "e2e"},
                "approval_id": approval_id,
            },
        )
        assert res_before_approval.status_code == 403

        # 4. Founder approves it for real.
        ApprovalService.approve(db, workspace_id=workspace.id, approval_id=approval_id, reviewed_by=user.id)

        # 5. Now the automation executes for real.
        res_after_approval = client.post(
            "/api/v1/automations/execute",
            json={
                "automation_key": "sales.followup_email",
                "payload": {"note": "e2e"},
                "approval_id": approval_id,
            },
        )
        assert res_after_approval.status_code == 200
        assert res_after_approval.json()["status"] in ("succeeded", "running")

        # 6. The same approval cannot be replayed for a second automation run.
        res_replay = client.post(
            "/api/v1/automations/execute",
            json={
                "automation_key": "sales.followup_email",
                "payload": {"note": "replay attempt"},
                "approval_id": approval_id,
            },
        )
        assert res_replay.status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_workspace_member, None)
