"""
COSA Intent Router Core Contracts
Intent Router là chốt chặn quan trọng giải quyết lỗi tự kích hoạt context khi người dùng chỉ chào hỏi (Structure.md Mục 15 & CLAUDE.md Mục 9).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """Phân loại nhóm ý định của người dùng"""
    GREETING = "conversation.greeting"                 # Lời chào hỏi thông thường ("chào", "hello", "hi")
    GENERAL_CHAT = "conversation.general"              # Trò chuyện trao đổi chung không liên quan dự án cụ thể
    BUSINESS_QUERY = "business.query"                  # Truy vấn dữ liệu kinh doanh cụ thể
    STRATEGY_ADVICE = "business.strategy_advice"       # Xin tư vấn chiến lược / Startup stage
    WORKFLOW_TRIGGER = "workflow.trigger"              # Yêu cầu kích hoạt một workflow nhiều bước
    CODING_TASK = "coding.task"                        # Yêu cầu lập trình / refactor / fix bug
    UNKNOWN = "intent.unknown"                         # Chưa xác định rõ ý định


class IntentClassificationResult(BaseModel):
    """Kết quả phân loại ý định tất định"""
    category: IntentCategory
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    requires_project_context: bool = Field(
        default=False, 
        description="True nếu BẮT BUỘC phải nạp context dự án (CLAUDE §9: Greeting luôn là False)"
    )
    target_project_id: Optional[str] = None
    suggested_skills: List[str] = Field(default_factory=list)
    suggested_tools: List[str] = Field(default_factory=list)
    suggested_workflow_id: Optional[str] = None
    extracted_parameters: Dict[str, Any] = Field(default_factory=dict)


class IntentRouterInterface(ABC):
    """Giao diện phân loại ý định người dùng độc lập"""

    @abstractmethod
    async def route_intent(
        self, 
        user_message: str, 
        current_session_context: Optional[Dict[str, Any]] = None
    ) -> IntentClassificationResult:
        """Phân loại ý định từ tin nhắn người dùng mà KHÔNG tự tiện quét database"""
        pass
