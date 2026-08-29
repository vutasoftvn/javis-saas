"""Closeout Task 2: build_cosa_agent_plane() phải dựng MemoryService +
KnowledgeIngestionService production (Postgres-backed) — không âm thầm
in-memory — và expose chúng trên CosaAgentPlane."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.memory.service import MemoryService
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


def _base_kwargs():
    return dict(
        company_client=AsyncMock(spec=CompanyServiceClient),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


def test_no_db_no_injection_falls_back_to_in_memory_backed_services(monkeypatch):
    # Không DB + không inject → in-memory (mirror art_repo). Production không
    # bao giờ tới đây vì run/conv/registry repo đã hard-fail khi thiếu DB.
    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)
    plane = build_cosa_agent_plane(**_base_kwargs())
    assert isinstance(plane.memory_service, MemoryService)
    assert isinstance(plane.knowledge_ingestion_service, KnowledgeIngestionService)


def test_memory_for_production_still_hard_fails_without_db(monkeypatch):
    # Guard P1 Task 1 vẫn nguyên: đường production tường minh fail-fast.
    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"):
        MemoryService.for_production()


def test_injected_services_are_exposed_on_plane():
    mem = MemoryService.in_memory()
    kis = KnowledgeIngestionService(InMemoryKnowledgeStore())
    plane = build_cosa_agent_plane(
        **_base_kwargs(),
        memory_service=mem,
        knowledge_ingestion_service=kis,
    )
    assert plane.memory_service is mem
    assert plane.knowledge_ingestion_service is kis
