from __future__ import annotations

from typing import Any

from agent.contracts.run import RunRequest
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
        if manifest is None:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="Governed workflow manifest is required for an AGENT step",
            )
        workspace_id = manifest.workspace_id or state.get("workspace_id")
        project_id = manifest.project_id or state.get("project_id")
        dep_id = (
            self._project_agent_deployment_id
            or manifest.project_agent_deployment_id
            or state.get("project_agent_deployment_id")
        )
        if not workspace_id or not project_id or not dep_id:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="AGENT step requires workspace, project, and project agent deployment authority",
            )
        if self._resolver is None or not hasattr(self._resolver, "resolve_authority"):
            return StepOutcome(
                status=StepStatus.FAILED,
                error="Live deployment authority resolver is required for an AGENT step",
            )

        # 1. Authority resolution: verify live deployment status
        agent_spec_info: dict[str, Any] | None = None
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
        if auth_ws != workspace_id:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Deployment workspace mismatch: expected {workspace_id}, got {auth_ws}",
            )
        if auth_proj != project_id:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Deployment project mismatch: expected {project_id}, got {auth_proj}",
            )

        agent_spec_info = auth.get("agentSpec") or auth.get("agent_spec")

        # 2. Match pinned agent spec from manifest
        pinned_specs = manifest.pinned_agent_specs
        if not agent_spec_info or not pinned_specs:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="AGENT step requires a live AgentSpec and an exact manifest pin",
            )
        spec_id = agent_spec_info.get("id")
        version = agent_spec_info.get("version")
        definition_hash = agent_spec_info.get("definitionHash") or agent_spec_info.get(
            "definition_hash"
        )
        pinned_spec = pinned_specs.get(spec_id) if spec_id else None
        if not isinstance(pinned_spec, dict):
            return StepOutcome(
                status=StepStatus.FAILED,
                error="Live AgentSpec is not pinned in the workflow manifest",
            )
        pinned_version = pinned_spec.get("version")
        pinned_hash = pinned_spec.get("definition_hash") or pinned_spec.get("definitionHash")
        if (
            not spec_id
            or not version
            or not definition_hash
            or version != pinned_version
            or definition_hash != pinned_hash
        ):
            return StepOutcome(
                status=StepStatus.FAILED,
                error="Live AgentSpec does not match the exact manifest pin",
            )

        # 3. Resolve skills through scoped resolver
        if self._resolver is not None and hasattr(self._resolver, "resolve_skills"):
            skill_refs = manifest.pinned_skill_specs
            if skill_refs:
                try:
                    await self._resolver.resolve_skills(workspace_id, skill_refs)
                except Exception as exc:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Skill resolution failed: {exc}",
                    )
        elif manifest.pinned_skill_specs:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="Scoped skill resolver is required for pinned workflow skills",
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
