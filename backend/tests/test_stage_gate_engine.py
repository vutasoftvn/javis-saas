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
    StageTransitionAudit,
    PrematureScalingAlert,
    StrategicDecision,
)
from platform_core.vault.models import Brain
from founder_os.strategy.services.stage_gate_service import StageGateService
from founder_os.strategy.routers.stage_gate_router import apply_stage_transition


@pytest.fixture
def db_session():
    """In-memory SQLite test session for Stage Gate Engine."""
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
        StageTransitionAudit.__table__,
        PrematureScalingAlert.__table__,
        StrategicDecision.__table__,
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


def test_stage_gate_evaluation_rejected_when_insufficient_evidence(db_session: Session):
    # Dự án S1 vừa khởi tạo, chưa có hypothesis nào được xác thực và chưa có evidence
    audit = StageGateService.evaluate_stage_readiness(
        db_session, 1001, 2001, "S2_SOLUTION_VALIDATION"
    )
    assert audit.id is not None
    assert audit.from_stage == "S1_PROBLEM_VALIDATION"
    assert audit.to_stage == "S2_SOLUTION_VALIDATION"
    assert audit.audit_status == "REJECTED"
    assert audit.readiness_score < 0.50
    assert len(audit.missing_criteria) > 0


def test_stage_gate_evaluation_approved_when_criteria_met(db_session: Session):
    # 1. Thêm Problem Hypothesis đã đạt điểm bằng chứng >= 0.5
    h1 = Hypothesis(
        id=101,
        workspace_id=1001,
        project_id=2001,
        category="problem",
        statement="Founder mất > 10 giờ/tuần để cập nhật kế hoạch thủ công.",
        importance=0.9,
        uncertainty=0.2,
        risk_score=0.18,
        evidence_score=0.85,
        confidence=0.8,
        status="SUPPORTED",
        stage_created="S1_PROBLEM_VALIDATION",
        evidence_refs=[501, 502],
    )
    # 2. Thêm 2 Bằng chứng cấp E2 & E3
    e1 = Evidence(
        id=501,
        workspace_id=1001,
        project_id=2001,
        type="interview",
        ladder_level="E2_OBSERVED_PROBLEM",
        source="Customer Interview #12",
        claim_supported="Khách hàng than phiền tốn thời gian",
        strength="strong",
        direction="supports",
        hypothesis_refs=[101],
    )
    e2 = Evidence(
        id=502,
        workspace_id=1001,
        project_id=2001,
        type="usage",
        ladder_level="E3_BEHAVIORAL_COMMITMENT",
        source="Alpha User Log",
        claim_supported="Khách hàng đăng nhập 5 ngày liên tiếp",
        strength="strong",
        direction="supports",
        hypothesis_refs=[101],
    )
    # 3. Thêm SWOT có bằng chứng
    swot = SwotItem(
        id=301,
        workspace_id=1001,
        project_id=2001,
        category="STRENGTH",
        statement="Tốc độ thử nghiệm nhanh",
        importance=0.9,
        evidence_status="verified",
        evidence_refs=[501],
    )
    db_session.add_all([h1, e1, e2, swot])
    db_session.commit()

    # Thẩm định lại
    audit = StageGateService.evaluate_stage_readiness(
        db_session, 1001, 2001, "S2_SOLUTION_VALIDATION"
    )
    assert audit.audit_status == "APPROVED"
    assert audit.readiness_score == 1.0
    assert len(audit.passed_criteria) == 3
    assert len(audit.missing_criteria) == 0


def test_anti_premature_guardrail_alerts(db_session: Session):
    # Dự án S1 có Tactic "Chạy Ads paid marketing ngân sách lớn"
    tows = TowsOption(
        id=401,
        workspace_id=1001,
        project_id=2001,
        quadrant="SO",
        title="Chiến dịch scale ads",
        tradeoffs="None",
        tactics_12wy=[
            {
                "week_number": 1,
                "title": "Chạy Ads paid marketing ngân sách lớn trên Facebook",
                "lead_indicator": "1000 click",
            }
        ],
    )
    db_session.add(tows)
    db_session.commit()

    alerts = StageGateService.check_anti_premature_guardrails(db_session, 1001, 2001)
    assert len(alerts) >= 1
    critical_alert = next((a for a in alerts if a.severity == "CRITICAL"), None)
    assert critical_alert is not None
    assert critical_alert.rule_code == "NO_PAID_ADS_IN_EARLY_STAGE"


def test_apply_stage_advancement_and_decision_lineage(db_session: Session):
    # 1. Tạo audit đã APPROVED
    audit = StageTransitionAudit(
        id=999,
        workspace_id=1001,
        project_id=2001,
        from_stage="S1_PROBLEM_VALIDATION",
        to_stage="S2_SOLUTION_VALIDATION",
        readiness_score=0.9,
        audit_status="APPROVED",
        passed_criteria=[],
        missing_criteria=[],
        detected_risks=[],
        recommendation_note="Đã đạt chuẩn",
    )
    db_session.add(audit)
    db_session.commit()

    # 2. Áp dụng nâng cấp
    project = StageGateService.apply_stage_advancement(db_session, 1001, 999)
    assert project.project_stage == "S2_SOLUTION_VALIDATION"

    # 3. Kiểm tra StrategicDecision được ghi nhận
    decision = db_session.query(StrategicDecision).filter(StrategicDecision.project_id == 2001).first()
    assert decision is not None
    assert "Nâng cấp giai đoạn" in decision.decision
    assert decision.selected_option == "S2_SOLUTION_VALIDATION"


def test_apply_stage_advancement_blocked_on_rejected_audit(db_session: Session):
    # Audit REJECTED
    audit = StageTransitionAudit(
        id=998,
        workspace_id=1001,
        project_id=2001,
        from_stage="S1_PROBLEM_VALIDATION",
        to_stage="S2_SOLUTION_VALIDATION",
        readiness_score=0.2,
        audit_status="REJECTED",
        passed_criteria=[],
        missing_criteria=[],
        detected_risks=[],
    )
    db_session.add(audit)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        StageGateService.apply_stage_advancement(db_session, 1001, 998)
    assert exc_info.value.status_code == 400
    assert "bị TỪ CHỐI" in exc_info.value.detail


def test_apply_stage_transition_requires_admin_role(db_session: Session):
    audit = StageTransitionAudit(
        id=997,
        workspace_id=1001,
        project_id=2001,
        from_stage="S1_PROBLEM_VALIDATION",
        to_stage="S2_SOLUTION_VALIDATION",
        readiness_score=0.9,
        audit_status="APPROVED",
        passed_criteria=[],
        missing_criteria=[],
        detected_risks=[],
    )
    db_session.add(audit)
    db_session.commit()

    member = WorkspaceMember(workspace_id=1001, user_id=1, role="member")

    with pytest.raises(HTTPException) as exc_info:
        apply_stage_transition(audit_id=997, payload=None, db=db_session, member=member)
    assert exc_info.value.status_code == 403

    admin_member = WorkspaceMember(workspace_id=1001, user_id=1, role="admin")
    result = apply_stage_transition(audit_id=997, payload=None, db=db_session, member=admin_member)
    assert result["new_stage"] == "S2_SOLUTION_VALIDATION"


def test_stage_gate_areas_and_recommended_action(db_session: Session):
    # APPROVED -> ADVANCE, strong_areas phản ánh passed_criteria
    approved = StageTransitionAudit(
        id=901,
        workspace_id=1001,
        project_id=2001,
        from_stage="S1_PROBLEM_VALIDATION",
        to_stage="S2_SOLUTION_VALIDATION",
        readiness_score=1.0,
        audit_status="APPROVED",
        passed_criteria=[{"id": "X", "title": "Tiêu chí X"}],
        missing_criteria=[],
        detected_risks=[],
    )
    db_session.add(approved)
    db_session.commit()
    assert approved.recommended_action == "ADVANCE"
    assert approved.strong_areas == ["Tiêu chí X"]
    assert approved.weak_areas == []
    assert approved.blockers == []

    # 3 audit REJECTED liên tiếp cùng from/to stage -> PIVOT (không có rủi ro CRITICAL)
    for i in range(3):
        rejected = StageTransitionAudit(
            id=910 + i,
            workspace_id=1001,
            project_id=2001,
            from_stage="S2_SOLUTION_VALIDATION",
            to_stage="S3_BUSINESS_VALIDATION",
            readiness_score=0.2,
            audit_status="REJECTED",
            passed_criteria=[],
            missing_criteria=[{"id": "Y", "title": "Tiêu chí Y"}],
            detected_risks=[],
        )
        db_session.add(rejected)
        db_session.commit()

    assert rejected.recommended_action == "PIVOT"
    assert rejected.blockers == ["Tiêu chí Y"]
    assert rejected.weak_areas == []

    # Thêm rủi ro CRITICAL -> STOP thay vì PIVOT
    rejected.detected_risks = [{"severity": "CRITICAL", "rule_code": "R1", "message": "Rủi ro nghiêm trọng"}]
    db_session.add(rejected)
    db_session.commit()
    assert rejected.recommended_action == "STOP"
