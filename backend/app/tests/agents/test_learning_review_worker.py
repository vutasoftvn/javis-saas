"""G1 §6 Learning Review Worker / G3 Phase 1E.

Verifies the read-mission/write-candidate-only safety invariant: every entry
point writes at most an AgentProposal (+ SkillTrajectoryCandidate for the
mission-completed path) and NEVER touches ApprovalRequest/WorkProduct/
AgentRun/Outcome state - proven with a real SQLite session so a stray
mutation would show up as a real row change, not just an unasserted mock call.
"""
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.proposals.models import AgentProposal
from app.workforce.agents.governance.models import AgentRun, AgentToolCall
from app.workforce.skills.models import SkillTrajectoryCandidate
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.learning.review_worker import LearningReviewWorker


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine, tables=[
        AgentProposal.__table__, AgentRun.__table__, AgentToolCall.__table__,
        SkillTrajectoryCandidate.__table__, Outcome.__table__, OutcomeRun.__table__,
    ])
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _patched(db: Session):
    """The worker opens its own SessionLocal() - patch it to hand back this
    test's real SQLite session (and no-op its close() so the fixture can
    still use it for assertions afterward)."""
    return patch("app.workforce.agents.learning.review_worker.SessionLocal", return_value=_NoCloseSession(db))


class _NoCloseSession:
    """Thin wrapper so `db.close()` inside the worker doesn't tear down the
    session the test fixture still needs for its own assertions."""
    def __init__(self, real: Session):
        self._real = real

    def __getattr__(self, name):
        if name == "close":
            return lambda: None
        return getattr(self._real, name)


def _completed_mission_event(mission_id: int, workspace_id: int, domains=("sales",)) -> dict:
    return {
        "event_id": "evt1",
        "run_id": str(mission_id),
        "workspace_id": str(workspace_id),
        "agent_key": "chief_of_staff",
        "event_type": "mission_completed",
        "timestamp": "2026-08-20T00:00:00+00:00",
        "data": {
            "result": {
                "mission_id": str(mission_id),
                "workspace_id": str(workspace_id),
                "goal": "Tăng pipeline quý này",
                "diagnosis": "Pipeline hiện tại đủ mạnh để mở rộng thử nghiệm.",
                "specialist_reports": {d: {"status": "ok"} for d in domains},
                "priorities": [],
                "action_plan": ["Liên hệ 10 lead mới", "Theo dõi 5 deal đang mở"],
                "required_approvals": [],
                "proposals": [],
                "status": "completed",
            }
        },
    }


def test_mission_completed_writes_exactly_one_learning_candidate_proposal(db: Session):
    ws_id = 1
    mission_id = generate_snowflake_id()
    event = _completed_mission_event(mission_id, ws_id)

    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    proposals = db.query(AgentProposal).filter(AgentProposal.workspace_id == ws_id).all()
    assert len(proposals) == 1
    p = proposals[0]
    assert p.proposal_type == "learning_candidate"
    assert p.status == "pending"
    assert p.domain == "sales"
    assert p.created_by_agent == "learning_review_worker"
    assert p.payload_jsonb["source_type"] == "mission_completed"
    assert "Tăng pipeline quý này" in p.title


def test_mission_completed_also_extracts_a_skill_trajectory_candidate(db: Session):
    ws_id = 1
    mission_id = generate_snowflake_id()
    event = _completed_mission_event(mission_id, ws_id)

    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    candidates = db.query(SkillTrajectoryCandidate).filter(SkillTrajectoryCandidate.workspace_id == ws_id).all()
    assert len(candidates) == 1
    assert candidates[0].domain == "sales"
    assert "Tăng pipeline quý này" in candidates[0].extracted_sop


def test_mission_completed_marks_cross_domain_for_multi_specialist_missions(db: Session):
    ws_id = 1
    mission_id = generate_snowflake_id()
    event = _completed_mission_event(mission_id, ws_id, domains=("sales", "finance"))

    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    proposal = db.query(AgentProposal).filter(AgentProposal.workspace_id == ws_id).first()
    assert proposal.domain == "cross_domain"
    assert proposal.payload_jsonb["domains"] == ["finance", "sales"]


def test_mission_completed_resolves_the_real_source_outcome_id(db: Session):
    ws_id = 1
    mission_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()
    outcome_run_id = generate_snowflake_id()

    outcome = Outcome(
        id=outcome_id, workspace_id=ws_id, title="Q3 pipeline growth",
        desired_result="Grow pipeline value", requested_by=1,
    )
    outcome_run = OutcomeRun(id=outcome_run_id, outcome_id=outcome_id, agent_run_id=mission_id)
    agent_run = AgentRun(
        id=mission_id, workspace_id=ws_id, user_id=1, agent_key="chief_of_staff",
        runtime="mock", status="completed", outcome_run_id=outcome_run_id,
    )
    db.add_all([outcome, outcome_run, agent_run])
    db.commit()

    event = _completed_mission_event(mission_id, ws_id)
    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    proposal = db.query(AgentProposal).filter(AgentProposal.workspace_id == ws_id).first()
    assert proposal.source_outcome_id == outcome_id


def test_mission_failed_events_are_ignored(db: Session):
    event = {
        "run_id": "123", "workspace_id": "1", "event_type": "mission_failed",
        "data": {"reason": "BUDGET_EXCEEDED", "message": "x"},
    }
    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    assert db.query(AgentProposal).count() == 0


def test_mission_with_no_specialist_reports_writes_nothing(db: Session):
    """No domain was actually delegated to - nothing trajectory-shaped exists to learn from."""
    event = _completed_mission_event(generate_snowflake_id(), 1, domains=())
    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    assert db.query(AgentProposal).count() == 0


def test_malformed_event_never_raises(db: Session):
    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event({"event_type": "mission_completed"})  # missing run_id/workspace_id
    assert db.query(AgentProposal).count() == 0


def test_on_work_product_rejected_writes_a_learning_candidate_with_real_feedback(db: Session):
    with _patched(db):
        LearningReviewWorker.on_work_product_rejected(
            workspace_id=1,
            work_product_id=999,
            agent_key="cmo_agent",
            title="Marketing campaign plan",
            feedback="Ngân sách đề xuất vượt quá giới hạn quý này.",
            run_id=None,
            rejection_kind="rejected",
        )

    proposal = db.query(AgentProposal).filter(AgentProposal.workspace_id == 1).first()
    assert proposal is not None
    assert proposal.proposal_type == "learning_candidate"
    assert proposal.domain == "cmo_agent"
    assert proposal.target_key == "work_product:999"
    assert proposal.description == "Ngân sách đề xuất vượt quá giới hạn quý này."
    assert proposal.payload_jsonb["source_type"] == "work_product_rejected"


def test_on_approval_rejected_writes_a_learning_candidate(db: Session):
    with _patched(db):
        LearningReviewWorker.on_approval_rejected(
            workspace_id=1,
            request_id=555,
            agent_key="sales_specialist",
            action_type="PUBLISH",
            reason="Nội dung chưa qua rà soát pháp lý.",
        )

    proposal = db.query(AgentProposal).filter(AgentProposal.workspace_id == 1).first()
    assert proposal is not None
    assert proposal.target_key == "approval_request:555"
    assert proposal.payload_jsonb["action_type"] == "PUBLISH"


def test_worker_never_touches_agent_run_rows(db: Session):
    """Read-mission/write-candidate-only: the mission review path reads
    AgentRun/AgentToolCall but must never insert/update/delete them."""
    ws_id = 1
    mission_id = generate_snowflake_id()
    child_run_id = generate_snowflake_id()
    db.add(AgentRun(
        id=mission_id, workspace_id=ws_id, user_id=1, agent_key="chief_of_staff",
        runtime="mock", status="completed",
    ))
    db.add(AgentRun(
        id=child_run_id, workspace_id=ws_id, user_id=1, agent_key="sales_specialist",
        runtime="sync_delegation", status="completed", parent_run_id=mission_id,
    ))
    db.add(AgentToolCall(id=generate_snowflake_id(), run_id=child_run_id, agent_key="sales_specialist", tool_name="sales.crm.read"))
    db.commit()
    run_count_before = db.query(AgentRun).count()
    tool_call_count_before = db.query(AgentToolCall).count()

    event = _completed_mission_event(mission_id, ws_id)
    with _patched(db):
        LearningReviewWorker.on_mission_terminal_event(event)

    assert db.query(AgentRun).count() == run_count_before
    assert db.query(AgentToolCall).count() == tool_call_count_before

    proposal = db.query(AgentProposal).filter(AgentProposal.workspace_id == ws_id).first()
    assert "sales.crm.read" in proposal.payload_jsonb["tools_used"]
    assert str(child_run_id) in proposal.evidence_ids_jsonb
