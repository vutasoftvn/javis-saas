from __future__ import annotations

from pathlib import Path
import pytest

from agent.skills.contracts import ProjectLifecycleStage
from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

P1_SKILL_IDS = [
    "research.market-sizing",
    "strategy.porters-five-forces",
    "strategy.competitor-profiling",
    "strategy.icp-definition",
    "discovery.interview-script",
    "discovery.interview-prep",
    "discovery.interview-summary",
    "discovery.jtbd-synthesis",
    "discovery.pain-point-analysis",
    "discovery.assumption-mapping",
    "sales.founder-led-sales-copilot",
    "marketing.channel-strategy",
]


def test_p1_inventory_complete():
    """Verify all 12 P1 problem validation skillpacks exist and are validly parsable."""
    assert len(P1_SKILL_IDS) == 12

    specs = {}
    for item in SKILLPACKS_DIR.rglob("manifest.yaml"):
        spec = parse_skillpack_spec(item.parent)
        specs[spec.id] = spec

    for skill_id in P1_SKILL_IDS:
        assert skill_id in specs, f"Missing P1 skillpack '{skill_id}'"
        spec = specs[skill_id]
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE")
        assert spec.autonomy.side_effect_class in ("R", "A")
        assert ProjectLifecycleStage.P1_PROBLEM_VALIDATION in spec.applicability.project_stages


def test_p1_governance_rules():
    """Verify safety boundaries on P1 packs."""
    # Discovery interview summary creates candidate evidence
    interview_sum_dir = SKILLPACKS_DIR / "discovery" / "interview-summary"
    spec = parse_skillpack_spec(interview_sum_dir)
    assert spec.autonomy.ceiling == "L1_PROPOSE"
    assert spec.autonomy.side_effect_class == "A"
    assert "strategy.evidence.create" in spec.required_capabilities

    # Founder sales copilot is L0 advisory only
    sales_dir = SKILLPACKS_DIR / "sales" / "founder-led-sales-copilot"
    spec = parse_skillpack_spec(sales_dir)
    assert spec.autonomy.ceiling == "L0_OBSERVE"
    assert spec.autonomy.side_effect_class == "R"
