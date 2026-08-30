from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

QUALITY_SKILLS = [
    "analytics.product-usage-analysis",
    "engineering.observability-readiness",
    "engineering.release-management",
    "ai.evaluation-design",
    "ai.red-team",
    "customer-success.support-copilot",
]


def test_tranche_b1_quality_inventory_complete():
    """Verify all 6 P3 quality/support skillpacks exist and are validly parsable."""
    assert len(QUALITY_SKILLS) == 6

    specs = {}
    for skill_id in QUALITY_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        specs[spec.id] = spec

    for skill_id in QUALITY_SKILLS:
        assert skill_id in specs
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert ProjectLifecycleStage.P3_BUILD_VALIDATE in spec.applicability.project_stages
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_b1_quality_governance_rules():
    """Verify non-deploying and non-sending boundaries on quality packs."""
    # Release management has no deploy capabilities
    release_spec = parse_skillpack_spec(SKILLPACKS_DIR / "engineering" / "release-management")
    assert release_spec.autonomy.ceiling == "L0_OBSERVE"
    assert "engineering.deploy" not in release_spec.required_capabilities
    assert "deploy" not in release_spec.required_capabilities

    # Support copilot has no autonomous message sending capability
    support_spec = parse_skillpack_spec(SKILLPACKS_DIR / "customer-success" / "support-copilot")
    assert "engagement.message.send" not in support_spec.required_capabilities
