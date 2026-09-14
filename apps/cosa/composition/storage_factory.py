from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agent.artifacts import (
    ArtifactRepository,
    InMemoryArtifactRepository,
    PostgresArtifactRepository,
)
from agent.capabilities.web_search import (
    InMemoryWebSearchBudgetStore,
    PostgresWebSearchBudgetStore,
    WebSearchBudgetStore,
)
from agent.conversations.repository import (
    ConversationRepository,
    PostgresConversationRepository,
)
from agent.governance.providers.postgres import PostgresGovernanceStateStore
from agent.governance.store import GovernanceStateStore
from agent.knowledge.snapshot_repository import (
    InMemoryKnowledgeSnapshotRepository,
    KnowledgeSnapshotRepository,
    PostgresKnowledgeSnapshotRepository,
)
from agent.project_activity.repository import (
    InMemoryProjectActivityRepository,
    PostgresProjectActivityRepository,
    ProjectActivityRepository,
)
from agent.registry.repository import (
    PostgresSpecRegistryRepository,
    SpecRegistryRepository,
)
from agent.runs.repository import PostgresRunRepository, RunRepository
from agent.runs.stream_events import (
    PostgresRunStreamEventRepository,
    RunStreamEventRepository,
)
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
from agent.vault import (
    InMemoryVaultRepository,
    PostgresVaultRepository,
    VaultRepository,
)
from agent.workforce.repository import (
    InMemoryWorkforceRepository,
    PostgresWorkforceRepository,
    WorkforceRepository,
)

from apps.cosa.models.repository import (
    InMemoryModelRoutingRepository,
    PostgresModelRoutingRepository,
)


def build_postgres_session_factory(database_url: str) -> tuple[Any, Any]:
    """Tạo AsyncEngine và async_sessionmaker từ database_url."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@dataclass(slots=True)
class PlaneStorageBundle:
    """Tập hợp tất cả các repository, state store và engines đã khởi tạo."""

    run_repository: RunRepository
    conversation_repository: ConversationRepository
    spec_registry: SpecRegistryRepository
    governance_store: GovernanceStateStore
    stream_event_repository: RunStreamEventRepository
    artifact_repository: ArtifactRepository
    workforce_repository: WorkforceRepository
    vault_repository: VaultRepository
    web_search_budget_store: WebSearchBudgetStore
    memory_service: Any
    knowledge_ingestion_service: Any
    knowledge_snapshot_repo: KnowledgeSnapshotRepository
    # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — durable, sequence-
    # numbered, idempotent Project Activity projection (migration 005). Soft-
    # wired giống artifact/workforce/vault ở trên: không fail-fast nếu thiếu
    # resolved_url, fallback InMemory cho test/dev.
    project_activity_repository: ProjectActivityRepository
    model_routing_repository: Any
    model_routing_session_factory: Any | None
    skill_candidate_store: SkillCandidateStore
    skill_improvement_repository: SkillImprovementRepository
    skill_usage_observer: Any
    created_engines: list[Any]


def init_plane_storage(
    *,
    repository: RunRepository | None = None,
    conversation_repository: ConversationRepository | None = None,
    spec_registry: SpecRegistryRepository | None = None,
    governance_store: GovernanceStateStore | None = None,
    stream_event_repository: RunStreamEventRepository | None = None,
    artifact_repository: ArtifactRepository | None = None,
    workforce_repository: WorkforceRepository | None = None,
    vault_repository: VaultRepository | None = None,
    web_search_budget_store: WebSearchBudgetStore | None = None,
    memory_service: Any | None = None,
    knowledge_ingestion_service: Any | None = None,
    knowledge_snapshot_repo: KnowledgeSnapshotRepository | None = None,
    database_url: str | None = None,
    model_routing_repository: Any | None = None,
    project_activity_repository: ProjectActivityRepository | None = None,
    skill_candidate_store: SkillCandidateStore | None = None,
    skill_improvement_repository: SkillImprovementRepository | None = None,
    skill_usage_observer: Any | None = None,
) -> PlaneStorageBundle:
    """Khởi tạo toàn bộ database sessions và repositories cho CosaAgentPlane.

    Production mặc định dùng Postgres*Repository — KHÔNG âm thầm rơi về in-memory
    nếu thiếu database_url (DB_FINAL_CUTOVER.md §8.1). Muốn dùng in-memory cho
    test/dev, truyền repository=InMemoryRunRepository() tường minh.
    """
    resolved_url = database_url or os.environ.get("AGENT_DATABASE_URL")
    created_engines: list[Any] = []

    if repository is not None:
        repo: RunRepository = repository
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit `repository=` "
                "or AGENT_DATABASE_URL to be set — production must not silently "
                "fall back to InMemoryRunRepository. For tests/local dev, pass "
                "repository=InMemoryRunRepository() explicitly."
            )
        engine, session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(engine)
        repo = PostgresRunRepository(session_factory)

    if conversation_repository is not None:
        conv_repo: ConversationRepository = conversation_repository
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit "
                "`conversation_repository=` or AGENT_DATABASE_URL to be set — "
                "production must not silently fall back to InMemoryConversationRepository. "
                "For tests/local dev, pass conversation_repository=InMemoryConversationRepository() "
                "explicitly."
            )
        conv_engine, conv_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(conv_engine)
        conv_repo = PostgresConversationRepository(conv_session_factory)

    if spec_registry is not None:
        registry_repo: SpecRegistryRepository = spec_registry
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit `spec_registry=` "
                "or AGENT_DATABASE_URL to be set — production must not silently "
                "fall back to InMemorySpecRegistryRepository. For tests/local dev, pass "
                "spec_registry=InMemorySpecRegistryRepository() explicitly."
            )
        reg_engine, reg_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(reg_engine)
        registry_repo = PostgresSpecRegistryRepository(reg_session_factory)

    if governance_store is not None:
        gov_store: GovernanceStateStore = governance_store
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit `governance_store=` "
                "or AGENT_DATABASE_URL to be set — production must not silently "
                "fall back to InMemoryGovernanceStateStore (Wave 2 gap: CapabilityGateway "
                "governance accumulator must survive process restart). For tests/local dev, "
                "pass governance_store=InMemoryGovernanceStateStore() explicitly."
            )
        gov_engine, gov_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(gov_engine)
        gov_store = PostgresGovernanceStateStore(gov_session_factory)

    if stream_event_repository is not None:
        stream_repo: RunStreamEventRepository = stream_event_repository
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit "
                "`stream_event_repository=` or AGENT_DATABASE_URL to be set — "
                "production must not silently fall back to in-memory SSE history "
                "(§7 durable event log). For tests/local dev, pass "
                "stream_event_repository=InMemoryRunStreamEventRepository() explicitly."
            )
        stream_engine, stream_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(stream_engine)
        stream_repo = PostgresRunStreamEventRepository(stream_session_factory)

    if artifact_repository is not None:
        art_repo: ArtifactRepository = artifact_repository
    elif resolved_url:
        art_engine, art_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(art_engine)
        art_repo = PostgresArtifactRepository(art_session_factory)
    else:
        art_repo = InMemoryArtifactRepository()

    if workforce_repository is not None:
        wf_repo: WorkforceRepository = workforce_repository
    elif resolved_url:
        wf_engine, wf_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(wf_engine)
        wf_repo = PostgresWorkforceRepository(wf_session_factory)
    else:
        wf_repo = InMemoryWorkforceRepository()

    if vault_repository is not None:
        vault_repo: VaultRepository = vault_repository
    elif resolved_url:
        vault_engine, vault_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(vault_engine)
        vault_repo = PostgresVaultRepository(vault_session_factory)
    else:
        vault_repo = InMemoryVaultRepository()

    # Memory & Knowledge stores
    if memory_service is None:
        from agent.memory.service import MemoryService as _MemoryService

        memory_service = (
            _MemoryService.for_production(resolved_url)
            if resolved_url
            else _MemoryService.in_memory()
        )

    if knowledge_ingestion_service is None:
        from agent.knowledge.service import KnowledgeIngestionService as _KIS

        # Task 8 (plan local-first-enterprise-knowledge) — vault_repository
        # cần cho KnowledgeIngestionService.retrieve_authorized_citations()
        # khi store không tự implement join thật (InMemoryKnowledgeStore);
        # PostgresKnowledgeStore bỏ qua tham số này (tự SQL join).
        if resolved_url:
            from agent.knowledge.store import get_knowledge_store as _get_kstore

            knowledge_ingestion_service = _KIS(
                _get_kstore(resolved_url), vault_repository=vault_repo
            )
        else:
            from agent.knowledge.store import InMemoryKnowledgeStore as _InMemKStore

            knowledge_ingestion_service = _KIS(_InMemKStore(), vault_repository=vault_repo)

    # IA07: knowledge_snapshot_repo trước đây không có trong bundle này nên
    # register_cosa_capabilities() luôn nhận None, khiến knowledge.read
    # capability không có nguồn dữ liệu thật kể cả khi AGENT_DATABASE_URL đã
    # cấu hình đầy đủ (chỉ InMemory ở test mới set nó).
    if knowledge_snapshot_repo is not None:
        knowledge_snap_repo: KnowledgeSnapshotRepository = knowledge_snapshot_repo
    elif resolved_url:
        know_engine, know_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(know_engine)
        knowledge_snap_repo = PostgresKnowledgeSnapshotRepository(know_session_factory)
    else:
        knowledge_snap_repo = InMemoryKnowledgeSnapshotRepository()

    # Task 3 — model routing repository. Cùng pattern "soft" như artifact/
    # workforce/vault ở trên: KHÔNG fail-fast nếu thiếu resolved_url (khác
    # run_repository/conversation/spec_registry/governance/stream_event —
    # routing theo workspace là tính năng opt-in mới, chưa phải core path bắt
    # buộc mọi run phải có). `model_routing_session_factory` giữ lại
    # session_factory THẬT (không phải chỉ engine) để
    # `apps/cosa/worker/run_core.py` tái dùng lúc dựng credential store LAZY
    # (không dựng credential store — vốn eagerly đọc/tạo key file cục bộ —
    # ngay ở đây cho MỌI plane build; xem task-3-report.md phần rủi ro side
    # effect).
    model_routing_session_factory: Any | None = None
    if model_routing_repository is not None:
        model_routing_repo: Any = model_routing_repository
    elif resolved_url:
        mr_engine, mr_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(mr_engine)
        model_routing_repo = PostgresModelRoutingRepository(mr_session_factory)
        model_routing_session_factory = mr_session_factory
    else:
        model_routing_repo = InMemoryModelRoutingRepository()

    # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — Project Activity
    # projection repository. Soft-wired (không raise nếu thiếu resolved_url)
    # cùng lý do artifact/workforce/vault ở trên: chưa phải core path bắt
    # buộc mọi run phải có ngay từ ngày build_cosa_agent_plane() đầu tiên.
    if project_activity_repository is not None:
        proj_activity_repo: ProjectActivityRepository = project_activity_repository
    elif resolved_url:
        pa_engine, pa_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(pa_engine)
        proj_activity_repo = PostgresProjectActivityRepository(pa_session_factory)
    else:
        proj_activity_repo = InMemoryProjectActivityRepository()

    # Web search budget store
    if web_search_budget_store is not None:
        search_budget: WebSearchBudgetStore = web_search_budget_store
    elif resolved_url:
        search_engine, search_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(search_engine)
        search_budget = PostgresWebSearchBudgetStore(search_session_factory)
    else:
        search_budget = InMemoryWebSearchBudgetStore()

    # Skill candidate store & improvement repository
    if skill_candidate_store is not None:
        cand_store = skill_candidate_store
    elif resolved_url:
        cand_engine, cand_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(cand_engine)
        cand_store = PostgresSkillCandidateStore(cand_session_factory)
    else:
        cand_store = InMemorySkillCandidateStore()

    if skill_improvement_repository is not None:
        imp_repo = skill_improvement_repository
    elif resolved_url:
        imp_engine, imp_session_factory = build_postgres_session_factory(resolved_url)
        created_engines.append(imp_engine)
        imp_repo = PostgresSkillImprovementRepository(
            imp_session_factory, candidate_store=cand_store
        )
    else:
        imp_repo = InMemorySkillImprovementRepository(candidate_store=cand_store)

    if skill_usage_observer is not None:
        usage_observer = skill_usage_observer
    else:
        usage_observer = SkillUsageObserver(imp_repo)

    return PlaneStorageBundle(
        run_repository=repo,
        conversation_repository=conv_repo,
        spec_registry=registry_repo,
        governance_store=gov_store,
        stream_event_repository=stream_repo,
        artifact_repository=art_repo,
        workforce_repository=wf_repo,
        vault_repository=vault_repo,
        web_search_budget_store=search_budget,
        memory_service=memory_service,
        knowledge_ingestion_service=knowledge_ingestion_service,
        knowledge_snapshot_repo=knowledge_snap_repo,
        model_routing_repository=model_routing_repo,
        model_routing_session_factory=model_routing_session_factory,
        project_activity_repository=proj_activity_repo,
        skill_candidate_store=cand_store,
        skill_improvement_repository=imp_repo,
        skill_usage_observer=usage_observer,
        created_engines=created_engines,
    )
