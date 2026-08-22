import pytest

from agentos.improvement.distillation import NotEnoughEvidenceError, SuccessfulEpisode, distill_skill
from agentos.skills.manifest import TrustTier


def test_distill_skill_raises_when_not_enough_episodes():
    episodes = [SuccessfulEpisode(agent_key="researcher", goal="research acme", output="found acme details")]
    with pytest.raises(NotEnoughEvidenceError):
        distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")


def test_distill_skill_produces_a_draft_from_matching_episodes():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="research acme", output="found acme details"),
        SuccessfulEpisode(agent_key="researcher", goal="research beta co", output="found beta co details"),
        SuccessfulEpisode(agent_key="researcher", goal="research gamma inc", output="found gamma inc details"),
        SuccessfulEpisode(agent_key="other_agent", goal="unrelated", output="unrelated output"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")

    assert draft.source_episode_count == 3
    assert draft.manifest.metadata.id == "core.researcher-pattern"
    assert draft.manifest.trust.tier == TrustTier.T2
    assert draft.manifest.quality.eval_score == 0.0
    assert "found acme details" in draft.instructions_markdown
    assert "found beta co details" in draft.instructions_markdown


def test_distill_skill_ignores_episodes_from_other_agents():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="a", output="a-out"),
        SuccessfulEpisode(agent_key="researcher", goal="b", output="b-out"),
        SuccessfulEpisode(agent_key="researcher", goal="c", output="c-out"),
        SuccessfulEpisode(agent_key="other_agent", goal="d", output="d-out"),
        SuccessfulEpisode(agent_key="other_agent", goal="e", output="e-out"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")

    assert draft.source_episode_count == 3
    assert "d-out" not in draft.instructions_markdown
