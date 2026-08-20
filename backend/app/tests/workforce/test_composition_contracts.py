import pytest
from pydantic import ValidationError

from app.workforce.composition.contracts import (
    ResolvedProfile,
    SessionOverride,
    ProfileExplanation
)
from app.workforce.agents.profiles.schemas import AgentProfile

def test_resolved_profile_contracts():
    """
    Test ResolvedProfile requires fields for visible tools, skill version selectors,
    workflow permissions, model policy, scope ceiling, approval baseline.
    """
    profile = AgentProfile(
        id="sales",
        name="Sales Agent",
        role="Sales",
        description="Sales functions",
        tools=["core.search", "crm.read"],
        skills=["skill_1"],
        workflows=["wf_1"],
        model_policy={"default": "reasoning"},
        permissions=["sales.read"]
    )
    
    resolved = ResolvedProfile(
        base_profile=profile,
        visible_tool_ids=["core.search"],
        active_skill_versions={"skill_1": "1.0.0"},
        workflow_permissions=["wf_1"],
        effective_model_policy={"default": "reasoning"},
        scope_ceiling={"grants": ["sales.read"]},
        approval_baseline={"requires_approval_for": ["crm.write"]},
        explanations=[
            ProfileExplanation(
                item_id="crm.read",
                item_type="tool",
                reason_code="PERMISSION",
                message="User lacks crm.read permission."
            )
        ]
    )
    
    assert "core.search" in resolved.visible_tool_ids
    assert resolved.active_skill_versions["skill_1"] == "1.0.0"
    assert resolved.explanations[0].reason_code == "PERMISSION"

def test_session_override_contracts():
    """
    Test SessionOverride represents monotonic reductions.
    """
    override = SessionOverride(
        remove_tool_ids=["core.search"],
        disable_skill_ids=["skill_1"],
        restrict_scope={"grants": ["sales.read"]}
    )
    assert "core.search" in override.remove_tool_ids
