from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.skills.candidate_store import (
    InMemorySkillCandidateStore,
    PostgresSkillCandidateStore,
    SkillCandidateStore,
)
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    PostgresSkillImprovementRepository,
    SkillImprovementRepository,
)
from agent.skills.usage_observer import SkillUsageObserver
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.composition.storage_factory import init_plane_storage

_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if not _DB_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_DATABASE_URL="):
                _DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


def test_plane_in_memory_composition_shares_stores() -> None:
    cand_store = InMemorySkillCandidateStore()
    imp_repo = InMemorySkillImprovementRepository(candidate_store=cand_store)
    observer = SkillUsageObserver(imp_repo)

    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        company_client=AsyncMock(spec=CompanyServiceClient),
        model=FakeSDKModel(),
        skill_candidate_store=cand_store,
        skill_improvement_repository=imp_repo,
        skill_usage_observer=observer,
    )

    assert plane.skill_candidate_store is cand_store
    assert plane.skill_improvement_repository is imp_repo
    assert plane.skill_usage_observer is observer


def test_plane_storage_bundle_with_database_url() -> None:
    if not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    bundle = init_plane_storage(database_url=_DB_URL)
    assert isinstance(bundle.skill_candidate_store, PostgresSkillCandidateStore)
    assert isinstance(bundle.skill_improvement_repository, PostgresSkillImprovementRepository)
    assert isinstance(bundle.skill_usage_observer, SkillUsageObserver)
