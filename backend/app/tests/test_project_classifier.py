from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest

from app.modules.strategy.models import Project, ProjectClassification
from app.modules.strategy.project_classifier_service import ProjectClassifierService


def test_heuristic_classify_new_business():
    service = ProjectClassifierService(db=MagicMock(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id())
    res = service.heuristic_classify(title="Mở rộng thị trường mới tại Singapore")
    assert res["project_type"] == "NEW_BUSINESS"
    assert res["research_required"] is True
    assert "PESTEL" in res["recommended_methodologies"]


def test_heuristic_classify_technical():
    service = ProjectClassifierService(db=MagicMock(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id())
    res = service.heuristic_classify(title="Refactor database schema and fix CI/CD pipeline bug")
    assert res["project_type"] == "TECHNICAL"
    assert res["research_required"] is False
    assert "CLAUDE_CODE" in res["recommended_methodologies"]


def test_heuristic_classify_product():
    service = ProjectClassifierService(db=MagicMock(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id())
    res = service.heuristic_classify(title="Phát triển tính năng mobile app MVP")
    assert res["project_type"] == "PRODUCT"
    assert res["research_required"] is True
    assert "STAGE_GATE" in res["recommended_methodologies"]


def test_classify_project_persistence():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=generate_snowflake_id(),
        title="Dự án tăng trưởng marketing Q3",
        phase="Active",
        status="active",
    )
    db.query.return_value.filter.return_value.first.side_effect = [proj, None]

    service = ProjectClassifierService(db=db, workspace_id=ws_id, user_id=user_id)
    res = service.classify_project(project_id=proj_id)

    assert res["project_type"] == "GROWTH"
    assert proj.project_type == "GROWTH"
    assert db.add.called
    assert db.commit.called
