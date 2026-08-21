# backend/app/workforce/agents/orchestration/adk/governed_tool.py
"""ADK BaseTool cho primitive ToolInvocation (ngắn hạn) — KHÔNG dùng cho công việc
durable/dài hạn (DeepSeek delegation), primitive đó đi qua TaskBoardService (xem
specialist_delegation_node.py, Task 16).

ExecutionScope PHẢI dựng từ context tin cậy phía server (scope_factory do caller ở
Task 20 cấp, lấy từ AgentRun/Outcome đã xác thực) — KHÔNG BAO GIỜ đọc từ
tool_context.state, vì đó là session state mà 1 LLM node phía trước có thể đã ghi
vào (xem Quyết định 1, mục "ExecutionScope phải dựng từ context tin cậy phía server").
"""
from typing import Any, Callable

from sqlalchemy.orm import Session

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.tools.invocation.contracts import ToolInvocationRequest
from app.workforce.tools.invocation.service import ToolInvocationService


class CosaGovernedTool(BaseTool):
    """Bọc 1 ToolSpec đã đăng ký trong app.core.tool_registry thành 1 ADK BaseTool,
    đi qua đúng governance pipeline mà DeepSeekHarnessAdapter.dispatch_tool_call
    dùng (PolicyGate -> GovernanceKernel -> NativeDispatcher/CapabilityBridge)."""

    def __init__(
        self,
        *,
        tool_flat_name: str,
        db_factory: Callable[[], Session],
        scope_factory: Callable[[], ExecutionScope],
        run_id_factory: Callable[[], int | None],
        source: str = "adk_workflow",
        description: str = "",
    ) -> None:
        super().__init__(name=tool_flat_name, description=description or f"Governed tool: {tool_flat_name}")
        self._tool_flat_name = tool_flat_name
        self._db_factory = db_factory
        self._scope_factory = scope_factory
        self._run_id_factory = run_id_factory
        self._source = source
        self._service = ToolInvocationService()

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        db = self._db_factory()
        scope = self._scope_factory()
        request = ToolInvocationRequest(
            scope=scope,
            tool_flat_name=self._tool_flat_name,
            arguments=dict(args),
            source=self._source,
            run_id=self._run_id_factory(),
        )
        result = await self._service.invoke(db, request)
        if result.status == "success":
            return result.output
        if result.status == "approval_required":
            return {"status": "approval_required", "approval_id": result.approval_id, "message": result.error_message}
        return {"status": result.status, "error": result.error_message}
