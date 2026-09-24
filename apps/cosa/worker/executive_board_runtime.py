"""Adapter chạy advisor overlay qua đường run chung của COSA (compliance + model routing).

`packages/agent` không biết Company/compliance/model routing, nên `ExecutiveBoardRunner`
chỉ cần 1 `ExecutionKernel`; adapter này là kernel đó ở tầng composition (`apps/cosa`).
"""

from __future__ import annotations

from typing import Any

from agent.contracts.run import RunRequest, RunResult
from agent.contracts.spec import AgentSpec
from agent.executive_board.runner import ExecutiveBoardRunner

from apps.cosa.agents.advisor_overlay_validation import validate_advisor_overlay
from apps.cosa.worker.run_core import RunCoreError, apply_compliance, run_kernel

__all__ = ["PlaneRoutedAdvisorKernel", "build_executive_board_runner"]


class PlaneRoutedAdvisorKernel:
    """`ExecutionKernel` conformant: mọi advisor run đi qua compliance gate rồi model routing."""

    def __init__(self, plane: Any) -> None:
        self._plane = plane

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        deployment_spec = await self._resolve_deployment_spec(request)
        # Overlay không có quyền Project độc lập: compliance đánh giá theo spec của Project
        # deployment (system_key = deployment spec id) nhưng chỉ với capability của overlay,
        # nên delegation không bao giờ rộng hơn những gì overlay thật sự dùng.
        compliance_spec = deployment_spec.model_copy(
            update={"capability_refs": list(spec.capability_refs)}
        )
        prep = await apply_compliance(
            self._plane, req=request, spec=spec, compliance_spec=compliance_spec
        )
        result, _ = await run_kernel(
            self._plane,
            prep,
            workspace_id=request.workspace_id or "",
            run_id=request.run_id or "",
        )
        return result

    async def _resolve_deployment_spec(self, request: RunRequest) -> AgentSpec:
        meta = request.metadata
        spec_id = meta.get("deployment_spec_id")
        version = meta.get("deployment_spec_version")
        spec_hash = meta.get("deployment_spec_hash")
        if not (spec_id and version and spec_hash):
            raise RunCoreError("deployment_pin_missing")
        record = await self._plane.spec_registry.get(
            spec_kind="agent", spec_id=spec_id, version=version
        )
        if record is None or record.definition_hash != spec_hash:
            raise RunCoreError("deployment_pin_drift")
        return AgentSpec(**record.content)


def build_executive_board_runner(plane: Any) -> ExecutiveBoardRunner:
    return ExecutiveBoardRunner(
        kernel=PlaneRoutedAdvisorKernel(plane),
        spec_registry=plane.spec_registry,
        overlay_validator=validate_advisor_overlay,
    )
