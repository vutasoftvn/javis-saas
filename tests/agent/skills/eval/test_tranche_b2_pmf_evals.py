from __future__ import annotations

from pathlib import Path
import pytest

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_DIR = REPO_ROOT / "skillpacks"

TRANCHE_B2_SKILLS = [
    # Task 5: 6 Decision packs
    "discovery.affinity-synthesis",
    "strategy.pivot-persevere",
    "analytics.pmf-survey",
    "analytics.pmf-scoreboard",
    "product.outcome-roadmap",
    "product.backlog-prioritization",
    # Task 6: 4 Learning/health packs
    "product.continuous-discovery",
    "growth.experimentation-system",
    "customer-success.health-scoring",
    "customer-success.churn-analysis",
]


def test_tranche_b2_pmf_inventory_complete():
    """Verify all 10 P4 PMF & maturity skillpacks exist and are validly parsable."""
    assert len(TRANCHE_B2_SKILLS) == 10

    specs = {}
    for skill_id in TRANCHE_B2_SKILLS:
        domain, name = skill_id.split(".", 1)
        pack_dir = SKILLPACKS_DIR / domain / name
        assert pack_dir.exists(), f"Directory not found for {skill_id}: {pack_dir}"
        spec = parse_skillpack_spec(pack_dir)
        specs[spec.id] = spec

    for skill_id in TRANCHE_B2_SKILLS:
        assert skill_id in specs or skill_id.replace("-", "_") in specs or skill_id.replace("_", "-") in specs
        # Find matching spec
        spec = next(s for s in specs.values() if s.id.replace("_", "-") == skill_id.replace("_", "-"))
        assert spec.definition_hash is not None
        assert spec.autonomy.ceiling in ("L0_OBSERVE", "L1_PROPOSE", "L2_EXECUTE_SAFE")
        assert spec.autonomy.side_effect_class in ("R", "A", "W_LOCAL")
        assert spec.evidence_requirement.self_validation_forbidden is True


def test_tranche_b2_pmf_governance_rules():
    """Verify advisory-only boundary on PMF scoreboard & pivot-persevere packs (no auto-pivot or auto-gate)."""
    # PMF Scoreboard and Pivot-Persevere have no auto-transition capabilities
    for skill_id in ["strategy.pivot-persevere", "analytics.pmf-scoreboard"]:
        domain, name = skill_id.split(".", 1)
        spec = parse_skillpack_spec(SKILLPACKS_DIR / domain / name)
        assert "strategy.pivot.execute" not in spec.required_capabilities
        assert "strategy.gate.pass" not in spec.required_capabilities
        assert "analytics.metric_snapshot.ingest" not in spec.required_capabilities

    # Growth experimentation cannot autonomously allocate budget or deploy
    growth_spec = parse_skillpack_spec(SKILLPACKS_DIR / "growth" / "experimentation-system")
    assert "finance.payout.execute" not in growth_spec.required_capabilities
    assert "engineering.deploy" not in growth_spec.required_capabilities
