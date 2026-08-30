from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

P2_P3_SKILL_IDS = [
    "strategy.value-proposition",
    "strategy.positioning",
    "discovery.assumption-prioritization",
    "strategy.experiment-design",
    "product.opportunity-solution-tree",
    "product.core-workflow-map",
    "product.mvp-prioritization",
    "product.mvp-experiment-selection",
    "product.prototype-brief",
    "engineering.solution-feasibility",
    "analytics.instrumentation-plan",
]


def test_p2_p3_inventory_complete():
    """Verify all 11 P2/P3 solution validation skillpacks exist and are validly parsable."""
    assert len(P2_P3_SKILL_IDS) == 11

    specs = {}
    for item in SKILLPACKS_DIR.rglob("manifest.yaml"):
        spec = parse_skillpack_spec(item.parent)
        specs[spec.id] = spec

    for skill_id in P2_P3_SKILL_IDS:
        assert skill_id in specs, f"Missing P2/P3 skillpack '{skill_id}'"
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert (
            ProjectLifecycleStage.P2_SOLUTION_VALIDATION in spec.applicability.project_stages
            or ProjectLifecycleStage.P3_BUILD_VALIDATE in spec.applicability.project_stages
        )


def test_p2_p3_governance_rules():
    """Verify safety boundaries on P2 and P3 packs."""
    # Engineering solution feasibility is observe only (no deploy tool)
    feasibility_dir = SKILLPACKS_DIR / "engineering" / "solution-feasibility"
    spec = parse_skillpack_spec(feasibility_dir)
    assert spec.autonomy.ceiling == "L0_OBSERVE"
    assert spec.autonomy.side_effect_class == "R"
    assert "deploy" not in spec.required_capabilities

    # Analytics instrumentation plan covers P2 and P3
    instrumentation_dir = SKILLPACKS_DIR / "analytics" / "instrumentation-plan"
    spec = parse_skillpack_spec(instrumentation_dir)
    assert ProjectLifecycleStage.P2_SOLUTION_VALIDATION in spec.applicability.project_stages
    assert ProjectLifecycleStage.P3_BUILD_VALIDATE in spec.applicability.project_stages
