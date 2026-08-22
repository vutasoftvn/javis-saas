import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
from founder_os.strategy.models import (
    Project,
    Hypothesis,
    Evidence,
    StrategicDecision,
)
from platform_core.vault.models import Brain
from founder_os.strategy.schemas.evidence_schemas import (
    HypothesisCreate,
    HypothesisCategoryEnum,
    EvidenceCreate,
    EvidenceLadderLevelEnum,
    EvidenceTypeEnum,
    EvidenceStrengthEnum,
    EvidenceDirectionEnum,
    StrategicDecisionCreate,
)
from founder_os.strategy.services.evidence_engine_service import EvidenceEngineService
from founder_os.strategy.services.decision_log_service import DecisionLogService


@pytest.fixture
def db_session():
    """In-memory SQLite test session with specific tables."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None, "finance": None, "sales": None, "marketing": None, "legal": None, "validation": None, "strategy": None, "operating": None, "knowledge": None, "policy_funding": None, "core": None, "runtime_ops": None})
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Project.__table__,
        Brain.__table__,
        Hypothesis.__table__,
        Evidence.__table__,
        StrategicDecision.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_evidence_ladder_scoring_and_auto_status(db_session):
    """Kiểm tra Thang đo Bằng chứng (Evidence Ladder) và cơ chế tự động chuyển trạng thái Giả định."""
    workspace = Workspace(id=1, name="Test WS")
    project = Project(id=10, workspace_id=1, brain_id=1, title="AI Hotel Assistant", project_stage="S1_PROBLEM_VALIDATION")
    db_session.add_all([workspace, project])
    db_session.commit()

    service = EvidenceEngineService(db=db_session, workspace_id=1, user_id=1)

    # 1. Tạo Giả định về Giá bán
    hypo_res = service.create_hypothesis(
        HypothesisCreate(
            project_id=10,
            category=HypothesisCategoryEnum.PRICING,
            statement="Khách sạn sẵn sàng trả $150/tháng cho chatbot CSKH",
            importance=0.9,
            uncertainty=0.8,
            next_action="Phỏng vấn và chốt 3 khách hàng dùng thử trả phí"
        )
    )
    assert hypo_res.status == "UNTESTED"
    assert hypo_res.risk_score == pytest.approx(0.72)
    assert hypo_res.evidence_score == 0.0

    # 2. Thêm bằng chứng E1 (Khách nói thích qua phỏng vấn)
    ev1 = service.create_evidence(
        EvidenceCreate(
            project_id=10,
            type=EvidenceTypeEnum.INTERVIEW,
            ladder_level=EvidenceLadderLevelEnum.E1_STATED_INTEREST,
            source="Phỏng vấn KS Liberty",
            claim_supported="GM nói giá $150 là hợp lý",
            strength=EvidenceStrengthEnum.MEDIUM,
            direction=EvidenceDirectionEnum.SUPPORTS,
            hypothesis_refs=[hypo_res.id]
        )
    )

    hypos = service.list_hypotheses(project_id=10)
    updated_hypo = hypos[0]
    assert updated_hypo.status == "TESTING"
    assert updated_hypo.evidence_score == pytest.approx(0.2)
    assert ev1.id in updated_hypo.evidence_refs

    # 3. Thêm bằng chứng E4 (Khách đặt cọc trả tiền thật - Economic Commitment)
    ev2 = service.create_evidence(
        EvidenceCreate(
            project_id=10,
            type=EvidenceTypeEnum.TRANSACTION,
            ladder_level=EvidenceLadderLevelEnum.E4_ECONOMIC_COMMITMENT,
            source="Stripe Invoice #001 - KS Rex",
            claim_supported="Khách sạn Rex ký hợp đồng pilot $150/tháng và trả tiền trước",
            strength=EvidenceStrengthEnum.STRONG,
            direction=EvidenceDirectionEnum.SUPPORTS,
            hypothesis_refs=[hypo_res.id]
        )
    )

    hypos = service.list_hypotheses(project_id=10)
    final_hypo = hypos[0]
    # E1 (0.2) + E4*strong (0.9 * 1.3 = 1.17) => clamped to 1.0 >= 0.75 và có E4 => SUPPORTED
    assert final_hypo.status == "SUPPORTED"
    assert final_hypo.evidence_score >= 0.75
    assert len(final_hypo.evidence_refs) == 2


def test_contradicted_evidence_invalidates_hypothesis(db_session):
    """Kiểm tra khi có bằng chứng phủ định mạnh, giả định tự động chuyển sang CONTRADICTED."""
    workspace = Workspace(id=1, name="Test WS")
    project = Project(id=20, workspace_id=1, brain_id=1, title="SaaS App", project_stage="S1_PROBLEM_VALIDATION")
    db_session.add_all([workspace, project])
    db_session.commit()

    service = EvidenceEngineService(db=db_session, workspace_id=1, user_id=1)

    hypo = service.create_hypothesis(
        HypothesisCreate(
            project_id=20,
            category=HypothesisCategoryEnum.CHANNEL,
            statement="Quảng cáo TikTok Ads sẽ mang lại CPA < $5",
            importance=0.8,
            uncertainty=0.7
        )
    )

    # Thêm bằng chứng campaign chạy thực tế thất bại
    service.create_evidence(
        EvidenceCreate(
            project_id=20,
            type=EvidenceTypeEnum.CAMPAIGN,
            ladder_level=EvidenceLadderLevelEnum.E3_BEHAVIORAL_COMMITMENT,
            source="TikTok Ads Campaign 01",
            claim_supported="CPA thực tế lên tới $45, hoàn toàn không có chuyển đổi",
            strength=EvidenceStrengthEnum.STRONG,
            direction=EvidenceDirectionEnum.CONTRADICTS,
            hypothesis_refs=[hypo.id]
        )
    )

    updated_hypo = service.list_hypotheses(project_id=20)[0]
    assert updated_hypo.status == "CONTRADICTED"


def test_assumption_risk_matrix(db_session):
    """Kiểm tra tính toán Ma trận Rủi ro Giả định 4 góc phần tư."""
    workspace = Workspace(id=1, name="Test WS")
    project = Project(id=30, workspace_id=1, brain_id=1, title="Fintech", project_stage="S2_SOLUTION_VALIDATION")
    db_session.add_all([workspace, project])
    db_session.commit()

    service = EvidenceEngineService(db=db_session, workspace_id=1, user_id=1)

    # 1. Critical (Imp >= 0.7, Unc >= 0.6)
    service.create_hypothesis(HypothesisCreate(
        project_id=30, category=HypothesisCategoryEnum.PRICING,
        statement="KH chịu trả phí 2% giao dịch", importance=0.8, uncertainty=0.7
    ))
    # 2. Monitor (Imp < 0.7, Unc >= 0.6)
    service.create_hypothesis(HypothesisCreate(
        project_id=30, category=HypothesisCategoryEnum.CHANNEL,
        statement="KH thích dùng dark mode", importance=0.4, uncertainty=0.8
    ))
    # 3. Important Low Risk (Imp >= 0.7, Unc < 0.6)
    service.create_hypothesis(HypothesisCreate(
        project_id=30, category=HypothesisCategoryEnum.LEGAL,
        statement="Cần giấy phép ví điện tử", importance=0.9, uncertainty=0.2
    ))
    # 4. Low Priority (Imp < 0.7, Unc < 0.6)
    service.create_hypothesis(HypothesisCreate(
        project_id=30, category=HypothesisCategoryEnum.OPERATIONAL,
        statement="Dùng Slack thay vì Telegram", importance=0.3, uncertainty=0.2
    ))

    matrix = service.get_assumption_matrix(project_id=30)
    assert matrix.total_hypotheses == 4
    assert matrix.critical_count == 1
    assert len(matrix.quadrants.critical_test_first) == 1
    assert len(matrix.quadrants.monitor) == 1
    assert len(matrix.quadrants.important_low_risk) == 1
    assert len(matrix.quadrants.low_priority) == 1


def test_decision_lineage_and_company_memory(db_session):
    """Kiểm tra lưu vết quyết định có bằng chứng và truy vấn Company Memory."""
    workspace = Workspace(id=1, name="Test WS")
    project = Project(id=40, workspace_id=1, brain_id=1, title="EdTech", project_stage="S3_BUSINESS_VALIDATION")
    db_session.add_all([workspace, project])
    db_session.commit()

    ev_service = EvidenceEngineService(db=db_session, workspace_id=1, user_id=1)
    ev = ev_service.create_evidence(
        EvidenceCreate(
            project_id=40,
            type=EvidenceTypeEnum.FINANCIAL,
            ladder_level=EvidenceLadderLevelEnum.E4_ECONOMIC_COMMITMENT,
            source="Báo cáo P&L Tháng 8",
            claim_supported="Biên lợi nhuận gộp gói B2B đạt 78%, cao hơn gói B2C (35%)",
            strength=EvidenceStrengthEnum.STRONG,
            direction=EvidenceDirectionEnum.SUPPORTS
        )
    )

    dec_service = DecisionLogService(db=db_session, workspace_id=1, user_id=1)
    dec = dec_service.record_decision(
        StrategicDecisionCreate(
            project_id=40,
            question="Tập trung nguồn lực vào phân khúc B2B hay B2C?",
            selected_option="Pivot toàn bộ sang B2B EdTech",
            alternatives=["Duy trì song song B2C và B2B", "Chỉ làm B2C"],
            rationale="Biên lợi nhuận gộp B2B vượt trội và CAC thu hồi dưới 2 tháng",
            evidence_refs=[ev.id],
            stage="S3_BUSINESS_VALIDATION",
            expected_result="Đạt MRR $10,000 sau 3 tháng"
        )
    )
    assert dec.id > 0
    assert dec.selected_option == "Pivot toàn bộ sang B2B EdTech"

    # Tra cứu Company Memory
    memory = dec_service.query_company_memory(query_text="B2B", project_id=40)
    assert len(memory) == 1
    assert memory[0]["question"] == "Tập trung nguồn lực vào phân khúc B2B hay B2C?"
    assert len(memory[0]["evidences"]) == 1
    assert memory[0]["evidences"][0]["id"] == ev.id
    assert memory[0]["evidences"][0]["ladder_level"] == "E4_ECONOMIC_COMMITMENT"
