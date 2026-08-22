# backend/tests/agentos/skills/test_marketing_skillpacks.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.loader import SkillManifestError
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

# backend/tests/agentos/skills/test_marketing_skillpacks.py -> parents[4] is the repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"
MARKETING_SKILLPACKS_ROOT = SKILLPACKS_ROOT / "marketing"


def test_market_research_skill_discovers_and_routes():
    registry = SkillRegistry()
    discovered = registry.discover(MARKETING_SKILLPACKS_ROOT / "market-research")

    assert discovered == ["marketing.market-research"]

    router = SkillRouter(registry)
    selected = router.select("do some market research on our competitors")
    assert selected is not None
    assert selected.metadata.id == "marketing.market-research"


def test_positioning_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "positioning")
    router = SkillRouter(registry)

    selected = router.select("help me write a positioning statement for our product")

    assert selected is not None
    assert selected.metadata.id == "marketing.positioning"
