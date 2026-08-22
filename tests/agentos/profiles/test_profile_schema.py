# tests/agentos/profiles/test_profile_schema.py
import pytest
from pydantic import ValidationError

from agentos.core.policy import PermissionLevel
from agentos.profiles.schema import AgentProfile


def test_agent_profile_schema_valid():
    profile = AgentProfile(
        id="co-founder",
        name="Co-Founder",
        version="1.0.0",
        mission="Strategic co-founder assistant",
        skills=["operations.okr", "core.weekly-review"],
        tools_allow=["operations.task.create", "operations.task.list"],
        permission_level=PermissionLevel.L3_EXECUTE,
        preferred_runtime="native",
        fallback_runtime="deepseek_harness",
        max_tool_calls=15,
        max_cost_usd=2.0,
        max_runtime_seconds=90,
    )
    assert profile.id == "co-founder"
    assert profile.permission_level == PermissionLevel.L3_EXECUTE
    assert profile.max_tool_calls == 15


def test_agent_profile_schema_validation_error():
    # Missing required fields like id, name, version, mission
    with pytest.raises(ValidationError):
        AgentProfile(
            id="broken",
            # missing name, version, mission
        )
