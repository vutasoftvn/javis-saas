from __future__ import annotations

import json
from pathlib import Path

from apps.cosa.agents.executive_advisor_overlays_generated import ADVISOR_OVERLAY_CATALOG
from apps.cosa.agents.executive_advisor_roles_generated import EXECUTIVE_ROLE_KEYS

SOURCE = Path("shared/contracts/executive-advisor-overlays.json")


def test_one_overlay_per_executive_role_without_duplicates():
    overlays = json.loads(SOURCE.read_text(encoding="utf-8"))["overlays"]
    keys = [o["roleKey"] for o in overlays]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(EXECUTIVE_ROLE_KEYS)
    assert set(ADVISOR_OVERLAY_CATALOG) == set(EXECUTIVE_ROLE_KEYS)


def test_overlays_are_advisory_and_pin_skills_with_hashes():
    for role_key, overlay in ADVISOR_OVERLAY_CATALOG.items():
        assert overlay.advisory_only is True, role_key
        assert overlay.skill_pins, role_key
        assert len(overlay.overlay_definition_hash) == 64
        assert all(len(p.definition_hash) == 64 for p in overlay.skill_pins)
