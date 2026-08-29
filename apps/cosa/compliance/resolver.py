from __future__ import annotations

from typing import Any
from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec

from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)
from apps.cosa.compliance.company_client import AiComplianceClient


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
            raise ComplianceDenied("MISSING_WORKSPACE_ID", "Workspace ID is required for AI compliance resolution")

        run_id = getattr(request, "run_id", None) or getattr(request, "id", None) or "run_initial"
        system_key = spec.id

        policy_snapshot_hash = None
        if request.metadata:
            policy_snapshot_hash = (
                request.metadata.get("policy_snapshot_ref")
                or request.metadata.get("policy_snapshot_hash")
            )

        try:
            snapshot = await self._client.resolve_snapshot(
                workspace_id=workspace_id,
                run_id=run_id,
                system_key=system_key,
                policy_snapshot_hash=policy_snapshot_hash,
            )
        except AiComplianceUnavailable as err:
            raise ComplianceDenied(err.code, str(err)) from err

        return {
            "compliance_snapshot": snapshot.model_dump(),
            "compliance_snapshot_ref": snapshot.snapshot_hash,
            "compliance_snapshot_version": snapshot.data_profile_version,
        }
