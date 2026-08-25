from __future__ import annotations

import os
from typing import Any, Optional

from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.capabilities.gateway import CapabilityGateway
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.governance.providers.postgres import PostgresGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agent_core.conversations.repository import (
    ConversationRepository,
    InMemoryConversationRepository,
    PostgresConversationRepository,
)
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import (
    InMemorySpecRegistryRepository,
    PostgresSpecRegistryRepository,
    SpecRegistryRepository,
)
from agent_core.runs.repository import InMemoryRunRepository, PostgresRunRepository, RunRepository
from agent_core.workflows.definition_registry import WorkflowDefinitionRegistry
from agent_core.workflows.engine import WorkflowEngine
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.capabilities.client import CompanyServiceClient
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
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

__all__ = ["CosaAgentPlane", "build_cosa_agent_plane"]


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
    ) -> None:
        self.repository = repository
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


def _build_postgres_session_factory(database_url: str):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


def build_cosa_agent_plane(
    *,
    repository: Optional[RunRepository] = None,
    conversation_repository: Optional[ConversationRepository] = None,
    spec_registry: Optional[SpecRegistryRepository] = None,
    governance_store: Optional[GovernanceStateStore] = None,
    company_client: Optional[CompanyServiceClient] = None,
    tenant_policy_client: Optional[CosaTenantPolicyClient] = None,
    database_url: Optional[str] = None,
    runtime: str = "openai_agents",
) -> CosaAgentPlane:
    """Khởi tạo hoàn chỉnh một môi trường CosaAgentPlane.

    Production mặc định dùng PostgresRunRepository/PostgresConversationRepository —
    KHÔNG âm thầm rơi về in-memory nếu thiếu database_url (DB_FINAL_CUTOVER.md §8.1).
    Muốn dùng in-memory cho test/dev, truyền `repository=InMemoryRunRepository()` và
    `conversation_repository=InMemoryConversationRepository()` tường minh.

    `runtime`: "openai_agents" (mặc định, production — ADR-RUNTIME-002) hoặc
    "langchain" (optional adapter, không trên cutover path — xem
    docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md).
    Import LangChain lazy bên trong nhánh này — `apps.cosa` không bắt buộc cài
    `langchain-core`/`langchain-deepseek` trừ khi thực sự chọn runtime này.
    """
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")

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
        session_factory = _build_postgres_session_factory(resolved_url)
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
        conv_session_factory = _build_postgres_session_factory(resolved_url)
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
        registry_session_factory = _build_postgres_session_factory(resolved_url)
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
        gov_session_factory = _build_postgres_session_factory(resolved_url)
        gov_store = PostgresGovernanceStateStore(gov_session_factory)

    client = company_client or CompanyServiceClient()
    tenant_policy = tenant_policy_client or CosaTenantPolicyClient()

    # 1. Capability Registry & Handlers
    cap_registry = CapabilityRegistry()
    cap_registry.register(OPERATIONS_TASK_LIST_SPEC, create_operations_task_list_handler(client))
    cap_registry.register(OPERATIONS_TASK_READ_SPEC, create_operations_task_read_handler(client))
    cap_registry.register(FINANCE_PAYOUT_EXECUTE_SPEC, create_finance_payout_execute_handler(client))
    cap_registry.register(FINANCE_TRANSACTION_RECORD_SPEC, create_finance_transaction_record_handler(client))

    # 2. Policy Engine & Approval Service
    policy_engine = CosaPolicyEngine()
    approval_service = DurableApprovalService(
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
    )

    # 3. Capability Gateway
    gateway = CapabilityGateway(
        registry=cap_registry,
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
        governance_store=gov_store,
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
        kernel = OpenAIAgentsKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    else:
        raise ValueError(f"Unknown runtime '{runtime}' — expected 'openai_agents' or 'langchain'")


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
    )
