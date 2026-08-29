"""Xác nhận build_cosa_agent_plane() không còn âm thầm mặc định
InMemoryRunRepository/InMemoryConversationRepository/InMemorySpecRegistryRepository/
InMemoryGovernanceStateStore cho production — đây là gap DB_FINAL_CUTOVER.md §8.1
đã audit xác nhận, mở rộng sang conversation substrate (Wave 1), spec registry
(Wave 3), và governance accumulator durability (gap phát hiện ở Wave 2, sửa sau
Wave 11) theo COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md."""
from __future__ import annotations

import os

import pytest

from agent_testkit.fake_sdk_model import FakeSDKModel


def test_build_cosa_agent_plane_uses_postgres_when_database_url_given():
    from agent_core.conversations.repository import PostgresConversationRepository
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
    from agent_core.registry.repository import PostgresSpecRegistryRepository
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(database_url="postgresql+asyncpg://x:x@localhost/x", model=FakeSDKModel())

    assert isinstance(plane.repository, PostgresRunRepository)
    assert isinstance(plane.conversation_repository, PostgresConversationRepository)
    assert isinstance(plane.spec_registry, PostgresSpecRegistryRepository)
    assert isinstance(plane.governance_store, PostgresGovernanceStateStore)


def test_build_cosa_agent_plane_uses_postgres_from_agent_database_url(monkeypatch):
    from agent_core.conversations.repository import PostgresConversationRepository
    from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
    from agent_core.registry.repository import PostgresSpecRegistryRepository
    from agent_core.runs.repository import PostgresRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    plane = build_cosa_agent_plane(model=FakeSDKModel())

    assert isinstance(plane.repository, PostgresRunRepository)
    assert isinstance(plane.conversation_repository, PostgresConversationRepository)
    assert isinstance(plane.spec_registry, PostgresSpecRegistryRepository)
    assert isinstance(plane.governance_store, PostgresGovernanceStateStore)


def test_build_cosa_agent_plane_raises_without_database_url_or_explicit_repository(monkeypatch):
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"):
        build_cosa_agent_plane()


def test_build_cosa_agent_plane_does_not_fall_back_to_legacy_agent_core_url(monkeypatch):
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENT_CORE_DATABASE_URL", "postgresql+asyncpg://legacy:legacy@localhost/agent_core")

    with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"):
        build_cosa_agent_plane()


def test_build_cosa_agent_plane_raises_without_database_url_even_with_explicit_run_repository_only(monkeypatch):
    """`repository=` một mình không đủ để bỏ qua yêu cầu conversation_repository —
    mỗi repository độc lập nhau, mỗi cái phải được cấp tường minh hoặc suy ra từ cùng
    1 AGENT_CORE_DATABASE_URL."""
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="conversation_repository"):
        build_cosa_agent_plane(repository=InMemoryRunRepository())


def test_build_cosa_agent_plane_raises_without_database_url_even_with_run_and_conversation_repository_only(monkeypatch):
    """Tương tự, `spec_registry=` cũng phải được cấp tường minh hoặc suy ra từ
    AGENT_CORE_DATABASE_URL — không đủ nếu chỉ có repository + conversation_repository."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="spec_registry"):
        build_cosa_agent_plane(
            repository=InMemoryRunRepository(),
            conversation_repository=InMemoryConversationRepository(),
        )


def test_build_cosa_agent_plane_raises_without_database_url_even_with_repository_conversation_and_spec_registry_only(monkeypatch):
    """Tương tự, `governance_store=` cũng phải được cấp tường minh hoặc suy ra từ
    AGENT_CORE_DATABASE_URL — CapabilityGateway governance accumulator phải durable
    (gap phát hiện Wave 2, sửa sau khi hoàn thành Wave 11)."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="governance_store"):
        build_cosa_agent_plane(
            repository=InMemoryRunRepository(),
            conversation_repository=InMemoryConversationRepository(),
            spec_registry=InMemorySpecRegistryRepository(),
        )


def test_build_cosa_agent_plane_raises_without_database_url_even_with_governance_store_only(monkeypatch):
    """Tương tự, `stream_event_repository=` cũng phải được cấp tường minh hoặc suy
    ra từ AGENT_CORE_DATABASE_URL — SSE replay phải durable, không rơi về
    in-memory `_history` (Phase 5, COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_
    2026-08-25.md §7/§29.6)."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="stream_event_repository"):
        build_cosa_agent_plane(
            repository=InMemoryRunRepository(),
            conversation_repository=InMemoryConversationRepository(),
            spec_registry=InMemorySpecRegistryRepository(),
            governance_store=InMemoryGovernanceStateStore(),
        )


def test_build_cosa_agent_plane_still_accepts_explicit_in_memory_repositories_for_tests():
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    explicit_repo = InMemoryRunRepository()
    explicit_conv_repo = InMemoryConversationRepository()
    explicit_registry_repo = InMemorySpecRegistryRepository()
    explicit_gov_store = InMemoryGovernanceStateStore()
    explicit_stream_repo = InMemoryRunStreamEventRepository()
    plane = build_cosa_agent_plane(
        repository=explicit_repo,
        conversation_repository=explicit_conv_repo,
        spec_registry=explicit_registry_repo,
        governance_store=explicit_gov_store,
        stream_event_repository=explicit_stream_repo,
        model=FakeSDKModel(),
    )

    assert plane.repository is explicit_repo
    assert plane.conversation_repository is explicit_conv_repo
    assert plane.spec_registry is explicit_registry_repo
    assert plane.governance_store is explicit_gov_store
    assert plane.stream_event_repository is explicit_stream_repo


def test_build_cosa_agent_plane_defaults_to_real_openai_agents_sdk_kernel():
    """Runtime mặc định là RealOpenAIAgentsSDKKernel (agents.Runner thật) —
    ADR-RUNTIME-002 (2026-08-25) chốt OpenAI Agents SDK làm primary execution
    runtime; trước Phase 1 (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-
    08-25.md) mặc định này trỏ nhầm vào ManualToolLoopKernel (khi đó còn tên
    OpenAIAgentsKernel) — một manual reasoning loop, không phải SDK thật."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    assert isinstance(plane.kernel, RealOpenAIAgentsSDKKernel)


def test_build_cosa_agent_plane_can_opt_into_manual_tool_loop_kernel():
    """`runtime="manual_tool_loop"` phải wire đúng ManualToolLoopKernel —
    opt-in tường minh, không phải default (thay thế test cũ đã khẳng định
    nhầm đây là default trước Phase 1)."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        runtime="manual_tool_loop",
    )
    assert isinstance(plane.kernel, ManualToolLoopKernel)


def test_build_cosa_agent_plane_can_opt_into_langchain_kernel():
    """`runtime="langchain"` phải wire đúng LangChainKernel — opt-in tường minh,
    không phải default. langchain-core là optional adapter dependency (ADR-
    RUNTIME-002) — skip nếu chưa cài (CI job `apps-cosa` không cài, Phase 6
    CI Green Gate), thay vì fail cứng."""
    pytest.importorskip("langchain_core")

    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from agent_integrations.langchain.kernel import LangChainKernel
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        runtime="langchain",
    )
    assert isinstance(plane.kernel, LangChainKernel)


def test_build_cosa_agent_plane_rejects_unknown_runtime():
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    with pytest.raises(ValueError, match="Unknown runtime"):
        build_cosa_agent_plane(
            repository=InMemoryRunRepository(),
            conversation_repository=InMemoryConversationRepository(),
            spec_registry=InMemorySpecRegistryRepository(),
            governance_store=InMemoryGovernanceStateStore(),
            stream_event_repository=InMemoryRunStreamEventRepository(),
            runtime="not_a_real_runtime",
        )


def test_build_cosa_agent_plane_wires_governance_store_into_gateway():
    """Gateway phải nhận ĐÚNG governance_store instance đã truyền vào — không tự
    tạo InMemoryGovernanceStateStore riêng bên trong (đó là chính bug Wave 2 đã sửa)."""
    from agent_core.conversations.repository import InMemoryConversationRepository
    from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
    from agent_core.registry.repository import InMemorySpecRegistryRepository
    from agent_core.runs.repository import InMemoryRunRepository
    from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
    from apps.cosa.composition.agent_plane import build_cosa_agent_plane

    explicit_gov_store = InMemoryGovernanceStateStore()
    plane = build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=explicit_gov_store,
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    assert plane.gateway._governance_store is explicit_gov_store
