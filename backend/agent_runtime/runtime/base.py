"""
COSA Agent Runtime Base Interface
COSA chỉ duy trì DUY NHẤT 01 Agent Runtime Interface (CLAUDE.md Mục 2 & Structure.md Mục 2).
Các vai trò Agent khác nhau được compose từ Profile, Skills, Tools, Workflows và Permissions.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.events.base import AgentEvent
from agent.profiles.schema import AgentProfile


class AgentRuntimeState(BaseModel):
    """Trạng thái nội tại của phiên thực thi Agent Runtime"""
    session_id: str
    profile: AgentProfile
    turn_count: int = 0
    is_paused: bool = False
    waiting_for_approval_event_id: Optional[str] = None
    accumulated_context: Dict[str, Any] = Field(default_factory=dict)
    active_subagents: List[str] = Field(default_factory=list)


class BaseAgentRuntime(ABC):
    """Giao diện trừu tượng duy nhất cho COSA Agent Runtime"""

    @abstractmethod
    async def start_session(
        self, 
        session_id: str, 
        profile: AgentProfile, 
        initial_context: Dict[str, Any]
    ) -> AgentRuntimeState:
        """Khởi tạo phiên làm việc của Agent"""
        pass

    @abstractmethod
    async def process_turn(
        self, 
        state: AgentRuntimeState, 
        user_message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        """Thực thi một vòng tương tác (Turn) và stream các AgentEvent về client"""
        pass

    @abstractmethod
    async def pause_for_approval(self, state: AgentRuntimeState, reason: str) -> bool:
        """Tạm dừng runtime khi phát hiện tác vụ HIGH/CRITICAL cần phê duyệt"""
        pass

    @abstractmethod
    async def resume_with_approval(
        self, 
        state: AgentRuntimeState, 
        approval_event: AgentEvent
    ) -> AsyncGenerator[AgentEvent, None]:
        """Tiếp tục vòng lặp sau khi Founder duyệt tác vụ"""
        pass
