# backend/tests/agentos/skills/test_skillpacks_integration.py
from pathlib import Path

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

# tests/agentos/skills/test_skillpacks_integration.py -> parents[3] is the repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


def test_all_existing_skillpacks_discover_and_load():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    expected_skills = [
        "core.weekly-review",
        "operations.okr",
        "operations.tasks",
        "operations.twelve_week_year",
        "marketing.campaign-review",
        "marketing.copywriting",
        "marketing.market-research",
        "marketing.positioning",
        "marketing.seo-plan",
    ]
    for skill_id in expected_skills:
        assert skill_id in discovered, f"Expected {skill_id} to be discovered"
        record = registry.get(skill_id)
        assert record.manifest.metadata.id == skill_id

    router = SkillRouter(registry)
    selected = router.select("help me run my weekly review")
    assert selected is not None
    assert selected.metadata.id == "core.weekly-review"

    loader = SkillInstructionLoader(registry)
    instructions = loader.load("core.weekly-review")
    assert "weekly review" in instructions.lower()
