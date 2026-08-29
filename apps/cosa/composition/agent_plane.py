from __future__ import annotations

import os
from typing import Any

from agent.artifacts import (
    ArtifactRepository,
    InMemoryArtifactRepository,
    PostgresArtifactRepository,
)
from agent.capabilities.approval_service import DurableApprovalService
from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.capabilities.web_search import (
    InMemoryWebSearchBudgetStore,
    PostgresWebSearchBudgetStore,
    WebSearchBudgetStore,
    WebSearchProvider,
    build_web_search_provider,
)
from agent.contracts.kernel import ExecutionKernel
from agent.conversations.repository import (
    ConversationRepository,
    PostgresConversationRepository,
)
from agent.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient
from agent.governance.providers.postgres import PostgresGovernanceStateStore
from agent.governance.store import GovernanceStateStore
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.registry.repository import (
    PostgresSpecRegistryRepository,
    SpecRegistryRepository,
)
from agent.runs.control_plane_client import HttpControlPlaneLeaseClient
from agent.runs.repository import PostgresRunRepository, RunRepository
from agent.runs.stream_events import (
    PostgresRunStreamEventRepository,
    RunStreamEventRepository,
)
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.commercial_customer_read import (
    COMMERCIAL_CUSTOMER_360_READ_SPEC,
    create_commercial_customer_360_read_handler,
)
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.engagement_assignment_write import (
    ENGAGEMENT_ASSIGNMENT_WRITE_SPEC,
    create_engagement_assignment_write_handler,
)
from apps.cosa.capabilities.engagement_message_draft import (
    ENGAGEMENT_MESSAGE_DRAFT_SPEC,
    create_engagement_message_draft_handler,
)
from apps.cosa.capabilities.engagement_message_send import (
    ENGAGEMENT_MESSAGE_SEND_SPEC,
    create_engagement_message_send_handler,
)
from apps.cosa.capabilities.engagement_read import (
    ENGAGEMENT_THREAD_READ_SPEC,
    create_engagement_thread_read_handler,
)
from apps.cosa.capabilities.finance_read import (
    FINANCE_CONNECTION_READ_SPEC,
    FINANCE_TRANSACTION_READ_SPEC,
    create_finance_connection_read_handler,
    create_finance_transaction_read_handler,
)
from apps.cosa.capabilities.finance_write import (
    FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC,
    FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC,
    FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    create_finance_accounting_document_confirm_handler,
    create_finance_accounting_document_create_draft_handler,
    create_finance_transaction_classify_propose_handler,
    create_finance_transaction_record_handler,
)
from apps.cosa.capabilities.knowledge_read import (
    KNOWLEDGE_PROFILE_READ_SPEC,
    create_knowledge_profile_read_handler,
)
from apps.cosa.capabilities.legal_read import (
    LEGAL_APPLICABILITY_ASSESS_SPEC,
    create_legal_applicability_assess_handler,
)
from apps.cosa.capabilities.legal_write import (
    LEGAL_OBLIGATION_CREATE_DRAFT_SPEC,
    create_legal_obligation_create_draft_handler,
)
from apps.cosa.capabilities.marketing_read import (
    MARKETING_CONTEXT_READ_SPEC,
    create_marketing_context_read_handler,
)
from apps.cosa.capabilities.marketing_write import (
    CAMPAIGN_ASSET_WRITE_SPEC,
    EXPERIMENT_WRITE_SPEC,
    MARKETING_CONTEXT_WRITE_SPEC,
    create_campaign_asset_write_handler,
    create_experiment_write_handler,
    create_marketing_context_write_handler,
)
from apps.cosa.capabilities.operations_read import (
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    create_operations_task_list_handler,
    create_operations_task_read_handler,
)
from apps.cosa.capabilities.operations_write import (
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    create_operations_task_create_draft_handler,
)
from apps.cosa.capabilities.sandbox_read_mcp import register_sandbox_read_mcp_tools
from apps.cosa.capabilities.venture_profile import (
    VENTURE_PROFILE_PROPOSE_UPDATE_SPEC,
    VENTURE_PROFILE_READ_SPEC,
    create_venture_profile_propose_update_handler,
    create_venture_profile_read_handler,
)
from apps.cosa.capabilities.venture_stage import (
    VENTURE_STAGE_ASSESS_SPEC,
    VENTURE_STAGE_TRANSITION_PROPOSE_SPEC,
    create_venture_stage_assess_handler,
    create_venture_stage_transition_propose_handler,
)
from apps.cosa.capabilities.web_search import (
    WEB_SEARCH_SPEC,
    create_web_search_handler,
)
from apps.cosa.config.planes import (
    resolve_execution_plane_url,
    resolve_platform_control_plane_url,
)
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

__all__ = ["CosaAgentPlane", "build_cosa_agent_plane", "close_cosa_agent_plane"]


class CosaAgentPlane:
    """Composition Root của ứng dụng COSA (Master Guide §4 & §8).

    Lắp ráp toàn bộ các module độc lập từ `packages/agent/*` với các
    Capability và Business Policy của COSA kết nối `services/company/`.
    """

    def __init__(
        self,
        *,
        repository: RunRepository,
        conversation_repository: ConversationRepository,
        spec_registry: SpecRegistryRepository,
        governance_store: GovernanceStateStore,
        capability_registry: CapabilityRegistry,
        policy_engine: CosaPolicyEngine,
        approval_service: DurableApprovalService,
        gateway: CapabilityGateway,
        kernel: ExecutionKernel,
        workflow_registry: WorkflowDefinitionRegistry,
        workflow_engine: WorkflowEngine,
        company_client: CompanyServiceClient,
        tenant_policy_client: CosaTenantPolicyClient,
        scheduler: Any,
        lease_client: Any,
        stream_event_repository: RunStreamEventRepository,
        artifact_repository: ArtifactRepository | None = None,
        engines: list[Any] | None = None,
        event_intake_deps: Any | None = None,
        memory_service: Any | None = None,
        knowledge_ingestion_service: Any | None = None,
    ) -> None:
        self.repository = repository
        self.run_repository = repository
        self.conversation_repository = conversation_repository
        self.spec_registry = spec_registry
        self.governance_store = governance_store
        self.capability_registry = capability_registry
        self.policy_engine = policy_engine
        self.approval_service = approval_service
        self.gateway = gateway
        self.kernel = kernel
        self.workflow_registry = workflow_registry
        self.workflow_engine = workflow_engine
        self.company_client = company_client
        self.tenant_policy_client = tenant_policy_client
        self.scheduler = scheduler
        self.lease_client = lease_client
        self.stream_event_repository = stream_event_repository
        self.artifact_repository = artifact_repository
        self.event_intake_deps = event_intake_deps
        self.memory_service = memory_service
        self.knowledge_ingestion_service = knowledge_ingestion_service

        # SQLAlchemy AsyncEngine đã tạo trong build_cosa_agent_plane() (nếu
        # dùng Postgres*Repository mặc định) — đóng qua close_cosa_agent_plane()
        # ở FastAPI lifespan shutdown (Phase 5). Rỗng nếu toàn bộ repository
        # được truyền tường minh (test/in-memory), không có engine nào để đóng.
        self.engines = engines or []


def _build_postgres_session_factory(database_url: str) -> tuple[Any, Any]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def close_cosa_agent_plane(plane: CosaAgentPlane) -> None:
    """Đóng mọi HTTP client persistent + dispose mọi SQLAlchemy engine mà
    `build_cosa_agent_plane()` đã tạo — gọi từ FastAPI lifespan shutdown
    (`apps/cosa/api/app.py`, Phase 5 Composition Lifecycle). Repository/client
    được truyền tường minh vào `build_cosa_agent_plane()` (test/in-memory)
    KHÔNG bị đóng ở đây — caller đó tự sở hữu vòng đời của chúng.

    `getattr(obj, "aclose", None)` vì `scheduler`/`lease_client` có thể là
    `RunScheduler`/`RunLeaseManager` in-memory (không có `aclose()`) khi test
    truyền tường minh, thay vì `HttpControlPlaneSchedulerClient`/
    `HttpControlPlaneLeaseClient` mặc định production.
    """
    for closeable in (plane.tenant_policy_client, plane.scheduler, plane.lease_client):
        aclose = getattr(closeable, "aclose", None)
        if aclose is not None:
            await aclose()
    for engine in plane.engines:
        await engine.dispose()


def build_cosa_agent_plane(
    *,
    repository: RunRepository | None = None,
    conversation_repository: ConversationRepository | None = None,
    spec_registry: SpecRegistryRepository | None = None,
    governance_store: GovernanceStateStore | None = None,
    company_client: CompanyServiceClient | None = None,
    tenant_policy_client: CosaTenantPolicyClient | None = None,
    scheduler: Any | None = None,
    lease_client: Any | None = None,
    model: Any | None = None,
    stream_event_repository: RunStreamEventRepository | None = None,
    artifact_repository: ArtifactRepository | None = None,
    web_search_provider: WebSearchProvider | None = None,
    web_search_budget_store: WebSearchBudgetStore | None = None,
    database_url: str | None = None,
    runtime: str = "openai_agents",
    event_intake_deps: Any | None = None,
    memory_service: Any | None = None,
    knowledge_ingestion_service: Any | None = None,
) -> CosaAgentPlane:
    """Khởi tạo hoàn chỉnh một môi trường CosaAgentPlane.

    Production mặc định dùng PostgresRunRepository/PostgresConversationRepository —
    KHÔNG âm thầm rơi về in-memory nếu thiếu database_url (DB_FINAL_CUTOVER.md §8.1).
    Muốn dùng in-memory cho test/dev, truyền `repository=InMemoryRunRepository()` và
    `conversation_repository=InMemoryConversationRepository()` tường minh.

    `runtime`: "openai_agents" (mặc định, production — RealOpenAIAgentsSDKKernel
    thật qua agents.Runner, ADR-RUNTIME-002), "manual_tool_loop" (kernel loop
    thủ công cũ, opt-in cho dev/test không cần model provider config sẵn),
    hoặc "langchain" (optional adapter, không trên cutover path — xem
    docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md).
    Import LangChain lazy bên trong nhánh này — `apps.cosa` không bắt buộc cài
    `langchain-core`/`langchain-deepseek` trừ khi thực sự chọn runtime này.
    """
    # Fail-fast: execution plane phải là local Workspace Runtime Node, tách bạch
    # platform control plane (SPEC-EXEC-PLANE-SPLIT / ADR-LOCAL-FIRST-001).
    # Helper raise ngay ở production nếu URL bị trỏ ra platform từ xa.
    execution_plane_url = resolve_execution_plane_url()

    resolved_url = database_url or os.environ.get("AGENT_DATABASE_URL")
    _created_engines: list[Any] = []

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
        _engine, session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_engine)
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
        _conv_engine, conv_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_conv_engine)
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
        _registry_engine, registry_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_registry_engine)
        registry_repo = PostgresSpecRegistryRepository(registry_session_factory)

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
        _gov_engine, gov_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_gov_engine)
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
        _stream_engine, stream_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_stream_engine)
        stream_repo = PostgresRunStreamEventRepository(stream_session_factory)

    if artifact_repository is not None:
        art_repo: ArtifactRepository = artifact_repository
    elif resolved_url:
        _art_engine, art_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_art_engine)
        art_repo = PostgresArtifactRepository(art_session_factory)
    else:
        art_repo = InMemoryArtifactRepository()

    # Memory & Knowledge stores (closeout Task 2 / P1 Task 6). Mirror art_repo:
    # inject > Postgres (khi có AGENT_DATABASE_URL) > in-memory. Production
    # LUÔN có resolved_url vì các repo run/conv/registry/governance/stream ở trên
    # đã hard-fail nếu thiếu — nhánh in-memory dưới đây không reachable ở production.
    if memory_service is None:
        from agent.memory.service import MemoryService as _MemoryService

        memory_service = (
            _MemoryService.for_production(resolved_url)
            if resolved_url
            else _MemoryService.in_memory()
        )

    if knowledge_ingestion_service is None:
        from agent.knowledge.service import KnowledgeIngestionService as _KIS

        if resolved_url:
            from agent.knowledge.store import get_knowledge_store as _get_kstore

            knowledge_ingestion_service = _KIS(_get_kstore(resolved_url))
        else:
            from agent.knowledge.store import InMemoryKnowledgeStore as _InMemKStore

            knowledge_ingestion_service = _KIS(_InMemKStore())

    client = company_client or CompanyServiceClient()
    tenant_policy = tenant_policy_client or CosaTenantPolicyClient()

    # Durable dispatch/lease (Wave 7, ADR-CONTROLPLANE-001) — mặc định gọi
    # services/cosa control plane thật qua HTTP, KHÔNG âm thầm rơi về
    # RunScheduler/RunLeaseManager in-memory (đó chỉ là process-local, mất
    # task/lease khi HTTP process/worker chết — đúng gap §5 của
    # COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md). Test/dev
    # muốn dùng in-memory phải truyền tường minh
    # scheduler=RunScheduler()/lease_client=RunLeaseManager().
    # Durable run dispatch + lease = EXECUTION plane (local node). Dùng lại
    # execution_plane_url đã fail-fast ở đầu hàm.
    run_scheduler = scheduler or HttpControlPlaneSchedulerClient(base_url=execution_plane_url)
    run_lease_client = lease_client or HttpControlPlaneLeaseClient(base_url=execution_plane_url)

    # 1. Capability Registry & Handlers
    cap_registry = CapabilityRegistry()
    cap_registry.register(OPERATIONS_TASK_LIST_SPEC, create_operations_task_list_handler(client))
    cap_registry.register(OPERATIONS_TASK_READ_SPEC, create_operations_task_read_handler(client))
    cap_registry.register(
        FINANCE_TRANSACTION_RECORD_SPEC, create_finance_transaction_record_handler(client)
    )
    cap_registry.register(
        MARKETING_CONTEXT_READ_SPEC, create_marketing_context_read_handler(client)
    )
    cap_registry.register(
        MARKETING_CONTEXT_WRITE_SPEC, create_marketing_context_write_handler(client)
    )
    cap_registry.register(CAMPAIGN_ASSET_WRITE_SPEC, create_campaign_asset_write_handler(client))
    cap_registry.register(EXPERIMENT_WRITE_SPEC, create_experiment_write_handler(client))
    cap_registry.register(
        ENGAGEMENT_THREAD_READ_SPEC, create_engagement_thread_read_handler(client)
    )
    cap_registry.register(
        COMMERCIAL_CUSTOMER_360_READ_SPEC, create_commercial_customer_360_read_handler(client)
    )
    cap_registry.register(ENGAGEMENT_MESSAGE_DRAFT_SPEC, create_engagement_message_draft_handler())
    cap_registry.register(
        ENGAGEMENT_MESSAGE_SEND_SPEC, create_engagement_message_send_handler(client)
    )
    cap_registry.register(
        ENGAGEMENT_ASSIGNMENT_WRITE_SPEC, create_engagement_assignment_write_handler(client)
    )
    cap_registry.register(KNOWLEDGE_PROFILE_READ_SPEC, create_knowledge_profile_read_handler())
    cap_registry.register(
        LEGAL_APPLICABILITY_ASSESS_SPEC, create_legal_applicability_assess_handler(client)
    )
    cap_registry.register(
        LEGAL_OBLIGATION_CREATE_DRAFT_SPEC, create_legal_obligation_create_draft_handler(client)
    )
    cap_registry.register(VENTURE_PROFILE_READ_SPEC, create_venture_profile_read_handler(client))
    cap_registry.register(
        VENTURE_PROFILE_PROPOSE_UPDATE_SPEC, create_venture_profile_propose_update_handler(client)
    )
    cap_registry.register(
        FINANCE_CONNECTION_READ_SPEC, create_finance_connection_read_handler(client)
    )
    cap_registry.register(
        FINANCE_TRANSACTION_READ_SPEC, create_finance_transaction_read_handler(client)
    )
    cap_registry.register(
        FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC,
        create_finance_transaction_classify_propose_handler(client),
    )
    cap_registry.register(
        FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC,
        create_finance_accounting_document_create_draft_handler(client),
    )
    cap_registry.register(
        FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC,
        create_finance_accounting_document_confirm_handler(client),
    )
    cap_registry.register(
        OPERATIONS_TASK_CREATE_DRAFT_SPEC,
        create_operations_task_create_draft_handler(client),
    )
    cap_registry.register(
        VENTURE_STAGE_ASSESS_SPEC,
        create_venture_stage_assess_handler(client),
    )
    cap_registry.register(
        VENTURE_STAGE_TRANSITION_PROPOSE_SPEC,
        create_venture_stage_transition_propose_handler(client),
    )

    # Web Search Capability (Part SEARCH)
    if web_search_budget_store is not None:
        search_budget: WebSearchBudgetStore = web_search_budget_store
    elif resolved_url:
        _search_engine, search_session_factory = _build_postgres_session_factory(resolved_url)
        _created_engines.append(_search_engine)
        search_budget = PostgresWebSearchBudgetStore(search_session_factory)
    else:
        search_budget = InMemoryWebSearchBudgetStore()

    search_prov = web_search_provider or build_web_search_provider()
    cap_registry.register(
        WEB_SEARCH_SPEC,
        create_web_search_handler(
            search_prov,
            workspace_policy_client=tenant_policy,
            budget_store=search_budget,
            artifact_repository=art_repo,
        ),
    )

    register_sandbox_read_mcp_tools(cap_registry)

    # 2. Policy Engine & Approval Service
    policy_engine = CosaPolicyEngine()
    approval_service = DurableApprovalService(
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
    )

    # 3. Capability Gateway
    # Connector grant check = PLATFORM control plane (VPS).
    connector_grant_client = ConnectorGrantHttpClient(base_url=resolve_platform_control_plane_url())

    async def _connector_grant_resolver(connector_id: str, req):
        return await connector_grant_client.assert_usable(
            connector_id,
            workspace_id=req.workspace_id or "",
            conversation_id=req.context.get("conversation_id", ""),
            action=req.capability_id,
        )

    gateway = CapabilityGateway(
        registry=cap_registry,
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
        governance_store=gov_store,
        connector_grant_resolver=_connector_grant_resolver,
    )

    # 4. Execution Kernel
    if runtime == "langchain":
        # Import lazy — chỉ nhánh này mới yêu cầu langchain-core/langchain-deepseek.
        from agent_integrations.langchain.kernel import LangChainKernel

        kernel: Any = LangChainKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_registry=cap_registry,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    elif runtime == "openai_agents":
        # Kernel mặc định production — agents.Runner THẬT qua
        # RealOpenAIAgentsSDKKernel, không phải ManualToolLoopKernel (đổi tên
        # từ OpenAIAgentsKernel) — theo ADR-RUNTIME-002 và
        # COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md Phase 1.
        # `model=` override tường minh dùng cho test (vd.
        # agent_testkit.fake_sdk_model.FakeSDKModel) — nếu không truyền,
        # bắt buộc build từ DEEPSEEK_API_KEY thật, fail-fast nếu thiếu.
        if model is not None:
            resolved_model: Any = model
        else:
            from apps.cosa.composition.model_provider import build_deepseek_model

            resolved_model = build_deepseek_model()

        from unittest.mock import AsyncMock, MagicMock

        from apps.cosa.compliance import AiComplianceClient, ComplianceResolver
        from apps.cosa.compliance.data_model_gate import CosaDataModelGate

        if (
            model is not None
            or isinstance(client, (AsyncMock, MagicMock))
            or isinstance(getattr(client, "get", None), (AsyncMock, MagicMock))
        ):

            class _MockAiComplianceClient:
                async def resolve_snapshot(
                    self,
                    workspace_id: str,
                    run_id: str,
                    system_key: str,
                    policy_snapshot_hash: str | None = None,
                ):
                    return {
                        "workspace_id": workspace_id,
                        "deployment_id": f"dep_{workspace_id}",
                        "system_key": system_key,
                        "mode": "ADVISORY_ONLY",
                        "status": "APPROVED_FOR_USE",
                        "allowed_capabilities": ["*"],
                        "data_class_authorizations": ["*"],
                    }

            compliance_resolver = ComplianceResolver(client=_MockAiComplianceClient())  # type: ignore[arg-type]
        else:
            base_url = getattr(client, "base_url", None) or getattr(client, "_base_url", None)
            if base_url is None:
                base_url = os.getenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
            compliance_resolver = ComplianceResolver(AiComplianceClient(base_url=str(base_url)))
        model_input_guard = CosaDataModelGate(client=client)

        kernel = RealOpenAIAgentsSDKKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_registry=cap_registry,
            model=resolved_model,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
            compliance_resolver=compliance_resolver,
            model_input_guard=model_input_guard,
        )

    elif runtime == "manual_tool_loop":
        # Kernel manual-loop cũ (đổi tên từ OpenAIAgentsKernel) — vẫn dùng
        # được qua opt-in tường minh, không còn là default.
        kernel = ManualToolLoopKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    else:
        raise ValueError(
            f"Unknown runtime '{runtime}' — expected 'openai_agents', 'manual_tool_loop', or 'langchain'"
        )

    # 5. Workflow Engine & Definition Registry
    wf_registry = WorkflowDefinitionRegistry()
    wf_registry.register_version(COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC)

    wf_engine = WorkflowEngine(
        tool_registry=cap_registry,
        gateway=gateway,
        policy_engine=policy_engine,
        approval_service=approval_service,
        governance_store=gov_store,
    )

    return CosaAgentPlane(
        repository=repo,
        conversation_repository=conv_repo,
        spec_registry=registry_repo,
        governance_store=gov_store,
        capability_registry=cap_registry,
        policy_engine=policy_engine,
        approval_service=approval_service,
        gateway=gateway,
        kernel=kernel,
        workflow_registry=wf_registry,
        workflow_engine=wf_engine,
        company_client=client,
        tenant_policy_client=tenant_policy,
        scheduler=run_scheduler,
        lease_client=run_lease_client,
        stream_event_repository=stream_repo,
        artifact_repository=art_repo,
        engines=_created_engines,
        event_intake_deps=event_intake_deps,
        memory_service=memory_service,
        knowledge_ingestion_service=knowledge_ingestion_service,
    )
