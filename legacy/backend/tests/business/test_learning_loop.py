from unittest.mock import MagicMock
import pytest

from db.models import Brain, WorkspaceMember
from core.snowflake import generate_snowflake_id
from business.marketing.models import (
    MarketingExperiment,
    MarketingLearning,
    MarketingDecision,
)
from business.marketing.models_validation import (
    Assumption,
    AssumptionStatus,
    ConfidenceLevel,
)
from business.marketing.schemas.validation_schemas import (
    AIEvaluateLearningLoopRequest,
    CreateLearningAndDecisionRequest,
)
from business.marketing.services.learning_loop_service import LearningLoopService
from business.marketing.routers.validation_router import (
    evaluate_learning_loop_ai,
    record_learning_and_decision_endpoint,
    list_decision_log_items,
)
from tests.marketing_fakes import FakeDb


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
# 1. 5 Core Questions of Learning Loop (§36 in E3.md)
# ===================================================================

def test_evaluate_learning_loop_supported_recommends_scale(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="SME Founder cần AI Marketing",
        status=AssumptionStatus.SUPPORTED.value,
        confidence=ConfidenceLevel.HIGH.value,
    )
    exp = MarketingExperiment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        hypothesis="8/10 founder xác nhận nhu cầu",
        conclusion="supported",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm], MarketingExperiment: [exp]})

    payload = AIEvaluateLearningLoopRequest(
        experiment_id=exp.id,
        assumption_id=asm.id,
        actual_outcome="8/10 founder phỏng vấn xác nhận",
    )
    res = evaluate_learning_loop_ai(payload=payload, member=member, db=db)

    assert "q1_what_happened" in res
    assert "q2_why" in res
    assert "q3_what_we_learned" in res
    assert "q4_assumption_changed" in res
    assert "q5_what_should_we_do_next" in res
    assert res["decision_recommendation"] == "scale"
    assert "scale" in res["proposed_decision"]["decision"].lower() or "mở rộng" in res["proposed_decision"]["decision"].lower()


def test_evaluate_learning_loop_contradicted_recommends_stop(scope):
    ws_id, brain, member = scope
    asm = Assumption(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        statement="Khách hàng chấp nhận giá 5 triệu",
        status=AssumptionStatus.CONTRADICTED.value,
    )
    exp = MarketingExperiment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        brain_id=brain.id,
        hypothesis="Tỷ lệ cọc 5 triệu đạt trên 5%",
        conclusion="contradicted",
    )
    db = FakeDb({Brain: [brain], Assumption: [asm], MarketingExperiment: [exp]})

    payload = AIEvaluateLearningLoopRequest(
        experiment_id=exp.id,
        assumption_id=asm.id,
        actual_outcome="0/100 khách hàng nhấn thanh toán mức 5 triệu",
    )
    res = evaluate_learning_loop_ai(payload=payload, member=member, db=db)

    assert res["decision_recommendation"] == "stop"
    assert "Dừng" in res["proposed_decision"]["decision"]


# ===================================================================
# 2. Record Learning & Decision Journal (§37, §38, §39, §53 in E3.md)
# ===================================================================

def test_record_learning_and_decision_log(scope):
    ws_id, brain, member = scope
    db = FakeDb({Brain: [brain]})

    exp_id = generate_snowflake_id()
    asm_id = generate_snowflake_id()
    ev_id = generate_snowflake_id()

    payload = CreateLearningAndDecisionRequest(
        experiment_id=exp_id,
        summary="Khách hàng ưu tiên tính tự động hóa hơn là đa kênh",
        learning="Tập trung thông điệp vào 1-click publishing thay vì all-in-one suite",
        affected_assumption_ids=[str(asm_id)],
        evidence_ids=[str(ev_id)],
        decision_recommendation="adjust",
        create_decision_log=True,
        decision_question="Có nên thay đổi nội dung trang chủ không?",
        decision_text="Cập nhật lại định vị trang chủ",
        decision_reason="Dữ liệu thử nghiệm cho thấy thông điệp 1-click tạo conversion cao hơn 3x",
        next_action="Viết lại H1 và Subheadline trong Customer Research Canvas",
        owner="Founder",
    )
    res = record_learning_and_decision_endpoint(
        payload=payload,
        brain_id=brain.id,
        member=member,
        db=db,
    )

    assert res["learning_id"] is not None
    assert res["decision_recommendation"] == "adjust"
    assert res["decision_log_id"] is not None
    assert "DEC-" in res["decision_title"]

    # Query Decision Log
    decisions = list_decision_log_items(experiment_id=exp_id, member=member, db=db)
    assert len(decisions) >= 1
    assert decisions[0].decision == "Cập nhật lại định vị trang chủ"
    assert decisions[0].based_on_assumption_ids == [str(asm_id)]
    assert decisions[0].based_on_evidence_ids == [str(ev_id)]
