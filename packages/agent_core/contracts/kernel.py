from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from agent_core.contracts.run import RunRequest, RunResult
from agent_core.contracts.spec import AgentSpec

__all__ = ["ExecutionKernel"]


@runtime_checkable
class ExecutionKernel(Protocol):
    """Giao thức ExecutionKernel Protocol theo Master Guide §9.1.

    Sở hữu vòng lặp model/tool reasoning, sinh tool-call, handoff agent-as-tool,
    streaming execution events và quản lý interruption state của SDK.

    Không trực tiếp sở hữu business authorization hoặc canonical database persistence.
    """

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        """Khởi chạy một Run mới từ đầu đến trạng thái hoàn thành hoặc tạm dừng."""
        ...

    async def resume(
        self,
        run_id: str,
        checkpoint_ref: str,
        updates: dict[str, Any],
    ) -> RunResult:
        """Nạp lại trạng thái từ checkpoint và tiếp tục thực thi sau khi được unblock/approve."""
        ...

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        """Hủy bỏ Run đang thực thi."""
        ...

    async def stream(
        self,
        request: RunRequest,
        spec: AgentSpec,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream các sự kiện thực thi trong thời gian thực (events stream)."""
        ...
