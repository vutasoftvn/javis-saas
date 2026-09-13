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

    def get_executor_health(self) -> dict[str, dict[str, Any]]:
        """Health/readiness status for all registered V1 workflow executors."""
        return {
            "agent": {
                "status": "ready" if getattr(self.workflow_engine, "_kernel", None) is not None else "degraded",
                "registered": True,
            },
            "tool_call": {
                "status": "ready" if self.gateway is not None else "degraded",
                "registered": True,
            },
            "approval_gate": {
                "status": "ready" if self.approval_service is not None else "degraded",
                "registered": True,
            },
            "deterministic": {
                "status": "ready",
                "registered": True,
                "handler_count": len(getattr(self.workflow_engine, "_registered_handlers", {})),
            },
            "retry": {
                "status": "ready",
                "registered": True,
            },
        }

    async def execute_spec(
        self,
        spec: Any,
        *,
        initial_state: dict[str, Any],
        custom_step_builders: Any = None,
    ) -> Any:
        return await self.workflow_engine.execute_spec(
            spec, initial_state=initial_state, custom_step_builders=custom_step_builders
        )

    async def execute_manifest(
        self,
        manifest: Any,
        *,
        initial_state: dict[str, Any] | None = None,
        spec: Any | None = None,
    ) -> Any:
        """Execute a governed workflow run manifest using explicit registered executors.

        Obtains builders from the explicit engine registry; must never synthesize
        generic fallbacks for arbitrary input steps.
        """
        resolved_spec = spec
        if resolved_spec is None and self.workflow_registry is not None:
            asset_id = getattr(manifest, "workflow_asset_id", None)
            version = getattr(manifest, "workflow_version", None)
            if asset_id:
                try:
                    resolved_spec = self.workflow_registry.get_version(asset_id, version or "1.0.0")
                except Exception:
                    resolved_spec = None

        if resolved_spec is None:
            manifest_json = getattr(manifest, "manifest_json", {})
            if manifest_json and "workflow_spec" in manifest_json:
                from agent.workflows.schema import WorkflowSpec

                resolved_spec = WorkflowSpec.model_validate(manifest_json["workflow_spec"])

        if resolved_spec is None:
            raise ValueError(
                f"Workflow spec not found for manifest {getattr(manifest, 'run_id', 'unknown')}"
            )

        state = dict(initial_state or {})
        state["_manifest"] = manifest
        if hasattr(manifest, "workspace_id"):
            state["workspace_id"] = manifest.workspace_id
        if hasattr(manifest, "project_id"):
            state["project_id"] = manifest.project_id
        if getattr(manifest, "project_agent_deployment_id", None):
            state["project_agent_deployment_id"] = manifest.project_agent_deployment_id

        return await self.workflow_engine.execute_spec(resolved_spec, initial_state=state)


class IWorkflowOrchestration:
    """Public interface for consumers — type hint only."""

    gateway: CapabilityGateway
    workflow_engine: WorkflowEngine
    workflow_registry: WorkflowDefinitionRegistry
    approval_service: Any

    def get_executor_health(self) -> dict[str, dict[str, Any]]:
        ...

    async def execute_spec(
        self,
        spec: Any,
        *,
        initial_state: dict[str, Any],
        custom_step_builders: Any = None,
    ) -> Any:
        ...

    async def execute_manifest(
        self,
        manifest: Any,
        *,
        initial_state: dict[str, Any] | None = None,
        spec: Any | None = None,
    ) -> Any:
        ...
