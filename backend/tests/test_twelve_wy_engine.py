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
from founder_os.strategy.models import (
    Project,
    TwelveWeekCycle,
    TacticalExecutionItem,
    WeeklyAccountabilityReview,
    Hypothesis,
    TowsOption,
)
from platform_core.vault.models import Brain
from founder_os.strategy.services.twelve_wy_service import TwelveWyService
from founder_os.strategy.schemas.twelve_wy_schemas import (
    TacticalItemCreate,
    TacticalItemUpdate,
)


@pytest.fixture
def db_session():
    """In-memory SQLite test session for 12WY Engine."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None})
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Project.__table__,
        Brain.__table__,
        TwelveWeekCycle.__table__,
        TacticalExecutionItem.__table__,
        WeeklyAccountabilityReview.__table__,
        Hypothesis.__table__,
        TowsOption.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    ws = Workspace(id=1001, name="Acme AI", company_stage="S1_PROBLEM_VALIDATION")
    brain = Brain(id=3001, workspace_id=1001, name="Acme Brain")
    p1 = Project(
        id=2001,
        workspace_id=1001,
        brain_id=3001,
        title="AI Co-founder MVP",
        project_stage="S1_PROBLEM_VALIDATION",
    )
    session.add_all([ws, brain, p1])
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_get_or_create_active_cycle(db_session: Session):
    cycle = TwelveWyService.get_or_create_active_cycle(db_session, 1001, 2001)
    assert cycle.id is not None
    assert cycle.duration_weeks == 12
    assert cycle.current_week == 1
    assert cycle.status == "ACTIVE"
    assert "AI Co-founder" in (cycle.theme or "")


def test_create_and_update_tactic_progress(db_session: Session):
    cycle = TwelveWyService.get_or_create_active_cycle(db_session, 1001, 2001)

    # 1. Tạo Tactic tuần 1
    payload = TacticalItemCreate(
        project_id=2001,
        cycle_id=cycle.id,
        week_number=1,
        title="Phỏng vấn 10 founder về quy trình lập kế hoạch",
        lead_indicator_name="Số cuộc gọi phỏng vấn",
        target_count=10,
        actual_count=0,
    )
    tactic = TwelveWyService.create_tactic(db_session, 1001, payload)
    assert tactic.id is not None
    assert tactic.status == "PLANNED"
    assert tactic.actual_count == 0

    # 2. Cập nhật tiến độ hoàn thành
    update_payload = TacticalItemUpdate(actual_count=10)
    updated = TwelveWyService.update_tactic(db_session, 1001, tactic.id, update_payload)
    assert updated.actual_count == 10
    assert updated.status == "DONE"
    assert updated.completed_at is not None


def test_weekly_execution_score_calculation(db_session: Session):
    cycle = TwelveWyService.get_or_create_active_cycle(db_session, 1001, 2001)

    # Thêm 3 tactics ở tuần 1: 2 DONE, 1 PLANNED
    TwelveWyService.create_tactic(
        db_session, 1001,
        TacticalItemCreate(
            project_id=2001, cycle_id=cycle.id, week_number=1,
            title="Tactic 1", lead_indicator_name="Count", target_count=5, actual_count=5,
        ),
    )
    TwelveWyService.create_tactic(
        db_session, 1001,
        TacticalItemCreate(
            project_id=2001, cycle_id=cycle.id, week_number=1,
            title="Tactic 2", lead_indicator_name="Count", target_count=2, actual_count=2,
        ),
    )
    TwelveWyService.create_tactic(
        db_session, 1001,
        TacticalItemCreate(
            project_id=2001, cycle_id=cycle.id, week_number=1,
            title="Tactic 3", lead_indicator_name="Count", target_count=3, actual_count=1,
        ),
    )

    score = TwelveWyService.calculate_week_score(db_session, cycle.id, 1)
    assert score == 66.7


def test_generate_weekly_review(db_session: Session):
    cycle = TwelveWyService.get_or_create_active_cycle(db_session, 1001, 2001)
    TwelveWyService.create_tactic(
        db_session, 1001,
        TacticalItemCreate(
            project_id=2001, cycle_id=cycle.id, week_number=1,
            title="Hoàn thành bản mockup", lead_indicator_name="Screen", target_count=4, actual_count=4,
        ),
    )

    review = TwelveWyService.generate_weekly_review(db_session, 1001, cycle.id, 1)
    assert review.id is not None
    assert review.execution_score == 100.0
    assert len(review.key_breakthroughs) == 1
    assert len(review.ai_recommendations) > 0


def test_cycle_dashboard(db_session: Session):
    dashboard = TwelveWyService.get_cycle_dashboard(db_session, 1001, 2001)
    assert dashboard["cycle"] is not None
    assert dashboard["current_week"] == 1
    assert len(dashboard["tactics_by_week"]) == 12
    assert len(dashboard["weekly_scores"]) == 12
