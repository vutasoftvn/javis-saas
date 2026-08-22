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


def test_seo_plan_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "seo-plan")
    router = SkillRouter(registry)

    selected = router.select("build an seo keyword plan for our blog")

    assert selected is not None
    assert selected.metadata.id == "marketing.seo-plan"


def test_copywriting_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "copywriting")
    router = SkillRouter(registry)

    selected = router.select("write ad copy for our landing page")

    assert selected is not None
    assert selected.metadata.id == "marketing.copywriting"


def test_campaign_review_skill_discovers_and_routes():
    registry = SkillRegistry()
    registry.discover(MARKETING_SKILLPACKS_ROOT / "campaign-review")
    router = SkillRouter(registry)

    selected = router.select("review how our last campaign performed")

    assert selected is not None
    assert selected.metadata.id == "marketing.campaign-review"


def test_full_catalog_discovers_all_core_and_marketing_skills():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    assert set(discovered) >= {
        "core.weekly-review",
        "marketing.market-research",
        "marketing.positioning",
        "marketing.seo-plan",
        "marketing.copywriting",
        "marketing.campaign-review",
    }


def test_domain_filter_disambiguates_review_skills_across_domains():
    registry = SkillRegistry()
    registry.discover(SKILLPACKS_ROOT)
    router = SkillRouter(registry)

    core_pick = router.select("review", domain="core")
    marketing_pick = router.select("review", domain="marketing")

    assert core_pick is not None and core_pick.metadata.id == "core.weekly-review"
    assert marketing_pick is not None and marketing_pick.metadata.id == "marketing.campaign-review"


def test_discover_never_reads_skill_md_bodies(tmp_path: Path):
    manifest_only_dir = tmp_path / "manifest-only-skill"
    manifest_only_dir.mkdir()
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "test.manifest-only", "name": "x", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(manifest_only_dir)},
        "capability": {"domain": "core", "category": "test", "intents": ["x"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.5, "success_rate": 0.5},
    }
    (manifest_only_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    # deliberately no SKILL.md written

    registry = SkillRegistry()
    discovered = registry.discover(tmp_path)

    assert discovered == ["test.manifest-only"]

    loader = SkillInstructionLoader(registry)
    with pytest.raises(SkillManifestError):
        loader.load("test.manifest-only")
