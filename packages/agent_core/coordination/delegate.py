from __future__ import annotations

from typing import Any, Optional
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec

__all__ = ["SpecialistDelegate"]


class SpecialistDelegate:
    """Primitive uỷ quyền tác vụ chuyên môn cho specialist agent sử dụng ExecutionKernel."""

    def __init__(self, kernel: ExecutionKernel) -> None:
        self._kernel = kernel

    async def delegate(
        self,
        specialist_spec: AgentSpec,
        task_input: dict[str, Any],
        principal: str = "supervisor",
        parent_correlation_id: Optional[str] = None,
    ) -> RunResult:
        request = RunRequest(
            principal=principal,
            root_executable_ref=specialist_spec.to_pinned_identity(),
            input=task_input,
            correlation_id=parent_correlation_id,
        )
        return await self._kernel.run(request, specialist_spec)
