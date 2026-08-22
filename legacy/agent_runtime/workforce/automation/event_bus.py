import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentPlatformEvent(BaseModel):
    """Event data model truyền tải qua Internal Event Bus."""
    event_type: str  # 'TASK_DISPATCHED', 'TASK_COMPLETED', 'APPROVAL_REQUESTED', 'BUDGET_EXCEEDED', 'ROUTINE_TRIGGERED', 'HEARTBEAT_STALLED'
    workspace_id: Optional[int] = None
    agent_key: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InternalEventBus:
    """Trục sự kiện bất đồng bộ nội bộ (In-Memory Async Event Bus) cho COSA."""

    _subscribers: Dict[str, List[Callable[[AgentPlatformEvent], Any]]] = {}

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable[[AgentPlatformEvent], Any]) -> None:
        """Đăng ký lắng nghe một loại sự kiện."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        if handler not in cls._subscribers[event_type]:
            cls._subscribers[event_type].append(handler)

    @classmethod
    def unsubscribe(cls, event_type: str, handler: Callable[[AgentPlatformEvent], Any]) -> None:
        """Hủy đăng ký handler."""
        if event_type in cls._subscribers and handler in cls._subscribers[event_type]:
            cls._subscribers[event_type].remove(handler)

    @classmethod
    def clear(cls) -> None:
        """Xóa toàn bộ subscribers (tiện ích cho unit test)."""
        cls._subscribers.clear()

    @classmethod
    async def publish(cls, event: AgentPlatformEvent) -> None:
        """Phát sự kiện đến tất cả handlers đã đăng ký (Non-blocking)."""
        handlers = cls._subscribers.get(event.event_type, [])
        # Hỗ trợ wildcard '*'
        handlers_all = cls._subscribers.get("*", [])

        all_target_handlers = handlers + handlers_all

        for handler in all_target_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"[EventBus] Error executing handler {handler} for event {event.event_type}: {e}")
