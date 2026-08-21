from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator
from enum import Enum


class ModelRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: ModelRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPayload:
    trace_id: str
    agent_key: str
    model_name: str
    messages: List[Message]
    temperature: float = 0.2
    max_tokens: int = 4096
    tools_schema: Optional[List[Dict[str, Any]]] = None
    stop_sequences: Optional[List[str]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class ExecutionResult:
    trace_id: str
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = "stop"  # stop | length | tool_calls | error
    latency_ms: int = 0
    raw_response: Optional[Dict[str, Any]] = None


class BaseRuntimeAdapter(ABC):
    """Lớp trừu tượng định nghĩa Interface chuẩn cho mọi AI Provider trong COSA."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.config = config or {}

    @abstractmethod
    async def check_capability(self) -> Dict[str, Any]:
        """Kiểm tra runtime CLI/API có sẵn sàng, authenticated, hỗ trợ headless/tools."""
        pass

    @abstractmethod
    async def execute(self, payload: ExecutionPayload) -> ExecutionResult:
        """Thực thi một payload hoàn chỉnh và trả về kết quả chuẩn hóa ExecutionResult."""
        pass

    @abstractmethod
    async def stream(self, payload: ExecutionPayload) -> AsyncIterator[str]:
        """Thực thi streaming phản hồi từ Model."""
        pass

    @abstractmethod
    async def cancel(self, run_id: str) -> bool:
        """Hủy phiên thực thi."""
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Kiểm tra liveness/health của adapter."""
        pass

    @abstractmethod
    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Tính toán chi phí USD ước tính dựa trên model và số lượng token."""
        pass
