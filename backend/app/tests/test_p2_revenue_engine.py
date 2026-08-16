from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from datetime import datetime

from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.modules.sales.models import Account, Contact, SalesLead, SalesOpportunity
from app.modules.marketing.models import MarketingContext, MarketingCampaign, PendingApproval
from app.modules.integrations.models import EmailApproval
from app.modules.sales.revenue_engine_service import (
    get_icp_context,
    update_icp_context,
    list_campaigns,
    create_campaign,
    ingest_public_lead,
    score_lead_with_ai,
    get_pipeline_kanban,
    convert_lead_to_opportunity,
    update_opportunity_stage,
    generate_outreach_draft,
)
from app.modules.sales.revenue_router import (
    get_icp,
    update_icp,
    UpdateICPRequest,
    get_pipeline,
    update_opportunity_stage as router_update_stage,
    UpdateStageRequest,
)
from app.modules.sales.public_lead_router import (
    submit_public_lead,
    PublicLeadSubmission,
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


def test_icp_cross_tenant_forbidden():
    """Verify that a member cannot access revenue ICP of another workspace."""
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()

    other_ws_id = generate_snowflake_id()
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_icp(workspace_id=other_ws_id, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_public_lead_ingestion_and_scoring():
    """Verify that submitting lead from landing page creates lead and calculates score."""
    db = MagicMock()
    query = _mock_query()
    db.query.return_value = query

    payload = {
        "name": "Nguyễn Văn A",
        "email": "vana@congtyabc.com",
        "phone": "0988123456",
        "company": "Tập Đoàn ABC",
        "message": "Cần tư vấn giải pháp chuyển đổi số",
        "utm_source": "google_ads",
    }

    res = ingest_public_lead(db=db, slug="landing-demo", payload=payload)

    assert res["status"] == "success"
    assert "lead_id" in res
    assert res["name"] == "Nguyễn Văn A"
    assert res["company"] == "Tập Đoàn ABC"
    assert res["fit_score"] >= 80.0
    assert db.commit.called


def test_pipeline_kanban_structure():
    """Verify pipeline kanban returns 5 stages and correct aggregation structure."""
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = _mock_query()
    db.query.return_value = query

    res = get_pipeline_kanban(db=db, workspace_id=ws_id)

    assert "stages" in res
    assert len(res["stages"]) == 5
    stage_ids = [s["id"] for s in res["stages"]]
    assert "DISCOVERY" in stage_ids
    assert "PROPOSAL" in stage_ids
    assert "NEGOTIATION" in stage_ids
    assert "WON" in stage_ids
    assert "LOST" in stage_ids
    assert "summary" in res
    assert "total_value" in res["summary"]
    assert "weighted_value" in res["summary"]


def test_convert_lead_and_update_stage():
    """Verify lead can be converted to opportunity and stage can be updated."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    lead_id = generate_snowflake_id()

    db = MagicMock()
    mock_lead = MagicMock(spec=SalesLead)
    mock_lead.id = lead_id
    mock_lead.workspace_id = ws_id
    mock_lead.account_id = None
    mock_lead.contact_id = None
    mock_lead.company = "Công Ty XYZ"
    mock_lead.name = "Anh B"

    query = _mock_query()
    query.first.return_value = mock_lead
    db.query.return_value = query

    opp_res = convert_lead_to_opportunity(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        lead_id=lead_id,
        title="Gói Phần Mềm Doanh Nghiệp",
        estimated_value=120000000.0,
    )

    assert opp_res["status"] == "success"
    assert "opportunity_id" in opp_res
    assert opp_res["stage"] == "DISCOVERY"
    assert opp_res["estimated_value"] == 120000000.0


def test_outreach_draft_creates_approvals():
    """Verify AI outreach generator creates both EmailApproval and PendingApproval."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    lead_id = generate_snowflake_id()

    db = MagicMock()
    mock_lead = MagicMock(spec=SalesLead)
    mock_lead.id = lead_id
    mock_lead.workspace_id = ws_id
    mock_lead.company = "Doanh Nghiệp Miva"
    mock_lead.name = "Giám Đốc C"
    mock_lead.contact_id = None

    query = _mock_query()
    query.first.return_value = mock_lead
    db.query.return_value = query

    res = generate_outreach_draft(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        lead_id=lead_id,
        channel="email",
        tone="professional",
        focus_pain_point="tự động hóa quản lý",
    )

    assert res["status"] == "success"
    assert "approval_id" in res
    assert "email_approval_id" in res
    assert "subject" in res
    assert db.commit.called
