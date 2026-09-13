from __future__ import annotations

from typing import Any

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.governance.contracts import PinnedSpecIdentity
from agent.workflows.models import StepOutcome, StepStatus

__all__ = ["AgentWorkflowStep"]


class AgentWorkflowStep:
    """Executes a pinned Agent workflow step governed by Company authority."""

    def __init__(
        self,
        resolver: Any | None = None,
        kernel: Any | None = None,
        *,
        name: str = "agent_step",
        output_key: str = "agent_output",
        project_agent_deployment_id: str | None = None,
    ) -> None:
        self.name = name
        self._resolver = resolver
        self._kernel = kernel
        self._output_key = output_key
        self._project_agent_deployment_id = project_agent_deployment_id

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        manifest = state.get("_manifest") or state.get("manifest")
        workspace_id = (
            (manifest.workspace_id if manifest else None)
            or state.get("workspace_id")
            or "default"
        )
        project_id = (
            (manifest.project_id if manifest else None)
            or state.get("project_id")
            or "default"
        )
        dep_id = (
            self._project_agent_deployment_id
            or (manifest.project_agent_deployment_id if manifest else None)
            or state.get("project_agent_deployment_id")
        )

        # 1. Authority resolution: verify live deployment status
        agent_spec_info: dict[str, Any] | None = None
        if self._resolver is not None and hasattr(self._resolver, "resolve_authority") and dep_id:
            try:
                auth = await self._resolver.resolve_authority(workspace_id, project_id, dep_id)
            except Exception as exc:
                return StepOutcome(
                    status=StepStatus.FAILED,
                    error=f"Failed to resolve deployment authority for '{dep_id}': {exc}",
                )

            auth_state = auth.get("state")
            if auth_state != "ACTIVE":
                return StepOutcome(
                    status=StepStatus.FAILED,
                    error=f"Deployment '{dep_id}' is not active (status: {auth_state})",
                )

            # Check workspace and project matching
            auth_ws = auth.get("workspaceId") or auth.get("workspace_id")
            auth_proj = auth.get("projectId") or auth.get("project_id")
            if auth_ws and auth_ws != workspace_id:
                return StepOutcome(
                    status=StepStatus.FAILED,
                    error=f"Deployment workspace mismatch: expected {workspace_id}, got {auth_ws}",
                )
            if auth_proj and auth_proj != project_id:
                return StepOutcome(
                    status=StepStatus.FAILED,
                    error=f"Deployment project mismatch: expected {project_id}, got {auth_proj}",
                )

            agent_spec_info = auth.get("agentSpec") or auth.get("agent_spec")

        # 2. Match pinned agent spec from manifest
        pinned_specs = manifest.pinned_agent_specs if manifest else {}
        spec_id = "default_agent"
        version = "1.0.0"
        definition_hash = "sha256:default"

        if agent_spec_info:
            spec_id = agent_spec_info.get("id", spec_id)
            version = agent_spec_info.get("version", version)
            definition_hash = (
                agent_spec_info.get("definitionHash")
                or agent_spec_info.get("definition_hash")
                or definition_hash
            )
        elif pinned_specs:
            first_key = next(iter(pinned_specs))
            spec_id = first_key
            spec_meta = pinned_specs[first_key]
            if isinstance(spec_meta, dict):
                version = spec_meta.get("version", version)
                definition_hash = (
                    spec_meta.get("definition_hash")
                    or spec_meta.get("definitionHash")
                    or definition_hash
                )

        # 3. Resolve skills through scoped resolver
        if self._resolver is not None and hasattr(self._resolver, "resolve_skills"):
            skill_refs = manifest.pinned_skill_specs if manifest else {}
            if skill_refs:
                try:
                    await self._resolver.resolve_skills(workspace_id, skill_refs)
                except Exception as exc:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Skill resolution failed: {exc}",
                    )

        # 4. Construct PinnedSpecIdentity and RunRequest
        root_ref = PinnedSpecIdentity(
            spec_kind="agent",
            spec_id=spec_id,
            spec_version=version,
            definition_hash=definition_hash,
        )

        prompt_input = (
            state.get("task_prompt")
            or state.get("input")
            or state.get("inputs")
            or {"prompt": "Execute agent workflow task"}
        )
        if isinstance(prompt_input, str):
            prompt_input = {"prompt": prompt_input}

        metadata: dict[str, Any] = {
            "project_id": project_id,
            "project_agent_deployment_id": dep_id,
        }
        if manifest:
            metadata["manifest_hash"] = manifest.manifest_hash
            metadata["run_id"] = manifest.run_id

        request = RunRequest(
            principal="workflow_executor",
            workspace_id=workspace_id,
            root_executable_ref=root_ref,
            input=prompt_input,
            metadata=metadata,
        )

        # 5. Invoke kernel
        if self._kernel is None:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="No kernel registered for AgentWorkflowStep",
            )

        try:
            result = await self._kernel.run(request)
        except Exception as exc:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Kernel run execution failed: {exc}",
            )

        status_val = getattr(result, "status", None)
        status_str = str(getattr(status_val, "value", status_val) or "").upper()
        if status_str not in ("COMPLETED", "SUCCESS"):
            err = getattr(result, "error", None) or "Agent kernel run did not complete successfully"
            return StepOutcome(status=StepStatus.FAILED, error=err)

        output = getattr(result, "final_output", result)
        return StepOutcome(
            status=StepStatus.COMPLETED,
            updates={self._output_key: output},
        )
