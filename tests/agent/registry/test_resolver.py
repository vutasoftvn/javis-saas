from __future__ import annotations

import pytest

from agent.contracts.model_policy import ModelPolicySpec
from agent.contracts.prompt import PromptSpec
from agent.contracts.spec import AgentSpec
from agent.registry.publisher import publish_agent_spec, publish_model_policy_spec, publish_prompt_spec
from agent.registry.repository import InMemorySpecRegistryRepository, SpecDependencyMissingError
from agent.registry.resolver import SpecResolver


async def _publish_full_agent_spec(repo) -> AgentSpec:
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung prompt").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    policy = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-chat").with_hash()
    await publish_model_policy_spec(policy, repository=repo, publisher="tester")

    spec = AgentSpec(
        id="test.agent.resolver_1",
        version="1.0.0",
        model_input_capability_ref="model.input.direct-user-message",
        prompt_ref=prompt.to_pinned_identity(),
        model_policy_ref=policy.to_pinned_identity(),
    )
    await publish_agent_spec(spec, repository=repo, publisher="tester")
    return spec.with_hash()


@pytest.mark.asyncio
async def test_resolve_exact_returns_content_when_hash_matches():
    repo = InMemorySpecRegistryRepository()
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    content = await resolver.resolve_exact("prompt", "cofounder/system", "1", prompt.definition_hash)

    assert content["text"] == "Nội dung"


@pytest.mark.asyncio
async def test_resolve_exact_raises_when_not_found():
    repo = InMemorySpecRegistryRepository()
    resolver = SpecResolver(repository=repo)

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await resolver.resolve_exact("prompt", "does.not.exist", "1", "a" * 64)
    assert exc_info.value.reason == "not_found"


@pytest.mark.asyncio
async def test_resolve_exact_raises_when_hash_mismatch():
    repo = InMemorySpecRegistryRepository()
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await resolver.resolve_exact("prompt", "cofounder/system", "1", "f" * 64)
    assert exc_info.value.reason == "hash_mismatch"


@pytest.mark.asyncio
async def test_resolve_agent_spec_dependencies_returns_resolved_content_and_edges():
    repo = InMemorySpecRegistryRepository()
    spec = await _publish_full_agent_spec(repo)
    resolver = SpecResolver(repository=repo)

    resolution = await resolver.resolve_agent_spec_dependencies(spec)

    assert resolution.agent_content["id"] == "test.agent.resolver_1"
    assert resolution.prompt_content["text"] == "Nội dung prompt"
    assert resolution.model_policy_content["model"] == "deepseek-chat"
    relations = {edge.relation for edge in resolution.edges}
    assert relations == {"uses_prompt", "uses_model_policy"}
    owners = {edge.owner.spec_id for edge in resolution.edges}
    assert owners == {"test.agent.resolver_1"}


@pytest.mark.asyncio
async def test_resolve_agent_spec_dependencies_returns_no_edges_when_no_refs_pinned():
    repo = InMemorySpecRegistryRepository()
    spec = AgentSpec(
        id="test.agent.resolver_2",
        version="1.0.0",
        model_input_capability_ref="model.input.direct-user-message",
    )
    await publish_agent_spec(spec, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    resolution = await resolver.resolve_agent_spec_dependencies(spec.with_hash())

    assert resolution.prompt_content is None
    assert resolution.model_policy_content is None
    assert resolution.edges == ()
