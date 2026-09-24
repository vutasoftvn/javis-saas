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

    operations_record = await repo.get("agent", "cosa.agents.operations", "1.3.0")
    finance_record = await repo.get("agent", "cosa.agents.finance", "1.2.0")
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

    record = await repo.get("agent", "cosa.agents.operations", "1.3.0")
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


def test_catalog_invariants():
    from apps.cosa.agents.catalog import (
        CATALOG_BY_PROFILE,
        PUBLIC_PROFILE_KEYS,
        deployed_entries,
        seeded_entries,
    )

    assert "founder_assistant" in PUBLIC_PROFILE_KEYS
    assert CATALOG_BY_PROFILE["founder_assistant"].agent_spec.id == "cosa.agents.founder_assistant"
    assert CATALOG_BY_PROFILE["cto"].agent_spec.id == "cosa.executive.cto"

    seeded_agent_ids = {entry.agent_spec.id for entry in seeded_entries()}
    seeded_prompt_ids = {entry.prompt_spec.id for entry in seeded_entries()}

    deployed = deployed_entries()
    assert {entry.agent_spec.id for entry in deployed} <= seeded_agent_ids
    assert {entry.prompt_spec.id for entry in deployed} <= seeded_prompt_ids


def _test_capability_registry():
    from unittest.mock import AsyncMock

    from agent.conversations.repository import InMemoryConversationRepository
    from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent.registry.repository import InMemorySpecRegistryRepository
    from agent.runs.repository import InMemoryRunRepository
    from agent.runs.stream_events import InMemoryRunStreamEventRepository
    from agent_testkit.fake_sdk_model import FakeSDKModel

    from apps.cosa.capabilities.client import CompanyServiceClient
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane
    from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client

    plane = build_cosa_agent_plane(
        company_client=AsyncMock(spec=CompanyServiceClient),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    return plane.capability_registry


@pytest.mark.asyncio
async def test_seed_cosa_runtime_specs_resolves_all_public_profiles():
    from agent.registry.resolver import SpecResolver

    from apps.cosa.agents.catalog import public_profile_specs
    from apps.cosa.agents.seed import seed_cosa_runtime_specs

    repo = InMemorySpecRegistryRepository()
    cap_registry = _test_capability_registry()

    await seed_cosa_runtime_specs(spec_registry=repo, capability_registry=cap_registry)

    resolver = SpecResolver(repo)
    for _profile_key, agent_spec in public_profile_specs().items():
        content = await resolver.resolve_exact(
            "agent", agent_spec.id, agent_spec.version, agent_spec.compute_hash()
        )
        assert content is not None
        assert content["id"] == agent_spec.id


@pytest.mark.asyncio
async def test_seed_cosa_runtime_specs_fails_closed_when_deployed_entry_missing():
    from apps.cosa.agents.catalog import deployed_entries
    from apps.cosa.agents.seed import seed_cosa_runtime_specs

    repo = InMemorySpecRegistryRepository()
    cap_registry = _test_capability_registry()

    await seed_cosa_runtime_specs(spec_registry=repo, capability_registry=cap_registry)

    # Delete one deployed spec record from registry
    first_deployed = deployed_entries()[0]
    repo._by_version.pop(("agent", first_deployed.agent_spec.id, first_deployed.agent_spec.version), None)

    # Re-running verification should fail closed
    with pytest.raises(RuntimeError, match="not found in registry"):
        for entry in deployed_entries():
            record = await repo.get("agent", entry.agent_spec.id, entry.agent_spec.version)
            if record is None:
                raise RuntimeError(
                    f"Deployed agent spec {entry.agent_spec.id}:{entry.agent_spec.version} "
                    "not found in registry after seeding"
                )

