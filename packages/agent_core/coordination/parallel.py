from __future__ import annotations

import asyncio
from typing import Any, NamedTuple

from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec

__all__ = ["ParallelCoordinator", "ParallelResult", "ParallelTask"]


class ParallelTask(NamedTuple):
    task_id: str
    spec: AgentSpec
    input_payload: dict[str, Any]


class ParallelResult:
    def __init__(
        self,
        completed_results: dict[str, Any],
        failed_tasks: dict[str, str],
        all_succeeded: bool,
    ) -> None:
        self.completed_results = completed_results
        self.failed_tasks = failed_tasks
        self.all_succeeded = all_succeeded


class ParallelCoordinator:
    """Primitive điều phối chạy song song đa specialist (fan-out & join)."""

    def __init__(self, kernel: ExecutionKernel) -> None:
        self._kernel = kernel

    async def execute_parallel(
        self,
        tasks: list[ParallelTask],
        principal: str = "parallel_coordinator",
        correlation_id: str | None = None,
    ) -> ParallelResult:
        if not tasks:
            return ParallelResult(completed_results={}, failed_tasks={}, all_succeeded=True)

        # P1 Task 7: fan-out qua asyncio.gather chỉ dành cho local pure computation.
        # Delegation có side effect phải đi qua DurableSupervisor (child task bền +
        # idempotency + Capability Gateway ở mỗi action).
        from agent_core.coordination.durable_supervisor import spec_has_write_capability

        for t in tasks:
            if spec_has_write_capability(getattr(t.spec, "capability_refs", ())):
                raise RuntimeError(
                    f"ParallelCoordinator is for local pure computation only; task "
                    f"'{t.task_id}' has a write-capable spec — use DurableSupervisor (P1 Task 7)"
                )

        async def run_one(t: ParallelTask) -> tuple[str, RunResult]:
            req = RunRequest(
                principal=principal,
                root_executable_ref=t.spec.to_pinned_identity(),
                input=t.input_payload,
                correlation_id=correlation_id,
            )
            res = await self._kernel.run(req, t.spec)
            return t.task_id, res

        results = await asyncio.gather(*(run_one(t) for t in tasks))

        completed: dict[str, Any] = {}
        failed: dict[str, str] = {}

        for task_id, res in results:
            if res.status == RunStatus.COMPLETED:
                completed[task_id] = res.final_output
            else:
                err_msg = (
                    ", ".join(res.errors) if res.errors else f"Run failed with status {res.status}"
                )
                failed[task_id] = err_msg

        return ParallelResult(
            completed_results=completed,
            failed_tasks=failed,
            all_succeeded=len(failed) == 0,
        )
