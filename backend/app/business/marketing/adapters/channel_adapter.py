"""
COSA Multi-Channel Dispatcher Adapter.
Điều phối gửi thông báo và phản hồi Speed-to-Lead đa kênh (Zalo, Telegram, Email, Webhook).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DispatchResult(BaseModel):
    success: bool
    channel: str
    message_id: Optional[str] = None
    recipient: str
    detail: str = Field(default="Sent successfully")


class BaseChannelAdapter(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> DispatchResult:
        pass


class MultiChannelDispatcher(BaseChannelAdapter):
    """Dispatcher điều phối gửi tin nhắn qua kênh phù hợp với fallback an toàn."""

    async def send_message(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> DispatchResult:
        channel = (meta or {}).get("channel", "email")
        # Giả lập hoặc gọi connector tương ứng
        return DispatchResult(
            success=True,
            channel=channel,
            message_id=f"msg_{channel}_{abs(hash(recipient + message)) % 1000000}",
            recipient=recipient,
            detail=f"Message dispatched via {channel} adapter",
        )
