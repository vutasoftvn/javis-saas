from __future__ import annotations

import pytest

pytest.importorskip("agents")

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.skills.contracts import PinnedSkillRef, SkillSpec
from agent.registry.publisher import publish_skill_spec
from agent.skills.usage_observer import InMemorySkillUsageObserver
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response


@pytest.mark.asyncio
async def test_real_kernel_records_exact_resolved_pin_only_after_run_record_exists() -> None:
    repo = InMemoryRunRepository()
    spec_registry = InMemorySpecRegistryRepository()
    observer = InMemorySkillUsageObserver()
    model = FakeSDKModel(responses=[text_response("Hello from skill test")])

    # Publish a skill in registry
    skill = SkillSpec(
        id="brief",
        version="1.0.0",
        instructions="Draft clear briefs",
    )
    pub_record = await publish_skill_spec(skill, repository=spec_registry, publisher="test")
    definition_hash = pub_record.definition_hash

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        spec_registry=spec_registry,
        model=model,
        skill_usage_observer=observer,
    )

    spec = AgentSpec(
        id="analyst",
        version="1.0.0",
        instructions="Analyze data",
        pinned_skills=[
            PinnedSkillRef(
                skill_id="brief",
                version="1.0.0",
                definition_hash=definition_hash,
            )
        ],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()

    request = RunRequest(
        input={"prompt": "test skill observation"},
        principal="user:test",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_obs",
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED

    run_ids = await observer.run_ids()
    assert result.run_id in run_ids

    identities = await observer.identities(result.run_id)
    assert identities == [("brief", "1.0.0", definition_hash)]

    # Check that RunRecord exists in repo
    run_record = await repo.get_run(result.run_id)
    assert run_record is not None
    assert run_record.run_id == result.run_id


@pytest.mark.asyncio
async def test_observer_does_not_record_when_pin_resolution_fails() -> None:
    repo = InMemoryRunRepository()
    spec_registry = InMemorySpecRegistryRepository()
    observer = InMemorySkillUsageObserver()
    model = FakeSDKModel(responses=[text_response("Hello")])

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        spec_registry=spec_registry,
        model=model,
        skill_usage_observer=observer,
    )

    # Agent with non-existent pinned skill
    spec = AgentSpec(
        id="analyst_broken",
        version="1.0.0",
        instructions="Analyze data",
        pinned_skills=[
            PinnedSkillRef(
                skill_id="nonexistent_skill",
                version="1.0.0",
                definition_hash="sha256:missing",
            )
        ],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()

    request = RunRequest(
        input={"prompt": "fail test"},
        principal="user:test",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_obs",
    )

    with pytest.raises(Exception):
        await kernel.run(request, spec)

    assert await observer.all() == []
