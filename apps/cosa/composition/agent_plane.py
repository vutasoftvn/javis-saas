from __future__ import annotations

import os
from typing import Any

from agent.artifacts import ArtifactRepository
from agent.capabilities.approval_service import DurableApprovalService
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.grants import ConnectorGrant
from agent.capabilities.registry import CapabilityRegistry
from agent.capabilities.web_search import (
    WebSearchBudgetStore,
    WebSearchProvider,
)
from agent.contracts.kernel import ExecutionKernel
from agent.conversations.repository import ConversationRepository
from agent.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient
from agent.governance.store import GovernanceStateStore
from agent.knowledge.snapshot_repository import KnowledgeSnapshotRepository
from agent.project_activity.repository import ProjectActivityRepository
from agent.registry.repository import SpecRegistryRepository
from agent.runs.control_plane_client import HttpControlPlaneLeaseClient
from agent.runs.repository import RunRepository
from agent.runs.stream_events import RunStreamEventRepository
from agent.skills.candidate_store import SkillCandidateStore
from agent.skills.improvement_repository import SkillImprovementRepository
from agent.vault import VaultRepository
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine
from agent.workflows.repository import (
    InMemoryWorkflowDefinitionRepository,
    WorkflowDefinitionRepository,
)
from agent.workforce.repository import WorkforceRepository

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.workspace_settings_client import WorkspaceSettingsClient
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
from apps.cosa.knowledge_ingestion.dependencies import KnowledgeIngestionDependencies
from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.evaluator import CosaPolicyEngine
from apps.cosa.policies.profile_locale_client import ProfileLocaleClient
from apps.cosa.project_activity.service import ProjectActivityService
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
        workflow_definition_repository: WorkflowDefinitionRepository,
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
        workspace_settings_client: WorkspaceSettingsClient | None = None,
        profile_locale_client: ProfileLocaleClient | None = None,
        knowledge_snapshot_repo: KnowledgeSnapshotRepository | None = None,
        knowledge_ingestion_deps: KnowledgeIngestionDependencies | None = None,
        model_route_resolver: Any | None = None,
        model_provider_factory: Any | None = None,
        model_routing_session_factory: Any | None = None,
        model_routing_repository: Any | None = None,
        project_activity_repository: ProjectActivityRepository | None = None,
        project_activity_service: ProjectActivityService | None = None,
        skill_candidate_store: SkillCandidateStore | None = None,
        skill_improvement_repository: SkillImprovementRepository | None = None,
        skill_usage_observer: Any | None = None,
        skill_improvement_service: Any | None = None,
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
        self.workflow_definition_repository = workflow_definition_repository
        self.company_client = company_client
        self.tenant_policy_client = tenant_policy_client
        self.skill_candidate_store = skill_candidate_store
        self.skill_improvement_repository = skill_improvement_repository
        self.skill_usage_observer = skill_usage_observer
        self.skill_improvement_service = skill_improvement_service
        # COSA Automation MVP (Task 6) — worker -> Company outcome projection.
        # Lazily created so a plane built for unit tests without COMPANY_SERVICE_URL
        # simply reports nothing (the worker handler is None-safe).
        from apps.cosa.events.automation_outcome_client import build_automation_outcome_client

        self.automation_outcome_client = build_automation_outcome_client()
        self.profile_locale_client = profile_locale_client or ProfileLocaleClient()
        # Task 4 — thin HTTP client gọi COSA Control Plane (services/cosa) để
        # đọc/ghi workspace_skill_policies. Mặc định luôn có instance (không
        # None) để settings_routes.py fail rõ ràng (503) khi control plane
        # network-unreachable, thay vì fail âm thầm vì thiếu wiring.
        self.workspace_settings_client = workspace_settings_client or WorkspaceSettingsClient()
        self.scheduler = scheduler
        self.lease_client = lease_client
        self.stream_event_repository = stream_event_repository
        self.artifact_repository = artifact_repository
        self.workforce_repository = workforce_repository
        self.vault_repository = vault_repository
        self.event_intake_deps = event_intake_deps
        self.memory_service = memory_service
        self.knowledge_ingestion_service = knowledge_ingestion_service
        self.knowledge_snapshot_repo = knowledge_snapshot_repo
        # Task 4 — local storage/scanner/sandbox cho knowledge ingestion pipeline
        # thật, non-null chỉ khi KNOWLEDGE_INGESTION_ENABLED=true. Đúng 1 instance
        # dùng chung cho cả API process lẫn worker dispatch (không mỗi task 1
        # WorkspaceDocumentStore riêng).
        self.knowledge_ingestion_deps = knowledge_ingestion_deps
        # Task 5 — expose ở plane level (không chỉ giấu trong kernel private
        # attribute) để apps/cosa/worker/handlers.py có thể gọi
        # `resolve_for_run()` TRƯỚC `plane.kernel.run()`.
        self.compliance_resolver = compliance_resolver

        # Task 3 (plan 2026-09-07-local-first-model-routing) — expose ở plane
        # level cùng lý do với compliance_resolver ở trên: `run_kernel()`
        # (apps/cosa/worker/run_core.py) cần resolve route + (khi cần) build
        # model client THẬT trước khi gọi kernel.run(), không phải logic giấu
        # trong 1 kernel implementation cụ thể.
        #
        # `model_provider_factory` mặc định None và được `run_core.py` dựng
        # LAZY + cache lại lên plane ngay tại đây — KHÔNG dựng eagerly ở mọi
        # lần build_cosa_agent_plane(), vì `LocalCredentialStore.__init__`
        # (Task 2) eagerly đọc/tạo `COSA_LOCAL_SECRETS_KEY_FILE` (side effect
        # ghi file dưới $HOME ở môi trường dev) — chỉ nên trả giá đó khi 1
        # route THẬT không phải system-default cần build client, không phải
        # cho mọi worker/API process khởi động hay mọi test gọi
        # build_cosa_agent_plane().
        self.model_route_resolver = model_route_resolver
        self.model_provider_factory = model_provider_factory
        self.model_routing_session_factory = model_routing_session_factory
        self.model_routing_repository = model_routing_repository

        # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — durable
        # Project Activity repository, dùng bởi project_activity_routes.py
        # (list/detail/stream endpoints) để query durable activity events.
        # Cũng được inject vào ProjectActivityService — None-safe.
        self.project_activity_repository = project_activity_repository

        # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — durable
        # Project Activity projection service, dùng bởi conversation_routes.py
        # (chat.accepted/run.queued sau khi canonical record đã persist) và
        # CosaEventStreamManager.emit() (mọi durable runtime stream event
        # khác). None-safe: caller phải tự guard `if plane.project_activity_service`
        # trước khi gọi — build_cosa_agent_plane() luôn dựng 1 instance thật
        # (InMemory hoặc Postgres tuỳ AGENT_DATABASE_URL), None chỉ xảy ra khi
        # CosaAgentPlane được dựng thủ công (test) không truyền tham số này.
        self.project_activity_service = project_activity_service

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
            workflow_definition_repository=self.workflow_definition_repository,
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
        getattr(plane.profile_locale_client, "_client", None),
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
    workspace_settings_client: WorkspaceSettingsClient | None = None,
    profile_locale_client: ProfileLocaleClient | None = None,
    knowledge_snapshot_repo: KnowledgeSnapshotRepository | None = None,
    knowledge_ingestion_deps: KnowledgeIngestionDependencies | None = None,
    model_routing_repository: Any | None = None,
    model_route_resolver: Any | None = None,
    project_activity_repository: ProjectActivityRepository | None = None,
    skill_candidate_store: SkillCandidateStore | None = None,
    skill_improvement_repository: SkillImprovementRepository | None = None,
    skill_usage_observer: Any | None = None,
    skill_improvement_service: Any | None = None,
    workflow_definition_repository: WorkflowDefinitionRepository | None = None,
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
        knowledge_snapshot_repo=knowledge_snapshot_repo,
        database_url=database_url,
        model_routing_repository=model_routing_repository,
        project_activity_repository=project_activity_repository,
        skill_candidate_store=skill_candidate_store,
        skill_improvement_repository=skill_improvement_repository,
        skill_usage_observer=skill_usage_observer,
    )

    # Task 3 — Project Activity projection service, luôn dựng 1 instance thật
    # (không None) quanh repository đã resolve ở storage (InMemory hoặc
    # Postgres tuỳ AGENT_DATABASE_URL) — cùng nguyên tắc "production không
    # âm thầm rơi về no-op" áp dụng cho các thành phần khác trong module này.
    resolved_project_activity_service = ProjectActivityService(storage.project_activity_repository)

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
        # IA07: trước đây không truyền -> luôn None -> knowledge.read capability
        # không có nguồn dữ liệu thật, kể cả khi AGENT_DATABASE_URL đã cấu hình.
        knowledge_snapshot_repo=storage.knowledge_snapshot_repo,
        # Task 8 — knowledge.enterprise.read cần KnowledgeIngestionService thật
        # (đã wire vault_repository cho path InMemory, xem storage_factory.py).
        knowledge_ingestion_service=storage.knowledge_ingestion_service,
    )

    # 3. Policy Engine & Approval Service
    policy_engine = CosaPolicyEngine()
    approval_service = DurableApprovalService(
        repository=storage.run_repository,
        policy_evaluator=policy_engine.evaluate,
    )

    # 4. Capability Gateway
    connector_grant_client = ConnectorGrantHttpClient(base_url=resolve_platform_control_plane_url())

    async def _connector_grant_resolver(
        connector_id: str, req: GatewayExecutionRequest
    ) -> ConnectorGrant | None:
        return await connector_grant_client.assert_usable(
            connector_id,
            workspace_id=req.workspace_id or "",
            conversation_id=req.context.get("conversation_id", ""),
            action=req.capability_id,
        )

    from apps.cosa.authorization.live_authorizer import LiveAuthorizationAuthorizer

    live_authorizer = LiveAuthorizationAuthorizer(company_client=client)

    gateway = CapabilityGateway(
        registry=cap_registry,
        repository=storage.run_repository,
        policy_evaluator=policy_engine.evaluate,
        governance_store=storage.governance_store,
        connector_grant_resolver=_connector_grant_resolver,
        live_authorizer=live_authorizer,
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
        skill_usage_observer=storage.skill_usage_observer,
    )

    # 5b. Model route resolver (Task 3, plan 2026-09-07-local-first-model-
    # routing) — resolve `ResolvedModelRoute` theo (workspace_id,
    # agent_spec_id), độc lập với việc build model client THẬT (lazy, xem
    # `CosaAgentPlane.__init__`). `system_default` chỉ dùng làm PROVENANCE
    # (persist vào RunRequest.model_policy) khi workspace chưa cấu hình
    # policy/profile nào — KHÔNG dùng để build client (route
    # `is_system_default=True` -> `run_core.run_kernel()` tiếp tục dùng
    # `plane.kernel` (đã build model qua `build_execution_kernel()` ở bước 5
    # phía trên) thay vì build lại, nên system_default ở đây không cần
    # credential_ref/không cần DEEPSEEK_API_KEY hợp lệ).
    resolved_model_route_resolver = model_route_resolver
    if resolved_model_route_resolver is None:
        from apps.cosa.models.contracts import ProviderType, SystemDefaultModelProfile
        from apps.cosa.models.resolver import ModelRouteResolver

        system_default = SystemDefaultModelProfile(
            profile_id="system-default",
            provider_type=ProviderType.DEEPSEEK_API,
            model_id=os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
            credential_ref=None,
        )
        resolved_model_route_resolver = ModelRouteResolver(
            repository=storage.model_routing_repository,
            system_default=system_default,
        )

    # 6. Workflow Engine & Definition Registry
    wf_registry = WorkflowDefinitionRegistry()
    wf_registry.register_version(COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC)
    resolved_workflow_definition_repository = workflow_definition_repository
    workflow_asset_repository: Any
    if resolved_workflow_definition_repository is None:
        resolved_database_url = database_url or os.environ.get("AGENT_DATABASE_URL")
        if resolved_database_url:
            from agent.workflows.postgres_repository import PostgresWorkflowDefinitionRepository

            from agent.assets.repository import PostgresWorkspaceAssetRepository

            wf_definition_engine, wf_definition_session_factory = build_postgres_session_factory(
                resolved_database_url
            )
            storage.created_engines.append(wf_definition_engine)
            resolved_workflow_definition_repository = PostgresWorkflowDefinitionRepository(
                wf_definition_session_factory
            )
            workflow_asset_repository = PostgresWorkspaceAssetRepository(
                wf_definition_session_factory
            )
        else:
            from agent.assets.repository import InMemoryWorkspaceAssetRepository

            resolved_workflow_definition_repository = InMemoryWorkflowDefinitionRepository()
            workflow_asset_repository = InMemoryWorkspaceAssetRepository()
    else:
        resolved_database_url = database_url or os.environ.get("AGENT_DATABASE_URL")
        if resolved_database_url:
            from agent.assets.repository import PostgresWorkspaceAssetRepository

            wf_asset_engine, wf_asset_session_factory = build_postgres_session_factory(
                resolved_database_url
            )
            storage.created_engines.append(wf_asset_engine)
            workflow_asset_repository = PostgresWorkspaceAssetRepository(wf_asset_session_factory)
        else:
            from agent.assets.repository import InMemoryWorkspaceAssetRepository

            workflow_asset_repository = InMemoryWorkspaceAssetRepository()
    from apps.cosa.workflows.deployment_authority_resolver import CompanyDeploymentAuthorityResolver

    workflow_authority_resolver = CompanyDeploymentAuthorityResolver(
        client,
        asset_repository=workflow_asset_repository,
    )

    wf_engine = WorkflowEngine(
        tool_registry=cap_registry,
        gateway=gateway,
        policy_engine=policy_engine,
        approval_service=approval_service,
        governance_store=storage.governance_store,
        kernel=kernel,
        resolver=workflow_authority_resolver,
    )

    # 7. Knowledge ingestion dependencies (Task 4) — chỉ dựng khi feature flag
    # bật; production fail-fast nếu thiếu scanner/sandbox thật đã inject
    # (build_knowledge_ingestion_dependencies tự raise).
    resolved_knowledge_ingestion_deps = knowledge_ingestion_deps
    if resolved_knowledge_ingestion_deps is None:
        from apps.cosa.knowledge_ingestion.contracts import knowledge_ingestion_enabled
        from apps.cosa.knowledge_ingestion.dependencies import (
            build_knowledge_ingestion_dependencies,
        )

        if knowledge_ingestion_enabled():
            resolved_knowledge_ingestion_deps = build_knowledge_ingestion_dependencies(
                database_url=database_url or os.environ.get("AGENT_DATABASE_URL")
            )

    resolved_skill_improvement_service = skill_improvement_service
    if (
        resolved_skill_improvement_service is None
        and storage.skill_improvement_repository is not None
        and storage.spec_registry is not None
        and storage.skill_candidate_store is not None
        and kernel is not None
    ):
        from apps.cosa.skills.improvement_evaluators import SkillEvaluatorRegistry
        from apps.cosa.skills.improvement_policy import EffectiveSkillImprovementPolicy
        from apps.cosa.skills.improvement_service import SkillImprovementService

        resolved_skill_improvement_service = SkillImprovementService(
            repository=storage.skill_improvement_repository,
            spec_registry=storage.spec_registry,
            candidate_store=storage.skill_candidate_store,
            kernel=kernel,
            policy=EffectiveSkillImprovementPolicy(),
            evaluator_registry=SkillEvaluatorRegistry(),
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
        workflow_definition_repository=resolved_workflow_definition_repository,
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
        knowledge_snapshot_repo=storage.knowledge_snapshot_repo,
        knowledge_ingestion_deps=resolved_knowledge_ingestion_deps,
        compliance_resolver=compliance_resolver,
        workspace_settings_client=workspace_settings_client,
        profile_locale_client=profile_locale_client,
        model_route_resolver=resolved_model_route_resolver,
        model_routing_session_factory=storage.model_routing_session_factory,
        model_routing_repository=storage.model_routing_repository,
        project_activity_repository=storage.project_activity_repository,
        project_activity_service=resolved_project_activity_service,
        skill_candidate_store=storage.skill_candidate_store,
        skill_improvement_repository=storage.skill_improvement_repository,
        skill_usage_observer=storage.skill_usage_observer,
        skill_improvement_service=resolved_skill_improvement_service,
    )
