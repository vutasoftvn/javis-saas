from __future__ import annotations

from pathlib import Path
import pytest

from agent_recipes.loader import load_all_recipes, load_recipe


def test_load_all_recipes_succeeds():
    """Verify that all production recipe.yaml files load cleanly with pinned skill refs."""
    recipes_root = Path("packages/agent_recipes")
    recipes = load_all_recipes(recipes_root)
    assert len(recipes) >= 7

    competitor_intel = next((r for r in recipes if r.id == "sales.competitor-intelligence"), None)
    assert competitor_intel is not None
    assert len(competitor_intel.required_skills) == 1
    pinned = competitor_intel.required_skills[0].ref
    assert pinned.skill_id == "strategy.evidence-synthesis"
    assert pinned.version == "1.1.0"
    assert pinned.definition_hash == "b093992020d1eac8b7b684c271b18d1bec9ca1e916b8d3600c8dcd892b1773bc"

    research_synth = next((r for r in recipes if r.id == "research.research-synthesize"), None)
    assert research_synth is not None
    assert len(research_synth.required_skills) == 1
    pinned_research = research_synth.required_skills[0].ref
    assert pinned_research.skill_id == "strategy.evidence-synthesis"
    assert pinned_research.version == "1.1.0"


def test_reject_floating_skill_reference(tmp_path: Path):
    """Verify that floating skill references (e.g. path strings 'skillpacks/...') are strictly rejected."""
    bad_recipe = tmp_path / "bad_recipe.yaml"
    bad_recipe.write_text(
        """
apiVersion: cosa.agent-platform/v1
kind: Recipe
metadata:
  id: test.bad-recipe
  name: Bad Recipe
  domain: test
  version: 1.0.0
requires:
  capabilities: []
  skills:
    - ref: skillpacks/strategy/evidence-synthesis
outputs:
  artifact_kind: report
  format: markdown
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        load_recipe(bad_recipe)
    assert "Floating skill reference 'skillpacks/strategy/evidence-synthesis' is prohibited" in str(exc_info.value)
