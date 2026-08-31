"""WorkflowOrchestration — narrower interface for workflow orchestration concerns."""

from __future__ import annotations

from typing import Any

from agent.capabilities.gateway import CapabilityGateway
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine


class WorkflowOrchestration:
    """Encapsulates workflow-related dependencies (gateway, engine, registry, approval service)."""

    def __init__(
        self,
        gateway: CapabilityGateway,
        workflow_engine: WorkflowEngine,
        workflow_registry: WorkflowDefinitionRegistry,
        approval_service: Any,
    ) -> None:
        self.gateway = gateway
        self.workflow_engine = workflow_engine
        self.workflow_registry = workflow_registry
        self.approval_service = approval_service


class IWorkflowOrchestration:
    """Public interface for consumers — type hint only."""

    gateway: CapabilityGateway
    workflow_engine: WorkflowEngine
    workflow_registry: WorkflowDefinitionRegistry
    approval_service: Any
