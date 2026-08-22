from pathlib import Path

from agentos.improvement.gap_detection import CapabilityGap, CapabilityGapEvidence
from agentos.improvement.proposal import ProposalStatus, propose_candidates
from agentos.skills.manifest import (
    SkillCapability,
    SkillLifecycleStatus,
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


def _register_skill(
    registry: SkillRegistry, skill_id: str, intents: list[str], *, status: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE
) -> None:
    manifest = SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain="marketing", category="research", intents=intents),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=False),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=TrustTier.T0, security_scan="passed"),
        quality=SkillQuality(eval_score=0.8, success_rate=0.8),
    )
    registry.register(manifest, Path("."), status=status)


def test_propose_candidates_ranks_matching_skills():
    registry = SkillRegistry()
    _register_skill(registry, "marketing.keyword-clustering", ["keyword clustering", "group keywords"])
    _register_skill(registry, "marketing.copywriting", ["write ad copy"])
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.candidate_skill_ids[0] == "marketing.keyword-clustering"
    assert proposal.status == ProposalStatus.PROPOSED
    assert proposal.expected_gain > 0


def test_propose_candidates_returns_empty_when_nothing_matches():
    registry = SkillRegistry()
    _register_skill(registry, "marketing.copywriting", ["write ad copy"])
    gap = CapabilityGap(
        capability="finance.reconcile-invoices",
        evidence=CapabilityGapEvidence(failed_tasks=5, average_eval=0.4),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.candidate_skill_ids == []
    assert proposal.expected_gain == 0.0


def test_propose_candidates_marks_inactive_candidate_as_medium_risk():
    registry = SkillRegistry()
    _register_skill(
        registry, "marketing.keyword-clustering", ["keyword clustering"], status=SkillLifecycleStatus.VERIFIED
    )
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.risk == "medium"
