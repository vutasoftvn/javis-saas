# tests/agentos/profiles/test_profile_registry.py
from pathlib import Path
import pytest
import yaml

from agentos.profiles.registry import ProfileNotFoundError, ProfileRegistry, ProfileValidationError
from agentos.profiles.schema import AgentProfile
from agentos.skills.registry import SkillRegistry
from agentos.tools.registry import ToolRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"
PROFILES_ROOT = REPO_ROOT / "agentos" / "profiles" / "definitions"


@pytest.fixture(scope="module")
def initialized_registries():
    skill_reg = SkillRegistry()
    skill_reg.discover(SKILLPACKS_ROOT)

    tool_reg = ToolRegistry()
    tool_reg.register_cluster_tools()

    return skill_reg, tool_reg


def test_profile_registry_discovers_all_definitions(initialized_registries):
    skill_reg, tool_reg = initialized_registries
    profile_reg = ProfileRegistry()

    discovered = profile_reg.discover(PROFILES_ROOT, skill_registry=skill_reg, tool_registry=tool_reg)

    assert "co-founder" in discovered
    assert "sales.researcher" in discovered
    assert "strategy.specialist" in discovered

    default_prof = profile_reg.get_default()
    assert default_prof.id == "co-founder"
    assert default_prof.name == "Co-Founder"

    # Alias / normalized lookup
    assert profile_reg.get("co_founder").id == "co-founder"
    assert profile_reg.get("sales.researcher").id == "sales.researcher"


def test_profile_registry_fails_loudly_on_nonexistent_skill(tmp_path: Path, initialized_registries):
    skill_reg, tool_reg = initialized_registries
    profile_reg = ProfileRegistry()

    bad_profile = {
        "id": "bad-skill-agent",
        "name": "Bad Agent",
        "version": "1.0.0",
        "mission": "Testing missing skill reference",
        "skills": ["nonexistent.magic.skill"],
        "tools_allow": ["operations.task.create"],
        "permission_level": "L2_DRAFT",
    }
    (tmp_path / "bad_skill.yaml").write_text(yaml.safe_dump(bad_profile), encoding="utf-8")

    with pytest.raises(ProfileValidationError) as exc_info:
        profile_reg.discover(tmp_path, skill_registry=skill_reg, tool_registry=tool_reg)

    assert "nonexistent.magic.skill" in str(exc_info.value)
    assert "does not exist in SkillRegistry" in str(exc_info.value)


def test_profile_registry_fails_loudly_on_nonexistent_tool(tmp_path: Path, initialized_registries):
    skill_reg, tool_reg = initialized_registries
    profile_reg = ProfileRegistry()

    bad_profile = {
        "id": "bad-tool-agent",
        "name": "Bad Agent",
        "version": "1.0.0",
        "mission": "Testing missing tool reference",
        "skills": ["operations.okr"],
        "tools_allow": ["nonexistent.magic.tool"],
        "permission_level": "L2_DRAFT",
    }
    (tmp_path / "bad_tool.yaml").write_text(yaml.safe_dump(bad_profile), encoding="utf-8")

    with pytest.raises(ProfileValidationError) as exc_info:
        profile_reg.discover(tmp_path, skill_registry=skill_reg, tool_registry=tool_reg)

    assert "nonexistent.magic.tool" in str(exc_info.value)
    assert "does not exist in ToolRegistry" in str(exc_info.value)


def test_profile_registry_not_found():
    profile_reg = ProfileRegistry()
    with pytest.raises(ProfileNotFoundError):
        profile_reg.get("unknown-profile")
