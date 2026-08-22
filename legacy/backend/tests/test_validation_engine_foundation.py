import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"

from db.base import Base
from platform_core.auth.models import Workspace, User, WorkspaceMember
from platform_core.vault.models import Brain
from founder_os.strategy.models import Project
from founder_os.validation.models import (
    ValidationSession,
    StructuredClaim,
    FieldRevision,
    ValidationAssumption,
    ValidationHypothesis,
    ValidationExperiment,
    ValidationEvidence,
    ValidationReview,
    ValidationDecision,
    DimensionState,
    ProjectStageHistory,
    ClaimConfirmationStatus,
    EpistemicType,
    DimensionName,
    DimensionStateEnum,
    FeasibilityPillar,
    AssumptionCategory,
    AssumptionStatus,
    ExperimentType,
    EvidenceType,
    EvidenceRelationship,
    ReviewProviderType,
    ReviewVerdict,
    FounderDecisionEnum,
)
from founder_os.validation.schemas import (
    StructuredClaimCreate,
    StructuredClaimEditRequest,
    AssumptionCreate,
    AssumptionUpdate,
    HypothesisCreate,
    ExperimentCreate,
    EvidenceCreate,
    ValidationReviewCreate,
    ValidationDecisionCreate,
)
from founder_os.validation.service import ValidationEngineService


@pytest.fixture
def db_session():
    """In-memory SQLite test session for Validation Engine."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None, "finance": None, "sales": None, "marketing": None, "legal": None, "validation": None, "strategy": None, "operating": None, "knowledge": None, "policy_funding": None, "core": None, "runtime_ops": None})
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Brain.__table__,
        Project.__table__,
        ValidationSession.__table__,
        StructuredClaim.__table__,
        FieldRevision.__table__,
        ValidationAssumption.__table__,
        ValidationHypothesis.__table__,
        ValidationExperiment.__table__,
        ValidationEvidence.__table__,
        ValidationReview.__table__,
        ValidationDecision.__table__,
        DimensionState.__table__,
        ProjectStageHistory.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Seed User, Workspace, Brain, Project
    user = User(id=1, email="founder@cosa.ai", password_hash="pw", display_name="Founder")
    ws = Workspace(id=10, name="COSA AI Workspace")
    member = WorkspaceMember(id=100, user_id=1, workspace_id=10, role="owner")
    brain = Brain(id=20, workspace_id=10, name="Main Brain")
    project = Project(
        id=30,
        workspace_id=10,
        brain_id=20,
        title="COSA Hospitality",
        description="AI operations for hotels",
        project_stage="VALIDATION",
    )

    session.add_all([user, ws, member, brain, project])
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine, tables=tables)


def test_session_lifecycle(db_session: Session):
    """Kiểm tra khởi tạo và lấy lại validation session."""
    session = ValidationEngineService.get_or_create_session(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        initial_topic=DimensionName.CUSTOMER.value,
    )
    assert session.id is not None
    assert session.project_id == 30
    assert session.current_topic == DimensionName.CUSTOMER.value
    assert session.workflow_state == "DATA_COLLECTION"

    # Lấy lại session đã có (không tạo duplicate)
    session2 = ValidationEngineService.get_or_create_session(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
    )
    assert session2.id == session.id


def test_structured_claims_confirm_and_edit_history(db_session: Session):
    """Kiểm tra tạo claim, xác nhận và sửa claim kèm lưu vết FieldRevision."""
    # 1. Tạo claim từ chat
    claim_in = StructuredClaimCreate(
        dimension=DimensionName.CUSTOMER,
        subject="hotel_size",
        predicate="room_count",
        value={"range": "30-100 rooms"},
        epistemic_type=EpistemicType.ASSUMPTION,
        source_type="FOUNDER_CHAT",
        confidence=0.8,
    )
    claim = ValidationEngineService.create_claim(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        claim_in=claim_in,
    )
    assert claim.id is not None
    assert claim.confirmation_status == ClaimConfirmationStatus.AI_INFERRED.value

    # 2. Confirm claim
    confirmed_claim = ValidationEngineService.confirm_claim(
        db=db_session,
        claim_id=claim.id,
        confidence=1.0,
    )
    assert confirmed_claim.confirmation_status == ClaimConfirmationStatus.FOUNDER_CONFIRMED.value

    # 3. Founder sửa claim (Edit) -> tạo FieldRevision
    edit_in = StructuredClaimEditRequest(
        new_value={"range": "50-120 rooms"},
        reason="Updated target after market survey",
    )
    edited_claim = ValidationEngineService.edit_claim(
        db=db_session,
        claim_id=claim.id,
        edit_in=edit_in,
        changed_by="FOUNDER",
    )
    assert edited_claim.confirmation_status == ClaimConfirmationStatus.FOUNDER_EDITED.value
    assert edited_claim.value_jsonb == {"range": "50-120 rooms"}

    # 4. Kiểm tra revision log bất biến
    revisions = db_session.query(FieldRevision).filter_by(claim_id=claim.id).all()
    assert len(revisions) == 1
    assert revisions[0].field_path == "CUSTOMER.hotel_size.room_count"
    assert revisions[0].old_value_jsonb == {"range": "30-100 rooms"}
    assert revisions[0].new_value_jsonb == {"range": "50-120 rooms"}
    assert revisions[0].reason == "Updated target after market survey"


def test_assumption_risk_calculation(db_session: Session):
    """Kiểm tra tính điểm rủi ro Importance * Uncertainty (1-25) (F1.md §43)."""
    # Assumption rủi ro sống còn (5 * 5 = 25)
    asm_in = AssumptionCreate(
        category=AssumptionCategory.PRICING,
        statement="Hotels will pay 1.5M VND / month",
        importance=5,
        uncertainty=5,
        impact=5,
    )
    asm = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=asm_in,
    )
    assert asm.risk_score == 25
    assert asm.status == AssumptionStatus.UNTESTED.value

    # Update uncertainty sau khi có test (5 * 2 = 10)
    updated_asm = ValidationEngineService.update_assumption(
        db=db_session,
        assumption_id=asm.id,
        update_in=AssumptionUpdate(uncertainty=2, status=AssumptionStatus.SUPPORTED),
    )
    assert updated_asm.risk_score == 10
    assert updated_asm.status == AssumptionStatus.SUPPORTED.value


def test_hypothesis_quality_gate(db_session: Session):
    """Kiểm tra Hypothesis Quality Gate (5 thành phần bắt buộc: Action, Target, Metric, Threshold, Timeframe)."""
    # 1. Tạo assumption trước
    asm = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.CUSTOMER,
            statement="Hotel managers care about night shift automation",
            importance=4,
            uncertainty=4,
        ),
    )

    # 2. Tạo hypothesis đầy đủ 5 yếu tố
    hypo_in = HypothesisCreate(
        assumption_id=asm.id,
        action="Send outreach offer",
        target_segment="20 boutique hotels in Da Nang",
        metric="Demo bookings",
        threshold=">= 5 demo bookings and >= 2 paid deposits",
        timeframe_days=7,
    )
    hypo = ValidationEngineService.build_hypothesis(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypo_in=hypo_in,
    )
    assert hypo.quality_gate_passed is True
    assert hypo.status == "READY"
    assert "IF [Send outreach offer]" in hypo.statement
    assert "FOR [20 boutique hotels in Da Nang]" in hypo.statement
    assert "WITHIN [7 DAYS]" in hypo.statement


def test_experiment_and_evidence_ledger(db_session: Session):
    """Kiểm tra liên kết Experiment -> Evidence -> Assumption."""
    asm = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.PRICING,
            statement="Hotels will pay 1.5M/mo",
            importance=5,
            uncertainty=5,
        ),
    )
    hypo = ValidationEngineService.build_hypothesis(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypo_in=HypothesisCreate(
            assumption_id=asm.id,
            action="Pitch 10 pricing calls",
            target_segment="Da Nang Hotels",
            metric="Deposit payment",
            threshold=">= 2 deposits",
            timeframe_days=5,
        ),
    )
    exp = ValidationEngineService.create_experiment(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        exp_in=ExperimentCreate(
            hypothesis_id=hypo.id,
            experiment_type=ExperimentType.PRICING_TEST,
            name="10 Direct Pricing Calls",
            success_threshold=">= 2 paid deposits",
            duration_days=5,
        ),
    )
    assert exp.id is not None

    # Ghi nhận evidence thực tế
    evi = ValidationEngineService.record_evidence(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        evi_in=EvidenceCreate(
            assumption_id=asm.id,
            hypothesis_id=hypo.id,
            experiment_id=exp.id,
            evidence_type=EvidenceType.REAL_PAYMENT,
            source_type="BANK_TRANSFER",
            source_ref="INV-2026-001",
            observation="Grand Beach Hotel paid 1.5M deposit after demo",
            metric_name="paid_deposits",
            metric_value="1",
            relationship=EvidenceRelationship.SUPPORTS,
            confidence=1.0,
        ),
    )
    assert evi.id is not None
    assert evi.evidence_type == EvidenceType.REAL_PAYMENT.value
    assert evi.relationship == EvidenceRelationship.SUPPORTS.value


def test_ai_review_and_founder_decision_independence(db_session: Session):
    """Kiểm tra AI Review độc lập và Founder là Decision Owner (không bị AI ghi đè)."""
    # 1. AI Reviewer sinh báo cáo
    review = ValidationEngineService.create_review(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        review_in=ValidationReviewCreate(
            review_provider_type=ReviewProviderType.AI,
            verdict=ReviewVerdict.TEST_MORE,
            confidence_score=0.74,
            supported_points=["Interest exists in night shift automation"],
            challenged_points=["Payment threshold not yet reached (1/2)"],
            missing_evidence=["Need 1 more deposit"],
            critical_risks=["Pricing resistance from budget hotels"],
            recommended_next_action="Run 5 more calls with 4-star hotels",
            human_review_recommended=False,
        ),
    )
    assert review.verdict == ReviewVerdict.TEST_MORE.value

    # 2. Founder quyết định PROCEED và ghi rõ lý do
    decision = ValidationEngineService.record_decision(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        decision_in=ValidationDecisionCreate(
            review_id=review.id,
            founder_decision=FounderDecisionEnum.PROCEED,
            rationale="I want to proceed to prototype because 3 more hotels verbally agreed to pay next week.",
            risks_acknowledged=["pricing_unvalidated"],
        ),
        user_id=1,
    )
    assert decision.ai_recommendation == ReviewVerdict.TEST_MORE.value
    assert decision.founder_decision == FounderDecisionEnum.PROCEED.value
    assert decision.decided_by == 1


def test_state_vector_composite_response(db_session: Session):
    """Kiểm tra tổng hợp State Vector của Project."""
    # Seed một số Dimension State
    ds1 = DimensionState(
        workspace_id=10,
        project_id=30,
        dimension=DimensionName.CUSTOMER.value,
        pillar=FeasibilityPillar.DESIRABILITY.value,
        state=DimensionStateEnum.SUPPORTED.value,
        confidence=0.82,
        summary="Da Nang boutique hotels confirmed",
    )
    ds2 = DimensionState(
        workspace_id=10,
        project_id=30,
        dimension=DimensionName.PRICING.value,
        pillar=FeasibilityPillar.VIABILITY.value,
        state=DimensionStateEnum.TESTING.value,
        confidence=0.22,
        summary="1 deposit collected so far",
    )
    db_session.add_all([ds1, ds2])
    db_session.commit()

    sv = ValidationEngineService.get_state_vector(db=db_session, project_id=30)
    assert sv.project_id == 30
    assert sv.project_stage == "VALIDATION"
    assert "CUSTOMER" in sv.dimensions
    assert sv.dimensions["CUSTOMER"].confidence == 0.82
    assert "PRICING" in sv.dimensions
    assert sv.dimensions["PRICING"].confidence == 0.22
    assert sv.overall_confidence == 0.52


@pytest.mark.asyncio
async def test_adaptive_interview_chat_flow(db_session: Session):
    """Kiểm tra luồng Adaptive Interview qua Chat và trích xuất claims."""
    from founder_os.validation.interview_service import ValidationInterviewService

    # 1. Founder chat câu đầu tiên về customer
    res = await ValidationInterviewService.process_user_turn(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        user_message="Khách hàng đầu tiên là các khách sạn boutique từ 30 đến 100 phòng tại Đà Nẵng.",
        current_topic=DimensionName.CUSTOMER.value,
    )
    assert res["session_id"] is not None
    assert res["current_topic"] == DimensionName.CUSTOMER.value
    assert len(res["extracted_claims"]) > 0

    # 2. Kiểm tra claim đã được lưu trong DB
    claims = db_session.query(StructuredClaim).filter_by(project_id=30).all()
    assert len(claims) >= 1
    assert claims[0].confirmation_status == ClaimConfirmationStatus.AI_INFERRED.value


@pytest.mark.asyncio
async def test_risk_matrix_and_experiment_recommendation(db_session: Session):
    """Kiểm tra Ma trận rủi ro và Đề xuất Thử nghiệm nhỏ nhất (Phase 3)."""
    from founder_os.validation.risk_service import RiskPrioritizationService

    # 1. Tạo 2 giả định: 1 Critical Risk (5*5=25) và 1 Low Risk (2*2=4)
    asm_crit = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.PRICING,
            statement="Hotels will pay 1.5M/mo",
            importance=5,
            uncertainty=5,
        ),
    )
    asm_low = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.TECHNICAL,
            statement="Database latency < 100ms",
            importance=2,
            uncertainty=2,
        ),
    )

    # 2. Kiểm tra ma trận rủi ro
    rm = RiskPrioritizationService.get_risk_matrix(
        db=db_session,
        workspace_id=10,
        project_id=30,
    )
    assert rm.total_assumptions >= 2
    assert len(rm.critical_risks) >= 1
    assert rm.critical_risks[0].id == asm_crit.id
    assert rm.critical_risks[0].risk_score == 25
    assert len(rm.low_risks) >= 1

    # 3. Sinh giả thuyết từ assumption rủi ro tử huyệt
    gen_hypo = await RiskPrioritizationService.generate_hypothesis_from_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_id=asm_crit.id,
    )
    assert gen_hypo.assumption_id == asm_crit.id
    assert "THEN [" in gen_hypo.statement

    # 4. Lấy hypothesis vừa tạo và đề xuất thử nghiệm nhỏ nhất
    hypos = db_session.query(ValidationHypothesis).filter_by(assumption_id=asm_crit.id).all()
    assert len(hypos) >= 1

    rec_exp = await RiskPrioritizationService.recommend_experiment_for_hypothesis(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypothesis_id=hypos[0].id,
    )
    assert rec_exp.hypothesis_id == hypos[0].id
    assert rec_exp.name is not None
    assert rec_exp.duration_days > 0


@pytest.mark.asyncio
async def test_ai_review_and_single_next_best_action_synthesis(db_session: Session):
    """Kiểm tra AI Reviewer đối soát bằng chứng và Bộ tổng hợp 1 Next Best Action duy nhất (Phase 4)."""
    from founder_os.validation.review_service import ValidationReviewService

    # 1. Tạo assumption và hypothesis
    asm = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.PRICING,
            statement="Boutique hotels will pay 1.5M/mo",
            importance=5,
            uncertainty=5,
        ),
    )
    hypo = ValidationEngineService.build_hypothesis(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypo_in=HypothesisCreate(
            assumption_id=asm.id,
            action="Pitch 1.5M package to 10 hotels",
            target_segment="Boutique hotels",
            metric="Deposit rate",
            threshold=">= 30%",
            timeframe_days=7,
        ),
    )

    # 2. Thử chạy AI Reviewer
    review_res = await ValidationReviewService.perform_ai_review(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypothesis_id=hypo.id,
    )
    assert review_res.id is not None
    assert review_res.verdict in ["PASS", "CONDITIONAL_PASS", "TEST_MORE", "CHALLENGED", "FAIL"]

    # 3. Thử tổng hợp Next Best Action duy nhất
    nba = ValidationReviewService.synthesize_single_next_best_action(
        db=db_session,
        workspace_id=10,
        project_id=30,
    )
    assert nba.project_id == 30
    assert nba.title is not None
    assert nba.why is not None
    assert nba.priority == "P0_CRITICAL"


def test_review_package_export_for_human_expert(db_session: Session):
    """Kiểm tra Xuất Gói Thẩm Định (ReviewPackage) phục vụ Human Expert Review (Phase 6)."""
    from founder_os.validation.review_service import ValidationReviewService

    asm = ValidationEngineService.create_assumption(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        assumption_in=AssumptionCreate(
            category=AssumptionCategory.CUSTOMER,
            statement="Customer acquisition cost < 200k",
            importance=4,
            uncertainty=4,
        ),
    )
    hypo = ValidationEngineService.build_hypothesis(
        db=db_session,
        workspace_id=10,
        brain_id=20,
        project_id=30,
        hypo_in=HypothesisCreate(
            assumption_id=asm.id,
            action="Run FB Ads Campaign",
            target_segment="Hotel Managers",
            metric="CAC",
            threshold="< 200k VND",
            timeframe_days=5,
        ),
    )

    pkg = ValidationReviewService.export_review_package(
        db=db_session,
        workspace_id=10,
        project_id=30,
        hypothesis_id=hypo.id,
    )
    assert pkg.project_id == 30
    assert pkg.hypothesis_id == hypo.id
    assert pkg.human_review_enabled is False
    assert "hypothesis" in pkg.read_only_bundle
    assert "claims" in pkg.read_only_bundle
    assert "evidence_ledger" in pkg.read_only_bundle




