import pytest

from packages.agent.skills.candidate_store import SkillFeedbackRecord
from packages.agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    SkillUsageObservation,
)


def make_observation(*, project_id: str, manifest_hash: str) -> SkillUsageObservation:
    return SkillUsageObservation(
        workspace_id="ws-1",
        run_id="run-1",
        skill_id="skill-1",
        skill_version="1.0.0",
        definition_hash="sha256:skillhash",
        root_spec_id="root-1",
        root_definition_hash="sha256:roothash",
        project_id=project_id,
        manifest_hash=manifest_hash,
    )


def make_feedback(*, project_id: str, manifest_hash: str) -> SkillFeedbackRecord:
    return SkillFeedbackRecord(
        workspace_id="ws-1",
        run_id="run-1",
        skill_id="skill-1",
        project_id=project_id,
        manifest_hash=manifest_hash,
    )


@pytest.mark.asyncio
async def test_feedback_requires_exact_project_run_and_manifest_observation():
    repo = InMemorySkillImprovementRepository()
    await repo.record_resolved_skill_use(make_observation(project_id="p-1", manifest_hash="m-1"))

    # Different project -> must raise ValueError with "No observation"
    with pytest.raises(ValueError, match="No observation"):
        await repo.record_feedback_and_maybe_enqueue(
            feedback=make_feedback(project_id="p-2", manifest_hash="m-1"),
            policy=None,
        )

    # Different manifest_hash -> must raise ValueError with "No observation"
    with pytest.raises(ValueError, match="No observation"):
        await repo.record_feedback_and_maybe_enqueue(
            feedback=make_feedback(project_id="p-1", manifest_hash="m-2"),
            policy=None,
        )

    # Matching project and manifest -> success
    result = await repo.record_feedback_and_maybe_enqueue(
        feedback=make_feedback(project_id="p-1", manifest_hash="m-1"),
        policy=None,
    )
    assert result is not None
