from __future__ import annotations

import uuid
import pytest

from agent.contracts.spec import AgentSpec
from agent.runs.models import RunRecord, RunStatus
from agent.skills.contracts import PinnedSkillRef, SkillSpec
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    SkillUsageObservation,
)
from agent.skills.usage_observer import InMemorySkillUsageObserver, SkillUsageObserver


def _make_run(workspace_id: str = "ws-1", run_id: str = "run-1") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        workspace_id=workspace_id,
        principal="user:test",
        root_executable_id="agent-1",
        root_executable_version="1.0.0",
        root_definition_hash="sha256:root",
        status=RunStatus.RUNNING,
    )


@pytest.mark.asyncio
async def test_observer_records_exact_resolved_pins() -> None:
    repo = InMemorySkillImprovementRepository()
    observer = InMemorySkillUsageObserver(repo)

    run = _make_run()
    spec = AgentSpec(id="agent-1", version="1.0.0", definition_hash="sha256:root")
    resolved_skills = [
        SkillSpec(id="brief", version="1.0.0", definition_hash="sha256:brief_hash", instructions="Write brief"),
        SkillSpec(id="critique", version="2.0.0", definition_hash="sha256:critique_hash", instructions="Critique"),
    ]

    obs = await observer.record_resolved_pins(run, spec, resolved_skills)
    assert len(obs) == 2
    assert obs[0].skill_id == "brief"
    assert obs[0].definition_hash == "sha256:brief_hash"
    assert obs[1].skill_id == "critique"
    assert obs[1].definition_hash == "sha256:critique_hash"

    # Verify repository has observations
    saved = await repo.get_usage_observations("ws-1", "run-1")
    assert len(saved) == 2


@pytest.mark.asyncio
async def test_observer_duplicate_call_is_idempotent() -> None:
    repo = InMemorySkillImprovementRepository()
    observer = InMemorySkillUsageObserver(repo)

    run = _make_run()
    spec = AgentSpec(id="agent-1", version="1.0.0")
    skills = [SkillSpec(id="brief", version="1.0.0", definition_hash="sha256:brief")]

    await observer.record_resolved_pins(run, spec, skills)
    await observer.record_resolved_pins(run, spec, skills)

    # Repository must only have 1 unique observation for (run, skill, version, hash)
    saved = await repo.get_usage_observations("ws-1", "run-1")
    assert len(saved) == 1
