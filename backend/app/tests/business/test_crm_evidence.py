from unittest.mock import MagicMock
import pytest

from app.db.models import Brain, WorkspaceMember
from app.core.snowflake import generate_snowflake_id
from app.business.marketing.models_validation import (
    Assumption,
    AssumptionCategory,
    AssumptionStatus,
    ConfidenceLevel,
    CustomerInterview,
    MarketingAttribution,
    Evidence,
)
from app.business.marketing.schemas.validation_schemas import (
    CustomerInterviewCreate,
    AIExtractInterviewRequest,
    MarketingAttributionCreate,
)
from app.business.marketing.services.interview_service import InterviewService
from app.business.marketing.routers.validation_router import (
    record_customer_interview,
    list_customer_interviews,
    extract_interview_ai,
    record_marketing_attribution,
    list_marketing_attributions,
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
# 1. AI Customer Interview Extraction (§35 in E3.md)
# ===================================================================

def test_extract_interview_from_transcript():
    transcript = (
        "Founder: Chào anh, hiện tại bên mình quản lý marketing thế nào?\n"
        "Khách: Bên anh đang dùng Notion và Excel kết hợp ChatGPT nhưng mất thời gian và phân tán dữ liệu kinh khủng.\n"
        "Founder: Vấn đề lớn nhất là gì ạ?\n"
        "Khách: Khó khăn lớn nhất là không biết kênh nào hiệu quả thực sự.\n"
        "Founder: Anh có ngại dùng công cụ mới không?\n"
        "Khách: Anh hơi lo ngại về bảo mật dữ liệu khách hàng.\n"
        "Founder: Mức ngân sách anh sẵn sàng chi?\n"
        "Khách: “Nếu giải quyết triệt để, anh sẵn sàng trả phí 1 triệu mỗi tháng”.\n"
    )
    result = InterviewService.extract_interview_from_transcript(
        transcript_text=transcript,
        customer_name="Anh Nam - CEO",
        segment="Founder SME",
    )

    assert result["customer_name"] == "Anh Nam - CEO"
    assert result["segment"] == "Founder SME"
    assert len(result["pains"]) >= 1
    assert len(result["alternatives"]) >= 1
    assert len(result["objections"]) >= 1
    assert "1 triệu" in (result["willingness_to_pay"] or "")
    assert len(result["notable_quotes"]) >= 1


# ===================================================================
# 2. Record Interview & Auto-Generate Evidence (§35, §101 in E3.md)
# ===================================================================

def test_record_interview_generates_evidence_and_updates_assumption(scope):
    ws_id, brain, member = scope
    asm_problem = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        category=AssumptionCategory.PROBLEM.value,
        statement="SME Founder gặp khó khăn vì phân tán dữ liệu",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.UNTESTED.value,
        evidence_ids=[],
    )
    asm_pricing = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        category=AssumptionCategory.PRICING.value,
        statement="Khách hàng sẵn sàng trả 1 triệu/tháng",
        impact=5,
        uncertainty=5,
        criticality=25,
        status=AssumptionStatus.UNTESTED.value,
        evidence_ids=[],
    )
    db = FakeDb({Brain: [brain], Assumption: [asm_problem, asm_pricing]})

    payload = CustomerInterviewCreate(
        customer_name="Chị Linh - Quản lý Homestay",
        segment="Chủ Homestay",
        pains=["Mất thời gian quản lý bài viết trên nhiều kênh"],
        alternatives=["Tự đăng tay trên Facebook và Zalo"],
        objections=["Sợ AI đăng sai thông tin phòng"],
        willingness_to_pay="Sẵn sàng trả 500k/tháng nếu tự động 100%",
        notable_quotes=["“Mỗi ngày tôi mất 2 tiếng chỉ để copy bài đăng”"],
    )
    created_interview = record_customer_interview(payload=payload, brain_id=brain.id, member=member, db=db)

    assert created_interview.customer_name == "Chị Linh - Quản lý Homestay"
    assert len(created_interview.evidence_ids) >= 1

    # Verify that the underlying problem assumption received evidence
    assert len(asm_problem.evidence_ids) >= 1
    assert asm_problem.status in (AssumptionStatus.SUPPORTED.value, AssumptionStatus.PARTIALLY_SUPPORTED.value)


# ===================================================================
# 3. AI Extract Interview Endpoint Integration
# ===================================================================

def test_extract_interview_ai_endpoint_with_save(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        category="problem",
        statement="Khách hàng mất thời gian",
        status="untested",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm]})

    transcript = (
        "Khách: Vấn đề lớn nhất là mất thời gian tạo nội dung hàng ngày.\n"
        "Khách: “Tôi sẵn sàng trả phí nếu có công cụ tự động”."
    )
    payload = AIExtractInterviewRequest(
        transcript=transcript,
        customer_name="Bác Bình",
        save_to_db=True,
    )
    res = extract_interview_ai(payload=payload, brain_id=brain.id, member=member, db=db)

    assert res["customer_name"] == "Bác Bình"
    assert res["saved_interview_id"] is not None
    assert res["generated_evidence_count"] >= 1


# ===================================================================
# 4. Marketing Attribution (§58, §59 in E3.md: Lead -> Exp -> Asm)
# ===================================================================

def test_record_and_list_marketing_attribution(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    exp_id = generate_snowflake_id()
    camp_id = generate_snowflake_id()
    contact_id = generate_snowflake_id()

    payload = MarketingAttributionCreate(
        contact_id=contact_id,
        campaign_id=camp_id,
        experiment_id=exp_id,
        variant_id="variant_b_privacy",
        utm_source="facebook",
        utm_medium="cpc",
        utm_campaign="spring_validation_2026",
    )
    attr = record_marketing_attribution(payload=payload, member=member, db=db)

    assert attr.contact_id == contact_id
    assert attr.experiment_id == exp_id
    assert attr.utm_source == "facebook"
    assert attr.variant_id == "variant_b_privacy"

    # List attributions
    results = list_marketing_attributions(experiment_id=exp_id, member=member, db=db)
    assert len(results) >= 1
    assert results[0].variant_id == "variant_b_privacy"
