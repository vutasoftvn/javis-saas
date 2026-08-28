from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.identity import PinnedSkillRef
from agent_core.registry.publisher import publish_skill_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.skills.contracts import SkillSpec, SkillStatus
from agent_core.skills.resolver import SkillResolver
from apps.cosa.agents.specs import COSA_MARKETING_AGENT_SPEC
from apps.cosa.api.skill_registry_routes import sync_built_in_skills


@pytest.mark.asyncio
async def test_resolve_marketing_agent_pinned_skills():
    """Verify that all pinned skills in COSA_MARKETING_AGENT_SPEC resolve cleanly against synced spec registry."""
    repo = InMemorySpecRegistryRepository()
    plane = MagicMock()
    plane.spec_registry = repo

    # Sync all built-in skills
    await sync_built_in_skills(MagicMock(), None, None, plane)

    resolver = SkillResolver(repo)

    # 1. Resolve all pinned skills of COSA_MARKETING_AGENT_SPEC
    resolved_skills = await resolver.resolve(COSA_MARKETING_AGENT_SPEC.pinned_skills)
    assert len(resolved_skills) == len(COSA_MARKETING_AGENT_SPEC.pinned_skills)
    resolved_ids = {s.id for s in resolved_skills}
    assert "marketing.positioning" in resolved_ids
    assert "marketing.copywriting" in resolved_ids
    assert "marketing.market-research" in resolved_ids
    assert "research.deep-research" in resolved_ids
    assert "strategy.competitor-profiling" in resolved_ids


@pytest.mark.asyncio
async def test_resolve_missing_skill_raises_error():
    """Verify that resolving an un-published skill raises SKILL_RESOLUTION_ERROR."""
    repo = InMemorySpecRegistryRepository()
    resolver = SkillResolver(repo)

    missing_pin = PinnedSkillRef(
        skill_id="nonexistent.skill",
        version="1.0.0",
        definition_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )

    with pytest.raises(AgentRuntimeError) as exc_info:
        await resolver.resolve([missing_pin])
    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR


@pytest.mark.asyncio
async def test_resolve_hash_mismatch_raises_error():
    """Verify that resolving a skill with mismatched definition_hash raises SKILL_RESOLUTION_ERROR."""
    repo = InMemorySpecRegistryRepository()
    spec = SkillSpec(
        id="test.sample-skill",
        version="1.0.0",
        name="Sample Skill",
        instructions="Do sample tasks.",
        status=SkillStatus.PUBLISHED,
    )
    published = await publish_skill_spec(spec, repository=repo, publisher="test")

    resolver = SkillResolver(repo)

    # Mismatched hash
    tampered_pin = PinnedSkillRef(
        skill_id="test.sample-skill",
        version="1.0.0",
        definition_hash="tampered_hash_value_99999",
    )

    with pytest.raises(AgentRuntimeError) as exc_info:
        await resolver.resolve([tampered_pin])
    assert exc_info.value.code == RuntimeErrorCode.SKILL_RESOLUTION_ERROR
