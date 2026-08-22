import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from fastapi import HTTPException

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
    PestelSignal,
    SwotItem,
    TowsOption,
    BscGoal,
)
from platform_core.vault.models import Brain
from founder_os.strategy.schemas.lens_schemas import (
    PestelSignalCreate,
    PestelDimensionEnum,
    SwotItemCreate,
    SwotTypeEnum,
    TowsOptionCreate,
    TowsTypeEnum,
    TowsToTacticConvertRequest,
    BscGoalCreate,
    BscPerspectiveEnum,
)
from founder_os.strategy.services.strategy_lens_service import StrategyLensService


@pytest.fixture
def db_session():
    """In-memory SQLite test session for Strategy Lenses."""
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
        PestelSignal.__table__,
        SwotItem.__table__,
        TowsOption.__table__,
        BscGoal.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Seed Workspace, Brain, and Projects
    ws = Workspace(id=1001, name="Acme AI", company_stage="S1_PROBLEM_VALIDATION")
    brain = Brain(id=3001, workspace_id=1001, name="Acme Brain")
    p1 = Project(
        id=2001,
        workspace_id=1001,
        brain_id=3001,
        title="AI Co-founder MVP",
        project_stage="S1_PROBLEM_VALIDATION",
    )
    p2 = Project(
        id=2002,
        workspace_id=1001,
        brain_id=3001,
        title="AI Scale & Growth Enterprise",
        project_stage="S5_OPERATE_GROWTH",
    )
    session.add_all([ws, brain, p1, p2])
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_pestel_signal_and_conversion_to_hypothesis(db_session: Session):
    # 1. Tạo tín hiệu PESTEL
    payload = PestelSignalCreate(
        project_id=2001,
        dimension=PestelDimensionEnum.TECHNOLOGICAL,
        signal_title="Sự bùng nổ của Local LLM Small Models",
        description="Các mô hình on-device LLM giảm 80% chi phí suy luận inference.",
        impact_level="high",
        time_horizon="short_term",
    )
    signal = StrategyLensService.create_pestel_signal(db_session, 1001, payload)
    assert signal.id is not None
    assert signal.dimension == "technological"
    assert signal.impact_level == "high"

    # 2. Chuyển đổi thành Giả định cần kiểm chứng
    hypo = StrategyLensService.convert_pestel_to_hypothesis(db_session, 1001, signal.id)
    assert hypo.id is not None
    assert hypo.category == "market"
    assert hypo.importance == 0.9
    assert hypo.status == "UNTESTED"
    assert hypo.stage_created == "S1_PROBLEM_VALIDATION"

    # Kiểm tra tín hiệu đã lưu liên kết resulting_hypothesis_id
    refreshed_signal = db_session.query(PestelSignal).filter(PestelSignal.id == signal.id).first()
    assert refreshed_signal.resulting_hypothesis_id == hypo.id


def test_swot_requires_evidence_for_strength_weakness(db_session: Session):
    # 1. Thêm STRENGTH mà KHÔNG có evidence_refs -> Phải chặn lại (400)
    invalid_swot = SwotItemCreate(
        project_id=2001,
        category=SwotTypeEnum.STRENGTH,
        statement="Chúng tôi có thuật toán phân tích nhanh gấp 10 lần đối thủ.",
        importance=0.9,
        evidence_refs=[],
    )
    with pytest.raises(HTTPException) as exc_info:
        StrategyLensService.create_swot_item(db_session, 1001, invalid_swot)
    assert exc_info.value.status_code == 400
    assert "bắt buộc phải có ít nhất 1 bằng chứng" in exc_info.value.detail

    # 2. Thêm STRENGTH CÓ evidence_refs -> Thành công & verified
    valid_strength = SwotItemCreate(
        project_id=2001,
        category=SwotTypeEnum.STRENGTH,
        statement="Khách hàng hài lòng cao với tính năng lập kế hoạch tự động.",
        importance=0.85,
        evidence_refs=[9001, 9002],
    )
    item = StrategyLensService.create_swot_item(db_session, 1001, valid_strength)
    assert item.id is not None
    assert item.evidence_status == "verified"
    assert len(item.evidence_refs) == 2

    # 3. Thêm OPPORTUNITY từ PESTEL -> Thành công
    opp = SwotItemCreate(
        project_id=2001,
        category=SwotTypeEnum.OPPORTUNITY,
        statement="Thị trường AI SaaS Đông Nam Á tăng trưởng 45%/năm.",
        importance=0.8,
        pestel_signal_ref=501,
    )
    opp_item = StrategyLensService.create_swot_item(db_session, 1001, opp)
    assert opp_item.id is not None
    assert opp_item.evidence_status == "verified"


def test_tows_option_and_12wy_tactics_generation(db_session: Session):
    # 1. Tạo chiến lược TOWS SO (Maxi-Maxi)
    payload = TowsOptionCreate(
        project_id=2001,
        quadrant=TowsTypeEnum.SO,
        title="Ra mắt gói Starter AI với giá tối ưu để chiếm lĩnh thị trường",
        strategy_description="Tận dụng tốc độ suy luận nhanh của Small LLM để cung cấp mức giá rẻ hơn đối thủ 50%.",
        linked_strength_ids=[101],
        linked_opportunity_ids=[201],
    )
    option = StrategyLensService.create_tows_option(db_session, 1001, payload)
    assert option.id is not None
    assert option.quadrant == "SO"

    # 2. Sinh chiến thuật 12 Tuần từ TOWS
    tactic_req = TowsToTacticConvertRequest(
        tactic_title="Chạy chiến dịch beta test cho 50 khách hàng đầu tiên",
        week_number=2,
        lead_indicator="100 bài đăng LinkedIn & 20 cuộc phỏng vấn khách hàng",
        owner_agent="Growth Agent",
    )
    updated_option = StrategyLensService.convert_tows_to_tactics(
        db_session, 1001, option.id, tactic_req
    )
    assert updated_option.status == "selected"
    assert updated_option.resulting_hypothesis_id is not None
    assert len(updated_option.tactics_12wy) == 1
    assert updated_option.tactics_12wy[0]["week_number"] == 2
    assert updated_option.tactics_12wy[0]["lead_indicator"] == "100 bài đăng LinkedIn & 20 cuộc phỏng vấn khách hàng"


def test_bsc_stage_gating_policy(db_session: Session):
    # 1. Dự án S1 (AI Co-founder MVP) cố tạo BSC Goal -> Phải bị chặn lại (400)
    early_bsc = BscGoalCreate(
        project_id=2001,
        perspective=BscPerspectiveEnum.FINANCIAL,
        objective="Tối ưu Gross Margin đạt 80%",
        kpi_name="Gross Margin",
        target_value="80%",
        current_value="65%",
    )
    with pytest.raises(HTTPException) as exc_info:
        StrategyLensService.create_bsc_goal(db_session, 1001, early_bsc)
    assert exc_info.value.status_code == 400
    assert "chỉ được mở khóa từ S5" in exc_info.value.detail

    # 2. Dự án S5 (AI Scale & Growth Enterprise) tạo BSC Goal -> Thành công
    mature_bsc = BscGoalCreate(
        project_id=2002,
        perspective=BscPerspectiveEnum.FINANCIAL,
        objective="Đạt ARR 1M$ và Runway > 24 tháng",
        kpi_name="Annual Recurring Revenue (ARR)",
        target_value="1,000,000 USD",
        current_value="450,000 USD",
        initiatives=["Mở rộng kênh Enterprise Sales", "Tối ưu Server Unit Economics"],
    )
    goal = StrategyLensService.create_bsc_goal(db_session, 1001, mature_bsc)
    assert goal.id is not None
    assert goal.perspective == "FINANCIAL"
    assert goal.target_value == "1,000,000 USD"

    # 3. Kiểm tra Stage Lens Summary phân biệt khóa/mở BSC
    summary_s1 = StrategyLensService.get_stage_lens_summary(db_session, 1001, 2001)
    assert summary_s1.is_bsc_unlocked is False
    assert len(summary_s1.bsc_goals) == 0

    summary_s5 = StrategyLensService.get_stage_lens_summary(db_session, 1001, 2002)
    assert summary_s5.is_bsc_unlocked is True
    assert len(summary_s5.bsc_goals) == 1
