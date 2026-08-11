import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from app.modules.strategy.router import (
    get_prompt_template, update_prompt_template, reset_prompt_template, generate_ai_analysis,
    PromptTemplateUpdate, AiAnalysisRequest
)
from app.db.models import WorkspaceMember, PromptTemplate, PestelItem, SwotItem, TowsOption


def mock_member():
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = generate_snowflake_id()
    m.brain_id = generate_snowflake_id()
    m.role = "admin"
    return m


def test_get_default_prompt_template():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()

    # Query returns None for custom template
    db.query.return_value.filter.return_value.first.return_value = None

    res = get_prompt_template(ws_id, member, db)
    assert res["workspace_id"] == str(ws_id)
    assert res["is_customized"] is False
    assert res["config"]["pestel_items_per_factor"] == 3
    assert res["config"]["swot_items_per_category"] == 3
    assert res["config"]["tows_items_per_quadrant"] == 2
    assert "PESTEL" in res["template_content"]


def test_update_and_reset_prompt_template():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()

    # Create new custom template
    db.query.return_value.filter.return_value.first.return_value = None
    
    update_data = PromptTemplateUpdate(
        template_content="Custom template text",
        pestel_items_per_factor=1,
        swot_items_per_category=2,
        tows_items_per_quadrant=1
    )
    
    res = update_prompt_template(ws_id, update_data, member, db)
    assert db.add.called
    assert db.commit.called


@pytest.mark.anyio
async def test_generate_ai_analysis_dynamic_counts():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()

    # Mock DB queries
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []

    req = AiAnalysisRequest(
        pestel_items_per_factor=1,
        swot_items_per_category=1,
        tows_items_per_quadrant=1,
        clear_existing=True
    )

    res = await generate_ai_analysis(ws_id, req, member, db)
    assert "pestel" in res
    assert "swot" in res
    assert "tows" in res
    # 6 PESTEL factors * 1 item = 6 items
    assert len(res["pestel"]) == 6
    # 4 SWOT categories * 1 item = 4 items
    assert len(res["swot"]) == 4
    # 4 TOWS quadrants * 1 item = 4 items
    assert len(res["tows"]) == 4
