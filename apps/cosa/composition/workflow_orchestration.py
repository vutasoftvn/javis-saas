"""WorkflowOrchestration — narrower interface for workflow orchestration concerns."""

from __future__ import annotations

from typing import Any

from agent.capabilities.gateway import CapabilityGateway
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine
from agent.workflows.repository import WorkflowDefinitionRepository


class WorkflowOrchestration:
    """Encapsulates workflow-related dependencies (gateway, engine, registry, approval service)."""

    def __init__(
        self,
        gateway: CapabilityGateway,
        workflow_engine: WorkflowEngine,
        workflow_registry: WorkflowDefinitionRegistry,
        approval_service: Any,
        workflow_definition_repository: WorkflowDefinitionRepository | None = None,
    ) -> None:
        self.gateway = gateway
        self.workflow_engine = workflow_engine
        self.workflow_registry = workflow_registry
        self.approval_service = approval_service
        self.workflow_definition_repository = workflow_definition_repository

    def get_executor_health(self) -> dict[str, dict[str, Any]]:
        """Health/readiness status for all registered V1 workflow executors."""
        has_authority_resolver = callable(
            getattr(getattr(self.workflow_engine, "_resolver", None), "resolve_authority", None)
        )
        has_skill_resolver = callable(
            getattr(getattr(self.workflow_engine, "_resolver", None), "resolve_skills", None)
        )
        has_definition_repository = self.workflow_definition_repository is not None
        handler_count = len(getattr(self.workflow_engine, "_registered_handlers", {}))
        return {
            "agent": {
                "status": (
                    "ready"
                    if getattr(self.workflow_engine, "_kernel", None) is not None
                    and has_authority_resolver
                    and has_skill_resolver
                    and has_definition_repository
                    else "degraded"
                ),
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
                "handler_count": handler_count,
            },
            "retry": {
                "status": "ready" if handler_count else "degraded",
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

    async def _resolve_pinned_spec(self, manifest: Any, spec: Any | None = None) -> Any:
        """Resolve the exact `WorkflowSpec` pinned by `manifest` from the durable
        definition repository — never the caller's in-memory object, never a
        floating "latest" version (Task 8-10 exact-hash pin contract). Shared by
        `execute_manifest` (fresh run) and `resume_manifest` (Task 11) so a resume
        re-verifies the exact same pin instead of re-deriving its own copy."""
        if self.workflow_definition_repository is None:
            raise RuntimeError(
                "Durable workflow definition repository is required for manifest execution"
            )

        record = await self.workflow_definition_repository.get_definition(
            manifest.workflow_asset_id,
            manifest.workflow_version,
            workspace_id=manifest.workspace_id,
        )
        if record is None:
            raise ValueError(
                f"Durable workflow definition not found for manifest {getattr(manifest, 'run_id', 'unknown')}"
            )

        from agent.workflows.schema import WorkflowSpec

        resolved_spec = WorkflowSpec.model_validate(record.spec_data)
        resolved_hash = resolved_spec.definition_hash or resolved_spec.compute_hash()
        if (
            resolved_spec.id != manifest.workflow_asset_id
            or resolved_spec.version != manifest.workflow_version
            or resolved_hash != record.definition_hash
            or record.definition_hash != manifest.workflow_definition_hash
        ):
            raise ValueError(
                "Resolved workflow definition does not match the exact manifest definition hash pin"
            )
        if spec is not None:
            supplied_hash = getattr(spec, "definition_hash", None) or spec.compute_hash()
            if (
                spec.id != resolved_spec.id
                or spec.version != resolved_spec.version
                or supplied_hash != resolved_hash
            ):
                raise ValueError(
                    "Caller-supplied workflow definition does not match the durable manifest pin"
                )
        return resolved_spec

    def _seed_manifest_state(self, state: dict[str, Any], manifest: Any) -> dict[str, Any]:
        state["_manifest"] = manifest
        if hasattr(manifest, "workspace_id"):
            state["workspace_id"] = manifest.workspace_id
        if hasattr(manifest, "project_id"):
            state["project_id"] = manifest.project_id
        if getattr(manifest, "project_agent_deployment_id", None):
            state["project_agent_deployment_id"] = manifest.project_agent_deployment_id
        # Task 11 — the durable `run_id` (NOT the ephemeral in-memory
        # `Workflow.id`) must be reachable from step state: `GatewayToolCallStep`
        # uses it to namespace its gateway invocation, and `ApprovalGateStep`
        # threads it into the CHANGE_REQUEST's `RunApprovalRecord.run_id` so an
        # approved `workflow_gate` can be resolved back to the exact
        # `governed_workflow_run` to resume.
        if getattr(manifest, "run_id", None):
            state["run_id"] = manifest.run_id
        return state

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
        resolved_spec = await self._resolve_pinned_spec(manifest, spec)
        state = self._seed_manifest_state(dict(initial_state or {}), manifest)
        return await self.workflow_engine.execute_spec(resolved_spec, initial_state=state)

    async def resume_manifest(
        self,
        manifest: Any,
        workflow: Any,
        *,
        spec: Any | None = None,
    ) -> Any:
        """Resume a previously paused (`WAITING_APPROVAL`) governed workflow run
        (Task 11) — `workflow` is the exact `Workflow` DAG state reloaded from
        the caller's durable checkpoint, never a fresh instance. Re-resolves the
        pinned spec (same exact-hash contract as `execute_manifest`) rather than
        trusting whatever `WorkflowSpec` object happens to be in memory, so a
        worker restart between pause and resume can never silently pick up a
        newer published workflow version."""
        resolved_spec = await self._resolve_pinned_spec(manifest, spec)
        self._seed_manifest_state(workflow.state, manifest)
        return await self.workflow_engine.resume_spec(workflow, resolved_spec)


class IWorkflowOrchestration:
    """Public interface for consumers — type hint only."""

    gateway: CapabilityGateway
    workflow_engine: WorkflowEngine
    workflow_registry: WorkflowDefinitionRegistry
    approval_service: Any
    workflow_definition_repository: WorkflowDefinitionRepository | None

    def get_executor_health(self) -> dict[str, dict[str, Any]]: ...

    async def execute_spec(
        self,
        spec: Any,
        *,
        initial_state: dict[str, Any],
        custom_step_builders: Any = None,
    ) -> Any: ...

    async def execute_manifest(
        self,
        manifest: Any,
        *,
        initial_state: dict[str, Any] | None = None,
        spec: Any | None = None,
    ) -> Any: ...

    async def resume_manifest(
        self,
        manifest: Any,
        workflow: Any,
        *,
        spec: Any | None = None,
    ) -> Any: ...
