import os
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_mvp_stage_scoped


def test_mvp_stage_and_workspace_template_are_tenant_scoped():
    from app.modules.strategy.models import MvpStage, WorkspaceTemplate

    workspace_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    project_id = generate_snowflake_id()

    stage = MvpStage(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        brain_id=brain_id,
        project_id=project_id,
        sequence_no=1,
        title="Validate demand",
        hypothesis="SMEs will commit to pilots before an MVP is built.",
        status="DRAFT",
    )
    template = WorkspaceTemplate(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        brain_id=brain_id,
        name="Core Startup",
        source_key="core_startup",
        active_version_no=1,
    )

    assert stage.workspace_id == template.workspace_id == workspace_id
    assert stage.brain_id == template.brain_id == brain_id


def test_get_mvp_stage_scoped_rejects_cross_tenant_stage():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException, match="MVP stage not found"):
        get_mvp_stage_scoped(
            db,
            generate_snowflake_id(),
            generate_snowflake_id(),
            generate_snowflake_id(),
        )


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_only_one_active_stage_is_allowed_per_project():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import MvpStage, Project

    db = SessionLocal()
    try:
        user = User(phone="0911111111", password_hash="test", display_name="Founder")
        workspace = Workspace(name="Stage invariant workspace")
        db.add_all([user, workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        brain = Brain(workspace_id=workspace.id, name="Stage invariant brain")
        db.add_all([member, brain])
        db.flush()
        project = Project(workspace_id=workspace.id, brain_id=brain.id, title="Stage invariant project")
        db.add(project)
        db.flush()

        db.add(MvpStage(
            workspace_id=workspace.id, brain_id=brain.id, project_id=project.id,
            sequence_no=1, title="Stage 1", hypothesis="First hypothesis", status="ACTIVE",
        ))
        db.flush()

        db.add(MvpStage(
            workspace_id=workspace.id, brain_id=brain.id, project_id=project.id,
            sequence_no=2, title="Stage 2", hypothesis="Second hypothesis", status="ACTIVE",
        ))
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(os.environ.get("RUN_DB_INTEGRATION") != "1", reason="requires migrated Postgres")
def test_cross_tenant_stage_lookup_is_not_found():
    from app.db.models import Brain, User, Workspace, WorkspaceMember
    from app.db.session import SessionLocal
    from app.modules.strategy.models import MvpStage, Project

    db = SessionLocal()
    try:
        user = User(phone="0922222222", password_hash="test", display_name="Founder 2")
        owner_workspace = Workspace(name="Owner workspace")
        foreign_workspace = Workspace(name="Foreign workspace")
        db.add_all([user, owner_workspace, foreign_workspace])
        db.flush()
        member = WorkspaceMember(workspace_id=owner_workspace.id, user_id=user.id, role="admin")
        brain = Brain(workspace_id=owner_workspace.id, name="Owner brain")
        db.add_all([member, brain])
        db.flush()
        project = Project(workspace_id=owner_workspace.id, brain_id=brain.id, title="Owner project")
        db.add(project)
        db.flush()
        stage = MvpStage(
            workspace_id=owner_workspace.id, brain_id=brain.id, project_id=project.id,
            sequence_no=1, title="Owner stage", hypothesis="Owner hypothesis", status="DRAFT",
        )
        db.add(stage)
        db.flush()

        with pytest.raises(HTTPException, match="MVP stage not found"):
            get_mvp_stage_scoped(db, stage.id, foreign_workspace.id, brain.id)
    finally:
        db.rollback()
        db.close()
