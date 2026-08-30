from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

P2_TRANCHE_B1_SKILLS = [
    "strategy.pricing",
    "sales.design-partner-selection",
]


def test_tranche_b1_p2_inventory_complete():
    """Verify both P2 decision packs exist and are validly parsable."""
    specs = {}
    for skill_id in P2_TRANCHE_B1_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        specs[spec.id] = spec

    for skill_id in P2_TRANCHE_B1_SKILLS:
        assert skill_id in specs
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert ProjectLifecycleStage.P2_SOLUTION_VALIDATION in spec.applicability.project_stages
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_b1_p2_governance_rules():
    """Verify safety boundaries on P2 decision packs."""
    # 1. strategy.pricing does not allow autonomous billing mutation
    pricing_dir = SKILLPACKS_DIR / "strategy" / "pricing"
    spec = parse_skillpack_spec(pricing_dir)
    assert spec.autonomy.ceiling == "L1_PROPOSE"
    assert "finance.payout.execute" not in spec.required_capabilities

    # 2. sales.design-partner-selection does not allow outbound send
    partner_dir = SKILLPACKS_DIR / "sales" / "design-partner-selection"
    spec = parse_skillpack_spec(partner_dir)
    assert spec.autonomy.ceiling == "L1_PROPOSE"
    assert "engagement.message.send" not in spec.required_capabilities
