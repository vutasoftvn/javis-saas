from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import uuid


@dataclass(frozen=True)
class AgentIdentity:
    """Định danh của Agent trong ngữ cảnh phiên chạy."""
    workspace_id: int
    agent_id: int
    agent_key: str
    user_id: Optional[int] = None
    session_id: Optional[int] = None


@dataclass
class ExecutionContext:
    """Execution Context mang đầy đủ thông tin định danh, bảo mật và truy vết cho mọi tác vụ."""
    workspace_id: int
    user_id: Optional[int]
    session_id: Optional[int]
    agent_id: int
    agent_key: str
    roles: List[str] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity(
            workspace_id=self.workspace_id,
            agent_id=self.agent_id,
            agent_key=self.agent_key,
            user_id=self.user_id,
            session_id=self.session_id,
        )
