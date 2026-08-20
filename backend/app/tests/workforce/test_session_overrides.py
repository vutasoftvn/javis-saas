import pytest
from app.workforce.composition.contracts import ResolvedProfile, SessionOverride
from app.workforce.composition.overrides import apply_session_override
from app.workforce.agents.profiles.schemas import AgentProfile

@pytest.fixture
def resolved_profile():
    base = AgentProfile(
        id="sales", name="Sales", role="Sales", description="...",
        tools=["crm.read", "core.search"]
    )
    return ResolvedProfile(
        base_profile=base,
        visible_tool_ids=["crm.read", "core.search"],
        active_skill_versions={"skill_1": "1.0"},
        workflow_permissions=[],
        effective_model_policy={"default": "reasoning"},
        scope_ceiling={"grants": ["sales.read", "crm.read"]},
        approval_baseline={"requires_approval_for": ["crm.write"]},
        explanations=[]
    )

def test_apply_override_valid_subtractive(resolved_profile):
    override = SessionOverride(
        remove_tool_ids=["core.search"],
        disable_skill_ids=["skill_1"],
        restrict_scope={"grants": ["crm.read"]}
    )
    
    result = apply_session_override(resolved_profile, override)
    
    assert "core.search" not in result.visible_tool_ids
    assert "crm.read" in result.visible_tool_ids
    assert "skill_1" not in result.active_skill_versions
    assert result.scope_ceiling["grants"] == ["crm.read"]

def test_apply_override_invalid_additive_scope_is_ignored(resolved_profile):
    override = SessionOverride(
        restrict_scope={"grants": ["sales.read", "crm.read", "admin.write"]} # admin.write is additive
    )
    
    result = apply_session_override(resolved_profile, override)
    
    # admin.write should not be added
    assert "admin.write" not in result.scope_ceiling["grants"]
    assert "sales.read" in result.scope_ceiling["grants"]
