from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

CORE_AND_P0_SKILL_IDS = [
    "lifecycle.context-resolver",
    "lifecycle.next-best-action",
    "lifecycle.gate-evaluator",
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
    "analytics.metric-contract",
    "research.deep-research",
    "operations.weekly-review",
    "strategy.venture-thesis",
    "strategy.business-model",
    "strategy.decision-rights",
    "strategy.pestle-analysis",
    "finance.runway-forecast",
    "finance.budget-guardrails",
    "research.industry-trends",
    "ai.data-rights-review",
    "ai.model-provider-risk",
]


def test_core_and_p0_inventory_complete():
    """Verify all 25 Core and P0 skillpacks exist and are validly parsable."""
    assert len(CORE_AND_P0_SKILL_IDS) == 25

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
    """Verify safety boundaries on Core and P0 packs."""
    # Gate evaluator cannot have write side-effect
    gate_eval_dir = SKILLPACKS_DIR / "lifecycle" / "gate-evaluator"
    spec = parse_skillpack_spec(gate_eval_dir)
    assert spec.autonomy.ceiling == "L0_OBSERVE"
    assert spec.autonomy.side_effect_class == "R"
    assert "strategy.gate_evaluation.create" in spec.required_capabilities

    # Evidence intake must be candidate-only
    intake_dir = SKILLPACKS_DIR / "evidence" / "intake-provenance"
    spec = parse_skillpack_spec(intake_dir)
    assert spec.evidence_requirement.min_source_refs >= 1
    assert "strategy.evidence.create" in spec.required_capabilities

    # Venture thesis must declare P0_DISCOVERY
    thesis_dir = SKILLPACKS_DIR / "strategy" / "venture-thesis"
    spec = parse_skillpack_spec(thesis_dir)
    assert ProjectLifecycleStage.P0_DISCOVERY in spec.applicability.project_stages
