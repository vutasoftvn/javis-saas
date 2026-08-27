from __future__ import annotations

import os
from typing import Any, Optional

from agent_core.artifacts import (
    ArtifactRepository,
    InMemoryArtifactRepository,
    PostgresArtifactRepository,
)
from agent_core.capabilities.approval_service import DurableApprovalService

from agent_core.capabilities.gateway import CapabilityGateway
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient
from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agent_core.conversations.repository import (
    ConversationRepository,
    InMemoryConversationRepository,
    PostgresConversationRepository,
)
from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import (
    InMemorySpecRegistryRepository,
    PostgresSpecRegistryRepository,
    SpecRegistryRepository,
)
from agent_core.runs.control_plane_client import HttpControlPlaneLeaseClient
from agent_core.runs.repository import InMemoryRunRepository, PostgresRunRepository, RunRepository
from agent_core.runs.stream_events import (
    PostgresRunStreamEventRepository,
    RunStreamEventRepository,
)
from agent_core.workflows.definition_registry import WorkflowDefinitionRegistry
from agent_core.workflows.engine import WorkflowEngine
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.finance_write import (
    FINANCE_PAYOUT_EXECUTE_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    create_finance_payout_execute_handler,
    create_finance_transaction_record_handler,
)
from apps.cosa.capabilities.operations_read import (
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    create_operations_task_list_handler,
    create_operations_task_read_handler,
)
from apps.cosa.capabilities.sandbox_read_mcp import register_sandbox_read_mcp_tools
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

__all__ = ["CosaAgentPlane", "build_cosa_agent_plane", "close_cosa_agent_plane"]


class CosaAgentPlane:
    """Composition Root của ứng dụng COSA (Master Guide §4 & §8).
    
    Lắp ráp toàn bộ các module độc lập từ `packages/agent_core/*` với các
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
        artifact_repository: Optional[ArtifactRepository] = None,
        engines: Optional[list[Any]] = None,
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
    repository: Optional[RunRepository] = None,
    conversation_repository: Optional[ConversationRepository] = None,
    spec_registry: Optional[SpecRegistryRepository] = None,
    governance_store: Optional[GovernanceStateStore] = None,
    company_client: Optional[CompanyServiceClient] = None,
    tenant_policy_client: Optional[CosaTenantPolicyClient] = None,
    scheduler: Optional[Any] = None,
    lease_client: Optional[Any] = None,
    model: Optional[Any] = None,
    stream_event_repository: Optional[RunStreamEventRepository] = None,
    artifact_repository: Optional[ArtifactRepository] = None,
    database_url: Optional[str] = None,
    runtime: str = "openai_agents",
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
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
    _created_engines: list[Any] = []

    if repository is not None:
        repo: RunRepository = repository
    else:
        if not resolved_url:
            raise RuntimeError(
                "build_cosa_agent_plane() requires either an explicit `repository=` "
                "or AGENT_CORE_DATABASE_URL to be set — production must not silently "
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
                "`conversation_repository=` or AGENT_CORE_DATABASE_URL to be set — "
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
                "or AGENT_CORE_DATABASE_URL to be set — production must not silently "
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
                "or AGENT_CORE_DATABASE_URL to be set — production must not silently "
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
                "`stream_event_repository=` or AGENT_CORE_DATABASE_URL to be set — "
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


    client = company_client or CompanyServiceClient()
    tenant_policy = tenant_policy_client or CosaTenantPolicyClient()

    # Durable dispatch/lease (Wave 7, ADR-CONTROLPLANE-001) — mặc định gọi
    # services/cosa control plane thật qua HTTP, KHÔNG âm thầm rơi về
    # RunScheduler/RunLeaseManager in-memory (đó chỉ là process-local, mất
    # task/lease khi HTTP process/worker chết — đúng gap §5 của
    # COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md). Test/dev
    # muốn dùng in-memory phải truyền tường minh
    # scheduler=RunScheduler()/lease_client=RunLeaseManager().
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    run_scheduler = scheduler or HttpControlPlaneSchedulerClient(base_url=control_plane_url)
    run_lease_client = lease_client or HttpControlPlaneLeaseClient(base_url=control_plane_url)

    # 1. Capability Registry & Handlers
    cap_registry = CapabilityRegistry()
    cap_registry.register(OPERATIONS_TASK_LIST_SPEC, create_operations_task_list_handler(client))
    cap_registry.register(OPERATIONS_TASK_READ_SPEC, create_operations_task_read_handler(client))
    cap_registry.register(FINANCE_PAYOUT_EXECUTE_SPEC, create_finance_payout_execute_handler(client))
    cap_registry.register(FINANCE_TRANSACTION_RECORD_SPEC, create_finance_transaction_record_handler(client))
    register_sandbox_read_mcp_tools(cap_registry)

    # 2. Policy Engine & Approval Service
    policy_engine = CosaPolicyEngine()
    approval_service = DurableApprovalService(
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
    )

    # 3. Capability Gateway
    connector_grant_client = ConnectorGrantHttpClient(base_url=control_plane_url)

    async def _connector_grant_resolver(connector_id: str, req):
        return await connector_grant_client.assert_usable(
            connector_id,
            company_id=req.workspace_id or "",  # workspace_id is the sole tenant key
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

        kernel = RealOpenAIAgentsSDKKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_registry=cap_registry,
            model=resolved_model,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
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
    )

