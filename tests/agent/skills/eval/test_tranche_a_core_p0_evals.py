from __future__ import annotations

from pathlib import Path
import pytest

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

# Startup Core clean-slate (`8b5ea05a`) removed the framework strategy /
# lifecycle-gate / analytics-metric skillpacks. This inventory tracks only the
# retained Core/P0 packs.
CORE_AND_P0_SKILL_IDS = [
    "lifecycle.context-resolver",
    "lifecycle.next-best-action",
    "evidence.intake-provenance",
    "evidence.gap-analysis",
    "evidence.artifact-review",
    "governance.approval-plan",
    "governance.policy-resolution",
    "governance.risk-register",
    "governance.privacy-assessment",
    "governance.security-assessment",
    "governance.human-handoff",
    "governance.compliance-gap-analysis",
    "research.deep-research",
    "operations.weekly-review",
    "finance.runway-forecast",
    "finance.budget-guardrails",
    "research.industry-trends",
    "ai.data-rights-review",
    "ai.model-provider-risk",
]


def test_core_and_p0_inventory_complete():
    """Verify all retained Core and P0 skillpacks exist and are validly parsable."""
    assert len(CORE_AND_P0_SKILL_IDS) == 19

    specs = {}
    for item in SKILLPACKS_DIR.rglob("manifest.yaml"):
        spec = parse_skillpack_spec(item.parent)
        specs[spec.id] = spec

    for skill_id in CORE_AND_P0_SKILL_IDS:
        assert skill_id in specs, f"Missing Core/P0 skillpack '{skill_id}'"
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_core_and_p0_governance_rules():
    """Verify safety boundaries on retained Core and P0 packs."""
    # Evidence intake must be candidate-only
    intake_dir = SKILLPACKS_DIR / "evidence" / "intake-provenance"
    spec = parse_skillpack_spec(intake_dir)
    assert spec.evidence_requirement.min_source_refs >= 1
    assert "strategy.evidence.create" in spec.required_capabilities
