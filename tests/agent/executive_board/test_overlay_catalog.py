from __future__ import annotations

import pytest
from agent.governance.contracts import AutonomyLevel
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.skills.resolver import SkillResolver  # noqa: F401

from apps.cosa.agents.catalog import seeded_entries
from apps.cosa.agents.executive_advisor_overlays_generated import ADVISOR_OVERLAY_CATALOG
from apps.cosa.agents.executive_advisor_roles_generated import EXECUTIVE_ROLE_CATALOG
from apps.cosa.agents.seed import seed_cosa_agent_specs


def test_every_overlay_maps_to_seeded_l1_agent_spec_with_exact_identity():
    specs = {e.agent_spec.id: e.agent_spec for e in seeded_entries()}
    for role_key, overlay in ADVISOR_OVERLAY_CATALOG.items():
        spec = specs[overlay.overlay_spec_id]
        assert spec.version == overlay.overlay_spec_version, role_key
        assert spec.compute_hash() == overlay.overlay_definition_hash, role_key
        assert spec.autonomy_level == AutonomyLevel.L1_PROPOSE, role_key
        assert spec.metadata["advisory_only"] is True
        pins = {(p.skill_id, p.version, p.definition_hash) for p in spec.pinned_skills}
        expected = {(p.skill_id, p.version, p.definition_hash) for p in overlay.skill_pins}
        assert pins == expected, role_key
        assert overlay.required_profile_key == EXECUTIVE_ROLE_CATALOG[role_key].required_profile_key


def test_role_skill_pin_strings_match_overlay_skill_pins():
    for role_key, role in EXECUTIVE_ROLE_CATALOG.items():
        overlay = ADVISOR_OVERLAY_CATALOG[role_key]
        from_role = sorted(
            (ref[len("skillpack:") :].partition("@")[0].replace("/", "."), ref.partition("@")[2])
            for ref in role.required_skill_pins
        )
        from_overlay = sorted((p.skill_id, p.version) for p in overlay.skill_pins)
        assert from_role == from_overlay, role_key


@pytest.mark.asyncio
async def test_all_fifteen_overlays_publish_to_registry():
    repo = InMemorySpecRegistryRepository()
    await seed_cosa_agent_specs(repo)
    for overlay in ADVISOR_OVERLAY_CATALOG.values():
        record = await repo.get(
            spec_kind="agent",
            spec_id=overlay.overlay_spec_id,
            version=overlay.overlay_spec_version,
        )
        assert record is not None
        assert record.definition_hash == overlay.overlay_definition_hash
    assert len(ADVISOR_OVERLAY_CATALOG) == 15
