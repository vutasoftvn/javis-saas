from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.modules.strategy.routers.project_orchestration_router import (
    confirm_mvp_roadmap,
    save_mvp_roadmap_draft,
)
from app.modules.strategy.schemas.project_orchestration_schemas import RoadmapDraft


def _member():
    m = MagicMock()
    m.workspace_id = generate_snowflake_id()
    m.user_id = generate_snowflake_id()
    m.role = "admin"
    return m


def test_save_mvp_roadmap_draft_endpoint_serializes_stages():
    member = _member()
    db = MagicMock()
    draft = RoadmapDraft.model_validate({"stages": [
        {"title": "Stage A", "hypothesis": "A hypothesis that is long enough", "scope": ["do x"], "exit_criteria": ["metric hit"]},
        {"title": "Stage B", "hypothesis": "Another hypothesis long enough", "scope": ["do y"], "exit_criteria": ["metric hit"]},
    ]})

    with patch("app.modules.strategy.routers.project_orchestration_router._service") as mock_service_factory:
        mock_service = MagicMock()
        stage = MagicMock(sequence_no=1, title="Stage A", hypothesis="A hypothesis that is long enough",
                           status="DRAFT", scope_jsonb={"items": ["do x"], "non_goals": []},
                           exit_criteria_jsonb={"items": ["metric hit"]})
        stage.id = generate_snowflake_id()
        mock_service.save_roadmap_draft.return_value = [stage]
        mock_service_factory.return_value = mock_service

        result = save_mvp_roadmap_draft(
            project_id=generate_snowflake_id(), workspace_id=member.workspace_id,
            data=draft, member=member, db=db,
        )

    assert result["stages"][0]["title"] == "Stage A"
    assert result["stages"][0]["status"] == "DRAFT"
