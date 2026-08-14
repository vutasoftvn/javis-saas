import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.snowflake import generate_snowflake_id
from app.modules.chat.worker_prompt import WorkerPromptResult
from app.modules.strategy.models import MvpStage
from app.modules.strategy.project_orchestration_service import ProjectOrchestrationService
from app.modules.strategy.vault_artifact_service import create_stage_artifact

_MODULE = "app.modules.strategy.project_orchestration_service"


def _worker_reply(text: str, captured_prompts=None):
    """Thay agent-worker: brain-api không giữ khoá provider nên nó KHÔNG được tự gọi model,
    nó chỉ được đưa prompt cho worker và đọc lại kết quả (chat/worker_prompt.py)."""

    def _run(db, *, brain_id, prompt, title, manual_hint, **kwargs):
        if captured_prompts is not None:
            captured_prompts.append(prompt)
        return WorkerPromptResult(text=text, provider="openrouter", model="deepseek/deepseek-chat", latency_ms=12)

    return _run


def _service_with_project(project_id, workspace_id):
    db = MagicMock()
    project = MagicMock()
    project.id = project_id
    project.workspace_id = workspace_id
    project.title = "Fake project"
    project.description = "Fake description"
    db.query.return_value.filter.return_value.first.return_value = project
    service = ProjectOrchestrationService(db, workspace_id, generate_snowflake_id(), generate_snowflake_id())
    return db, service


def test_generate_roadmap_returns_unpersisted_draft_on_valid_response():
    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)

    ai_response = (
        '{"stages": ['
        '{"title": "Validate demand", "hypothesis": "SMEs will pre-commit before build", '
        '"scope": ["Interview 20 SMEs"], "non_goals": ["Do not build UI yet"], '
        '"exit_criteria": ["10 signed LOIs"]},'
        '{"title": "Build MVP", "hypothesis": "A thin slice converts pilots", '
        '"scope": ["Ship core flow"], "non_goals": [], "exit_criteria": ["3 paying pilots"]}'
        ']}'
    )
    with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
         patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply(ai_response)), \
         patch(f"{_MODULE}.fetch_foundation_context", return_value=None):
        draft = service.generate_roadmap(project_id)

    assert [s.title for s in draft.stages] == ["Validate demand", "Build MVP"]
    assert db.commit.called
    # No MvpStage rows added - generation never persists.
    added_types = {type(call.args[0]) for call in db.add.call_args_list if call.args}
    assert MvpStage not in added_types


def test_generate_roadmap_raises_422_on_invalid_ai_output():
    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)

    with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
         patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply("not valid json at all")), \
         patch(f"{_MODULE}.fetch_foundation_context", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            service.generate_roadmap(project_id)

    assert exc_info.value.status_code == 422


def test_generate_roadmap_never_calls_a_provider_from_brain_api():
    """brain-api không giữ khoá provider (docker-compose chỉ truyền cờ
    PROVIDER_CONFIGURED_*), nên gọi thẳng provider ở đây chỉ "chạy" khi có khoá lọt vào
    container bằng đường khác. Đúng lỗi đó đã đưa nút này tới một khoá OpenAI hết quota và
    báo cho founder "AI đang bị giới hạn tốc độ, thử lại sau ít phút" mãi không hết."""
    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)

    ai_response = (
        '{"stages": ['
        '{"title": "Validate demand", "hypothesis": "SMEs will pre-commit before build", '
        '"scope": ["Interview 20 SMEs"], "exit_criteria": ["10 signed LOIs"]},'
        '{"title": "Build MVP", "hypothesis": "A thin slice converts pilots", '
        '"scope": ["Ship core flow"], "exit_criteria": ["3 paying pilots"]}'
        ']}'
    )

    def _explode(*args, **kwargs):
        raise AssertionError("brain-api không được tự dựng client provider")

    with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
         patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply(ai_response)), \
         patch(f"{_MODULE}.fetch_foundation_context", return_value=None), \
         patch("app.modules.chat.providers.build_provider", side_effect=_explode):
        draft = service.generate_roadmap(project_id)

    assert len(draft.stages) == 2


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_generate_roadmap_prompt_includes_approved_foundation():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import CoreValue, Project, StrategyCanvas, StrategyFoundation, StrategyRevision

    db = SessionLocal()
    try:
        user = User(phone=f"09{generate_snowflake_id() % 10**8:08d}", password_hash="test", display_name="Founder")
        workspace = Workspace(name="Foundation context workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        brain = Brain(workspace_id=workspace.id, name="Foundation context brain")
        db.add_all([member, brain])
        db.flush()

        canvas = StrategyCanvas(workspace_id=workspace.id, brain_id=brain.id, name="Canvas", created_by=user.id)
        db.add(canvas)
        db.flush()
        revision = StrategyRevision(canvas_id=canvas.id, revision_no=1, status="approved", created_by=user.id)
        db.add(revision)
        db.flush()
        foundation = StrategyFoundation(
            strategy_revision_id=revision.id,
            vision="Trở thành nền tảng định danh số hàng đầu Đông Nam Á",
            mission="Cung cấp xác thực điện tử an toàn cho mọi doanh nghiệp",
        )
        db.add(foundation)
        db.flush()
        db.add(CoreValue(foundation_id=foundation.id, slot_no=1, title="Bảo mật tối đa", description="...", decision_rule="..."))
        db.commit()

        project = Project(workspace_id=workspace.id, brain_id=brain.id, title="Foundation context project")
        db.add(project)
        db.commit()

        service = ProjectOrchestrationService(db, workspace.id, brain.id, user.id)
        ai_response = (
            '{"stages": ['
            '{"title": "Validate demand", "hypothesis": "SMEs will pre-commit before build", '
            '"scope": ["Interview 20 SMEs"], "exit_criteria": ["10 signed LOIs"]},'
            '{"title": "Build MVP", "hypothesis": "A thin slice converts pilots", '
            '"scope": ["Ship core flow"], "exit_criteria": ["3 paying pilots"]}'
            ']}'
        )
        captured_prompts = []

        with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
             patch(
                 f"{_MODULE}.run_worker_prompt_sync",
                 side_effect=_worker_reply(ai_response, captured_prompts),
             ):
            service.generate_roadmap(project.id)

        assert len(captured_prompts) == 1
        assert "Trở thành nền tảng định danh số hàng đầu Đông Nam Á" in captured_prompts[0]
        assert "Bảo mật tối đa" in captured_prompts[0]
    finally:
        db.rollback()
        db.close()


def test_generate_roadmap_raises_503_when_provider_not_configured():
    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)

    with patch(f"{_MODULE}.is_provider_configured", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            service.generate_roadmap(project_id)

    assert exc_info.value.status_code == 503


def test_save_roadmap_draft_persists_stages_as_draft_status():
    from app.modules.strategy.schemas.project_orchestration_schemas import RoadmapDraft

    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)

    draft = RoadmapDraft.model_validate({"stages": [
        {"title": "Stage A", "hypothesis": "A hypothesis that is long enough", "scope": ["do x"], "exit_criteria": ["metric hit"]},
        {"title": "Stage B", "hypothesis": "Another hypothesis long enough", "scope": ["do y"], "exit_criteria": ["metric hit"]},
    ]})
    stages = service.save_roadmap_draft(project_id, draft)

    assert len(stages) == 2
    assert stages[0].status == "DRAFT"
    assert [s.sequence_no for s in stages] == [1, 2]
    assert db.add_all.called


def test_confirm_roadmap_requires_an_existing_draft():
    project_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    db, service = _service_with_project(project_id, ws_id)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        service.confirm_roadmap(project_id)

    assert exc_info.value.status_code == 422


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_save_then_confirm_roadmap_writes_vault_artifact_and_audit_event():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import Project, StrategyAuditEvent
    from app.modules.strategy.schemas.project_orchestration_schemas import RoadmapDraft
    from app.modules.vault.models import VaultDocument

    db = SessionLocal()
    try:
        user = User(phone=f"09{generate_snowflake_id() % 10**8:08d}", password_hash="test", display_name="Founder 3")
        workspace = Workspace(name="Roadmap confirm workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        brain = Brain(workspace_id=workspace.id, name="Roadmap confirm brain")
        db.add_all([member, brain])
        db.flush()
        project = Project(workspace_id=workspace.id, brain_id=brain.id, title="Roadmap confirm project")
        db.add(project)
        db.flush()

        service = ProjectOrchestrationService(db, workspace.id, brain.id, user.id, "admin")
        draft = RoadmapDraft.model_validate({"stages": [
            {"title": "Stage A", "hypothesis": "A hypothesis that is long enough", "scope": ["do x"], "exit_criteria": ["metric hit"]},
            {"title": "Stage B", "hypothesis": "Another hypothesis long enough", "scope": ["do y"], "exit_criteria": ["metric hit"]},
        ]})
        service.save_roadmap_draft(project.id, draft)

        confirmed = service.confirm_roadmap(project.id)

        assert [s.status for s in confirmed] == ["CONFIRMED", "CONFIRMED"]
        assert [s.sequence_no for s in confirmed] == [1, 2]

        doc = db.query(VaultDocument).filter(
            VaultDocument.brain_id == brain.id,
            VaultDocument.path == f"projects/{project.id}/mvp_roadmap.md",
        ).first()
        assert doc is not None
        assert doc.current_revision_id is not None

        audit = db.query(StrategyAuditEvent).filter(
            StrategyAuditEvent.project_id == project.id
        ).first()
        assert audit is not None
        assert audit.event_type == "FOUNDER_DECISION"
    finally:
        db.rollback()
        db.close()


def _approved_plan():
    from app.modules.strategy.schemas.project_orchestration_schemas import StagePlanDraft

    return StagePlanDraft.model_validate({
        "objectives": [{"title": "Validate demand", "key_results": [
            {"title": "10 signed LOIs", "target_value": 10, "unit": "count"},
            {"title": "20 customer interviews"},
        ]}],
        "weekly_focus": [f"Week {i} focus" for i in range(1, 13)],
    })


def _setup_confirmed_stage():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import MvpStage, Project
    from app.modules.strategy.template_service import TemplateService

    db = SessionLocal()
    user = User(phone=f"09{generate_snowflake_id() % 10**8:08d}", password_hash="test", display_name="Activator")
    workspace = Workspace(name="Activation workspace")
    db.add_all([user, workspace])
    db.flush()
    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
    brain = Brain(workspace_id=workspace.id, name="Activation brain")
    db.add_all([member, brain])
    db.flush()
    TemplateService(db, workspace.id, brain.id).provision_workspace_templates()
    project = Project(workspace_id=workspace.id, brain_id=brain.id, title="Activation project")
    db.add(project)
    db.flush()
    stage = MvpStage(
        workspace_id=workspace.id, brain_id=brain.id, project_id=project.id,
        sequence_no=1, title="Stage 1", hypothesis="Some hypothesis for activation", status="CONFIRMED",
    )
    db.add(stage)
    db.commit()
    service = ProjectOrchestrationService(db, workspace.id, brain.id, user.id, "admin")
    return db, service, project, stage


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_activate_stage_creates_one_okr_cycle_and_twelve_weekly_plans():
    db, service, project, stage = _setup_confirmed_stage()
    try:
        result = service.activate_stage(project.id, stage.id, _approved_plan())

        assert result["stage"].status == "ACTIVE"
        assert len(result["weekly_plans"]) == 12
        assert [p.week_no for p in result["weekly_plans"]] == list(range(1, 13))
        assert result["okr_cycle"].mvp_stage_id == stage.id
        db.refresh(project)
        assert project.active_stage_id == stage.id
        assert stage.template_snapshot_jsonb
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_activate_stage_rejects_a_second_active_stage_with_409():
    db, service, project, stage = _setup_confirmed_stage()
    try:
        service.activate_stage(project.id, stage.id, _approved_plan())

        from app.modules.strategy.models import MvpStage
        second_stage = MvpStage(
            workspace_id=project.workspace_id, brain_id=project.brain_id, project_id=project.id,
            sequence_no=2, title="Stage 2", hypothesis="Second stage hypothesis", status="CONFIRMED",
        )
        db.add(second_stage)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            service.activate_stage(project.id, second_stage.id, _approved_plan())
        assert exc_info.value.status_code == 409
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_activate_stage_rejects_a_draft_stage():
    from app.modules.strategy.models import MvpStage

    db, service, project, _confirmed_stage = _setup_confirmed_stage()
    try:
        draft_stage = MvpStage(
            workspace_id=project.workspace_id, brain_id=project.brain_id, project_id=project.id,
            sequence_no=2, title="Draft stage", hypothesis="Draft stage hypothesis", status="DRAFT",
        )
        db.add(draft_stage)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            service.activate_stage(project.id, draft_stage.id, _approved_plan())
        assert exc_info.value.status_code == 422
    finally:
        db.rollback()
        db.close()


def _setup_active_stage():
    db, service, project, stage = _setup_confirmed_stage()
    service.activate_stage(project.id, stage.id, _approved_plan())
    return db, service, project, stage


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_material_revision_preview_supersedes_unstarted_assignments_and_preserves_evidence():
    from app.modules.strategy.routing_service import RoutingService
    from app.modules.strategy.schemas.project_orchestration_schemas import (
        ServiceAssessmentDecision,
        StageRevisionChange,
    )

    db, service, project, stage = _setup_active_stage()
    try:
        # An approved-but-not-started assignment exists via the routing flow.
        routing = RoutingService(db, project.workspace_id, project.brain_id, service.user_id)
        with patch("app.modules.strategy.routing_service.is_provider_configured", return_value=False):
            assessments = routing.generate_assessment(stage.id)
        decision = ServiceAssessmentDecision(assessment_id=str(assessments[0].id), approved=True)
        routing.confirm_assessment(stage.id, [decision])

        # An already-written stage artefact must be preserved by the preview.
        create_stage_artifact(
            db, service.user_id, project.brain_id, "admin",
            project_id=project.id, artifact_kind="research_note", content="# Notes",
            stage_id=stage.id,
        )

        revision = service.preview_stage_revision(stage.id, StageRevisionChange(
            hypothesis="A materially different hypothesis than before",
        ))

        assert revision.change_type == "MATERIAL"
        assert len(revision.impact_preview_jsonb["supersede_assignment_ids"]) == 1
        assert len(revision.impact_preview_jsonb["preserve_evidence_document_ids"]) == 1
        assert revision.status == "PREVIEWED"
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_apply_revision_rejects_a_stale_preview():
    from app.modules.strategy.schemas.project_orchestration_schemas import StageRevisionChange

    db, service, project, stage = _setup_active_stage()
    try:
        first = service.preview_stage_revision(stage.id, StageRevisionChange(hypothesis="First revised hypothesis text"))
        second = service.preview_stage_revision(stage.id, StageRevisionChange(hypothesis="Second revised hypothesis text"))

        with pytest.raises(HTTPException) as exc_info:
            service.apply_stage_revision(stage.id, first.id)
        assert exc_info.value.status_code == 409

        applied = service.apply_stage_revision(stage.id, second.id)
        assert applied.hypothesis == "Second revised hypothesis text"
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_go_decision_completes_current_stage_and_leaves_next_stage_untouched():
    from app.modules.strategy.models import MvpStage

    db, service, project, stage = _setup_active_stage()
    try:
        next_stage = MvpStage(
            workspace_id=project.workspace_id, brain_id=project.brain_id, project_id=project.id,
            sequence_no=2, title="Stage 2", hypothesis="Second stage hypothesis", status="CONFIRMED",
        )
        db.add(next_stage)
        db.commit()

        result = service.confirm_week13(stage.id, "GO", "All key results met, advancing")

        assert result["stage"].status == "COMPLETED"
        db.refresh(next_stage)
        assert next_stage.status == "CONFIRMED"
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_hold_decision_keeps_stage_active():
    db, service, project, stage = _setup_active_stage()
    try:
        result = service.confirm_week13(stage.id, "HOLD", "Still validating, continue as planned")
        assert result["stage"].status == "ACTIVE"
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_generate_week13_returns_facts_without_ai_when_unconfigured():
    with patch(f"{_MODULE}.is_provider_configured", return_value=False):
        db, service, project, stage = _setup_active_stage()
        try:
            result = service.generate_week13(stage.id)
            assert result["ai_recommendation"] is None
            assert result["facts"]["total_commitments"] == 0
        finally:
            db.rollback()
            db.close()
