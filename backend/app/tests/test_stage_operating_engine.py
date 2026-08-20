"""G3 Phase 1D (Stage Operating Engine): `Workspace.company_stage` used to be a
static default that never changed after workspace creation. These tests lock in
that it now mirrors the workspace's primary project's `project_stage` whenever
that project genuinely advances through the evidence-gated Stage Gate, and that
the Toolset Resolver (Phase 1C) actually receives that real, moving value end
to end - not just in resolve_toolset() isolation as covered in Phase 1C's own
tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session

from app.core.tool_registry import register
from app.core.toolset_resolver import get_workspace_company_stage


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.db.base import Base
from app.platform.auth.models import Workspace, User, WorkspaceMember
from app.founder_os.strategy.models import (
    Project,
    Hypothesis,
    Evidence,
    PestelSignal,
    SwotItem,
    TowsOption,
    BscGoal,
    StageTransitionAudit,
    PrematureScalingAlert,
    StrategicDecision,
)
from app.platform.vault.models import Brain
from app.platform.core.models import FeatureFlag
from app.workforce.extensions.models import ExtensionRegistration
from app.founder_os.strategy.services.stage_gate_service import StageGateService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    tables = [
        User.__table__, Workspace.__table__, WorkspaceMember.__table__, Project.__table__,
        Brain.__table__, Hypothesis.__table__, Evidence.__table__, PestelSignal.__table__,
        SwotItem.__table__, TowsOption.__table__, BscGoal.__table__,
        StageTransitionAudit.__table__, PrematureScalingAlert.__table__, StrategicDecision.__table__,
        FeatureFlag.__table__, ExtensionRegistration.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _approved_audit(db, *, audit_id, workspace_id, project_id, from_stage, to_stage):
    audit = StageTransitionAudit(
        id=audit_id, workspace_id=workspace_id, project_id=project_id,
        from_stage=from_stage, to_stage=to_stage, readiness_score=0.9,
        audit_status="APPROVED", passed_criteria=[], missing_criteria=[], detected_risks=[],
        recommendation_note="Đã đạt chuẩn",
    )
    db.add(audit)
    db.commit()
    return audit


def test_apply_stage_advancement_syncs_company_stage_for_the_primary_project(db_session: Session):
    ws = Workspace(id=1001, name="Acme AI", company_stage="S0_GENESIS")
    brain = Brain(id=3001, workspace_id=1001, name="Acme Brain")
    p1 = Project(
        id=2001, workspace_id=1001, brain_id=3001, title="Flagship MVP",
        status="active", strategic_priority="P0", project_stage="S1_PROBLEM_VALIDATION",
    )
    db_session.add_all([ws, brain, p1])
    db_session.commit()

    _approved_audit(db_session, audit_id=999, workspace_id=1001, project_id=2001,
                     from_stage="S1_PROBLEM_VALIDATION", to_stage="S2_SOLUTION_VALIDATION")

    StageGateService.apply_stage_advancement(db_session, 1001, 999)

    refreshed = db_session.query(Workspace).filter(Workspace.id == 1001).first()
    assert refreshed.company_stage == "S2_SOLUTION_VALIDATION"


def test_apply_stage_advancement_does_not_sync_company_stage_for_a_non_primary_project(db_session: Session):
    """A company can have a secondary/exploratory project moving through its own
    stage ladder independently - only the P0/primary project's advancement should
    move the company-level stage."""
    ws = Workspace(id=1001, name="Acme AI", company_stage="S0_GENESIS")
    brain = Brain(id=3001, workspace_id=1001, name="Acme Brain")
    primary = Project(
        id=2001, workspace_id=1001, brain_id=3001, title="Flagship MVP",
        status="active", strategic_priority="P0", project_stage="S1_PROBLEM_VALIDATION",
    )
    secondary = Project(
        id=2002, workspace_id=1001, brain_id=3001, title="Side experiment",
        status="active", strategic_priority="P1", project_stage="S1_PROBLEM_VALIDATION",
    )
    db_session.add_all([ws, brain, primary, secondary])
    db_session.commit()

    _approved_audit(db_session, audit_id=997, workspace_id=1001, project_id=2002,
                     from_stage="S1_PROBLEM_VALIDATION", to_stage="S2_SOLUTION_VALIDATION")

    StageGateService.apply_stage_advancement(db_session, 1001, 997)

    refreshed = db_session.query(Workspace).filter(Workspace.id == 1001).first()
    assert refreshed.company_stage == "S0_GENESIS"  # untouched - secondary project advanced, not the primary one


def test_get_workspace_company_stage_reads_the_real_value(db_session: Session):
    ws = Workspace(id=1001, name="Acme AI", company_stage="S3_BUSINESS_VALIDATION")
    db_session.add(ws)
    db_session.commit()

    assert get_workspace_company_stage(db_session, 1001) == "S3_BUSINESS_VALIDATION"


def test_get_workspace_company_stage_returns_none_for_an_unknown_workspace(db_session: Session):
    assert get_workspace_company_stage(db_session, 9999999) is None


def test_stage_advancement_flows_end_to_end_into_the_live_chat_toolset(db_session: Session):
    """Proves the Phase 1D exit criterion for real: once the primary project's
    stage genuinely advances through the evidence-gated Stage Gate, the live chat
    tool_specs() surface (Phase 1C's real call site, not a resolver unit test)
    starts/stops offering a stage-gated tool - with zero changes to resolver code."""
    from app.workforce.chat import company_tools

    @register(
        "stagetest", "gtm_only_tool",
        chat_schema={"description": "x"},
        available_stages=frozenset({"S4_GO_TO_MARKET"}),
    )
    def gtm_only_tool(db, workspace_id):
        return {"ok": True}

    ws = Workspace(id=1001, name="Acme AI", company_stage="S1_PROBLEM_VALIDATION")
    brain = Brain(id=3001, workspace_id=1001, name="Acme Brain")
    project = Project(
        id=2001, workspace_id=1001, brain_id=3001, title="Flagship MVP",
        status="active", strategic_priority="P0", project_stage="S1_PROBLEM_VALIDATION",
    )
    db_session.add_all([ws, brain, project])
    db_session.commit()

    before_names = [s["function"]["name"] for s in company_tools.tool_specs(db_session, 1001)]
    assert "stagetest_gtm_only_tool" not in before_names

    _approved_audit(db_session, audit_id=999, workspace_id=1001, project_id=2001,
                     from_stage="S1_PROBLEM_VALIDATION", to_stage="S4_GO_TO_MARKET")
    StageGateService.apply_stage_advancement(db_session, 1001, 999)

    after_names = [s["function"]["name"] for s in company_tools.tool_specs(db_session, 1001)]
    assert "stagetest_gtm_only_tool" in after_names
