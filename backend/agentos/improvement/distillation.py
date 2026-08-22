from __future__ import annotations

from pydantic import BaseModel

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

MIN_EPISODES_TO_DISTILL = 3


class SuccessfulEpisode(BaseModel):
    agent_key: str
    goal: str
    output: str


class DistilledSkillDraft(BaseModel):
    manifest: SkillManifest
    instructions_markdown: str
    source_episode_count: int


class NotEnoughEvidenceError(Exception):
    def __init__(self, agent_key: str, count: int) -> None:
        super().__init__(
            f"Only {count} successful episode(s) for {agent_key!r} — need at least "
            f"{MIN_EPISODES_TO_DISTILL} to distill a skill (blueprint §37)"
        )
        self.agent_key = agent_key
        self.count = count


def distill_skill(
    agent_key: str, episodes: list[SuccessfulEpisode], *, skill_id: str, domain: str
) -> DistilledSkillDraft:
    """Skill Distillation, draft stage only (blueprint §37): successful
    traces -> detect repeated pattern -> extract procedure -> draft
    SKILL.md. Stops before sandbox / human approval / publish — this
    function never writes to skillpacks/ or touches
    agentos.skills.supply_chain; a human reviews the draft, and
    publishing it (if approved) goes through the existing Phase 6
    SupplyChainPipeline rather than a bespoke publish path invented here.
    Trust tier starts at T2 (not auto-trusted T0) and quality.eval_score
    at 0.0, since the draft itself hasn't been evaluated yet — only its
    source episodes succeeded.
    """
    matching = [episode for episode in episodes if episode.agent_key == agent_key]
    if len(matching) < MIN_EPISODES_TO_DISTILL:
        raise NotEnoughEvidenceError(agent_key, len(matching))

    steps = "\n".join(f"{i + 1}. {episode.output}" for i, episode in enumerate(matching))
    instructions = f"# {skill_id}\n\nDistilled from {len(matching)} successful runs by `{agent_key}`:\n\n{steps}\n"

    manifest = SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(
            id=skill_id,
            name=skill_id,
            version="0.1.0",
            description=f"Distilled from {len(matching)} successful {agent_key} runs",
        ),
        publisher=SkillPublisher(name="internal", type="distilled"),
        source=SkillSource(type="local", path=f"skillpacks/distilled/{skill_id}"),
        capability=SkillCapability(domain=domain, category="distilled", intents=[]),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=False),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=TrustTier.T2, security_scan="pending"),
        quality=SkillQuality(eval_score=0.0, success_rate=0.0),
    )
    return DistilledSkillDraft(
        manifest=manifest, instructions_markdown=instructions, source_episode_count=len(matching)
    )
