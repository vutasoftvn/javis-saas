import pytest

from app.workforce.agents.registry import AGENT_PRESETS, get_preset, list_presets
from app.core.tool_bootstrap import load_all_tools
from app.core.tool_registry import get_tool_by_flat_name
from app.workforce.registry.defaults import DEFAULT_TOOL_MANIFESTS

load_all_tools()


def test_agent_presets_contain_expected_roles():
    expected_roles = {
        "chief_of_staff",
        "sales_specialist",
        "finance_specialist",
        "data_analyst",
        "researcher",
        "coding_agent",
    }
    assert expected_roles.issubset(set(AGENT_PRESETS.keys()))

    presets = list_presets()
    assert len(presets) >= len(expected_roles)


def test_all_preset_tools_exist_in_registry():
    """Verify that no tool flat name declared in any AgentPreset drifts or points
    to a non-existent tool.
    """
    for agent_key, preset in AGENT_PRESETS.items():
        assert preset.agent_key == agent_key
        assert preset.permission_profile is not None

        for tool_name in preset.tool_flat_names:
            # Core tools use provider-safe flat names.  Harness-managed tools
            # retain their qualified manifest keys until the adapter resolves
            # them at runtime.
            if "." in tool_name:
                assert any(manifest["key"] == tool_name for manifest in DEFAULT_TOOL_MANIFESTS), (
                    f"AgentPreset '{agent_key}' references non-existent Harness tool '{tool_name}'"
                )
            else:
                spec = get_tool_by_flat_name(tool_name)
                assert spec is not None, f"AgentPreset '{agent_key}' references non-existent tool '{tool_name}'"

        for write_tool in preset.write_tools:
            assert write_tool in preset.tool_flat_names, (
                f"AgentPreset '{agent_key}' declares write_tool '{write_tool}' not present in tool_flat_names"
            )


def test_get_preset_returns_correct_instance_or_none():
    cos = get_preset("chief_of_staff")
    assert cos is not None
    assert cos.agent_key == "chief_of_staff"
    assert cos.permission_profile == "chief_of_staff_suggest"
    assert "sales_get_pipeline_summary" in cos.tool_flat_names

    unknown = get_preset("non_existent_agent")
    assert unknown is None
