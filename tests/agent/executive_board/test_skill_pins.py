from __future__ import annotations

import pytest

from agent.executive_board.models import ExecutiveBoardInputError
from agent.executive_board.skill_pins import parse_skill_pin_ref, resolve_role_pin_skills
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository


def test_parse_skill_pin_ref_converts_slash_to_dot():
    skill_id, version = parse_skill_pin_ref("skillpack:executive/cfo-advisor@1.0.0")
    assert skill_id == "executive.cfo-advisor"
    assert version == "1.0.0"


def test_parse_skill_pin_ref_rejects_unknown_prefix():
    with pytest.raises(ExecutiveBoardInputError, match="UNSUPPORTED_SKILL_PIN_FORMAT"):
        parse_skill_pin_ref("executive/cfo-advisor@1.0.0")


@pytest.mark.asyncio
async def test_resolve_role_pin_skills_returns_pinned_ref_with_real_hash():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.cfo-advisor",
            version="1.0.0",
            definition_hash="abc123hash",
            content={"id": "executive.cfo-advisor", "version": "1.0.0", "instructions": "..."},
            publisher="cosa_built_in",
        )
    )

    refs = await resolve_role_pin_skills(("skillpack:executive/cfo-advisor@1.0.0",), registry)

    assert len(refs) == 1
    assert refs[0].skill_id == "executive.cfo-advisor"
    assert refs[0].version == "1.0.0"
    assert refs[0].definition_hash == "abc123hash"


@pytest.mark.asyncio
async def test_resolve_role_pin_skills_raises_when_not_published():
    registry = InMemorySpecRegistryRepository()
    with pytest.raises(ExecutiveBoardInputError, match="SKILL_PIN_NOT_PUBLISHED"):
        await resolve_role_pin_skills(("skillpack:executive/cco-advisor@1.0.0",), registry)
