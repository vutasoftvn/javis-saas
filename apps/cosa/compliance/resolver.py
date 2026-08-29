from __future__ import annotations

from typing import Any

from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec

from apps.cosa.compliance.company_client import AiComplianceClient
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)


class ComplianceResolver:
    def __init__(self, client: AiComplianceClient | None = None) -> None:
        self._client = client or AiComplianceClient()

    async def resolve_for_run(
        self,
        request: RunRequest,
        spec: AgentSpec,
    ) -> dict[str, Any]:
        workspace_id = request.workspace_id
        if not workspace_id:
            raise ComplianceDenied(
                "MISSING_WORKSPACE_ID", "Workspace ID is required for AI compliance resolution"
            )

        run_id = getattr(request, "run_id", None) or getattr(request, "id", None) or "run_initial"
        system_key = spec.id

        policy_snapshot_hash = None
        if request.metadata:
            policy_snapshot_hash = request.metadata.get(
                "policy_snapshot_ref"
            ) or request.metadata.get("policy_snapshot_hash")

        try:
            snapshot = await self._client.resolve_snapshot(
                workspace_id=workspace_id,
                run_id=run_id,
                system_key=system_key,
                policy_snapshot_hash=policy_snapshot_hash,
            )
        except AiComplianceUnavailable as err:
            raise ComplianceDenied(err.code, str(err)) from err

        snap_dict = snapshot.model_dump() if hasattr(snapshot, "model_dump") else snapshot
        snap_hash = getattr(snapshot, "snapshot_hash", None) or (
            snap_dict.get("snapshot_hash") if isinstance(snap_dict, dict) else "sha256:mock"
        )
        snap_version = getattr(snapshot, "data_profile_version", None) or (
            snap_dict.get("data_profile_version") if isinstance(snap_dict, dict) else "v1"
        )

        return {
            "compliance_snapshot": snap_dict,
            "compliance_snapshot_ref": snap_hash,
            "compliance_snapshot_version": snap_version,
        }
