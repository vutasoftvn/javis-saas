from pathlib import Path

import pytest
import yaml

from agentos.core.approval import ApprovalService
from agentos.improvement.approval_gate import apply_approval_decision, mark_promoted, request_proposal_approval
from agentos.improvement.distillation import SuccessfulEpisode, distill_skill
from agentos.improvement.gap_detection import CapabilityOutcome, GapDetector
from agentos.improvement.hierarchy import ImprovementLevel, PrematureCoreCodeChangeError, require_cheaper_levels_exhausted
from agentos.improvement.proposal import ProposalStatus, propose_candidates
from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.pipeline import SupplyChainPipeline


def _write_external_skill(root: Path, skill_id: str) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {
            "id": skill_id,
            "name": skill_id,
            "version": "1.0.0",
            "description": "keyword clustering helper",
        },
        "publisher": {"name": "community", "type": "community"},
        "source": {
            "type": "git",
            "path": f"skills/{skill_id}",
            "repository": "https://github.com/example/skills",
            "commit": "4bc9a82c1234567890abcdef1234567890abcdef",
        },
        "capability": {
            "domain": "marketing",
            "category": "seo",
            "intents": ["keyword clustering", "group keywords"],
        },
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.85, "success_rate": 0.85},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("# Keyword Clustering\n\nCluster keywords.\n", encoding="utf-8")
    return skill_dir


@pytest.mark.asyncio
async def test_full_self_improvement_loop_from_gap_to_promoted_skill(tmp_path: Path):
    # 1. Observe repeated failures -> detect a capability gap.
    outcomes = [
        CapabilityOutcome(capability="marketing.keyword-clustering", succeeded=False, eval_score=0.5)
        for _ in range(5)
    ] + [CapabilityOutcome(capability="marketing.keyword-clustering", succeeded=True, eval_score=0.6)]
    gaps = GapDetector(min_failures=3, eval_threshold=0.6).detect(outcomes)
    assert len(gaps) == 1
    gap = gaps[0]

    # 2. A real supply-chain-verified candidate skill exists in the registry.
    skill_dir = _write_external_skill(tmp_path / "source", "marketing.keyword-clustering")
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    candidate = ExternalSkillCandidate(
        id="marketing.keyword-clustering",
        name="Keyword Clustering",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/marketing.keyword-clustering",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)
    pipeline.scan(skill_id)  # -> VERIFIED (low risk, high trust manifest)

    # 3. Search skill — Improvement Hierarchy level SKILL_SELECTION, no
    #    core code change needed, so the guard passes trivially.
    require_cheaper_levels_exhausted(ImprovementLevel.SKILL_SELECTION, [ImprovementLevel.CONTEXT_RETRIEVAL])
    proposal = propose_candidates(gap, registry)
    assert proposal.candidate_skill_ids[0] == "marketing.keyword-clustering"
    assert proposal.risk == "medium"  # candidate is VERIFIED, not yet ACTIVE

    # 4. Human approval, then promotion — through Phase 6's real pipeline.
    approval_service = ApprovalService()
    approval = request_proposal_approval(proposal, approval_service, requester="improvement_agent")
    approval_service.decide(approval.id, reviewer="founder", approved=True, reason="looks good")
    proposal = apply_approval_decision(proposal, approval_service.get(approval.id))
    proposal = mark_promoted(proposal)
    pipeline.stage(skill_id)
    pipeline.promote_to_active(skill_id, approved_by="founder")

    assert proposal.status == ProposalStatus.PROMOTED
    assert registry.get(skill_id).status == SkillLifecycleStatus.ACTIVE


def test_distillation_produces_a_draft_and_core_code_escalation_is_blocked_without_justification():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="research a", output="found a"),
        SuccessfulEpisode(agent_key="researcher", goal="research b", output="found b"),
        SuccessfulEpisode(agent_key="researcher", goal="research c", output="found c"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")
    assert draft.source_episode_count == 3

    with pytest.raises(PrematureCoreCodeChangeError):
        require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, [ImprovementLevel.SKILL_SELECTION])
