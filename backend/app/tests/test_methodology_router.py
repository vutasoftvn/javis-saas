import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest

from app.modules.strategy.models import Project, ProjectClassification, MethodologyPlan
from app.modules.strategy.methodology_router import MethodologyRouterService


def test_route_methodology_automatic():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=generate_snowflake_id(),
        title="Phát triển SaaS MVP",
        project_type="PRODUCT",
    )
    # 1. get_project_scoped -> proj
    # 2. classification query -> None
    # 3. plan query -> None
    db.query.return_value.filter.return_value.first.side_effect = [proj, None, None]

    service = MethodologyRouterService(db=db, workspace_id=ws_id, user_id=user_id)
    plan = service.route_methodology(project_id=proj_id)

    assert "SWOT" in plan["selected_methodologies"]
    assert "STAGE_GATE" in plan["selected_methodologies"]
    assert plan["status"] == "active"
    assert db.add.called
    assert db.commit.called


def test_route_methodology_custom_selection():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=generate_snowflake_id(),
        title="Dự án đặc biệt",
        project_type="STRATEGIC",
    )
    db.query.return_value.filter.return_value.first.side_effect = [proj, None, None]

    service = MethodologyRouterService(db=db, workspace_id=ws_id, user_id=user_id)
    custom_list = ["PESTEL", "SWOT", "OKR", "CLAUDE_CODE"]
    plan = service.route_methodology(
        project_id=proj_id,
        custom_methodologies=custom_list,
        rationale_override="Nhà sáng lập chọn phương pháp linh hoạt.",
    )

    assert plan["selected_methodologies"] == custom_list
    assert "CLAUDE_CODE" in plan["selected_methodologies"]
    assert plan["rationale"] == "Nhà sáng lập chọn phương pháp linh hoạt."
