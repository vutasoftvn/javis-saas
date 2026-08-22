# backend/tests/agentos/skills/test_router.py
from pathlib import Path

from agentos.skills.manifest import (
    SkillCapability,
    SkillManifest,
    SkillMetadata,
    SkillPermissions,
    SkillPublisher,
    SkillQuality,
    SkillRisk,
    SkillRuntime,
    SkillSource,
    SkillTrust,
    TrustTier,
)
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter, score_skill


def _make_manifest(
    skill_id: str,
    intents: list[str],
    *,
    tier: TrustTier = TrustTier.T0,
    eval_score: float = 0.8,
    business_write: bool = False,
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain="core", category="general", intents=intents),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=business_write),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=tier, security_scan="passed"),
        quality=SkillQuality(eval_score=eval_score, success_rate=0.8),
    )


def test_score_skill_rewards_matching_intents():
    manifest = _make_manifest("core.weekly-review", ["weekly review", "reflection"])
    assert score_skill("do the weekly review", manifest) > score_skill("unrelated task", manifest)


def test_router_selects_highest_scoring_active_skill():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["weekly review"]), skill_dir=Path("."))
    registry.register(_make_manifest("core.other", ["something else"]), skill_dir=Path("."))
    router = SkillRouter(registry)

    selected = router.select("please run my weekly review")

    assert selected is not None
    assert selected.metadata.id == "core.weekly-review"


def test_router_returns_none_when_nothing_relevant():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.other", ["something else"]), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("do the weekly review") is None


def test_router_excludes_skills_below_min_trust():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.risky", ["weekly review"], tier=TrustTier.T3), skill_dir=Path("."))
    router = SkillRouter(registry, min_trust=TrustTier.T2)

    assert router.select("weekly review") is None


def test_router_excludes_business_write_skill_unless_allowed():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.writer", ["weekly review"], business_write=True), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("weekly review") is None
    assert router.select("weekly review", allow_business_write=True) is not None
