"""
COSA Workflows Core Contracts
Workflow mô tả quy trình nghiệp vụ nhiều bước tất định (Structure.md Mục 13).
Không viết quy trình nghiệp vụ dài bên trong System Prompt.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowStepType(str, Enum):
    """Phân loại bước trong quy trình Workflow"""
    SKILL = "skill"                     # Bước áp dụng kiến thức Skill
    TOOL = "tool"                       # Bước gọi một Tool thực thi
    PARALLEL_TOOLS = "parallel_tools"   # Bước chạy đồng thời nhiều Tools
    HUMAN_APPROVAL = "human_approval"   # Bước dừng chờ Founder phê duyệt
    SUBAGENT = "subagent"               # Bước phân phối cho Subagent thực thi


class WorkflowStep(BaseModel):
    """Định nghĩa một bước thực thi trong Workflow"""
    id: str = Field(..., description="Mã định danh duy nhất của bước")
    name: str = Field(default="", description="Tên hiển thị của bước")
    type: WorkflowStepType
    target: str = Field(..., description="Mã Skill / Tool / Subagent tương ứng")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tham số truyền vào bước")
    parallel: bool = Field(default=False, description="Chạy song song với bước kế tiếp")
    timeout_seconds: int = Field(default=300, description="Thời gian tối đa cho bước")


class WorkflowDefinition(BaseModel):
    """Khai báo cấu hình của một Workflow hoàn chỉnh"""
    id: str = Field(..., description="Mã định danh duy nhất của Workflow (ví dụ: lead-generation, market-analysis)")
    name: str = Field(..., description="Tên quy trình")
    domain: str = Field(..., description="Lĩnh vực: startup, marketing, sales, coding, management")
    description: str = Field(default="", description="Mô tả mục tiêu của quy trình")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Danh sách các bước tuần tự/song song")
    version: str = Field(default="1.0.0", description="Phiên bản của Workflow")


class BaseWorkflow(ABC):
    """Giao diện trừu tượng cơ sở cho Workflow Runner"""
    definition: WorkflowDefinition

    @abstractmethod
    async def validate_flow(self) -> bool:
        """Kiểm tra tính toàn vẹn của chuỗi các bước trong Workflow"""
        pass

    @abstractmethod
    async def execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Thực thi một bước đơn lẻ và thu thập kết quả"""
        pass
