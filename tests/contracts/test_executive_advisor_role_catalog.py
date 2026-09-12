from __future__ import annotations

import json
from pathlib import Path
import pytest

from apps.cosa.agents.executive_advisor_roles_generated import (
    EXECUTIVE_ROLE_CATALOG,
    STARTUP_CORE_PRESETS,
    is_executive_role_key,
)


def test_discovery_preset_is_small_and_uses_real_profiles():
    preset = STARTUP_CORE_PRESETS["startup-discovery"]
    assert preset.default_role_keys == ("chief_of_staff", "cmo", "cfo")
    assert EXECUTIVE_ROLE_CATALOG["cfo"].required_profile_key == "finance"
    assert EXECUTIVE_ROLE_CATALOG["chief_of_staff"].runtime_readiness == "READY"
    assert "cpo" not in preset.default_role_keys


def test_build_launch_preset_includes_coo():
    preset = STARTUP_CORE_PRESETS["startup-build-launch"]
    assert preset.default_role_keys == ("chief_of_staff", "cmo", "cfo", "coo")
    assert EXECUTIVE_ROLE_CATALOG["coo"].required_profile_key == "operations"
    assert EXECUTIVE_ROLE_CATALOG["coo"].runtime_readiness == "READY"


def test_roles_ready_must_have_profile_in_startup_catalog():
    startup_profiles_path = Path("shared/contracts/startup-team-profiles.json")
    with open(startup_profiles_path, "r", encoding="utf-8") as f:
        startup_data = json.load(f)
    startup_keys = {p["key"] for p in startup_data["profiles"]}

    for role_key, role in EXECUTIVE_ROLE_CATALOG.items():
        assert is_executive_role_key(role_key)
        assert len(role.required_skill_pins) > 0, f"Role {role_key} has empty skill pins"
        if role.runtime_readiness == "READY":
            assert role.required_profile_key in startup_keys, (
                f"READY role {role_key} requires profile {role.required_profile_key} "
                f"not found in startup-team-profiles.json"
            )
        assert role.advisory_only is True


def test_operations_profile_and_roles_ready():
    startup_profiles_path = Path("shared/contracts/startup-team-profiles.json")
    with open(startup_profiles_path, "r", encoding="utf-8") as f:
        startup_data = json.load(f)

    operations = next(p for p in startup_data["profiles"] if p["key"] == "operations")
    assert operations == {
        "key": "operations",
        "label": "Operations",
        "defaultMode": "TEMPLATE",
        "runtimeReadiness": "READY",
    }
    for key in ("chief_of_staff", "coo"):
        role = EXECUTIVE_ROLE_CATALOG[key]
        assert role.required_profile_key == "operations"
        assert role.runtime_readiness == "READY"
        assert role.advisory_only is True
