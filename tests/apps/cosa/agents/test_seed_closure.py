from __future__ import annotations

import pytest
from agent.contracts.identity import PinnedSkillRef
from agent.contracts.spec import AgentSpec
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository

from apps.cosa.agents import seed as seed_module
from apps.cosa.agents.catalog import RuntimeAgentCatalogEntry
from apps.cosa.agents.specs import COSA_EXECUTIVE_CFO_PROMPT


async def _registry_with_skill(tools: list[str]) -> InMemorySpecRegistryRepository:
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="s.one",
            version="1.0.0",
            definition_hash="h" * 64,
            content={"required_capabilities": tools},
            publisher="test",
        )
    )
    return registry


def _entry(capability_refs: list[str]) -> RuntimeAgentCatalogEntry:
    spec = AgentSpec(
        id="agent.x",
        capability_refs=capability_refs,
        pinned_skills=[PinnedSkillRef(skill_id="s.one", version="1.0.0", definition_hash="h" * 64)],
    )
    return RuntimeAgentCatalogEntry(
        profile_key="x",
        agent_spec=spec,
        prompt_spec=COSA_EXECUTIVE_CFO_PROMPT,
        availability="deployed_not_public",
    )


@pytest.mark.asyncio
async def test_skill_tool_missing_from_capability_registry_is_rejected(monkeypatch):
    monkeypatch.setattr(seed_module, "seeded_entries", lambda: (_entry(["cap.a"]),))
    registry = await _registry_with_skill(["cap.a"])
    with pytest.raises(RuntimeError, match="unregistered=\\['cap.a'\\]"):
        await seed_module._verify_skill_capability_closure(registry, capability_ids=set())


@pytest.mark.asyncio
async def test_skill_tool_outside_agent_capability_refs_is_rejected(monkeypatch):
    monkeypatch.setattr(seed_module, "seeded_entries", lambda: (_entry([]),))
    registry = await _registry_with_skill(["cap.a"])
    with pytest.raises(RuntimeError, match="outside_capability_refs=\\['cap.a'\\]"):
        await seed_module._verify_skill_capability_closure(registry, capability_ids={"cap.a"})


@pytest.mark.asyncio
async def test_pinned_skill_absent_from_registry_is_rejected(monkeypatch):
    monkeypatch.setattr(seed_module, "seeded_entries", lambda: (_entry([]),))
    with pytest.raises(RuntimeError, match="absent from registry"):
        await seed_module._verify_skill_capability_closure(
            InMemorySpecRegistryRepository(), capability_ids=set()
        )


@pytest.mark.asyncio
async def test_closed_skill_passes(monkeypatch):
    monkeypatch.setattr(seed_module, "seeded_entries", lambda: (_entry(["cap.a"]),))
    registry = await _registry_with_skill(["cap.a"])
    await seed_module._verify_skill_capability_closure(registry, capability_ids={"cap.a"})
