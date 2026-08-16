from unittest.mock import AsyncMock, MagicMock, patch
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


@pytest.mark.asyncio
async def test_sales_action_requires_governance_approval():
    """Verify that SalesActionCapability.dispatch_outreach without approval is halted by GovernanceKernel."""
    from app.agents.domains.sales.action import SalesActionCapability

    ws_id = generate_snowflake_id()
    db = MagicMock()

    drafts = [
        {
            "recipient_name": "Lead A",
            "recipient_email": "leada@test.com",
            "subject": "Chào hàng",
            "message": "Nội dung tiếp cận",
        }
    ]

    # Calling without is_approved=True -> must be intercepted by GovernanceKernel
    res = await SalesActionCapability.dispatch_outreach(
        db=db,
        workspace_id=ws_id,
        drafts=drafts,
        channel="email",
        is_approved=False,
    )

    assert res["status"] == "approval_required"
    assert "approval_id" in res
    assert res["dispatched_count"] == 0
    assert "paused by Governance" in res["summary"]


@pytest.mark.asyncio
async def test_sales_action_default_is_approved_fails_closed_through_governance():
    """Regression test for fail-open default bug.

    Callers that omit `is_approved` entirely (relying on the default) must
    still be routed through GovernanceKernel -- the "NO EXTERNAL ACTION
    WITHOUT GOVERNANCE" invariant requires a fail-closed default, not a
    fail-open one. This must fail against code where
    `is_approved: bool = True` since that default skips governance and
    dispatches directly to the (mocked) n8n webhook.
    """
    from app.agents.domains.sales.action import SalesActionCapability

    ws_id = generate_snowflake_id()
    db = MagicMock()

    drafts = [
        {
            "recipient_name": "Lead A",
            "recipient_email": "leada@test.com",
            "subject": "Chào hàng",
            "message": "Nội dung tiếp cận",
        }
    ]

    with patch(
        "app.agents.domains.sales.action.dispatch_outbound_action",
        new_callable=AsyncMock,
    ) as mock_dispatch:
        # Intentionally omit `is_approved` to exercise the default value.
        res = await SalesActionCapability.dispatch_outreach(
            db=db,
            workspace_id=ws_id,
            drafts=drafts,
            channel="email",
        )

        # Governance must have intercepted the call -- the real outbound
        # n8n dispatch must never have been reached.
        assert mock_dispatch.called is False

    assert res["status"] == "approval_required"
    assert "approval_id" in res
    assert res["dispatched_count"] == 0
    assert "paused by Governance" in res["summary"]


def test_sales_reality_verifier_crm_lead_success():
    """Verify RealityVerifier passes when lead exists in database."""
    from app.agents.verification.reality_verifier import RealityVerifier, VerificationVerdict

    ws_id = generate_snowflake_id()
    lead_id = generate_snowflake_id()

    db = MagicMock()
    mock_lead = MagicMock(spec=SalesLead)
    mock_lead.id = lead_id
    mock_lead.workspace_id = ws_id
    mock_lead.name = "Nguyễn Văn B"
    mock_lead.company = "Công Ty Test"
    mock_lead.stage = "NEW"
    mock_lead.fit_score = 90.0
    mock_lead.qualification_status = "QUALIFIED"

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_lead
    db.execute.return_value = mock_result

    res = RealityVerifier.verify_crm_lead(
        db=db,
        workspace_id=ws_id,
        lead_id=lead_id,
        expected_company="Công Ty Test",
        expected_stage="NEW",
    )

    assert res.verdict == VerificationVerdict.VERIFIED
    assert len(res.evidence) == 1
    assert res.evidence[0].domain == "sales"
    assert res.evidence[0].resource_type == "lead"
    assert res.evidence[0].is_valid is True


def test_sales_reality_verifier_crm_lead_missing_fails():
    """Verify RealityVerifier fails when lead is not found in database."""
    from app.agents.verification.reality_verifier import RealityVerifier, VerificationVerdict

    ws_id = generate_snowflake_id()
    lead_id = generate_snowflake_id()

    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    res = RealityVerifier.verify_crm_lead(
        db=db,
        workspace_id=ws_id,
        lead_id=lead_id,
        expected_company="Công Ty Ảo",
    )

    assert res.verdict == VerificationVerdict.FAILED
    assert len(res.unresolved) > 0
    assert "does not exist in workspace" in res.unresolved[0]


def test_email_approval_and_reality_verification():
    """Verify RealityVerifier confirms email approval when status is sent."""
    from app.agents.verification.reality_verifier import RealityVerifier, VerificationVerdict

    ws_id = generate_snowflake_id()
    approval_id = generate_snowflake_id()

    db = MagicMock()
    mock_approval = MagicMock(spec=EmailApproval)
    mock_approval.id = approval_id
    mock_approval.workspace_id = ws_id
    mock_approval.to_email = "test@company.com"
    mock_approval.subject = "Thư hợp tác"
    mock_approval.status = "sent"
    mock_approval.provider = "resend"
    mock_approval.decided_at = datetime.utcnow()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_approval
    db.execute.return_value = mock_result

    res = RealityVerifier.verify_email_approval_sent(
        db=db,
        workspace_id=ws_id,
        approval_id=approval_id,
    )

    assert res.verdict == VerificationVerdict.VERIFIED
    assert len(res.evidence) == 1
    assert res.evidence[0].domain == "communication"
    assert res.evidence[0].is_valid is True


def test_end_to_end_revenue_engine_flow():
    """Verify the full End-to-End P2 flow: Prospect Scoring -> CRM Ingestion -> Reality Verification -> Outreach Queue."""
    from app.modules.sales.revenue_engine_service import execute_prospect_to_qualified_lead_pipeline

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    db = MagicMock()
    stored_leads = {}

    def mock_add(obj):
        if isinstance(obj, SalesLead):
            stored_leads[obj.id] = obj

    db.add.side_effect = mock_add

    # Mock query for generate_outreach_draft
    query = _mock_query()
    query.first.side_effect = lambda: next(iter(stored_leads.values()), None)
    db.query.return_value = query

    # Mock execute for RealityVerifier
    def mock_execute(stmt):
        mock_res = MagicMock()
        # Extract lead_id from statement if possible or return the latest added lead matching query
        mock_res.scalar_one_or_none.side_effect = lambda: list(stored_leads.values())[-1] if stored_leads else None
        return mock_res

    db.execute.side_effect = mock_execute

    raw_prospects = [
        {
            "name": "Nguyễn Giám Đốc",
            "company": "Công Ty AI Tech",
            "title": "CEO & Founder",
            "industry": "AI & SaaS",
            "email": "ceo@aitech.vn",
        },
        {
            "name": "Trần Nhân Viên",
            "company": "Cửa Hàng Tạp Hóa",
            "title": "Nhân viên bán hàng",
            "industry": "Bán lẻ",
            "email": "retail@taphoa.vn",
        },
    ]

    res = execute_prospect_to_qualified_lead_pipeline(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        raw_prospects=raw_prospects,
        generate_drafts=True,
    )

    assert res["status"] == "success"
    assert res["processed_count"] == 2
    assert res["qualified_count"] == 1
    assert res["all_verified"] is True
    assert len(res["leads"]) == 2
    assert res["leads"][0]["qualification_status"] == "QUALIFIED"
    assert res["leads"][1]["qualification_status"] == "NURTURE"


