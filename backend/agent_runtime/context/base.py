"""
COSA Context Engine & Context Budget Core Contracts
Context không phải là toàn bộ database. Context nạp có chọn lọc theo Intent và Budget (Structure.md Mục 16, 17, 18).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContextScope(str, Enum):
    """Phạm vi ngữ cảnh kinh doanh (Structure.md Mục 17)"""
    COMPANY = "company"
    PROJECT = "project"
    STARTUP_STAGE = "startup_stage"
    CUSTOMER = "customer"
    CAMPAIGN = "campaign"
    TASK = "task"
    KNOWLEDGE = "knowledge"
    CONVERSATION = "conversation"


class ContextBudget(BaseModel):
    """Quản lý ngân sách Token cho ngữ cảnh (Structure.md Mục 18)"""
    max_context_tokens: int = Field(default=8000, description="Số token tối đa cho context nạp vào LLM")
    reserved_completion_tokens: int = Field(default=4000, description="Token dự phòng cho output")
    current_estimated_tokens: int = Field(default=0, description="Token ước tính hiện tại")


class ResolvedContext(BaseModel):
    """Dữ liệu ngữ cảnh đã qua chọn lọc, nén và kiểm tra ngân sách"""
    scopes: List[ContextScope] = Field(default_factory=list)
    system_instructions: str = ""
    domain_knowledge: str = ""
    operational_data: Dict[str, Any] = Field(default_factory=dict)
    total_estimated_tokens: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextEngineInterface(ABC):
    """Giao diện bộ máy nạp và tối ưu ngữ cảnh"""

    @abstractmethod
    async def resolve_context(
        self, 
        scopes: List[ContextScope], 
        params: Dict[str, Any], 
        budget: Optional[ContextBudget] = None
    ) -> ResolvedContext:
        """Nạp các ngữ cảnh cần thiết theo yêu cầu tường minh (Explicit Context Rule)"""
        pass

    @abstractmethod
    def compress_context(self, raw_data: str, max_tokens: int) -> str:
        """Nén ngữ cảnh khi vượt quá ngân sách token"""
        pass
