from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field

from agentos.improvement.gap_detection import CapabilityGap
from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import score_skill


class ProposalStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"


class ImprovementProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gap: CapabilityGap
    candidate_skill_ids: list[str]
    expected_gain: float
    risk: str
    status: ProposalStatus = ProposalStatus.PROPOSED


def propose_candidates(gap: CapabilityGap, registry: SkillRegistry, *, limit: int = 3) -> ImprovementProposal:
    """Search-skill / evaluate-candidates stage of the self-improvement
    loop (blueprint §34/§35). Ranks every registered skill — regardless
    of lifecycle status, since a VERIFIED-but-not-yet-ACTIVE Phase 6
    supply-chain candidate is a legitimate proposal target — against the
    gap's capability name, reusing the exact same relevance scoring as
    SkillRouter (Phase 4/5).
    """
    scored = [(score_skill(gap.capability, record.manifest), record) for record in registry.list()]
    ranked = sorted((pair for pair in scored if pair[0] > 0), key=lambda pair: pair[0], reverse=True)
    top = ranked[:limit]
    expected_gain = max((score for score, _ in top), default=0.0)
    risk = "low" if top and top[0][1].status == SkillLifecycleStatus.ACTIVE else "medium"
    return ImprovementProposal(
        gap=gap,
        candidate_skill_ids=[record.manifest.metadata.id for _, record in top],
        expected_gain=expected_gain,
        risk=risk,
    )
