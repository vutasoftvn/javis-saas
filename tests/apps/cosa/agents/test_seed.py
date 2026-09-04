from __future__ import annotations

import pytest
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import (
    InMemorySpecRegistryRepository,
    SpecVersionHashConflictError,
)

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.agents.specs import (
    COSA_DEPLOYED_AGENT_SPECS,
    COSA_FINANCE_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
)


@pytest.mark.asyncio
async def test_seed_publishes_both_agent_specs():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    operations_record = await repo.get("agent", "cosa.agents.operations", "1.2.0")
    finance_record = await repo.get("agent", "cosa.agents.finance", "1.1.0")
    assert operations_record is not None
    assert operations_record.definition_hash == COSA_OPERATIONS_AGENT_SPEC.compute_hash()
    assert finance_record is not None
    assert finance_record.definition_hash == COSA_FINANCE_AGENT_SPEC.compute_hash()


@pytest.mark.asyncio
async def test_seed_publishes_prompt_and_model_policy_dependencies_first():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    prompt_record = await repo.get("prompt", "cosa.agents.operations.prompt", "1.0.0")
    policy_record = await repo.get("model_policy", "cosa.model_policy.default", "1.0.0")
    assert prompt_record is not None
    assert policy_record is not None


@pytest.mark.asyncio
async def test_seed_is_idempotent_when_called_twice():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)
    await seed_cosa_agent_specs(repo)  # không raise SpecVersionHashConflictError

    record = await repo.get("agent", "cosa.agents.operations", "1.2.0")
    assert record is not None


@pytest.mark.asyncio
async def test_seed_fails_closed_on_same_version_stale_agent_content():
    repo = InMemorySpecRegistryRepository()
    stale_content = COSA_OPERATIONS_AGENT_SPEC.model_dump(
        mode="json", exclude={"model_input_capability_ref"}
    )
    await repo.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=COSA_OPERATIONS_AGENT_SPEC.id,
            version=COSA_OPERATIONS_AGENT_SPEC.version,
            definition_hash="stale-hash-without-model-input-scope",
            content=stale_content,
            status="published",
        )
    )

    with pytest.raises(SpecVersionHashConflictError):
        await seed_cosa_agent_specs(repo)


@pytest.mark.asyncio
async def test_seed_publishes_every_deployed_agent_spec():
    """COSA_DEPLOYED_AGENT_SPECS (dùng bởi seed_cosa_runtime_specs để verify
    pinned_skills) phải tương ứng đúng với những AgentSpec mà
    seed_cosa_agent_specs() thực sự publish — tránh lệch giữa 2 danh sách."""
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    for agent_spec in COSA_DEPLOYED_AGENT_SPECS:
        record = await repo.get("agent", agent_spec.id, agent_spec.version)
        assert record is not None
        assert record.definition_hash == agent_spec.compute_hash()
