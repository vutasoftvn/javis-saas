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
    domain: str = "core",
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain=domain, category="general", intents=intents),
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


def test_router_domain_filter_selects_within_domain():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["review"], domain="core"), skill_dir=Path("."))
    registry.register(_make_manifest("marketing.campaign-review", ["review"], domain="marketing"), skill_dir=Path("."))
    router = SkillRouter(registry)

    core_pick = router.select("review", domain="core")
    marketing_pick = router.select("review", domain="marketing")

    assert core_pick is not None and core_pick.metadata.id == "core.weekly-review"
    assert marketing_pick is not None and marketing_pick.metadata.id == "marketing.campaign-review"


def test_router_without_domain_filter_still_returns_a_match():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["review"], domain="core"), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("review") is not None


def test_router_candidates_ranking_and_rbac_permission_check():
    registry = SkillRegistry()
    registry.register(
        _make_manifest("core.weekly-review", ["weekly review", "review"], eval_score=0.9),
        skill_dir=Path("."),
    )
    registry.register(
        _make_manifest("operations.okr", ["create okr cycle", "define objective"], eval_score=0.8),
        skill_dir=Path("."),
    )
    router = SkillRouter(registry)

    # 1. Matching intent -> top candidate
    candidates = router.select_candidates("Let's do our weekly review")
    assert len(candidates) > 0
    assert candidates[0].manifest.metadata.id == "core.weekly-review"
    assert candidates[0].is_available is True

    # 2. Denied role: auditor role cannot run business write skills
    write_manifest = SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id="ops.write", name="ops write", version="1.0.0", description="modify business data"),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path="ops.write"),
        capability=SkillCapability(domain="ops", category="tasks", intents=["modify tasks"]),
        permissions=SkillPermissions(required=["MODIFY_BUSINESS_DATA"]),
        risk=SkillRisk(level="medium"),
        trust=SkillTrust(tier=TrustTier.T0),
    )
    registry.register(write_manifest, skill_dir=Path("."))

    candidates = router.select_candidates("modify tasks", role="auditor")
    assert len(candidates) > 0
    ops_candidate = next(c for c in candidates if c.manifest.metadata.id == "ops.write")
    assert ops_candidate.is_available is False
    assert "Role 'auditor' is denied" in ops_candidate.unavailable_reason

    # Router select ignores unavailable candidate for auditor
    selected = router.select("modify tasks", role="auditor")
    assert selected is None

    # Founder role can run
    selected_founder = router.select("modify tasks", role="founder")
    assert selected_founder is not None
    assert selected_founder.metadata.id == "ops.write"
