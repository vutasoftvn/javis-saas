# backend/tests/agentos/skills/test_skillpacks_integration.py
from pathlib import Path

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

# tests/agentos/skills/test_skillpacks_integration.py -> parents[3] is the repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


def test_weekly_review_skillpack_discovers_and_routes_end_to_end():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    assert "core.weekly-review" in discovered

    router = SkillRouter(registry)
    selected = router.select("help me run my weekly review")
    assert selected is not None
    assert selected.metadata.id == "core.weekly-review"

    loader = SkillInstructionLoader(registry)
    instructions = loader.load("core.weekly-review")
    assert "weekly review" in instructions.lower()
