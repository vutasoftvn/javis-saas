from __future__ import annotations

import pytest

from agent_core.contracts.spec import AgentSpec
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import (
    InMemorySpecRegistryRepository,
    SpecVersionHashConflictError,
)


@pytest.mark.asyncio
async def test_publish_agent_spec_is_immutable_and_idempotent():
    repo = InMemorySpecRegistryRepository()
    spec = AgentSpec(id="test.agent.registry_1", version="1.0.0", instructions="Ban đầu")

    record1 = await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert record1.spec_kind == "agent"
    assert record1.spec_id == "test.agent.registry_1"
    assert record1.version == "1.0.0"
    assert record1.definition_hash == spec.with_hash().definition_hash

    # Publish lại đúng nội dung -> idempotent, không lỗi
    record2 = await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert record2.definition_hash == record1.definition_hash

    # Cùng version nhưng đổi nội dung -> phải reject, không được ghi đè
    changed_spec = AgentSpec(id="test.agent.registry_1", version="1.0.0", instructions="Đã đổi nội dung")
    with pytest.raises(SpecVersionHashConflictError):
        await publish_agent_spec(changed_spec, repository=repo, publisher="tester")

    # Bump version thì publish được bình thường
    v2_spec = AgentSpec(id="test.agent.registry_1", version="2.0.0", instructions="Đã đổi nội dung")
    record_v2 = await publish_agent_spec(v2_spec, repository=repo, publisher="tester")
    assert record_v2.version == "2.0.0"
    assert record_v2.definition_hash != record1.definition_hash

    versions = await repo.list_versions("agent", "test.agent.registry_1")
    assert {v.version for v in versions} == {"1.0.0", "2.0.0"}


@pytest.mark.asyncio
async def test_kernel_run_publishes_spec_to_registry():
    """Wave 3 exit criteria: Run pin đúng version/hash spec đã dùng, spec content
    được lưu bất biến trong registry — có thể resolve lại sau này dù code đổi."""
    from agent_core.contracts.run import RunRequest
    from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient

    repo = InMemoryRunRepository()
    registry = InMemorySpecRegistryRepository()
    kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry, model_client=MockToolLoopModelClient())

    spec = AgentSpec(id="test.agent.kernel_publish_1", version="1.0.0", instructions="Test kernel publish")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "hello"},
    )

    result = await kernel.run(request, spec)

    published = await registry.get("agent", "test.agent.kernel_publish_1", "1.0.0")
    assert published is not None
    assert published.definition_hash == spec.with_hash().definition_hash

    run_rec = await repo.get_run(result.run_id)
    assert run_rec.root_definition_hash == published.definition_hash


from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.registry.publisher import publish_model_policy_spec, publish_prompt_spec


@pytest.mark.asyncio
async def test_publish_prompt_spec_is_immutable_and_idempotent():
    repo = InMemorySpecRegistryRepository()
    spec = PromptSpec(id="test.prompt.registry_1", version="1.0.0", text="Bản đầu")

    record1 = await publish_prompt_spec(spec, repository=repo, publisher="tester")
    assert record1.spec_kind == "prompt"
    assert record1.definition_hash == spec.with_hash().definition_hash

    record2 = await publish_prompt_spec(spec, repository=repo, publisher="tester")
    assert record2.definition_hash == record1.definition_hash

    changed = PromptSpec(id="test.prompt.registry_1", version="1.0.0", text="Đã đổi")
    with pytest.raises(SpecVersionHashConflictError):
        await publish_prompt_spec(changed, repository=repo, publisher="tester")


@pytest.mark.asyncio
async def test_publish_model_policy_spec_is_immutable_and_idempotent():
    repo = InMemorySpecRegistryRepository()
    spec = ModelPolicySpec(id="test.model_policy.registry_1", version="1.0.0", model="deepseek-chat")

    record1 = await publish_model_policy_spec(spec, repository=repo, publisher="tester")
    assert record1.spec_kind == "model_policy"
    assert record1.definition_hash == spec.with_hash().definition_hash

    record2 = await publish_model_policy_spec(spec, repository=repo, publisher="tester")
    assert record2.definition_hash == record1.definition_hash


from agent_core.registry.repository import SpecDependencyMissingError


@pytest.mark.asyncio
async def test_publish_agent_spec_rejects_prompt_ref_not_in_registry():
    repo = InMemorySpecRegistryRepository()
    from agent_core.governance.contracts import PinnedSpecIdentity

    spec = AgentSpec(
        id="test.agent.m2_dep_1",
        version="1.0.0",
        prompt_ref=PinnedSpecIdentity(
            spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="a" * 64
        ),
    )

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert exc_info.value.reason == "not_found"
    assert exc_info.value.dependency_kind == "prompt"


@pytest.mark.asyncio
async def test_publish_agent_spec_rejects_prompt_ref_with_hash_mismatch():
    repo = InMemorySpecRegistryRepository()
    published_prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung thật").with_hash()
    await publish_prompt_spec(published_prompt, repository=repo, publisher="tester")

    from agent_core.governance.contracts import PinnedSpecIdentity

    spec = AgentSpec(
        id="test.agent.m2_dep_2",
        version="1.0.0",
        prompt_ref=PinnedSpecIdentity(
            spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="f" * 64
        ),
    )

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert exc_info.value.reason == "hash_mismatch"


@pytest.mark.asyncio
async def test_publish_agent_spec_succeeds_when_prompt_ref_matches_published_hash():
    repo = InMemorySpecRegistryRepository()
    published_prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung thật").with_hash()
    await publish_prompt_spec(published_prompt, repository=repo, publisher="tester")

    spec = AgentSpec(
        id="test.agent.m2_dep_3",
        version="1.0.0",
        prompt_ref=published_prompt.to_pinned_identity(),
    )

    record = await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert record.spec_kind == "agent"
