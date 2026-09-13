"""Shared live Company deployment/grant/policy-epoch re-authorization used by
more than one workflow step type (`GatewayToolCallStep`, `ApprovalGateStep`
continuation). `AgentWorkflowStep` (packages/agent/workflows/agent_step.py)
does its own inline version of this same check plus an additional AgentSpec
pin comparison it alone needs — this module intentionally covers only the
piece that's actually shared (deployment state + workspace/project scope),
so a paused/revoked Company deployment fails closed the exact same way no
matter which step type hit it, without inventing a second mechanism.
"""

from __future__ import annotations

from typing import Any

__all__ = ["check_live_deployment_authority", "resolve_deployment_context"]


def resolve_deployment_context(
    state: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """Extract (workspace_id, project_id, project_agent_deployment_id) from a
    workflow step's state — preferring the pinned `GovernedWorkflowRunManifest`
    (`_manifest`/`manifest` key, seeded by `WorkflowOrchestration`) over loose
    state keys, since the manifest is the durable, tamper-evident source."""
    manifest = state.get("_manifest") or state.get("manifest")
    if manifest is not None:
        return (
            getattr(manifest, "workspace_id", None) or state.get("workspace_id"),
            getattr(manifest, "project_id", None) or state.get("project_id"),
            getattr(manifest, "project_agent_deployment_id", None)
            or state.get("project_agent_deployment_id"),
        )
    return (
        state.get("workspace_id"),
        state.get("project_id"),
        state.get("project_agent_deployment_id"),
    )


async def check_live_deployment_authority(
    resolver: Any,
    *,
    workspace_id: str,
    project_id: str,
    project_agent_deployment_id: str,
) -> tuple[bool, str | None]:
    """Re-resolve the live Company `project_agent_deployment` authority right
    before an effect (tool call, or completing a paused approval gate) runs.
    Returns `(True, None)` when authority still holds, or `(False,
    safe_reason_code)` — never a raw exception string — on any mismatch,
    pause/revoke or resolver failure, so the caller fails closed."""
    try:
        auth = await resolver.resolve_authority(
            workspace_id, project_id, project_agent_deployment_id
        )
    except Exception:
        return False, "deployment_authority_unavailable"

    if auth.get("state") != "ACTIVE":
        return False, "deployment_not_active"

    auth_workspace_id = auth.get("workspaceId") or auth.get("workspace_id")
    auth_project_id = auth.get("projectId") or auth.get("project_id")
    if auth_workspace_id != workspace_id or auth_project_id != project_id:
        return False, "deployment_scope_mismatch"

    return True, None
