from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember
from app.core.snowflake import generate_snowflake_id
from app.modules.organization.models import Organization, Department, WorkforceMember
from app.modules.organization.router import (
    get_organization_overview,
    get_org_chart_endpoint,
    hire_ai_endpoint,
    get_command_center_endpoint,
    get_daily_briefing_endpoint,
    HireAIEmployeeRequest,
)


def test_organization_bootstrap_and_departments():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    org_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    # Mock org query
    mock_org = MagicMock(spec=Organization)
    mock_org.id = org_id
    mock_org.workspace_id = ws_id
    mock_org.name = "COSA Global"
    
    # Mock existing departments query to return 6 depts
    mock_depts = [
        MagicMock(id=generate_snowflake_id(), capability_domain="ceo_office", name="Văn phòng Điều hành"),
        MagicMock(id=generate_snowflake_id(), capability_domain="product_tech", name="Kỹ thuật & Sản phẩm"),
        MagicMock(id=generate_snowflake_id(), capability_domain="marketing", name="Tiếp thị & Tăng trưởng"),
        MagicMock(id=generate_snowflake_id(), capability_domain="operations", name="Vận hành & Tác nghiệp"),
        MagicMock(id=generate_snowflake_id(), capability_domain="finance", name="Tài chính & Kế toán"),
        MagicMock(id=generate_snowflake_id(), capability_domain="legal", name="Pháp chế & Tuân thủ"),
    ]
    
    db.query.return_value.filter.return_value.first.return_value = mock_org
    db.query.return_value.filter.return_value.all.return_value = mock_depts
    
    res = get_organization_overview(workspace_id=ws_id, member=member, db=db)
    assert res["name"] == "COSA Global"
    assert res["departments_count"] == 6


def test_hire_ai_employee_flow():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    dept_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    data = HireAIEmployeeRequest(
        name="Alex - AI Growth Lead",
        role_title="Trưởng nhóm Tăng trưởng Tự động",
        department_id=dept_id,
        tools=["chat", "analytics", "campaign_generator"]
    )
    
    res = hire_ai_endpoint(workspace_id=ws_id, data=data, member=member, db=db)
    assert res["name"] == "Alex - AI Growth Lead"
    assert res["role_title"] == "Trưởng nhóm Tăng trưởng Tự động"
    assert res["status"] == "active"
    assert db.add.called
    assert db.commit.called


def test_ceo_command_center_and_daily_briefing():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 5
    
    cc = get_command_center_endpoint(workspace_id=ws_id, member=member, db=db)
    assert "workforce_metrics" in cc
    assert "governance_metrics" in cc
    # health_status is now a real derived signal (pending-approvals backlog
    # size), not a hardcoded constant - with no brains configured on this
    # mock db, pending_approvals_count resolves to 0, so it's "OPTIMAL".
    assert cc["health_status"] == "OPTIMAL"
    
    briefing = get_daily_briefing_endpoint(workspace_id=ws_id, member=member, db=db)
    assert "Bản tin Điều hành" in briefing["title"]
    assert len(briefing["key_highlights"]) > 0


def test_hire_ai_rejects_department_from_another_org():
    """A department_id must actually belong to this workspace's organization -
    otherwise a member could link a new hire into a different workspace's
    department by guessing/reusing its UUID."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    foreign_dept_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id

    db = MagicMock()
    # No Department (or Organization) row matches this filter chain - both
    # the org lookup (falls back to "create new") and the department
    # ownership check resolve through the same unconfigured `.first()`.
    db.query.return_value.filter.return_value.first.return_value = None

    data = HireAIEmployeeRequest(
        name="Rogue Hire",
        role_title="Should not be created",
        department_id=foreign_dept_id,
    )

    with pytest.raises(HTTPException) as exc_info:
        hire_ai_endpoint(workspace_id=ws_id, data=data, member=member, db=db)

    assert exc_info.value.status_code == 404


def test_organization_cross_tenant_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a
    
    db = MagicMock()
    
    with pytest.raises(HTTPException) as exc_info:
        get_organization_overview(workspace_id=ws_id_b, member=member, db=db)
        
    assert exc_info.value.status_code == 403
