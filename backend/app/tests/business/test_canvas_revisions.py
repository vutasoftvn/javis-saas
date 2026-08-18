from unittest.mock import MagicMock
import pytest

from app.db.models import Brain, WorkspaceMember
from app.core.snowflake import generate_snowflake_id
from app.business.marketing.models_validation import CanvasRevision
from app.business.marketing.schemas.validation_schemas import (
    AIProposeCanvasRevisionRequest,
    CanvasRevisionCreateProposalRequest,
)
from app.business.marketing.services.canvas_revision_service import CanvasRevisionService
from app.business.marketing.routers.validation_router import (
    propose_canvas_revision_ai,
    create_canvas_revision_proposal,
    approve_canvas_revision,
    reject_canvas_revision,
    list_canvas_revisions,
)
from app.tests.marketing_fakes import FakeDb


def mock_member(ws_id: int) -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = ws_id
    m.role = "admin"
    return m


@pytest.fixture
def scope():
    ws_id = generate_snowflake_id()
    brain = Brain(id=generate_snowflake_id(), workspace_id=ws_id)
    return ws_id, brain, mock_member(ws_id)


# ===================================================================
# 1. AI Propose Canvas Revision (§41, §42 in E3.md)
# ===================================================================

def test_propose_canvas_revision_on_contradiction(scope):
    _, _, member = scope
    current_canvas = {
        "icp": "Founder công ty từ 50-100 nhân sự",
        "pains": "Cần tự động hóa 100% không cần người duyệt",
    }
    payload = AIProposeCanvasRevisionRequest(
        canvas_type="customer_research",
        current_canvas=current_canvas,
        evidence_statement="Phỏng vấn 10 founder: 9/10 yêu cầu phải có Human Approval Gate trước khi đăng bài",
        is_contradiction=True,
    )
    res = propose_canvas_revision_ai(payload=payload, member=member)

    assert res["canvas_type"] == "customer_research"
    assert "pains" in res["changed_fields"]
    assert res["is_contradiction"] is True
    assert "mâu thuẫn" in res["reason"].lower()
    assert "Human Approval Gate" in res["new_snapshot"]["pains"]


def test_propose_canvas_revision_on_supporting_evidence(scope):
    _, _, member = scope
    current_canvas = {
        "core_offer": "Gói Starter 500k/tháng",
        "pricing": "500,000 VND / tháng",
    }
    payload = AIProposeCanvasRevisionRequest(
        canvas_type="offer",
        current_canvas=current_canvas,
        evidence_statement="Pricing Test: 8% khách hàng nhấn nút đặt cọc gói 500k",
        is_contradiction=False,
    )
    res = propose_canvas_revision_ai(payload=payload, member=member)

    assert res["canvas_type"] == "offer"
    assert "pricing" in res["changed_fields"]
    assert res["is_contradiction"] is False
    assert "Validated" in res["new_snapshot"]["pricing"]


# ===================================================================
# 2. Canvas Revision Proposal & Human Approval Workflow (§41, §103)
# ===================================================================

def test_canvas_revision_proposal_approval_flow(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    # 1. Create Revision Proposal (Status = pending_review)
    prop_payload = CanvasRevisionCreateProposalRequest(
        canvas_type="customer_research",
        changed_fields=["pains"],
        previous_snapshot={"pains": "Nỗi đau cũ"},
        new_snapshot={"pains": "Nỗi đau mới đã được xác thực"},
        reason="Dữ liệu phỏng vấn 15 khách hàng xác nhận",
        evidence_ids=["EV-12345"],
        auto_approve=False,
    )
    rev = create_canvas_revision_proposal(
        payload=prop_payload,
        brain_id=brain.id,
        member=member,
        db=db,
    )

    assert rev.status == "pending_review"
    assert rev.approved_by is None

    # 2. List Revisions
    pending_list = list_canvas_revisions(status="pending_review", member=member, db=db)
    assert len(pending_list) >= 1
    assert pending_list[0].id == rev.id

    # 3. Founder Approves Revision
    approved_rev = approve_canvas_revision(revision_id=rev.id, member=member, db=db)
    assert approved_rev.status == "approved"
    assert approved_rev.approved_by == member.user_id


def test_canvas_revision_proposal_rejection_flow(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    prop_payload = CanvasRevisionCreateProposalRequest(
        canvas_type="offer",
        changed_fields=["pricing"],
        previous_snapshot={"pricing": "1 triệu"},
        new_snapshot={"pricing": "2 triệu"},
        reason="Đề xuất tăng giá",
        evidence_ids=[],
        auto_approve=False,
    )
    rev = create_canvas_revision_proposal(
        payload=prop_payload,
        brain_id=brain.id,
        member=member,
        db=db,
    )

    rejected_rev = reject_canvas_revision(revision_id=rev.id, member=member, db=db)
    assert rejected_rev.status == "rejected"
