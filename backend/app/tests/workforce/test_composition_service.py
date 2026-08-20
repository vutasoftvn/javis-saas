import pytest
from app.workforce.composition.service import ProfileCompositionService
from app.workforce.agents.profiles.schemas import AgentProfile
from app.workforce.agents.runtime.execution_scope import ExecutionScope

@pytest.fixture
def base_profile():
    return AgentProfile(
        id="sales",
        name="Sales",
        role="Sales",
        description="Sales agent",
        tools=["crm.read", "core.search", "ext.notion.create"],
        skills=["skill_sales_pitch"],
        permissions=["sales.read", "crm.read"],
        model_policy={"default": "reasoning"}
    )

@pytest.fixture
def mock_execution_scope():
    return ExecutionScope(
        workspace_id=1,
        company_id=1,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="member",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=("sales.read", "core.basic")  # Lacks crm.read
    )

def test_resolve_profile_insufficient_scope(base_profile, mock_execution_scope):
    """
    Test crm.read bị loại bỏ vì scope không có crm.read grant.
    """
    service = ProfileCompositionService()
    resolved = service.resolve(base_profile, mock_execution_scope)
    
    assert "crm.read" not in resolved.visible_tool_ids
    
    # Tìm explanation
    expl = next((e for e in resolved.explanations if e.item_id == "crm.read"), None)
    assert expl is not None
    assert expl.reason_code == "SCOPE"

def test_resolve_profile_disabled_extension(base_profile, mock_execution_scope):
    """
    Test ext.notion.create bị loại bỏ nếu extension registry báo disable.
    Trong unit test, có thể mock extension registry trả về inactive.
    """
    # Mock extension registry cho test này
    service = ProfileCompositionService()
    resolved = service.resolve(base_profile, mock_execution_scope)
    
    assert "ext.notion.create" not in resolved.visible_tool_ids
    
    expl = next((e for e in resolved.explanations if e.item_id == "ext.notion.create"), None)
    assert expl is not None
    assert expl.reason_code == "EXTENSION_DISABLED"
