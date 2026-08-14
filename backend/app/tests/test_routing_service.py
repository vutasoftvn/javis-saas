import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.snowflake import generate_snowflake_id
from app.modules.chat.worker_prompt import WorkerPromptResult

_MODULE = "app.modules.strategy.routing_service"

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres"
)


def _worker_reply(text: str):
    """Thay agent-worker: brain-api không giữ khoá provider nên nó chỉ đưa prompt cho
    worker rồi đọc lại kết quả (chat/worker_prompt.py)."""

    def _run(db, *, brain_id, prompt, title, manual_hint, **kwargs):
        return WorkerPromptResult(
            text=text, provider="openrouter", model="deepseek/deepseek-chat", latency_ms=12
        )

    return _run


def _setup():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import MvpStage, Project
    from app.modules.strategy.template_service import TemplateService

    db = SessionLocal()
    user = User(phone=f"09{generate_snowflake_id() % 10**8:08d}", password_hash="test", display_name="Router")
    workspace = Workspace(name="Routing workspace")
    db.add_all([user, workspace])
    db.flush()
    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
    brain = Brain(workspace_id=workspace.id, name="Routing brain")
    db.add_all([member, brain])
    db.flush()
    TemplateService(db, workspace.id, brain.id).provision_workspace_templates()
    project = Project(workspace_id=workspace.id, brain_id=brain.id, title="Routing project")
    db.add(project)
    db.flush()
    stage = MvpStage(
        workspace_id=workspace.id, brain_id=brain.id, project_id=project.id,
        sequence_no=1, title="Stage 1", hypothesis="Some hypothesis for routing", status="CONFIRMED",
    )
    db.add(stage)
    db.commit()
    return db, workspace.id, brain.id, user.id, stage.id


def test_regulated_capability_is_required_but_never_autonomous():
    from app.modules.strategy.routing_service import RoutingService

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        ai_response = (
            '{"assessments": [{"capability_key": "legal_compliance.compliance_checklist", '
            '"disposition": "REQUIRED", "reason": "Regulated domain", "expected_output": "Checklist"}]}'
        )
        with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
             patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply(ai_response)):
            assessments = service.generate_assessment(stage_id)

        assert len(assessments) == 1
        legal = assessments[0]
        assert legal.disposition == "REQUIRED"
        assert legal.professional_review_required is True
        assert legal.execution_mode == "MANUAL"
        assert legal.risk_level == "REGULATED"
    finally:
        db.rollback()
        db.close()


def test_generate_assessment_falls_back_to_deterministic_rule_when_ai_unconfigured():
    from app.modules.strategy.models import CapabilityDefinition
    from app.modules.strategy.routing_service import RoutingService

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        with patch(f"{_MODULE}.is_provider_configured", return_value=False):
            assessments = service.generate_assessment(stage_id)

        caps = {
            c.id: c.capability_key
            for c in db.query(CapabilityDefinition).filter(CapabilityDefinition.workspace_id == ws_id).all()
        }
        dispositions = {caps[a.capability_id]: a.disposition for a in assessments}
        assert dispositions["core_startup.research_validation"] == "REQUIRED"
        assert dispositions["operations.process_setup"] == "OPTIONAL"
    finally:
        db.rollback()
        db.close()


def test_confirm_assessment_rejects_autonomous_override_for_regulated_capability():
    from app.modules.strategy.routing_service import RoutingService
    from app.modules.strategy.schemas.project_orchestration_schemas import ServiceAssessmentDecision

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        with patch(f"{_MODULE}.is_provider_configured", return_value=False):
            assessments = service.generate_assessment(stage_id)
        regulated = next(a for a in assessments if a.risk_level == "REGULATED")

        decision = ServiceAssessmentDecision(
            assessment_id=str(regulated.id), approved=True, execution_mode="AUTONOMOUS"
        )
        with pytest.raises(HTTPException) as exc_info:
            service.confirm_assessment(stage_id, [decision])
        assert exc_info.value.status_code == 422
    finally:
        db.rollback()
        db.close()


def test_confirm_assessment_accepts_approved_manual_execution_and_creates_assignment():
    from app.modules.strategy.models import StageAssignment, StageServiceAssessment
    from app.modules.strategy.routing_service import RoutingService
    from app.modules.strategy.schemas.project_orchestration_schemas import ServiceAssessmentDecision

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        with patch(f"{_MODULE}.is_provider_configured", return_value=False):
            assessments = service.generate_assessment(stage_id)
        target = assessments[0]

        decision = ServiceAssessmentDecision(assessment_id=str(target.id), approved=True)
        confirmed = service.confirm_assessment(stage_id, [decision])

        assert confirmed[0].status == "CONFIRMED"
        refreshed = db.query(StageServiceAssessment).filter(StageServiceAssessment.id == target.id).first()
        assert refreshed.status == "CONFIRMED"

        assignment = db.query(StageAssignment).filter(StageAssignment.assessment_id == target.id).first()
        assert assignment is not None
        assert assignment.status == "DRAFT"
        assert assignment.mvp_stage_id == stage_id
    finally:
        db.rollback()
        db.close()


def test_confirm_assessment_rejected_decision_creates_no_assignment():
    from app.modules.strategy.models import StageAssignment
    from app.modules.strategy.routing_service import RoutingService
    from app.modules.strategy.schemas.project_orchestration_schemas import ServiceAssessmentDecision

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        with patch(f"{_MODULE}.is_provider_configured", return_value=False):
            assessments = service.generate_assessment(stage_id)
        target = assessments[0]

        decision = ServiceAssessmentDecision(assessment_id=str(target.id), approved=False)
        service.confirm_assessment(stage_id, [decision])

        assert db.query(StageAssignment).filter(StageAssignment.assessment_id == target.id).count() == 0
    finally:
        db.rollback()
        db.close()
