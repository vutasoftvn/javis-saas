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
    StrategyCanvas,
    StrategyRevision,
    StrategyFoundation,
    CoreValue
)
from founder_os.strategy.schemas.stage_schemas import ProjectStageEnum
from founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine
from founder_os.strategy.services.stage_resolver_service import StageResolverService


@pytest.fixture
def db_session():
    """In-memory SQLite test session with specific tables."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None})
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Project.__table__,
        StrategyCanvas.__table__,
        StrategyRevision.__table__,
        StrategyFoundation.__table__,
        CoreValue.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_management_policy_engine_all_stages():
    """Kiểm tra chính sách của toàn bộ 7 Stage (S0 - S6) đều được định nghĩa đầy đủ."""
    for stage_enum in ProjectStageEnum:
        policy = ManagementPolicyEngine.get_policy(stage_enum)
        assert policy.stage == stage_enum
        assert len(policy.primary_goal) > 0
        assert len(policy.primary_questions) > 0
        assert len(policy.required_entities) > 0
        assert len(policy.primary_metrics) > 0
        assert len(policy.recommended_methods) > 0
        assert len(policy.priority_agents) > 0

    # Kiểm tra S1 không có BSC, NPS; S5 có đầy đủ 12WY, OKRs
    s1_policy = ManagementPolicyEngine.get_policy(ProjectStageEnum.S1_PROBLEM_VALIDATION)
    assert "bsc" in s1_policy.deemphasized_tools
    assert "customer_discovery" in s1_policy.recommended_methods

    s5_policy = ManagementPolicyEngine.get_policy(ProjectStageEnum.S5_OPERATE_GROWTH)
    assert "twelve_week_year" in s5_policy.recommended_methods
    assert "Execution Agent" in s5_policy.priority_agents


def test_stage_resolver_with_specific_project(db_session):
    """Kiểm tra StageResolverService với một Project cụ thể."""
    ws = Workspace(id=1001, name="Test Company", company_stage="S5_OPERATE_GROWTH")
    db_session.add(ws)
    
    project = Project(
        id=2001,
        workspace_id=1001,
        brain_id=3001,
        title="AI Hotel Intelligence",
        project_stage="S2_SOLUTION_VALIDATION",
        stage_goal="Validate willingness to pay with 3 hotel pilots",
        critical_constraints=["High integration complexity", "Untested pricing"],
        status="active"
    )
    db_session.add(project)
    db_session.commit()

    resolver = StageResolverService(db=db_session, workspace_id=1001)
    context = resolver.resolve_context(project_id=2001)

    assert context.workspace_id == 1001
    assert context.company_stage == "S5_OPERATE_GROWTH"
    assert context.project_id == 2001
    assert context.project_title == "AI Hotel Intelligence"
    assert context.project_stage == ProjectStageEnum.S2_SOLUTION_VALIDATION
    assert context.stage_goal == "Validate willingness to pay with 3 hotel pilots"
    assert len(context.critical_constraints) == 2
    assert context.policy.code == "S2"


def test_stage_resolver_fallback_p0(db_session):
    """Kiểm tra StageResolverService tự động fallback về Project P0 active khi không truyền project_id."""
    ws = Workspace(id=1002, name="Miva Corp", company_stage="S5_OPERATE_GROWTH")
    db_session.add(ws)

    # Dự án P1 thường
    p1 = Project(
        id=2002,
        workspace_id=1002,
        brain_id=3002,
        title="Side Project",
        strategic_priority="P1",
        project_stage="S1_PROBLEM_VALIDATION",
        status="active"
    )
    # Dự án P0 trọng tâm
    p0 = Project(
        id=2003,
        workspace_id=1002,
        brain_id=3002,
        title="Core SaaS Platform",
        strategic_priority="P0",
        project_stage="S4_GO_TO_MARKET",
        status="active"
    )
    db_session.add_all([p1, p0])
    db_session.commit()

    resolver = StageResolverService(db=db_session, workspace_id=1002)
    context = resolver.resolve_context(project_id=None)

    assert context.project_id == 2003
    assert context.project_title == "Core SaaS Platform"
    assert context.project_stage == ProjectStageEnum.S4_GO_TO_MARKET
    assert context.policy.code == "S4"


def test_stage_resolver_company_identity(db_session):
    """Kiểm tra trích xuất Vision, Mission và Core Values từ StrategyFoundation."""
    ws = Workspace(id=1003, name="Visionary Corp", company_stage="S5_OPERATE_GROWTH")
    db_session.add(ws)

    canvas = StrategyCanvas(id=4001, workspace_id=1003, brain_id=5001, name="Main Canvas")
    db_session.add(canvas)
    
    rev = StrategyRevision(id=4002, canvas_id=4001, revision_no=1, created_by=1)
    db_session.add(rev)

    foundation = StrategyFoundation(
        id=4003,
        strategy_revision_id=4002,
        vision="Empower 1M founders",
        mission="Build the best AI operating system"
    )
    db_session.add(foundation)

    cv1 = CoreValue(id=4004, foundation_id=4003, slot_no=1, title="Extreme Focus", description="Focus on 1 goal", decision_rule="Say no to noise")
    cv2 = CoreValue(id=4005, foundation_id=4003, slot_no=2, title="Evidence First", description="Value real data", decision_rule="Verify with customers")
    db_session.add_all([cv1, cv2])
    db_session.commit()

    resolver = StageResolverService(db=db_session, workspace_id=1003)
    context = resolver.resolve_context(project_id=None)

    assert context.company_vision == "Empower 1M founders"
    assert context.company_mission == "Build the best AI operating system"
    assert len(context.company_values) == 2
    assert "Extreme Focus" in context.company_values
    assert "Evidence First" in context.company_values
