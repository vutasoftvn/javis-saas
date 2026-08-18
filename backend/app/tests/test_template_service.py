import os

import pytest

from app.core.snowflake import generate_snowflake_id

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres"
)


def _new_service():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.founder_os.strategy.template_service import TemplateService

    db = SessionLocal()
    user = User(phone=f"09{generate_snowflake_id() % 10**8:08d}", password_hash="test", display_name="Admin")
    workspace = Workspace(name="Template service workspace")
    db.add_all([user, workspace])
    db.flush()
    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
    brain = Brain(workspace_id=workspace.id, name="Template service brain")
    db.add_all([member, brain])
    db.flush()
    return db, TemplateService(db, workspace.id, brain.id), user.id


def test_provision_is_idempotent_and_creates_six_local_templates():
    db, service, _user_id = _new_service()
    try:
        created = service.provision_workspace_templates()
        assert len(created) == 6
        assert service.provision_workspace_templates() == []
    finally:
        db.rollback()
        db.close()


def test_reset_archives_local_version_without_changing_stage_snapshot():
    from app.founder_os.strategy.models import MvpStage, Project, WorkspaceTemplateVersion

    db, service, user_id = _new_service()
    try:
        created = service.provision_workspace_templates()
        template = next(t for t in created if t.source_key == "core_startup")

        # Simulate a stage that activated while the template was at version 1.
        project = Project(workspace_id=service.workspace_id, brain_id=service.brain_id, title="Reset test project")
        db.add(project)
        db.flush()
        stage = MvpStage(
            workspace_id=service.workspace_id, brain_id=service.brain_id, project_id=project.id,
            sequence_no=1, title="Stage 1", hypothesis="Some hypothesis", status="ACTIVE",
            template_snapshot_jsonb={str(template.id): 1},
        )
        db.add(stage)
        db.commit()

        reset = service.reset_template(template.id, user_id)

        assert reset.active_version_no == 2
        db.refresh(stage)
        assert stage.template_snapshot_jsonb == {str(template.id): 1}

        archived = db.query(WorkspaceTemplateVersion).filter(
            WorkspaceTemplateVersion.template_id == template.id,
            WorkspaceTemplateVersion.version_no == 1,
        ).first()
        assert archived.status == "ARCHIVED"
    finally:
        db.rollback()
        db.close()
