from unittest.mock import MagicMock
import pytest

from app.db.models import Brain, WorkspaceMember
from app.core.snowflake import generate_snowflake_id
from app.business.marketing.models import MarketingContext
from app.business.marketing.models_validation import (
    Assumption,
    AssumptionCategory,
    AssumptionStatus,
    ConfidenceLevel,
)
from app.business.marketing.schemas.validation_schemas import (
    AIExtractAssumptionsRequest,
)
from app.business.marketing.services.ai_assumption_extractor import AIAssumptionExtractor
from app.business.marketing.services.canvas_evaluator_service import CanvasEvaluatorService
from app.business.marketing.routers.validation_router import (
    extract_assumptions_ai,
    get_canvases_status,
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
# 1. AI Extraction from Text (§18 in E3.md)
# ===================================================================

def test_extract_assumptions_from_founder_text():
    text = (
        "Tôi nghĩ chủ homestay cần AI marketing tự động để tiết kiệm thời gian. "
        "Họ sẵn sàng trả phí 500k mỗi tháng nếu giúp tăng 20% đặt phòng. "
        "Landing page hiện tại đã nhận được 50 lượt đăng ký."
    )
    result = AIAssumptionExtractor.extract_from_text(text)

    assert result["total_extracted"] >= 2
    # Check that pricing/customer claims have high criticality
    pricing_asm = next((a for a in result["assumptions"] if a["category"] == "pricing"), None)
    assert pricing_asm is not None
    assert pricing_asm["impact"] == 5
    assert pricing_asm["criticality"] == 25  # 5 * 5


# ===================================================================
# 2. AI Extraction from Structured Canvas (§9, §10, §19, §20)
# ===================================================================

def test_extract_assumptions_from_customer_research_canvas():
    canvas_data = {
        "icp": {"segment": "Founder doanh nghiệp nhỏ tự làm marketing"},
        "jobs": ["Tự động hóa đăng bài mạng xã hội", "Quản lý dữ liệu tập trung"],
        "pains": ["Dùng quá nhiều AI tools rời rạc", "Không đo lường được hiệu quả"],
    }
    extracted = AIAssumptionExtractor.extract_from_canvas("customer_research", canvas_data)

    assert len(extracted) >= 3
    # First item must be high criticality
    assert extracted[0]["criticality"] >= 20
    assert any(a["category"] == "customer" for a in extracted)
    assert any(a["category"] == "problem" for a in extracted)


def test_extract_assumptions_from_offer_canvas():
    canvas_data = {
        "pricing": {"model": "SaaS Subscription 99$/month"},
        "core_offer": "Dùng thử 14 ngày không rủi ro và hoàn tiền 100%",
    }
    extracted = AIAssumptionExtractor.extract_from_canvas("offer_architecture", canvas_data)

    assert len(extracted) == 2
    assert extracted[0]["category"] == "pricing"
    assert extracted[0]["criticality"] == 25


# ===================================================================
# 3. Canvas Status Evaluator (§47: draft, hypothesis, testing, etc.)
# ===================================================================

def test_canvas_status_empty_is_draft(scope):
    ws_id, brain, _ = scope
    db = FakeDb({Brain: [brain], MarketingContext: [], Assumption: []})

    eval_result = CanvasEvaluatorService.evaluate_project_canvases(db=db, workspace_id=ws_id, brain_id=brain.id)
    canvases = eval_result["canvases"]

    assert canvases["customer_research"]["status"] == "draft"
    assert canvases["product_marketing"]["status"] == "draft"


def test_canvas_status_with_untested_assumptions_is_hypothesis(scope):
    ws_id, brain, _ = scope
    ctx = MarketingContext(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        customer_research={"icp": "SME Founder"},
    )
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        canvas_id="customer_research",
        category="customer",
        statement="SME Founder needs AI",
        status=AssumptionStatus.UNTESTED.value,
    )
    db = FakeDb({Brain: [brain], MarketingContext: [ctx], Assumption: [asm]})

    eval_result = CanvasEvaluatorService.evaluate_project_canvases(db=db, workspace_id=ws_id, brain_id=brain.id)
    cr_status = eval_result["canvases"]["customer_research"]

    assert cr_status["status"] == "hypothesis"
    assert cr_status["untested_count"] == 1


def test_canvas_status_with_contradiction_is_contradicted(scope):
    ws_id, brain, _ = scope
    ctx = MarketingContext(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        customer_research={"icp": "SME Founder"},
    )
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        canvas_id="customer_research",
        category="customer",
        statement="SME Founder cares about privacy",
        status=AssumptionStatus.CONTRADICTED.value,
    )
    db = FakeDb({Brain: [brain], MarketingContext: [ctx], Assumption: [asm]})

    eval_result = CanvasEvaluatorService.evaluate_project_canvases(db=db, workspace_id=ws_id, brain_id=brain.id)
    cr_status = eval_result["canvases"]["customer_research"]

    assert cr_status["status"] == "contradicted"
    assert cr_status["contradicted_count"] == 1


# ===================================================================
# 4. API Endpoints Integration
# ===================================================================

def test_extract_assumptions_ai_endpoint_with_save(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    payload = AIExtractAssumptionsRequest(
        text="Khách hàng doanh nghiệp vừa và nhỏ cần giải pháp tự động hóa Zalo marketing.",
        save_to_db=True,
    )
    res = extract_assumptions_ai(payload=payload, brain_id=brain.id, member=member, db=db)

    assert res["total_extracted"] >= 1
    assert res["saved_count"] >= 1
    assert len(db.added) >= 1


def test_get_canvases_status_endpoint(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain], MarketingContext: [], Assumption: []})

    status_res = get_canvases_status(brain_id=brain.id, member=member, db=db)
    assert "customer_research" in status_res["canvases"]
    assert "product_marketing" in status_res["canvases"]
    assert "offer_architecture" in status_res["canvases"]
    assert "brand_context" in status_res["canvases"]
