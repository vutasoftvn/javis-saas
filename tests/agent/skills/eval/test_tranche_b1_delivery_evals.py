from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

DELIVERY_SKILLS = [
    "product.prd",
    "product.user-story-and-acceptance",
    "engineering.vertical-slice",
    "engineering.alpha-validation",
    "product.pilot-onboarding",
    "product.feedback-synthesis",
]


def test_tranche_b1_delivery_inventory_complete():
    """Verify all 6 P3 delivery skillpacks exist and are validly parsable."""
    assert len(DELIVERY_SKILLS) == 6

    specs = {}
    for skill_id in DELIVERY_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        specs[spec.id] = spec

    for skill_id in DELIVERY_SKILLS:
        assert skill_id in specs
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert ProjectLifecycleStage.P3_BUILD_VALIDATE in spec.applicability.project_stages
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_b1_delivery_governance_rules():
    """Verify non-deploying boundary and safety on delivery packs."""
    # Vertical slice and Alpha validation are observe only with no deploy tools
    for skill_id in ["engineering.vertical-slice", "engineering.alpha-validation"]:
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)
        assert spec.autonomy.ceiling == "L0_OBSERVE"
        assert spec.autonomy.side_effect_class == "R"
        assert "deploy" not in spec.required_capabilities
        assert "engineering.deploy" not in spec.required_capabilities

    # Pilot onboarding has no autonomous pilot activation capability
    onboarding_spec = parse_skillpack_spec(SKILLPACKS_DIR / "product" / "pilot-onboarding")
    assert "strategy.pilot.activate" not in onboarding_spec.required_capabilities
