from __future__ import annotations

from typing import Optional

from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.capabilities.gateway import CapabilityGateway
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.runs.repository import InMemoryRunRepository, RunRepository
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
        capability_registry: CapabilityRegistry,
        policy_engine: CosaPolicyEngine,
        approval_service: DurableApprovalService,
        gateway: CapabilityGateway,
        kernel: OpenAIAgentsKernel,
        workflow_registry: WorkflowDefinitionRegistry,
        workflow_engine: WorkflowEngine,
        company_client: CompanyServiceClient,
    ) -> None:
        self.repository = repository
        self.capability_registry = capability_registry
        self.policy_engine = policy_engine
        self.approval_service = approval_service
        self.gateway = gateway
        self.kernel = kernel
        self.workflow_registry = workflow_registry
        self.workflow_engine = workflow_engine
        self.company_client = company_client


def build_cosa_agent_plane(
    *,
    repository: Optional[RunRepository] = None,
    company_client: Optional[CompanyServiceClient] = None,
    default_model: str = "deepseek-chat",
) -> CosaAgentPlane:
    """Khởi tạo hoàn chỉnh một môi trường CosaAgentPlane."""
    repo = repository or InMemoryRunRepository()
    client = company_client or CompanyServiceClient()

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
    )

    # 4. Execution Kernel
    kernel = OpenAIAgentsKernel(
        repository=repo,
        capability_executor=gateway.execute,
        policy_evaluator=policy_engine.evaluate,
    )


    # 5. Workflow Engine & Definition Registry
    wf_registry = WorkflowDefinitionRegistry()
    wf_registry.register_version(COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC)

    wf_engine = WorkflowEngine(
        tool_registry=cap_registry,
    )

    return CosaAgentPlane(
        repository=repo,
        capability_registry=cap_registry,
        policy_engine=policy_engine,
        approval_service=approval_service,
        gateway=gateway,
        kernel=kernel,
        workflow_registry=wf_registry,
        workflow_engine=wf_engine,
        company_client=client,
    )
