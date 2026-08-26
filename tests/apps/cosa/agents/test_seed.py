from __future__ import annotations

import pytest

from agent_core.registry.repository import InMemorySpecRegistryRepository
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC


@pytest.mark.asyncio
async def test_seed_publishes_both_agent_specs():
    repo = InMemorySpecRegistryRepository()

    await seed_cosa_agent_specs(repo)

    operations_record = await repo.get("agent", "cosa.agents.operations", "1.0.0")
    finance_record = await repo.get("agent", "cosa.agents.finance", "1.0.0")
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

    record = await repo.get("agent", "cosa.agents.operations", "1.0.0")
    assert record is not None
