"""
COSA Tool Execution Dispatcher
Điều phối thực thi công cụ, kết nối Event Store và chốt chặn an toàn Approval Gateway (Structure.md Mục 11, 27, 28).
"""
import time
from typing import Any, Dict, Optional
from agent.events.base import AgentEvent, EventStoreInterface, EventType
from tools.base import BaseTool, RiskLevel, ToolResult
from tools.registry import ToolRegistry, tool_registry


class ToolDispatcher:
    """Bộ điều phối thực thi Tool có giám sát sự kiện và kiểm soát rủi ro"""

    def __init__(
        self, 
        registry: Optional[ToolRegistry] = None, 
        event_store: Optional[EventStoreInterface] = None
    ):
        self.registry = registry or tool_registry
        self.event_store = event_store

    async def dispatch(
        self,
        tool_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        session_id: Optional[str] = None,
        actor_id: str = "agent",
        approved_by: Optional[str] = None
    ) -> ToolResult:
        """Thực thi công cụ với đầy đủ kiểm tra rủi ro và phát sinh nhật ký sự kiện"""
        tool = self.registry.get(tool_id)
        if not tool:
            return ToolResult(
                status="error",
                error=f"Tool '{tool_id}' not found in registry",
                metadata={"tool_id": tool_id}
            )

        # 1. CHỐT CHẶN RỦI RO (APPROVAL INTERCEPTOR)
        if tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not approved_by:
            if self.event_store and session_id:
                await self.event_store.append(
                    AgentEvent(
                        session_id=session_id,
                        type=EventType.APPROVAL_REQUESTED,
                        actor={"type": "agent", "id": actor_id},
                        payload={
                            "tool_id": tool_id,
                            "risk_level": tool.risk_level.value,
                            "action_summary": f"Yêu cầu phê duyệt thực thi công cụ nguy hiểm {tool_id}",
                            "action_payload": input_data
                        },
                        metadata={"risk_level": tool.risk_level.value}
                    )
                )

            return ToolResult(
                status="pending_approval",
                data=None,
                metadata={"risk_level": tool.risk_level.value, "tool_id": tool_id},
                presenter_payload={
                    "view_type": "approval_request_card",
                    "title": f"Yêu cầu Phê Duyệt Quyền {tool.risk_level.value}",
                    "tool_id": tool_id,
                    "risk_level": tool.risk_level.value,
                    "input_params": input_data,
                    "action_required": "Founder / Admin Approval required"
                }
            )

        # 2. PHÁT SINH EVENT TOOL.REQUESTED
        if self.event_store and session_id:
            await self.event_store.append(
                AgentEvent(
                    session_id=session_id,
                    type=EventType.TOOL_REQUESTED,
                    actor={"type": "agent", "id": actor_id},
                    payload={"tool_id": tool_id, "input_data": input_data},
                    metadata={"risk_level": tool.risk_level.value}
                )
            )

        # 3. THỰC THI TOOL
        start_time = time.time()
        try:
            result = await tool.execute(input_data, context)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ToolResult(
                status="error",
                error=str(e),
                metadata={"duration_ms": duration_ms, "tool_id": tool_id}
            )

        duration_ms = int((time.time() - start_time) * 1000)
        result.metadata["duration_ms"] = duration_ms
        result.metadata["tool_id"] = tool_id

        # Format presenter mặc định nếu tool chưa tự sinh
        if not result.presenter_payload:
            result.presenter_payload = tool.format_presenter(result.data)

        # 4. PHÁT SINH EVENT TOOL.COMPLETED
        if self.event_store and session_id:
            await self.event_store.append(
                AgentEvent(
                    session_id=session_id,
                    type=EventType.TOOL_COMPLETED,
                    actor={"type": "agent", "id": actor_id},
                    payload={
                        "tool_id": tool_id,
                        "status": result.status,
                        "presenter_payload": result.presenter_payload,
                        "has_side_effects": tool.risk_level != RiskLevel.LOW
                    },
                    metadata={"duration_ms": duration_ms}
                )
            )

        return result
