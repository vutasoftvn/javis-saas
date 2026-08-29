import pytest

from apps.cosa.agents.registry_loader import load_registered_agent_spec
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from agent_core.registry.repository import InMemorySpecRegistryRepository, PublishedSpecRecord


@pytest.mark.asyncio
async def test_loads_registered_agent_spec_as_typed_model():
    repo = InMemorySpecRegistryRepository()
    content = COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json")
    await repo.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id,
            version="1.0.0",
            definition_hash="h1",
            content=content,
            status="published",
        )
    )
    spec, reason = await load_registered_agent_spec(
        repo, COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id, version="1.0.0"
    )
    assert reason is None
    assert spec is not None
    assert spec.id == COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id
    assert "engagement.thread.read" in spec.capability_refs


@pytest.mark.asyncio
async def test_missing_record_returns_reason_code():
    repo = InMemorySpecRegistryRepository()
    spec, reason = await load_registered_agent_spec(repo, "cosa.agents.nope", version="1.0.0")
    assert spec is None
    assert reason == "agent_spec_not_registered"


@pytest.mark.asyncio
async def test_invalid_content_returns_reason_code():
    repo = InMemorySpecRegistryRepository()
    await repo.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id="cosa.agents.broken",
            version="1.0.0",
            definition_hash="h1",
            content={"not": "an agent spec"},
            status="published",
        )
    )
    spec, reason = await load_registered_agent_spec(repo, "cosa.agents.broken", version="1.0.0")
    assert spec is None
    assert reason == "agent_spec_content_invalid"
