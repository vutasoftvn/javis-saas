"""
COSA Agent Profile Declarative Schema
Agent Profile chỉ định vai trò nghiệp vụ (CMO, CFO, Head of Sales...), không chứa runtime implementation (Structure.md Mục 8).
Công thức: Agent = Profile + Model + Context + Skills + Tools + Workflows + Permissions + Runtime
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentProfile(BaseModel):
    """Khai báo cấu hình vai trò Agent"""
    id: str = Field(..., description="Mã định danh vai trò: marketing, sales, finance, legal, research, cofounder")
    name: str = Field(..., description="Tên đầy đủ của vai trò")
    role: str = Field(..., description="Chức danh: CMO, CFO, Head of Sales, General Counsel, Co-founder")
    description: str = Field(..., description="Mô tả phạm vi trách nhiệm nghiệp vụ")
    skills: List[str] = Field(default_factory=list, description="Danh sách Skill IDs được phân công")
    tools: List[str] = Field(default_factory=list, description="Danh sách Tool IDs được cấp phép")
    workflows: List[str] = Field(default_factory=list, description="Danh sách Workflow IDs được quyền chạy")
    model_policy: Dict[str, str] = Field(
        default_factory=lambda: {"default": "reasoning"},
        description="Chính sách chọn loại Model: default, fast, reasoning, coding, vision"
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Danh sách quyền hệ thống: crm.read, crm.write, web.search, finance.read..."
    )
    permission_profile: str = Field(
        default="read_only",
        description="Canonical L0-L3 permission profile used for governed execution",
    )
    preferred_runtime: Optional[str] = Field(
        default=None,
        description="Explicit AgentRuntime name; None delegates runtime selection to policy",
    )
    delegation_provider: str = Field(
        default="agent_runtime",
        description="Delegation provider family for this profile",
    )
    is_system: bool = Field(default=True, description="True nếu là profile mặc định của hệ thống")


class AgentProfileRegistryInterface(ABC):
    """Giao diện quản lý danh mục Agent Profiles"""

    @abstractmethod
    async def get_profile(self, profile_id: str) -> Optional[AgentProfile]:
        """Truy vấn hồ sơ vai trò Agent"""
        pass

    @abstractmethod
    async def list_profiles(self) -> List[AgentProfile]:
        """Lấy danh sách toàn bộ hồ sơ vai trò"""
        pass

    @abstractmethod
    async def register_profile(self, profile: AgentProfile) -> bool:
        """Đăng ký hoặc cập nhật hồ sơ vai trò mới (chỉ Admin được phép)"""
        pass
