"""
COSA Agent Sessions Core Contracts
Quản lý vòng đời phiên làm việc, State Restoration, Fork & Replay (Structure.md Mục 19, 21, 22, 23).
"""
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Trạng thái vòng đời của một Session"""
    ACTIVE = "active"
    PAUSED_WAITING_APPROVAL = "paused_waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    FORKED = "forked"


class SessionMetadata(BaseModel):
    """Metadata phiên làm việc có cấu trúc"""
    id: str = Field(default_factory=lambda: f"ses_{uuid4().hex[:12]}")
    company_id: str
    user_id: str
    profile_id: str
    project_id: Optional[str] = None
    parent_session_id: Optional[str] = None
    fork_event_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionManagerInterface(ABC):
    """Giao diện quản lý phiên làm việc"""

    @abstractmethod
    async def create_session(
        self, 
        company_id: str, 
        user_id: str, 
        profile_id: str, 
        project_id: Optional[str] = None
    ) -> SessionMetadata:
        """Khởi tạo phiên làm việc mới"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Truy vấn thông tin phiên làm việc"""
        pass

    @abstractmethod
    async def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """Cập nhật trạng thái phiên"""
        pass

    @abstractmethod
    async def fork_session(self, parent_session_id: str, from_event_id: str) -> SessionMetadata:
        """Phân nhánh phiên làm việc (Structure.md Mục 22)"""
        pass

    @abstractmethod
    async def replay_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Tái dựng lại quá trình thực thi từ Event Log (an toàn, không chạy side-effects - Structure.md Mục 23)"""
        pass
