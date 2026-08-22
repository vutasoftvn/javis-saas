from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from datetime import datetime

from core.snowflake import generate_snowflake_id
from db.models import WorkspaceMember, Task, Agent
from business.marketing.models import PendingApproval
from integrations.channels.models import Outbox, EmailApproval
from platform_core.core.founder_hub_service import (
    get_founder_command_center_data,
    execute_quick_approval,
)
from platform_core.core.founder_hub_router import (
    get_command_center,
    quick_approve,
    QuickApprovalRequest,
)


def _mock_query():
    q = MagicMock()
    q.join.return_value = q
    q.outerjoin.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.scalar.return_value = 0
    q.all.return_value = []
    q.first.return_value = None
    return q


def test_command_center_cross_tenant_forbidden():
    """Verify that user from workspace A cannot access command-center of workspace B."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()
    member.user_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_command_center(workspace_id=other_ws_id, member=member, db=db)

    assert exc_info.value.status_code == 403
    assert "Access forbidden" in exc_info.value.detail


def test_quick_approve_cross_tenant_forbidden():
    """Verify that user from workspace A cannot approve tasks in workspace B."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()
    member.user_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()
    req = QuickApprovalRequest(approval_id="1234567890", decision="approve", reason="OK")

    with pytest.raises(HTTPException) as exc_info:
        quick_approve(workspace_id=other_ws_id, payload=req, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_command_center_data_structure():
    """Verify that get_founder_command_center_data returns complete CEO Command Center structure."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    db.query.return_value = query

    data = get_founder_command_center_data(db=db, workspace_id=ws_id)

    # 1. Greeting
    assert "greeting" in data
    assert "title" in data["greeting"]
    assert "summary" in data["greeting"]

    # 2. Company Pulse
    assert "company_pulse" in data
    for pillar in ("sales", "cash", "marketing", "operations", "legal"):
        assert pillar in data["company_pulse"]
        assert "trend" in data["company_pulse"][pillar]
        assert "status" in data["company_pulse"][pillar]
        assert "indicator" in data["company_pulse"][pillar]
        assert "color" in data["company_pulse"][pillar]

    # 3. Today Priorities
    assert "today_priorities" in data
    assert isinstance(data["today_priorities"], list)
    assert len(data["today_priorities"]) >= 1
    assert "title" in data["today_priorities"][0]
    assert "priority" in data["today_priorities"][0]

    # 4. Waiting For You
    assert "waiting_for_you" in data
    assert isinstance(data["waiting_for_you"], list)

    # 5. Active Missions
    assert "active_missions" in data
    assert isinstance(data["active_missions"], list)


def test_quick_approve_creates_outbox_and_audit():
    """Verify that quick_approve approves pending item and creates an Outbox message and Audit Log."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    approval_id = generate_snowflake_id()

    db = MagicMock()
    mock_pending = MagicMock(spec=PendingApproval)
    mock_pending.id = approval_id
    mock_pending.workspace_id = ws_id
    mock_pending.action_type = "publish_post"
    mock_pending.details = {"post_id": 123}
    mock_pending.status = "pending"

    query = _mock_query()
    query.first.return_value = mock_pending
    db.query.return_value = query

    with patch("platform_core.core.founder_hub_service.write_audit_log") as mock_audit:
        result = execute_quick_approval(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            approval_id=approval_id,
            decision="approve",
            reason="Approved for publishing",
        )

        assert result["status"] == "success"
        assert result["outbox_id"] is not None
        assert mock_pending.status == "approved"
        assert mock_pending.reviewed_by == user_id
        assert db.commit.called
        assert mock_audit.called
