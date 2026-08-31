from __future__ import annotations

from typing import Any

from agent.artifacts import ArtifactRepository
from agent.capabilities.approval_service import DurableApprovalService
from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.capabilities.web_search import (
    WebSearchBudgetStore,
    WebSearchProvider,
)
from agent.contracts.kernel import ExecutionKernel
from agent.conversations.repository import ConversationRepository
from agent.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient
from agent.governance.store import GovernanceStateStore
from agent.registry.repository import SpecRegistryRepository
from agent.runs.control_plane_client import HttpControlPlaneLeaseClient
from agent.runs.repository import RunRepository
from agent.runs.stream_events import RunStreamEventRepository
from agent.vault import VaultRepository
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine
from agent.workforce.repository import WorkforceRepository

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.composition.capability_registration import register_cosa_capabilities
from apps.cosa.composition.compliance_coordination import ComplianceCoordination
from apps.cosa.composition.kernel_factory import build_execution_kernel
from apps.cosa.composition.run_execution_service import RunExecutionService
from apps.cosa.composition.storage_factory import (
    PlaneStorageBundle,
    build_postgres_session_factory,
    init_plane_storage,
)
from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.config.planes import (
    resolve_execution_plane_url,
    resolve_platform_control_plane_url,
)
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

__all__ = ["CosaAgentPlane", "build_cosa_agent_plane", "close_cosa_agent_plane"]

_build_postgres_session_factory = build_postgres_session_factory


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
        compliance_resolver: Any | None = None,
        workforce_repository: WorkforceRepository | None = None,
        vault_repository: VaultRepository | None = None,
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
        self.workforce_repository = workforce_repository
        self.vault_repository = vault_repository
        self.event_intake_deps = event_intake_deps
        self.memory_service = memory_service
        self.knowledge_ingestion_service = knowledge_ingestion_service
        # Task 5 — expose ở plane level (không chỉ giấu trong kernel private
        # attribute) để apps/cosa/worker/handlers.py có thể gọi
        # `resolve_for_run()` TRƯỚC `plane.kernel.run()`.
        self.compliance_resolver = compliance_resolver

        # SQLAlchemy AsyncEngine đã tạo trong build_cosa_agent_plane() (nếu
        # dùng Postgres*Repository mặc định) — đóng qua close_cosa_agent_plane()
        # ở FastAPI lifespan shutdown (Phase 5).
        self.engines = engines or []

    @property
    def run_execution(self) -> RunExecutionService:
        """Narrower interface for run execution (kernel, repository, lease, scheduler)."""
        return RunExecutionService(
            kernel=self.kernel,
            repository=self.repository,
            lease_client=self.lease_client,
            scheduler=self.scheduler,
        )

    @property
    def workflow_orchestration(self) -> WorkflowOrchestration:
        """Narrower interface for workflow orchestration (gateway, engine, registry, approval)."""
        return WorkflowOrchestration(
            gateway=self.gateway,
            workflow_engine=self.workflow_engine,
            workflow_registry=self.workflow_registry,
            approval_service=self.approval_service,
        )

    @property
    def compliance_coordination(self) -> ComplianceCoordination:
        """Narrower interface for compliance orchestration (policy, governance, compliance resolver)."""
        return ComplianceCoordination(
            policy_engine=self.policy_engine,
            capability_registry=self.capability_registry,
            governance_store=self.governance_store,
            compliance_resolver=self.compliance_resolver,
        )


async def close_cosa_agent_plane(plane: CosaAgentPlane) -> None:
    """Đóng mọi HTTP client persistent + dispose mọi SQLAlchemy engine mà
    `build_cosa_agent_plane()` đã tạo — gọi từ FastAPI lifespan shutdown
    (`apps/cosa/api/app.py`, Phase 5 Composition Lifecycle).
    """
    for obj in (
        plane.scheduler,
        plane.lease_client,
        plane.company_client,
        plane.tenant_policy_client,
    ):
        aclose = getattr(obj, "aclose", None)
        if callable(aclose):
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
    workforce_repository: WorkforceRepository | None = None,
    vault_repository: VaultRepository | None = None,
) -> CosaAgentPlane:
    """Khởi tạo hoàn chỉnh một môi trường CosaAgentPlane.

    Production mặc định dùng PostgresRunRepository/PostgresConversationRepository —
    KHÔNG âm thầm rơi về in-memory nếu thiếu database_url (DB_FINAL_CUTOVER.md §8.1).
    Muốn dùng in-memory cho test/dev, truyền `repository=InMemoryRunRepository()` và
    `conversation_repository=InMemoryConversationRepository()` tường minh.
    """
    # Fail-fast: execution plane phải là local Workspace Runtime Node, tách bạch
    # platform control plane (SPEC-EXEC-PLANE-SPLIT / ADR-LOCAL-FIRST-001).
    execution_plane_url = resolve_execution_plane_url()

    # 1. Storage & Repositories
    storage: PlaneStorageBundle = init_plane_storage(
        repository=repository,
        conversation_repository=conversation_repository,
        spec_registry=spec_registry,
        governance_store=governance_store,
        stream_event_repository=stream_event_repository,
        artifact_repository=artifact_repository,
        workforce_repository=workforce_repository,
        vault_repository=vault_repository,
        web_search_budget_store=web_search_budget_store,
        memory_service=memory_service,
        knowledge_ingestion_service=knowledge_ingestion_service,
        database_url=database_url,
    )

    client = company_client or CompanyServiceClient()
    tenant_policy = tenant_policy_client or CosaTenantPolicyClient()

    # Durable dispatch/lease (Wave 7, ADR-CONTROLPLANE-001)
    run_scheduler = scheduler or HttpControlPlaneSchedulerClient(base_url=execution_plane_url)
    run_lease_client = lease_client or HttpControlPlaneLeaseClient(base_url=execution_plane_url)

    # 2. Capability Registry & Handlers
    cap_registry = CapabilityRegistry()
    register_cosa_capabilities(
        cap_registry,
        client=client,
        tenant_policy=tenant_policy,
        search_budget=storage.web_search_budget_store,
        artifact_repo=storage.artifact_repository,
        web_search_provider=web_search_provider,
    )

    # 3. Policy Engine & Approval Service
    policy_engine = CosaPolicyEngine()
    approval_service = DurableApprovalService(
        repository=storage.run_repository,
        policy_evaluator=policy_engine.evaluate,
    )

    # 4. Capability Gateway
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
        repository=storage.run_repository,
        policy_evaluator=policy_engine.evaluate,
        governance_store=storage.governance_store,
        connector_grant_resolver=_connector_grant_resolver,
    )

    # 5. Execution Kernel
    kernel, compliance_resolver = build_execution_kernel(
        runtime=runtime,
        repository=storage.run_repository,
        spec_registry=storage.spec_registry,
        capability_registry=cap_registry,
        gateway=gateway,
        policy_engine=policy_engine,
        company_client=client,
        model=model,
    )

    # 6. Workflow Engine & Definition Registry
    wf_registry = WorkflowDefinitionRegistry()
    wf_registry.register_version(COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC)

    wf_engine = WorkflowEngine(
        tool_registry=cap_registry,
        gateway=gateway,
        policy_engine=policy_engine,
        approval_service=approval_service,
        governance_store=storage.governance_store,
    )

    return CosaAgentPlane(
        repository=storage.run_repository,
        conversation_repository=storage.conversation_repository,
        spec_registry=storage.spec_registry,
        governance_store=storage.governance_store,
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
        stream_event_repository=storage.stream_event_repository,
        artifact_repository=storage.artifact_repository,
        workforce_repository=storage.workforce_repository,
        vault_repository=storage.vault_repository,
        engines=storage.created_engines,
        event_intake_deps=event_intake_deps,
        memory_service=storage.memory_service,
        knowledge_ingestion_service=storage.knowledge_ingestion_service,
        compliance_resolver=compliance_resolver,
    )
