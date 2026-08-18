import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.core.snowflake import generate_snowflake_id
from app.founder_os.validation.models import (
    CustomerContact,
    CustomerInterviewSession,
    VerbatimQuote,
    ProblemSeverityScorecard,
    CustomerRoleEnum,
    BuyingSignalLevelEnum,
    QuestionTypeEnum,
    DimensionState,
    DimensionName,
)
from app.founder_os.validation.schemas import (
    CustomerContactCreate,
    InterviewSessionCreate,
    VerbatimQuoteCreate,
    ProblemScorecardRequest,
)
from app.founder_os.validation.question_auditor_service import QuestionAuditorService
from app.founder_os.validation.customer_discovery_service import CustomerDiscoveryService
from app.founder_os.validation.problem_intelligence_service import ProblemIntelligenceService
from app.founder_os.validation.risk_service import RiskPrioritizationService


@pytest.fixture
def db_session():
    mock_db = MagicMock()
    return mock_db



@pytest.mark.asyncio
async def test_question_auditor_leading_fallback():
    leading_q = "Nếu có tính năng này bạn có thấy tốt không?"
    res = await QuestionAuditorService.audit_question(leading_q)
    assert res.is_biased_or_leading is True
    assert res.classification == QuestionTypeEnum.LEADING.value
    assert len(res.suggested_rewrites) > 0


@pytest.mark.asyncio
async def test_question_auditor_past_behavior():
    past_q = "Lần gần nhất bạn xử lý việc này là khi nào?"
    res = await QuestionAuditorService.audit_question(past_q)
    assert res.is_biased_or_leading is False


def test_customer_discovery_crud_and_quotes():
    ws_id = generate_snowflake_id()
    project_id = generate_snowflake_id()

    # 1. Test model CustomerContact
    contact_data = CustomerContactCreate(
        name="Chị Lan",
        role=CustomerRoleEnum.BUYER.value,
        segment="SME Accounting",
        company="MivaCorp",
        contact_info="lan@example.com",
    )
    mock_db = MagicMock()
    contact = CustomerDiscoveryService.create_contact(
        db=mock_db, workspace_id=ws_id, project_id=project_id, data=contact_data
    )
    assert contact.name == "Chị Lan"
    assert contact.role == "BUYER"
    assert mock_db.add.called
    assert mock_db.commit.called

    # 2. Test model CustomerInterviewSession
    session_data = InterviewSessionCreate(
        contact_id=contact.id,
        role=CustomerRoleEnum.BUYER.value,
        segment="SME Accounting",
        raw_notes="Khách hàng mất 2 ngày tổng hợp báo cáo Excel.",
        transcript="Tôi mất gần 2 ngày cuối tháng để làm báo cáo Excel.",
    )
    session = CustomerDiscoveryService.create_interview_session(
        db=mock_db, workspace_id=ws_id, project_id=project_id, data=session_data
    )
    assert session.role == "BUYER"
    assert session.transcript == "Tôi mất gần 2 ngày cuối tháng để làm báo cáo Excel."

    # 3. Test Verbatim Quote (Immutable)
    quote_data = VerbatimQuoteCreate(
        raw_quote="Tôi mất gần 2 ngày cuối tháng để làm báo cáo Excel.",
        interpretation="Manual reporting overhead",
        interpretation_actor="AI",
        tags=["TIME", "COST"],
        buying_signal_level=BuyingSignalLevelEnum.LEVEL_2_PAIN.value,
    )
    quote = CustomerDiscoveryService.add_verbatim_quote(
        db=mock_db,
        workspace_id=ws_id,
        project_id=project_id,
        session_id=12345,
        data=quote_data,
    )
    assert quote.raw_quote == "Tôi mất gần 2 ngày cuối tháng để làm báo cáo Excel."
    assert quote.buying_signal_level == BuyingSignalLevelEnum.LEVEL_2_PAIN.value
    assert "TIME" in quote.tags_jsonb

    # 4. Test Role Coverage Evaluation
    session_user = CustomerInterviewSession(role=CustomerRoleEnum.USER.value)
    session_buyer = CustomerInterviewSession(role=CustomerRoleEnum.BUYER.value)
    session_buyer2 = CustomerInterviewSession(role=CustomerRoleEnum.BUYER.value)
    
    mock_db_coverage = MagicMock()
    mock_db_coverage.scalars.return_value.all.return_value = [session_user, session_buyer, session_buyer2]
    
    coverage = ProblemIntelligenceService.evaluate_role_coverage(
        db=mock_db_coverage, workspace_id=ws_id, project_id=project_id
    )
    assert coverage.user_count == 1
    assert coverage.buyer_count == 2
    assert coverage.decision_maker_count == 0
    assert coverage.has_decision_maker_gap is True
    assert "DECISION MAKER EVIDENCE GAP" in coverage.warning_message


def test_problem_scorecard_calculation():
    ws_id = generate_snowflake_id()
    project_id = generate_snowflake_id()

    # Case 1: Tạo mới mặc định (chưa có scorecard)
    mock_db = MagicMock()
    mock_db.scalar.return_value = None

    scorecard = ProblemIntelligenceService.get_or_calculate_scorecard(
        db=mock_db, workspace_id=ws_id, project_id=project_id
    )
    assert scorecard.total_score == 25
    assert scorecard.interpretation_result == "BELOW_RECOMMENDED_THRESHOLD"

    # Case 2: Cập nhật điểm vượt ngưỡng 40/50
    existing = ProblemSeverityScorecard(
        workspace_id=ws_id,
        project_id=project_id,
        frequency_score=5,
        severity_score=5,
        alternatives_score=5,
        wtp_score=5,
        market_potential_score=5,
        total_score=25,
    )
    mock_db_update = MagicMock()
    mock_db_update.scalar.return_value = existing

    update_req = ProblemScorecardRequest(
        frequency_score=9,
        severity_score=9,
        alternatives_score=8,
        wtp_score=9,
        market_potential_score=9,
        notes="Validated across 10 interviews",
    )
    updated = ProblemIntelligenceService.get_or_calculate_scorecard(
        db=mock_db_update, workspace_id=ws_id, project_id=project_id, override_data=update_req
    )
    assert updated.total_score == 44
    assert updated.interpretation_result == "STRONG_PROBLEM_VALIDATION"


def test_solution_bias_risk_detector():
    ws_id = generate_snowflake_id()
    project_id = generate_snowflake_id()

    mock_db = MagicMock()
    # Mock Problem dim = ASSUMPTION, Solution dim = VALIDATED
    prob_dim = DimensionState(dimension=DimensionName.PROBLEM.value, state="ASSUMPTION")
    sol_dim = DimensionState(dimension=DimensionName.SOLUTION.value, state="VALIDATED")

    mock_db.scalar.side_effect = [prob_dim, sol_dim]

    bias_res = RiskPrioritizationService.detect_solution_bias_risk(
        db=mock_db, workspace_id=ws_id, project_id=project_id
    )
    assert bias_res["solution_bias_risk"] == "HIGH"
    assert "SOLUTION BIAS RISK" in bias_res["warning_title"]
    assert len(bias_res["counter_questions"]) == 4
    assert bias_res["allow_proceed_anyway"] is True

